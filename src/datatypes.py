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
class NotificationsConfig:
    telegram_api_key: str
    telegram_chat_id: str


@dataclass
class SchedulerConfig:
    scrapping_hours: list


@dataclass
class Configuration:
    banks: dict
    accounts: dict
    cards: dict
    notifications: NotificationsConfig
    scheduler: SchedulerConfig


@dataclass
class BankConfig:
    id: str
    name: str
    username: str
    password: str
    accounts: list


@dataclass
class AccountConfig:
    type: str
    bank_id: str
    name: str
    id: str
    cards: list

@dataclass
class LocalAccountConfig:
    type: str
    id: str
    name: str


@dataclass
class CardConfig:
    type: str
    name: str
    number: str
    owner: str
    active: bool
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
    id: str

    @classmethod
    def from_config(cls, account_config):
        return cls(
            account_config.name,
            account_config.id
        )

@dataclass
class LocalAccount(TransactionSubject):
    id: str

    @classmethod
    def from_config(cls, account_config):
        return cls(
            account_config.name,
            account_config.id
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
class Category():
    id: str
    name: str
    parent: str = None

@dataclass
class RelatedTransaction():
    account_type: str
    account_id: str
    transaction_id: str

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
class StatusFlags():
    invalid: bool = False


@dataclass
class ParsedBankAccountTransaction():
    transaction_id: str
    type: TransactionType
    currency: str
    amount: float
    balance: float
    value_date: str
    transaction_date: str
    source: TransactionSubject
    destination: TransactionSubject
    account: Account
    card: Card
    details: dict
    keywords: list
    comment: str
    flags: ModifiedFlags = field(default_factory=ModifiedFlags)
    status_flags: StatusFlags = field(default_factory=StatusFlags)
    category: str= None
    tags: list = field(default_factory=list)


@dataclass
class ParsedCreditCardTransaction():
    transaction_id: str
    type: TransactionType
    currency: str
    amount: float
    value_date: str
    transaction_date: str
    source: TransactionSubject
    destination: TransactionSubject
    card: Card
    details: dict
    keywords: list
    comment: str
    flags: ModifiedFlags = field(default_factory=ModifiedFlags)
    status_flags: StatusFlags = field(default_factory=StatusFlags)
    category: str = None
    tags: list = field(default_factory=list)

@dataclass
class BankCreditCardTransaction():
    transaction_id: str
    type: TransactionType
    currency: str
    amount: float
    value_date: str
    transaction_date: str
    source: TransactionSubject
    destination: TransactionSubject
    card: Card
    details: dict
    keywords: list
    comment: str
    category: Category = None
    tags: list = field(default_factory=list)
    flags: ModifiedFlags = field(default_factory=ModifiedFlags)
    status_flags: StatusFlags = field(default_factory=StatusFlags)
    subtransactions: list = field(default_factory=list)
    related: RelatedTransaction = None
    _id: str = None
    _seq: int = None


@dataclass
class BankAccountTransaction():
    transaction_id: str
    type: TransactionType
    currency: str
    amount: float
    balance: float
    value_date: str
    transaction_date: str
    source: TransactionSubject
    destination: TransactionSubject
    account: Account
    card: Card
    details: dict
    keywords: list
    comment: str
    category: Category = None
    tags: list = field(default_factory=list)
    flags: ModifiedFlags = field(default_factory=ModifiedFlags)
    status_flags: StatusFlags = field(default_factory=StatusFlags)
    subtransactions: list = field(default_factory=list)
    related: RelatedTransaction = None
    offset: RelatedTransaction = None
    _id: str = None
    _seq: int = None

@dataclass
class LocalAccountTransaction():
    type: TransactionType
    currency: str
    amount: float
    balance: float
    transaction_date: str
    source: TransactionSubject
    destination: TransactionSubject
    account: LocalAccount
    card: Card
    keywords: list
    comment: str
    category: Category = None
    tags: list = field(default_factory=list)
    flags: ModifiedFlags = field(default_factory=ModifiedFlags)
    subtransactions: list = field(default_factory=list)
    related: RelatedTransaction = None
    offset: RelatedTransaction = None
    _id: str = None
    _seq: int = None

DATACLASSES = list(filter(lambda obj: is_dataclass(obj), locals().values()))
ENUMS = list(filter(lambda obj: isinstance(obj, EnumMeta), locals().values()))
