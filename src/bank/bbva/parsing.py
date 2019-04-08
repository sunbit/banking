from datatypes import TransactionType, TransactionDirection, ParsedMovement, DetailSpec, ModifiedFlags
from datatypes import Bank, Account, Card
from common.parsing import extract_literals, extract_keywords, extract_details

import datatypes


DETAIL_SPECS = [
    DetailSpec('transaction_id', 'id'),
    DetailSpec('transaction_type', 'scheme.subCategory.id'),
    DetailSpec('sender_account_number', 'wireTransactionDetail.sender.account.formats.ccc'),
    DetailSpec('sender_name', 'wireTransactionDetail.sender.person.name'),
    DetailSpec('receiver_name', 'wireTransactionDetail.sender.person.name'),
    DetailSpec('purchase_shop_name', 'shop.name'),
    DetailSpec('purchase_shop_name', 'cardTransactionDetail.shop.name'),
    DetailSpec('purchase_shop_name', 'humanConceptName'),
    DetailSpec('purchase_card_number', 'origin.panCode'),
    DetailSpec('purchase_card_number', 'origin.detailSourceKey', regex=r'(\d+)'),
    DetailSpec('creditor_name', 'billTransactionDetail.creditor.name'),
    DetailSpec('creditor_name', 'humanConceptName'),
    DetailSpec('description', 'humanExtendedConceptName'),
    DetailSpec('receipt_concept', 'billTransactionDetail.extendedBillConceptName'),
    DetailSpec('receipt_concept', 'extendedName'),
    DetailSpec('return_reason', 'billTransactionDetail.extendedIntentionName')

]

LITERAL_FIELDS = [
    'name',
    'humanConceptName',
    'concept.name',
    'extendedName',
    'humanExtendedConceptName',
    'cardTransactionDetail.concept.name',
    'cardTransactionDetail.concept.shop.name',
    'wireTransactionDetail.sender.person.name'
]


def get_type(details, movement_direction):
    """
        ipdb> pp(dict(set([(b['id'], b['name']) for b in [a['scheme']['subCategory'] for a in raw_movements]])))

        {'0017': 'PAGO CON TARJETA',
         '0114': 'INGRESO POR NOMINA O PENSION',
         '0022': 'DISPOSIC. DE EFECTIVO CAJERO/OFICINA',
         '0054': 'OTROS',
         '0058': 'PAGO DE ADEUDO DIRECTO SEPA',
         '0060': 'RECIBO TARJETA CRÉDITO',
         '0140': 'ABONO'
         '0149': 'TRANSFERENCIA RECIBIDA'
         '0064': 'TRANSFERENCIA REALIZADA'}
    """
    # If we need more detail use this:
    # type_code = movement['concept']['id']

    type_code = details['transaction_type']

    PAYCHECK = ['0114']
    PURCHASE = ['0017']
    TRANSFER = ['0149', '0064']
    WITHDRAWAL = ['0054', '0022']
    DOMICILED_RECEIPT = ['0058', '0140']
    CREDIT_CARD_INVOICE = ['0060']

    if type_code in PURCHASE:
        return {
            TransactionDirection.CHARGE: TransactionType.PURCHASE,
            TransactionDirection.INCOME: None
        }.get(movement_direction)

    if type_code in TRANSFER:
        return {
            TransactionDirection.CHARGE: TransactionType.ISSUED_TRANSFER,
            TransactionDirection.INCOME: TransactionType.RECEIVED_TRANSFER
        }.get(movement_direction)

    if type_code in PAYCHECK:
        return {
            TransactionDirection.CHARGE: None,
            TransactionDirection.INCOME: TransactionType.RECEIVED_TRANSFER
        }.get(movement_direction)

    if type_code in WITHDRAWAL:
        return {
            TransactionDirection.CHARGE: TransactionType.ATM_WITHDRAWAL,
            TransactionDirection.INCOME: None
        }.get(movement_direction)

    if type_code in DOMICILED_RECEIPT:
        return {
            TransactionDirection.CHARGE: TransactionType.DOMICILED_RECEIPT,
            TransactionDirection.INCOME: TransactionType.RETURN_DEPOSIT
        }.get(movement_direction)

    if type_code in CREDIT_CARD_INVOICE:
        return {
            TransactionDirection.CHARGE: TransactionType.CREDIT_CARD_INVOICE,
            TransactionDirection.INCOME: None
        }.get(movement_direction)


def get_source(details, movement_type):
    if movement_type is TransactionType.RECEIVED_TRANSFER:
        return datatypes.Issuer(details['sender_name'].title())
    if movement_type is TransactionType.ATM_WITHDRAWAL:
        return details['account']
    if movement_type is TransactionType.ISSUED_TRANSFER:
        return details['account']
    if movement_type is TransactionType.CREDIT_CARD_INVOICE:
        return details['account']
    if movement_type is TransactionType.DOMICILED_RECEIPT:
        return details['account']
    if movement_type is TransactionType.RETURN_DEPOSIT:
        return datatypes.Issuer(details['creditor_name'].title())
    if movement_type is TransactionType.MORTAGE_RECEIPT:
        return details['account']
    if movement_type is TransactionType.BANK_COMISSION:
        return details['account']
    if movement_type is TransactionType.BANK_COMISSION_RETURN:
        return details['bank']
    if movement_type is TransactionType.PURCHASE:
        return details['card']


def get_destination(details, movement_type):
    if movement_type is TransactionType.RECEIVED_TRANSFER:
        return details['account']
    if movement_type is TransactionType.ATM_WITHDRAWAL:
        return details['card']
    if movement_type is TransactionType.ISSUED_TRANSFER:
        return datatypes.Recipient(details['receiver_name'].title())
    if movement_type is TransactionType.CREDIT_CARD_INVOICE:
        return details['bank']
    if movement_type is TransactionType.MORTAGE_RECEIPT:
        return details['bank']
    if movement_type is TransactionType.BANK_COMISSION:
        return details['bank']
    if movement_type is TransactionType.BANK_COMISSION_RETURN:
        return details['account']
    if movement_type is TransactionType.DOMICILED_RECEIPT:
        return datatypes.Recipient(details['creditor_name'].title())
    if movement_type is TransactionType.RETURN_DEPOSIT:
        return details['account']
    if movement_type is TransactionType.PURCHASE:
        return datatypes.Recipient(details['purchase_shop_name'].title())


def get_comments(details, movement_type):
    if movement_type is TransactionType.RECEIVED_TRANSFER:
        return details['description'].title()
    if movement_type is TransactionType.ISSUED_TRANSFER:
        return details['description'].title()
    if movement_type is TransactionType.RETURN_DEPOSIT:
        return details['return_reason'].title()
    if movement_type is TransactionType.DOMICILED_RECEIPT:
        concept = details.get('receipt_concept')
        if concept is not None:
            return


def get_details(movement, bank_config, account_config):
    details = extract_details(movement, DETAIL_SPECS)

    details['account'] = Account.from_config(account_config)
    details['bank'] = Bank.from_config(bank_config)

    if 'purchase_card_number' in details:
        for card in account_config.cards:
            if card.number == details['purchase_card_number']:
                details['card'] = Card.from_config(card)
                break
        if 'card' not in details:
            # Possibly an old card no longer registered
            details['card'] = Card('Unknown card', details['purchase_card_number'])

    return details


def decode_date(date):
    return date.split('T')[0]


def parse_account_movement(bank_config, account_config, movement):
    amount = movement['amount']['amount']
    movement_direction = TransactionDirection.CHARGE if amount < 0 else TransactionDirection.INCOME

    details = get_details(movement, bank_config, account_config)
    movement_type = get_type(details, movement_direction)

    return ParsedMovement(
        transaction_id=movement['id'],
        type=movement_type,
        currency=movement['amount']['currency']['code'],
        amount=amount,
        balance=movement['balance']['availableBalance']['amount'],
        value_date=decode_date(movement['valueDate']),
        transaction_date=decode_date(movement['transactionDate']),
        source=get_source(details, movement_type),
        destination=get_destination(details, movement_type),
        details=details,
        keywords=extract_keywords(extract_literals(movement, LITERAL_FIELDS)),
        comment=get_comments(details, movement_type),
        flags=ModifiedFlags()
    )


def parse_credit_card_movement(bank_config, account_config, card_config, movement):
    amount = movement['amount']['amount']
    movement_direction = TransactionDirection.CHARGE if amount < 0 else TransactionDirection.INCOME

    details = get_details(movement, bank_config, account_config)

    # As we are processing a concrete card, and movement doesn't have this
    # information, we set it to be able to process all movements equally
    details['card'] = Card.from_config(card_config)

    #Until we don't have more information, we assume everything card related is
    # a purchase
    details['transaction_type'] = "0017"

    movement_type = get_type(details, movement_direction)

    return ParsedMovement(
        transaction_id=movement['id'],
        type=movement_type,
        currency=movement['amount']['currency']['code'],
        amount=amount,
        balance=None,
        value_date=decode_date(movement['valueDate']),
        transaction_date=decode_date(movement['transactionDate']),
        source=get_source(details, movement_type),
        destination=get_destination(details, movement_type),
        details=details,
        keywords=extract_keywords(extract_literals(movement, LITERAL_FIELDS)),
        comment=get_comments(details, movement_type),
        flags=ModifiedFlags()
    )
