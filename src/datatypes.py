from dataclasses import dataclass, field, is_dataclass
from enum import Enum, EnumMeta


class TransactionType(Enum):
    ISSUED_TRANSFER = 'Issued transfer'
    RECEIVED_TRANSFER = 'Received transfer'
    BANK_COMISSION = 'Bank comission'
    BANK_COMISSION_RETURN = 'Bank comission return'
    MORTAGE_RECEIPT = 'Mortage receipt'
    DOMICILED_RECEIPT = 'Domicilied receipt'
    RETURN_DEPOSIT = 'Return deposit'
    CREDIT_CARD_INVOICE = 'Credit card invoice'
    CREDIT_CARD_INVOICE_PAYMENT = 'Credit card invoice payment'
    PURCHASE = 'Purchase'
    PURCHASE_RETURN = 'Purchase return'
    ATM_WITHDRAWAL = 'ATM Withdrawal'
    UNKNOWN = '--'


class DataOrigin(Enum):
    ORIGINAL = 0
    RULES = 1
    USER = 2


class TransactionDirection(Enum):
    CHARGE = 0
    INCOME = 1


@dataclass
class BankConfig:
    id: str
    name: str
    username: str
    password: str
    accounts: list


@dataclass
class AccountConfig:
    bank: str
    name: str
    number: str
    cards: list


@dataclass
class CardConfig:
    type: str
    name: str
    number: str
    owner: str
    bank_id: str
    account_number: str


@dataclass
class UnknownSubject:
    pass


@dataclass
class UnknownWallet:
    pass


@dataclass
class TransactionSubject:
    name: str


@dataclass
class Bank(TransactionSubject):
    id: str

    @classmethod
    def from_config(cls, bank_config):
        return cls(
            bank_config.name,
            bank_config.id
        )


@dataclass
class Account(TransactionSubject):
    number: str

    @classmethod
    def from_config(cls, account_config):
        return cls(
            account_config.name,
            account_config.number
        )


@dataclass
class Card(TransactionSubject):
    number: str

    @classmethod
    def from_config(cls, card_config):
        return cls(
            card_config.name,
            card_config.number
        )


@dataclass
class Issuer(TransactionSubject):
    pass


@dataclass
class Recipient(TransactionSubject):
    pass


@dataclass
class Wallet(TransactionSubject):
    pass


@dataclass
class ModifiedFlags():
    type: int = DataOrigin.ORIGINAL
    source: int = DataOrigin.ORIGINAL
    destination: int = DataOrigin.ORIGINAL
    details: int = DataOrigin.ORIGINAL
    comment: int = DataOrigin.ORIGINAL
    tags: int = DataOrigin.ORIGINAL
    category: int = DataOrigin.ORIGINAL


@dataclass
class ParsedTransaction():
    transaction_id: str
    type: TransactionType
    currency: str
    amount: float
    balance: float
    value_date: str
    transaction_date: str
    source: TransactionSubject
    destination: TransactionSubject
    card: Card
    details: dict
    keywords: list
    comment: str
    flags: ModifiedFlags
    category: str = None
    tags: list = field(default_factory=list)


@dataclass
class Transaction():
    transaction_id: str
    type: TransactionType
    currency: str
    amount: float
    balance: float
    value_date: str
    transaction_date: str
    source: TransactionSubject
    destination: TransactionSubject
    card: Card
    details: dict
    keywords: list
    comment: str
    flags: ModifiedFlags
    category: str = None
    tags: list = field(default_factory=list)
    _id: str = None
    _seq: int = None


DATACLASSES = list(filter(lambda obj: is_dataclass(obj), locals().values()))
ENUMS = list(filter(lambda obj: isinstance(obj, EnumMeta), locals().values()))