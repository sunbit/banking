from dataclasses import dataclass
from datetime import datetime

from datatypes import BankAccountTransaction, Account, Card
from datatypes import BankCreditCardTransaction
from datatypes import TransactionType, UnknownSubject, ModifiedFlags


@dataclass
class TestClass():
    att1: str
    att2: dict


def make_test_account():
    return Account('TEST_ACCOUNT', '00000000001')


def make_test_card():
    return Card('TEST_CARD', '00000000001')


def make_transaction(
    transaction_id=None,
    type=TransactionType.UNKNOWN,
    details={},
    keywords=[],
    currency='EUR',
    amount=0.0,
    balance=0.0,
    comment='',
    source=None,
    destination=None,
    category=None,
    tags=[]
):
    return BankAccountTransaction(
        transaction_id=transaction_id,
        currency=currency,
        amount=amount,
        balance=balance,
        value_date=datetime.now(),
        transaction_date=datetime.now(),
        type=type,
        source=UnknownSubject() if source is None else source,
        destination=UnknownSubject()if destination is None else destination,
        account=make_test_account(),
        card=make_test_card(),
        details=details,
        keywords=keywords,
        comment=comment,
        tags=tags,
        category=category,
        flags=ModifiedFlags()
    )


def make_credit_card_transaction(
    transaction_id=None,
    transaction_date=None,
    value_date=None,
    type=TransactionType.UNKNOWN,
    details={},
    keywords=[],
    currency='EUR',
    amount=0.0,
    comment='',
    source=None,
    destination=None,
    category=None,
    tags=[],
    _seq=None,
):
    return BankCreditCardTransaction(
        transaction_id=transaction_id,
        currency=currency,
        amount=amount,
        value_date=datetime.now() if transaction_date is None else transaction_date,
        transaction_date=datetime.now() if value_date is None else value_date,
        type=type,
        source=UnknownSubject() if source is None else source,
        destination=UnknownSubject()if destination is None else destination,
        card=make_test_card(),
        details=details,
        keywords=keywords,
        comment=comment,
        tags=tags,
        category=category,
        flags=ModifiedFlags(),
        _seq=_seq
    )
