from itertools import chain

import json
import time
import re

from datatypes import TransactionType, TransactionDirection, ParsedMovement, DetailSpec, Account, Bank, Card, ModifiedFlags
from common.parsing import extract_literals, extract_keywords, extract_details, get_nested_item


import datatypes

DETAIL_SPECS = [
    DetailSpec('transaction_type', 'codigoMovimiento'),
    DetailSpec('transaction_type', 'claveMovimiento'),
    DetailSpec('purchase_shop_name', 'referencias.0440.descripcion'),
    DetailSpec('purchase_shop_name', 'lugarMovimiento'),
    DetailSpec('librado', 'referencias.0503.descripcion'),
    DetailSpec('concepto', 'referencias.0300.descripcion'),
    DetailSpec('beneficiarioOEmisor', 'beneficiarioOEmisor'),
    DetailSpec('beneficiarioOEmisor', 'referencias.0500.descripcion'),
    DetailSpec('issuer', 'referencias.0400.descripcion'),
    DetailSpec('is_transfer', 'indicadorTransferencia'),
    DetailSpec('purchase_card_number', 'referencias.0240.descripcion'),

]

LITERAL_FIELDS = [
    'beneficiarioOEmisor',
    'conceptoMovimiento.descripcionConcepto',
    'referencias.0300.descripcion',
    'referencias.0400.descripcion',
    'referencias.0440.descripcion',
    'referencias.0500.descripcion',
    'referencias.0503.descripcion'
]


def get_type(details, movement_direction):
    """
        Determine the movement type, from a bank prespective
        no
    """

    movement_code = details['transaction_type']

    PAYCHECK = ['105']
    TRANSFER_CODES = ['163', '203', '603', '673']
    BANK_COMISSION_CODES = ['205', '275', '578']
    RECEIPT_CODES = ['253', '257', '261']
    MORTAGE_RECEIPT = ['255']
    CREDIT_CARD_INVOICE = ['274', '400']
    PURCHASE = ['800', '410', '226']

    if movement_code in PAYCHECK:
        return {
            TransactionDirection.CHARGE: None,
            TransactionDirection.INCOME: TransactionType.RECEIVED_TRANSFER
        }.get(movement_direction)

    if movement_code in BANK_COMISSION_CODES:
        return {
            TransactionDirection.CHARGE: TransactionType.BANK_COMISSION,
            TransactionDirection.INCOME: TransactionType.BANK_COMISSION_RETURN
        }.get(movement_direction)

    if movement_code in RECEIPT_CODES:
        return {
            TransactionDirection.CHARGE: TransactionType.DOMICILED_RECEIPT,
            TransactionDirection.INCOME: None
        }.get(movement_direction)

    # This is indeed a special case of domicilied receipt, where the destination is the Bank itself.
    if movement_code in MORTAGE_RECEIPT:
        return {
            TransactionDirection.CHARGE: TransactionType.MORTAGE_RECEIPT,
            TransactionDirection.INCOME: None
        }.get(movement_direction)

    if movement_code in CREDIT_CARD_INVOICE:
        return {
            TransactionDirection.CHARGE: TransactionType.CREDIT_CARD_INVOICE,
            TransactionDirection.INCOME: TransactionType.CREDIT_CARD_INVOICE_PAYMENT
        }.get(movement_direction)

    if movement_code in PURCHASE:
        return {
            TransactionDirection.CHARGE: TransactionType.PURCHASE,
            TransactionDirection.INCOME: TransactionType.PURCHASE_RETURN
        }.get(movement_direction)

    if movement_code in TRANSFER_CODES:
        return {
            TransactionDirection.CHARGE: TransactionType.ISSUED_TRANSFER,
            TransactionDirection.INCOME: TransactionType.RECEIVED_TRANSFER
        }.get(movement_direction)

    return TransactionType.UNKNOWN


def get_source(details, movement_type):
    if movement_type is TransactionType.RECEIVED_TRANSFER:
        beneficiarioOEmisor = details.get('beneficiarioOEmisor')
        ordenante = details.get('issuer')
        return datatypes.Issuer((beneficiarioOEmisor if beneficiarioOEmisor is not None else ordenante).title())
    if movement_type is TransactionType.ISSUED_TRANSFER:
        return details['account']
    if movement_type is TransactionType.CREDIT_CARD_INVOICE:
        return details['account']
    if movement_type is TransactionType.DOMICILED_RECEIPT:
        return details['account']
    if movement_type is TransactionType.MORTAGE_RECEIPT:
        return details['account']
    if movement_type is TransactionType.BANK_COMISSION:
        return details['account']
    if movement_type is TransactionType.BANK_COMISSION_RETURN:
        return details['bank']
    if movement_type is TransactionType.PURCHASE:
        return details['card']
    if movement_type is TransactionType.PURCHASE_RETURN:
        return datatypes.Recipient(details['purchase_shop_name'].title())
    if movement_type is TransactionType.CREDIT_CARD_INVOICE_PAYMENT:
        return details['account']


def get_destination(details, movement_type):
    if movement_type is TransactionType.RECEIVED_TRANSFER:
        return details['account']
    if movement_type is TransactionType.ISSUED_TRANSFER:
        return datatypes.Recipient(details['beneficiarioOEmisor'].title())
    if movement_type is TransactionType.CREDIT_CARD_INVOICE:
        return details['bank']
    if movement_type is TransactionType.MORTAGE_RECEIPT:
        return details['bank']
    if movement_type is TransactionType.BANK_COMISSION:
        return details['bank']
    if movement_type is TransactionType.BANK_COMISSION_RETURN:
        return details['account']
    if movement_type is TransactionType.DOMICILED_RECEIPT:
        return datatypes.Recipient(details['issuer'].title())
    if movement_type is TransactionType.PURCHASE:
        return datatypes.Recipient(details['purchase_shop_name'].title())
    if movement_type is TransactionType.PURCHASE_RETURN:
        return details['card']
    if movement_type is TransactionType.CREDIT_CARD_INVOICE_PAYMENT:
        return details['bank']


def get_comment(details, movement, movement_type):
    if movement_type in [TransactionType.ISSUED_TRANSFER, TransactionType.RECEIVED_TRANSFER]:
        return get_nested_item(movement, 'referencias.0300.descripcion', default='').title()
    return ''


def references_by_code(movement):
    def fields(reference):
        result = dict(reference)
        result.pop('codigoPlantilla')
        return result
    return {
        reference['codigoPlantilla']: fields(reference)
        for reference in movement['referencias']
        if reference["codigoPlantilla"]
    }


def decode_numeric_value(importe):
    if 'importeConSigno' in importe:
        return importe['importeConSigno'] / (10.0 ** importe['numeroDecimales'])
    elif 'importe' in importe:
        return importe['importe'] / (10.0 ** importe['decimales'])


def get_details(movement, bank_config, account_config):
    details = extract_details(movement, DETAIL_SPECS)

    details['account'] = Account.from_config(account_config)
    details['bank'] = Bank.from_config(bank_config)

    if 'purchase_card_number' in details:
        for card in account_config.cards:
            # card is masked with **** except of the 4 first and last digits so we'll match
            # against those asterisks converted to digits
            match_card_regex = re.sub(r'\*+', r'\\d+', details['purchase_card_number'])
            if re.match(match_card_regex, card.number):
                details['card'] = Card.from_config(card)
                break
        if 'card' not in details:
            # Possibly an old card no longer registered
            details['card'] = Card('Unknown card', details['purchase_card_number'])

    return details


def create_id(movement, movement_type):
    year, month, day = movement['fechaValor']['valor'].split('-')
    return '{year}{month}{day}#{type}#{balance}#{amount}'.format(
        year=year, month=month, day=day,
        type=movement_type.name,
        amount=str(decode_numeric_value(movement['importe'])),
        balance=str(decode_numeric_value(movement['saldoPosterior']))
    )


def parse_account_movement(bank_config, account_config, movement):
    movement['referencias'] = references_by_code(movement)

    amount = decode_numeric_value(movement['importe'])
    movement_direction = TransactionDirection.CHARGE if amount < 0 else TransactionDirection.INCOME

    details = get_details(movement, bank_config, account_config)
    movement_type = get_type(details, movement_direction)

    return ParsedMovement(
        transaction_id=None,
        currency=movement['importe']['moneda']['nombreCorto'],
        amount=amount,
        balance=decode_numeric_value(movement['saldoPosterior']),
        value_date=movement['fechaValor']['valor'],
        transaction_date=movement['fechaMovimiento']['valor'],
        type=movement_type,
        source=get_source(details, movement_type),
        destination=get_destination(details, movement_type),
        details=details,
        keywords=extract_keywords(extract_literals(movement, LITERAL_FIELDS)),
        comment=get_comment(details, movement, movement_type),
        flags=ModifiedFlags()
    )


def parse_credit_card_movement(bank_config, account_config, card_config, movement):

    amount = decode_numeric_value(movement['importeMovimiento'])
    movement_direction = TransactionDirection.CHARGE if amount < 0 else TransactionDirection.INCOME

    details = get_details(movement, bank_config, account_config)
    # As we are processing a concrete card, and movement doesn't have this
    # information, we set it to be able to process all movements equally
    details['card'] = Card.from_config(card_config)

    movement_type = get_type(details, movement_direction)

    return ParsedMovement(
        transaction_id=None,
        currency=movement['importeMovimiento']['nombreMoneda'],
        amount=amount,
        balance=None,
        value_date=movement['fechaMovimiento']['valor'],
        transaction_date=movement['fechaMovimiento']['valor'],
        type=movement_type,
        source=get_source(details, movement_type),
        destination=get_destination(details, movement_type),
        details=extract_details(movement, DETAIL_SPECS),
        keywords=extract_keywords(extract_literals(movement, LITERAL_FIELDS)),
        comment=get_comment(details, movement, movement_type),
        flags=ModifiedFlags()
    )
