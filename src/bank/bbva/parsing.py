from itertools import chain

from datetime import datetime
import re

from datatypes import TransactionType, TransactionDirection, ParsedBankAccountTransaction, ParsedCreditCardTransaction
from datatypes import Account, Bank, Card, UnknownSubject, UnknownWallet
from common.parsing import extract_literals, extract_keywords
from common.utils import get_nested_item


import datatypes

KEYWORD_FIELDS = [
    'name',
    'humanConceptName',
    'concept.name',
    'extendedName',
    'humanExtendedConceptName',
    'cardTransactionDetail.concept.name',
    'cardTransactionDetail.concept.shop.name',
    'wireTransactionDetail.sender.person.name'
]


def get_type(transaction_code, transation_direction):
    """
        ipdb> pp(dict(set([(b['id'], b['name']) for b in [a['scheme']['subCategory'] for a in raw_transactions]])))

        {'0017': 'PAGO CON TARJETA',
         '0114': 'INGRESO POR NOMINA O PENSION',
         '0022': 'DISPOSIC. DE EFECTIVO CAJERO/OFICINA',
         '0054': 'OTROS',
         '0058': 'PAGO DE ADEUDO DIRECTO SEPA',
         '0060': 'RECIBO TARJETA CRÉDITO',
         '0149': 'TRANSFERENCIA RECIBIDA'
         '0064': 'TRANSFERENCIA REALIZADA'}

    If we need more detail, like in case of OTROS:

    code will came from transaction['concept']['id']

        { "00200": "RET. EFECTIVO  A DEBITO CON TARJ. EN CAJERO. AUT."
          "00400": "COMPRA BBVA WALLET"
        }
    """

    PAYCHECK = ['0114']
    PURCHASE = ['0017', '00400', '0005']
    TRANSFER = ['0149', '0064']
    WITHDRAWAL = ['0022', '00200', '0007']
    DOMICILED_RECEIPT = ['0058']
    CREDIT_CARD_INVOICE = ['0060', '0070']

    if transaction_code in PURCHASE:
        return {
            TransactionDirection.CHARGE: TransactionType.PURCHASE,
            TransactionDirection.INCOME: TransactionType.PURCHASE_RETURN
        }.get(transation_direction)

    if transaction_code in TRANSFER:
        return {
            TransactionDirection.CHARGE: TransactionType.ISSUED_TRANSFER,
            TransactionDirection.INCOME: TransactionType.RECEIVED_TRANSFER
        }.get(transation_direction)

    if transaction_code in PAYCHECK:
        return {
            TransactionDirection.CHARGE: None,
            TransactionDirection.INCOME: TransactionType.RECEIVED_TRANSFER
        }.get(transation_direction)

    if transaction_code in WITHDRAWAL:
        return {
            TransactionDirection.CHARGE: TransactionType.ATM_WITHDRAWAL,
            TransactionDirection.INCOME: None
        }.get(transation_direction)

    if transaction_code in DOMICILED_RECEIPT:
        return {
            TransactionDirection.CHARGE: TransactionType.DOMICILED_RECEIPT,
            TransactionDirection.INCOME: TransactionType.RETURN_DEPOSIT
        }.get(transation_direction)

    if transaction_code in CREDIT_CARD_INVOICE:
        return {
            TransactionDirection.CHARGE: TransactionType.CREDIT_CARD_INVOICE,
            TransactionDirection.INCOME: TransactionType.CREDIT_CARD_INVOICE_PAYMENT
        }.get(transation_direction)


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
    if transaction_type is TransactionType.BANK_COMISSION:
        return details['account']
    if transaction_type is TransactionType.PURCHASE:
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
        set_detail('shop_name', ['comments.[0].text', 'cardTransactionDetail.shop.name', 'humanConceptName'], fmt=title)
        set_detail('card_number', 'origin.panCode')
        set_detail('activity', 'cardTransactionDetail.shop.businessActivity.name')

    if transaction_type is TransactionType.ATM_WITHDRAWAL:
        set_detail('card_number', 'origin.detailSourceKey', fmt=capture(r'(\d+)', 0))
        set_detail('atm_name', ['cardTransactionDetail.shop.name', 'extendedName'])

    if transaction_type is TransactionType.ISSUED_TRANSFER:
        set_detail('beneficiary', 'wireTransactionDetail.sender.person.name', fmt=title)
        set_detail('concept', 'humanExtendedConceptName')

    if transaction_type is TransactionType.RECEIVED_TRANSFER:
        set_detail('origin_account_number', 'wireTransactionDetail.sender.account.formats.ccc')
        set_detail('issuer_name', 'wireTransactionDetail.sender.person.name')
        set_detail('concept', 'humanExtendedConceptName')

    if transaction_type is TransactionType.DOMICILED_RECEIPT:
        set_detail('creditor_name', ['billTransactionDetail.creditor.name'])
        set_detail('concept', ['billTransactionDetail.extendedBillConceptName', 'extendedName'], fmt=title)

    if transaction_type is TransactionType.RETURN_DEPOSIT:
        set_detail('return_reason', 'billTransactionDetail.extendedIntentionName', fmt=title)
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
        set_detail('shop_name', 'shop.name', fmt=title)

    return details


def decode_date(date):
    year, month, day, hour, minute, second = re.search(r'^(\d+)-(\d+)-(\d+)T(\d+):(\d+):(\d+)', date).groups()
    return datetime(*map(int, [year, month, day, hour, minute, second]))


def get_card(account_config, card_number):
    if card_number is None:
        return None

    if card_number in account_config.cards:
        return Card.from_config(account_config.cards[card_number])

    # Possibly an old card no longer registered
    return Card('Unknown card', card_number)


def get_comment(details, transaction_type):
    if transaction_type in [TransactionType.ISSUED_TRANSFER, TransactionType.RECEIVED_TRANSFER]:
        return details['concept']
    if transaction_type is TransactionType.RETURN_DEPOSIT:
        return details['return_reason']
    if transaction_type is TransactionType.DOMICILED_RECEIPT:
        return details['concept']


def parse_account_transaction(bank_config, account_config, transaction):
    amount = transaction['amount']['amount']
    transaction_code = get_nested_item(transaction, 'scheme.subCategory.id')

    if transaction_code == '0054':  # "Otros ..."
        transaction_code = get_nested_item(transaction, 'concept.id')

    transation_direction = TransactionDirection.CHARGE if amount < 0 else TransactionDirection.INCOME
    transaction_type = get_type(transaction_code, transation_direction)

    details = get_account_transaction_details(transaction, transaction_type)
    details['account'] = Account.from_config(account_config)
    details['bank'] = Bank.from_config(bank_config)

    card_number = details.pop('card_number', None)
    used_card = get_card(account_config, card_number)

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
        transaction_id=transaction['id'],
        type=transaction_type,
        currency=transaction['amount']['currency']['code'],
        amount=amount,
        balance=transaction['balance']['availableBalance']['amount'],
        value_date=decode_date(transaction['valueDate']),
        transaction_date=decode_date(transaction['transactionDate']),
        source=source,
        destination=destination,
        account=details.pop('account'),
        card=used_card,
        details=details,
        keywords=keywords,
        comment=comment if comment is not None else '',
    )


def parse_credit_card_transaction(bank_config, account_config, card_config, transaction):
    amount = transaction['amount']['amount']
    transaction_code = get_nested_item(transaction, 'concept.id')
    if transaction_code == '0000':
        # code 0000 seems like an error, as it's really a regular purcharse,
        # so we fake the code
        transaction_code = '0005'

    transation_direction = TransactionDirection.CHARGE if amount < 0 else TransactionDirection.INCOME
    transaction_type = get_type(transaction_code, transation_direction)

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

    is_debit_operation = transaction.get('operationTypeIndicator') == 'D'
    is_consolidated = transaction.get('status', {}).get('id') == '7'

    notify_not_added = False
    status_flags = datatypes.StatusFlags()

    if is_debit_operation:
        if notify_not_added:
            from common.notifications import get_notifier
            import bank
            banking_configuration = bank.load_config(bank.env()['main_config_file'])
            notifier = get_notifier(banking_configuration.notifications)
            notifier('Debit transaction found, not adding {bank.name} card transaction: {date} {amount}, {source}->{destination}'.format(
                bank=bank_config, amount=amount, date=transaction['valueDate'], source=str(source), destination=str(destination))
            )
        status_flags.invalid = True

    if not is_consolidated and notify_not_added:
        if notify_not_added:
            from common.notifications import get_notifier
            import bank
            banking_configuration = bank.load_config(bank.env()['main_config_file'])
            notifier = get_notifier(banking_configuration.notifications)
            notifier('Non consolidated transaction found, not adding {bank.name} card transaction: {date} {amount}, {source}->{destination}'.format(
                bank=bank_config, amount=amount, date=transaction['valueDate'], source=str(source), destination=str(destination))
            )
        return None

    return ParsedCreditCardTransaction(
        transaction_id=transaction['id'],
        type=transaction_type,
        currency=transaction['amount']['currency']['code'],
        amount=amount,
        value_date=decode_date(transaction['valueDate']),
        transaction_date=decode_date(transaction['transactionDate']),
        source=source,
        destination=destination,
        card=card_used,
        details=details,
        keywords=keywords,
        comment=comment if comment is not None else '',
        status_flags=status_flags
    )
