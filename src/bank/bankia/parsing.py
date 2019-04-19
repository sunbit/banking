from datetime import datetime
from itertools import chain

import re

from datatypes import TransactionType, TransactionDirection, ParsedBankAccountTransaction, ParsedCreditCardTransaction
from datatypes import Account, Bank, Card, ModifiedFlags, UnknownSubject, UnknownWallet
from common.parsing import extract_literals, extract_keywords, get_nested_item


import datatypes

KEYWORD_FIELDS = [
    'conceptoMovimiento.descripcionConcepto',
    'referencias.0300.descripcion',
    'referencias.0400.descripcion',
    'referencias.0440.descripcion',
    'referencias.0500.descripcion',
    'referencias.0503.descripcion'
]


def get_type(transaction_code, transaction_direction):
    """
        Determine the transaction type, from a bank prespective
        no
    """

    PAYCHECK = ['105']
    TRANSFER_CODES = ['163', '203', '603', '673']
    BANK_COMISSION_CODES = ['205', '275', '578']
    RECEIPT_CODES = ['253', '257', '261']
    MORTAGE_RECEIPT = ['255']
    CREDIT_CARD_INVOICE = ['274', '400']
    PURCHASE = ['800', '410', '226', '127']

    if transaction_code in PAYCHECK:
        return {
            TransactionDirection.CHARGE: None,
            TransactionDirection.INCOME: TransactionType.RECEIVED_TRANSFER
        }.get(transaction_direction)

    if transaction_code in BANK_COMISSION_CODES:
        return {
            TransactionDirection.CHARGE: TransactionType.BANK_COMISSION,
            TransactionDirection.INCOME: TransactionType.BANK_COMISSION_RETURN
        }.get(transaction_direction)

    if transaction_code in RECEIPT_CODES:
        return {
            TransactionDirection.CHARGE: TransactionType.DOMICILED_RECEIPT,
            TransactionDirection.INCOME: None
        }.get(transaction_direction)

    # This is indeed a special case of domicilied receipt, where the destination is the Bank itself.
    if transaction_code in MORTAGE_RECEIPT:
        return {
            TransactionDirection.CHARGE: TransactionType.MORTAGE_RECEIPT,
            TransactionDirection.INCOME: None
        }.get(transaction_direction)

    if transaction_code in CREDIT_CARD_INVOICE:
        return {
            TransactionDirection.CHARGE: TransactionType.CREDIT_CARD_INVOICE,
            TransactionDirection.INCOME: TransactionType.CREDIT_CARD_INVOICE_PAYMENT
        }.get(transaction_direction)

    if transaction_code in PURCHASE:
        return {
            TransactionDirection.CHARGE: TransactionType.PURCHASE,
            TransactionDirection.INCOME: TransactionType.PURCHASE_RETURN
        }.get(transaction_direction)

    if transaction_code in TRANSFER_CODES:
        return {
            TransactionDirection.CHARGE: TransactionType.ISSUED_TRANSFER,
            TransactionDirection.INCOME: TransactionType.RECEIVED_TRANSFER
        }.get(transaction_direction)

    return TransactionType.UNKNOWN


def get_source(details, transaction_type):

    def safe_issuer(subject):
        return UnknownSubject() if subject is None else datatypes.Issuer(subject)

    if transaction_type is TransactionType.ATM_WITHDRAWAL:
        return details['account']
    if transaction_type is TransactionType.ISSUED_TRANSFER:
        return details['account']
    if transaction_type is TransactionType.CREDIT_CARD_INVOICE:
        return details['account']
    if transaction_type is TransactionType.CREDIT_CARD_INVOICE_PAYMENT:
        return details['account']
    if transaction_type is TransactionType.DOMICILED_RECEIPT:
        return details['account']
    if transaction_type is TransactionType.MORTAGE_RECEIPT:
        return details['account']
    if transaction_type is TransactionType.BANK_COMISSION:
        return details['account']
    if transaction_type is TransactionType.MORTAGE_RECEIPT:
        return details['account']
    if transaction_type is TransactionType.PURCHASE:
        return details['account']
    if transaction_type is TransactionType.BANK_COMISSION:
        return details['account']
    if transaction_type is TransactionType.BANK_COMISSION_RETURN:
        return details['bank']
    if transaction_type is TransactionType.RETURN_DEPOSIT:
        return safe_issuer(details['creditor_name'])
    if transaction_type is TransactionType.RECEIVED_TRANSFER:
        return safe_issuer(details['issuer_name'])
    if transaction_type is TransactionType.PURCHASE_RETURN:
        return safe_issuer(details['shop_name'])


def get_destination(details, transaction_type):

    def safe_recipient(subject):
        return UnknownSubject() if subject is None else datatypes.Recipient(subject)

    if transaction_type is TransactionType.RECEIVED_TRANSFER:
        return details['account']
    if transaction_type is TransactionType.BANK_COMISSION_RETURN:
        return details['account']
    if transaction_type is TransactionType.RETURN_DEPOSIT:
        return details['account']
    if transaction_type is TransactionType.PURCHASE_RETURN:
        return details['account']
    if transaction_type is TransactionType.ATM_WITHDRAWAL:
        return UnknownWallet()
    if transaction_type is TransactionType.CREDIT_CARD_INVOICE:
        return details['bank']
    if transaction_type is TransactionType.MORTAGE_RECEIPT:
        return details['bank']
    if transaction_type is TransactionType.BANK_COMISSION:
        return details['bank']
    if transaction_type is TransactionType.CREDIT_CARD_INVOICE_PAYMENT:
        return details['bank']
    if transaction_type is TransactionType.ISSUED_TRANSFER:
        return safe_recipient(details['beneficiary'])
    if transaction_type is TransactionType.DOMICILED_RECEIPT:
        return safe_recipient(details['creditor_name'])
    if transaction_type is TransactionType.PURCHASE:
        return safe_recipient(details['shop_name'])


def references_by_code(transaction):
    def fields(reference):
        result = dict(reference)
        result.pop('codigoPlantilla')
        return result
    return {
        reference['codigoPlantilla']: fields(reference)
        for reference in transaction['referencias']
        if reference["codigoPlantilla"]
    }


def decode_numeric_value(importe):
    if 'importeConSigno' in importe:
        return importe['importeConSigno'] / (10.0 ** importe['numeroDecimales'])
    elif 'importe' in importe:
        return importe['importe'] / (10.0 ** importe['decimales'])


def get_account_transaction_details(transaction, transaction_type):
    details = {}

    def set_detail(fieldname, xpath_string_or_list, fmt=None, default=None):
        nonlocal details

        xpath_list = xpath_string_or_list if isinstance(xpath_string_or_list, list) else [xpath_string_or_list]

        for xpath in xpath_list:
            value = get_nested_item(transaction, xpath)
            formatted_value = None if value is None else (value if fmt is None else fmt(value))
            if formatted_value is not None:
                details[fieldname] = formatted_value
                return

        details[fieldname] = default

    def title(str):
        return str.title()

    def capture(regex, group):
        def wrap(value):
            match = re.search(regex, value)
            return match.groups()[0] if match else None
        return wrap

    if transaction_type is TransactionType.PURCHASE:
        set_detail('shop_name', 'referencias.0440.descripcion', fmt=title)
        set_detail('card_number', 'referencias.0240.descripcion')

    if transaction_type is TransactionType.PURCHASE_RETURN:
        set_detail('shop_name', 'referencias.0440.descripcion', fmt=title)
        set_detail('card_number', 'referencias.0240.descripcion')

    # if transaction_type is TransactionType.ATM_WITHDRAWAL:
    #     set_detail('card_number', '')
    #     set_detail('atm_name', '')

    if transaction_type is TransactionType.ISSUED_TRANSFER:
        set_detail('beneficiary', ['beneficiarioOEmisor', 'referencias.0500.descripcion'], fmt=title)
        set_detail('concept', 'referencias.0300.descripcion')

    if transaction_type is TransactionType.RECEIVED_TRANSFER:
        set_detail('issuer_name', 'beneficiarioOEmisor')
        set_detail('concept', 'referencias.0300.descripcion', fmt=title)

    if transaction_type is TransactionType.DOMICILED_RECEIPT:
        set_detail('creditor_name', 'referencias.0400.descripcion')
        set_detail('concept', 'referencias.0300.descripcion', fmt=title)
        set_detail('drawee', 'referencias.0503.descripcion', fmt=title)

    return details


def get_card_transaction_details(transaction, transaction_type):

    details = {}

    def set_detail(fieldname, xpath_string_or_list, fmt=None, default=None):
        nonlocal details

        xpath_list = xpath_string_or_list if isinstance(xpath_string_or_list, list) else [xpath_string_or_list]

        for xpath in xpath_list:
            value = get_nested_item(transaction, xpath)
            formatted_value = None if value is None else (value if fmt is None else fmt(value))
            if formatted_value is not None:
                details[fieldname] = formatted_value
                return

        details[fieldname] = default

    def title(str):
        return str.title()

    if transaction_type is TransactionType.PURCHASE:
        set_detail('shop_name', 'lugarMovimiento', fmt=title)

    if transaction_type is TransactionType.PURCHASE_RETURN:
        set_detail('shop_name', 'lugarMovimiento', fmt=title)

    return details


def get_card(account_config, card_number):

    if card_number is None:
        return None

    for card in account_config.cards.values():
        # card is masked with **** except of the 4 first and last digits so we'll match
        # against those asterisks converted to digits
        match_card_regex = re.sub(r'\*+', r'\\d+', card_number)
        if re.match(match_card_regex, card.number):
            return Card.from_config(card)

    # Possibly an old card no longer registered
    return Card('Unknown card', card_number)


def get_comment(details, transaction_type):
    if transaction_type in [TransactionType.ISSUED_TRANSFER, TransactionType.RECEIVED_TRANSFER]:
        return details['concept']


def decode_date(date, hour=None):
    year, month, day = date.split('T')[0].split('-')
    hour, minute, second = (0, 0, 0) if hour is None else hour.split(':')
    return datetime(*map(int, [year, month, day, hour, minute, second]))


def parse_account_transaction(bank_config, account_config, transaction):
    amount = decode_numeric_value(transaction['importe'])
    transaction_code = transaction['codigoMovimiento']
    transaction['referencias'] = references_by_code(transaction)
    transaction_direction = TransactionDirection.CHARGE if amount < 0 else TransactionDirection.INCOME
    transaction_type = get_type(transaction_code, transaction_direction)

    details = get_account_transaction_details(transaction, transaction_type)
    details['account'] = Account.from_config(account_config)
    details['bank'] = Bank.from_config(bank_config)

    card_number = details.pop('card_number', None)
    card_used = get_card(account_config, card_number)

    keywords = extract_keywords(
        chain(
            extract_literals(transaction, KEYWORD_FIELDS),
            filter(lambda value: isinstance(value, str), details.values())
        )
    )

    comment = get_comment(details, transaction_type)

    source = get_source(details, transaction_type)
    destination = get_destination(details, transaction_type)
    del details['bank']

    return ParsedBankAccountTransaction(
        transaction_id=None,
        currency=transaction['importe']['moneda']['nombreCorto'],
        amount=amount,
        balance=decode_numeric_value(transaction['saldoPosterior']),
        value_date=decode_date(transaction['fechaValor']['valor'], ),
        transaction_date=decode_date(transaction['fechaMovimiento']['valor']),
        type=transaction_type,
        source=source,
        destination=destination,
        account=details.pop('account'),
        card=card_used,
        details=details,
        keywords=keywords,
        comment=comment if comment is not None else '',
        flags=ModifiedFlags()
    )


def parse_credit_card_transaction(bank_config, account_config, card_config, transaction):

    amount = decode_numeric_value(transaction['importeMovimiento'])
    transaction_code = transaction['claveMovimiento']
    transaction_direction = TransactionDirection.CHARGE if amount < 0 else TransactionDirection.INCOME
    transaction_type = get_type(transaction_code, transaction_direction)

    details = get_card_transaction_details(transaction, transaction_type)
    details['account'] = Account.from_config(account_config)
    details['bank'] = Bank.from_config(bank_config)

    # As we are processing a concrete card, and transaction doesn't have this
    # information, we set it to be able to process all transactions equally
    card_used = Card.from_config(card_config)

    keywords = extract_keywords(
        chain(
            extract_literals(transaction, KEYWORD_FIELDS),
            filter(lambda value: isinstance(value, str), details.values())
        )
    )

    comment = get_comment(details, transaction_type)

    source = get_source(details, transaction_type)
    destination = get_destination(details, transaction_type)
    del details['bank']
    del details['account']

    return ParsedCreditCardTransaction(
        transaction_id=transaction['identificadorMovimiento'],
        currency=transaction['importeMovimiento']['nombreMoneda'],
        amount=amount,
        value_date=decode_date(transaction['fechaMovimiento']['valor'], transaction['horaMovimiento']['valor']),
        transaction_date=decode_date(transaction['fechaMovimiento']['valor'], transaction['horaMovimiento']['valor']),
        type=transaction_type,
        source=source,
        destination=destination,
        card=card_used,
        details=details,
        keywords=keywords,
        comment=comment if comment is not None else '',
        flags=ModifiedFlags()
    )
