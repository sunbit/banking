from database.runtime import update_credit_card_transactions
from datatypes import TransactionType
from database.io import decode_transaction
from .helpers import make_credit_card_transaction, make_test_account, make_test_card
from copy import deepcopy
from datetime import datetime
import pytest

from operator import eq, attrgetter


TEST_CREDIT_CARD_NUMBER = '00000000001'


def make_date(date_string):
    return datetime.strptime(date_string, '%Y-%m-%dT%H:%M:%S')


def T(date, amount, _seq=None):
    return make_credit_card_transaction(
        type=TransactionType.PURCHASE,
        amount=amount,
        transaction_date=make_date(date),
        value_date=make_date(date),
        source=make_test_account(),
        _seq=_seq
    )


database_tests = {}
failing_database_tests = {}

# HEAD = older stored transactions
# TAIL = newer stored transactions

database_tests['Add transactions to empty database'] = [
    [],
    [
        T('2019-01-01T00:00:00', -1.0),
        T('2019-01-01T01:00:00', -2.0),
        T('2019-01-02T00:00:00', -3.0),
    ],
    [
        T('2019-01-01T00:00:00', -1.0, 0),
        T('2019-01-01T01:00:00', -2.0, 1),
        T('2019-01-02T00:00:00', -3.0, 2),
    ],
]

database_tests['Add transactions to tail, all new'] = [
    [
        T('2019-01-01T00:00:00', -1.0, 0),
        T('2019-01-01T01:00:00', -2.0, 1),
        T('2019-01-02T00:00:00', -3.0, 2),
    ],
    [
        T('2019-02-01T00:00:00', -4.0),
        T('2019-02-01T01:00:00', -5.0),
        T('2019-02-02T00:00:00', -6.0),
    ],
    [
        T('2019-01-01T00:00:00', -1.0, 0),
        T('2019-01-01T01:00:00', -2.0, 1),
        T('2019-01-02T00:00:00', -3.0, 2),
        T('2019-02-01T00:00:00', -4.0, 3),
        T('2019-02-01T01:00:00', -5.0, 4),
        T('2019-02-02T00:00:00', -6.0, 5),
    ]
]

database_tests['Add transactions to head, all new'] = [
    [
        T('2019-02-01T00:00:00', -4.0, 0),
        T('2019-02-01T01:00:00', -5.0, 1),
        T('2019-02-02T00:00:00', -6.0, 2),
    ],
    [
        T('2019-01-01T00:00:00', -1.0),
        T('2019-01-01T01:00:00', -2.0),
        T('2019-01-02T00:00:00', -3.0),
    ],
    [
        T('2019-01-01T00:00:00', -1.0, 0),
        T('2019-01-01T01:00:00', -2.0, 1),
        T('2019-01-02T00:00:00', -3.0, 2),
        T('2019-02-01T00:00:00', -4.0, 3),
        T('2019-02-01T01:00:00', -5.0, 4),
        T('2019-02-02T00:00:00', -6.0, 5),
    ]
]

failing_database_tests['Add transactions in between, all new'] = [
    [
        T('2019-01-01T00:00:00', -4.0, 0),
        T('2019-01-01T01:00:00', -5.0, 1),
        T('2019-03-02T00:00:00', -6.0, 2),
    ],
    [
        T('2019-02-01T00:00:00', -1.0),
        T('2019-02-01T01:00:00', -2.0),
        T('2019-02-02T00:00:00', -3.0),
    ],
    T('2019-02-01T00:00:00', -1.0),
]

database_tests['Add transactions to tail, all exist'] = [
    [
        T('2019-01-01T00:00:00', -1.0, 0),
        T('2019-01-01T01:00:00', -2.0, 1),
        T('2019-01-02T00:00:00', -3.0, 2),
        T('2019-02-01T00:00:00', -4.0, 3),
        T('2019-02-01T01:00:00', -5.0, 4),
        T('2019-02-02T00:00:00', -6.0, 5),
    ],
    [
        T('2019-02-01T00:00:00', -4.0),
        T('2019-02-01T01:00:00', -5.0),
        T('2019-02-02T00:00:00', -6.0),
    ],
    [
        T('2019-01-01T00:00:00', -1.0, 0),
        T('2019-01-01T01:00:00', -2.0, 1),
        T('2019-01-02T00:00:00', -3.0, 2),
        T('2019-02-01T00:00:00', -4.0, 3),
        T('2019-02-01T01:00:00', -5.0, 4),
        T('2019-02-02T00:00:00', -6.0, 5),
    ]
]

database_tests['Add transactions to head, all exist'] = [
    [
        T('2019-01-01T00:00:00', -1.0, 0),
        T('2019-01-01T01:00:00', -2.0, 1),
        T('2019-01-02T00:00:00', -3.0, 2),
        T('2019-02-01T00:00:00', -4.0, 3),
        T('2019-02-01T01:00:00', -5.0, 4),
        T('2019-02-02T00:00:00', -6.0, 5),
    ],
    [
        T('2019-01-01T00:00:00', -1.0),
        T('2019-01-01T01:00:00', -2.0),
        T('2019-01-02T00:00:00', -3.0),
    ],
    [
        T('2019-01-01T00:00:00', -1.0, 0),
        T('2019-01-01T01:00:00', -2.0, 1),
        T('2019-01-02T00:00:00', -3.0, 2),
        T('2019-02-01T00:00:00', -4.0, 3),
        T('2019-02-01T01:00:00', -5.0, 4),
        T('2019-02-02T00:00:00', -6.0, 5),
    ]
]

database_tests['Add transactions in between, all exist'] = [
    [
        T('2019-01-01T00:00:00', -1.0, 0),
        T('2019-01-01T01:00:00', -2.0, 1),
        T('2019-01-02T00:00:00', -3.0, 2),
        T('2019-02-01T00:00:00', -4.0, 3),
        T('2019-02-01T01:00:00', -5.0, 4),
        T('2019-02-02T00:00:00', -6.0, 5),
    ],
    [

        T('2019-01-01T01:00:00', -2.0),
        T('2019-01-02T00:00:00', -3.0),
        T('2019-02-01T00:00:00', -4.0),
        T('2019-02-01T01:00:00', -5.0),
    ],
    [
        T('2019-01-01T00:00:00', -1.0, 0),
        T('2019-01-01T01:00:00', -2.0, 1),
        T('2019-01-02T00:00:00', -3.0, 2),
        T('2019-02-01T00:00:00', -4.0, 3),
        T('2019-02-01T01:00:00', -5.0, 4),
        T('2019-02-02T00:00:00', -6.0, 5),
    ]
]

database_tests['Database equals fetched transactions'] = [
    [
        T('2019-01-01T00:00:00', -1.0, 0),
        T('2019-01-01T01:00:00', -2.0, 1),
        T('2019-01-02T00:00:00', -3.0, 2),
        T('2019-02-01T00:00:00', -4.0, 3),
        T('2019-02-01T01:00:00', -5.0, 4),
        T('2019-02-02T00:00:00', -6.0, 5),
    ],
    [
        T('2019-01-01T00:00:00', -1.0),
        T('2019-01-01T01:00:00', -2.0),
        T('2019-01-02T00:00:00', -3.0),
        T('2019-02-01T00:00:00', -4.0),
        T('2019-02-01T01:00:00', -5.0),
        T('2019-02-02T00:00:00', -6.0),
    ],
    [
        T('2019-01-01T00:00:00', -1.0, 0),
        T('2019-01-01T01:00:00', -2.0, 1),
        T('2019-01-02T00:00:00', -3.0, 2),
        T('2019-02-01T00:00:00', -4.0, 3),
        T('2019-02-01T01:00:00', -5.0, 4),
        T('2019-02-02T00:00:00', -6.0, 5),
    ]
]

database_tests['Add transactions to head, newer ones already exist'] = [
    [
        T('2019-02-01T00:00:00', -4.0, 3),
        T('2019-02-01T01:00:00', -5.0, 4),
        T('2019-02-02T00:00:00', -6.0, 5),
    ],
    [
        T('2019-01-01T00:00:00', -1.0),
        T('2019-01-01T01:00:00', -2.0),
        T('2019-01-02T00:00:00', -3.0),
        T('2019-02-01T00:00:00', -4.0),
        T('2019-02-01T01:00:00', -5.0),
    ],
    [
        T('2019-01-01T00:00:00', -1.0, 0),
        T('2019-01-01T01:00:00', -2.0, 1),
        T('2019-01-02T00:00:00', -3.0, 2),
        T('2019-02-01T00:00:00', -4.0, 3),
        T('2019-02-01T01:00:00', -5.0, 4),
        T('2019-02-02T00:00:00', -6.0, 5),
    ]
]

failing_database_tests['Add transactions to head, newer ones already there except a middle one'] = [
    [
        T('2019-02-01T00:00:00', -4.0, 3),
        T('2019-02-01T01:00:00', -5.0, 4),
        T('2019-02-02T00:00:00', -6.0, 5),
    ],
    [
        T('2019-01-01T00:00:00', -1.0),
        T('2019-01-01T01:00:00', -2.0),
        T('2019-01-02T00:00:00', -3.0),
        T('2019-02-01T00:00:00', -4.0),
        # T('2019-02-01T01:00:00', -5.0),  <--- This one is missing from the fetched ones
        T('2019-02-02T00:00:00', -6.0),
    ],
    T('2019-02-01T01:00:00', -5.0, 4),
]

failing_database_tests['Add transactions to head, newer ones already there exceptone that differs'] = [
    [
        T('2019-02-01T00:00:00', -4.0, 3),
        T('2019-02-01T01:00:00', -5.0, 4),
        T('2019-02-02T00:00:00', -6.0, 5),
    ],
    [
        T('2019-01-01T00:00:00', -1.0),
        T('2019-01-01T01:00:00', -2.0),
        T('2019-01-02T00:00:00', -3.0),
        T('2019-02-01T00:00:00', -4.0),
        T('2019-02-01T01:00:00', -5.5),  # <--- This one differs from the stored ones
        T('2019-02-02T00:00:00', -6.0),
    ],
    T('2019-02-01T01:00:00', -5.0, 4),
]

database_tests['Add transactions to tail, older ones already exist'] = [
    [
        T('2019-01-01T00:00:00', -1.0, 0),
        T('2019-01-01T01:00:00', -2.0, 1),
        T('2019-01-02T00:00:00', -3.0, 2),
    ],
    [
        T('2019-01-01T01:00:00', -2.0),
        T('2019-01-02T00:00:00', -3.0),
        T('2019-02-01T00:00:00', -4.0),
        T('2019-02-01T01:00:00', -5.0),
        T('2019-02-02T00:00:00', -6.0),
    ],
    [
        T('2019-01-01T00:00:00', -1.0, 0),
        T('2019-01-01T01:00:00', -2.0, 1),
        T('2019-01-02T00:00:00', -3.0, 2),
        T('2019-02-01T00:00:00', -4.0, 3),
        T('2019-02-01T01:00:00', -5.0, 4),
        T('2019-02-02T00:00:00', -6.0, 5),
    ]
]

failing_database_tests['Add transactions to tail, older ones already exist except a middle one'] = [
    [
        T('2019-01-01T00:00:00', -1.0, 0),
        T('2019-01-01T01:00:00', -2.0, 1),
        T('2019-01-02T00:00:00', -3.0, 2),
    ],
    [
        T('2019-01-01T01:00:00', -2.0),
        # T('2019-01-02T00:00:00', -3.0, 2),  <--- This one is missing from the fetched ones
        T('2019-02-01T00:00:00', -4.0),
        T('2019-02-01T01:00:00', -5.0),
        T('2019-02-02T00:00:00', -6.0),
    ],
    T('2019-01-02T00:00:00', -3.0, 2)
]


failing_database_tests['Add transactions to tail, older ones already exist, one differs'] = [
    [
        T('2019-01-01T00:00:00', -1.0, 0),
        T('2019-01-01T01:00:00', -2.0, 1),
        T('2019-01-02T00:00:00', -3.0, 2),
    ],
    [
        T('2019-01-01T01:00:00', -2.0),
        T('2019-01-02T00:00:00', -3.5),  # <--- This one differs from the stored ones
        T('2019-02-01T00:00:00', -4.0),
        T('2019-02-01T01:00:00', -5.0),
        T('2019-02-02T00:00:00', -6.0),
    ],
    T('2019-01-02T00:00:00', -3.0, 2)
]

database_tests['Add transactions to head and tail, in between transactions already exist'] = [
    [
        T('2019-01-02T00:00:00', -3.0, 2),
        T('2019-02-01T00:00:00', -4.0, 3),
    ],
    [
        T('2019-01-01T00:00:00', -1.0),
        T('2019-01-01T01:00:00', -2.0),
        T('2019-01-02T00:00:00', -3.0),
        T('2019-02-01T00:00:00', -4.0),
        T('2019-02-01T01:00:00', -5.0),
        T('2019-02-02T00:00:00', -6.0),
    ],
    [
        T('2019-01-01T00:00:00', -1.0, 0),
        T('2019-01-01T01:00:00', -2.0, 1),
        T('2019-01-02T00:00:00', -3.0, 2),
        T('2019-02-01T00:00:00', -4.0, 3),
        T('2019-02-01T01:00:00', -5.0, 4),
        T('2019-02-02T00:00:00', -6.0, 5),
    ]
]


failing_database_tests['Add transactions to head and tail, in between transactions already exist, except a middle one'] = [
    [
        T('2019-01-02T00:00:00', -3.0, 2),
        T('2019-02-01T00:00:00', -4.0, 3),
        T('2019-02-01T01:00:00', -5.0, 4),
    ],
    [
        T('2019-01-01T00:00:00', -1.0),
        T('2019-01-01T01:00:00', -2.0),
        T('2019-01-02T00:00:00', -3.0),
        # T('2019-02-01T00:00:00', -4.0, 3), <--- This one is missing from the fetched ones
        T('2019-02-01T01:00:00', -5.0),
        T('2019-02-02T00:00:00', -6.0),
    ],
    T('2019-02-01T00:00:00', -4.0, 3),
]

failing_database_tests['Add transactions to head and tail, in between transactions already exist, one differs'] = [
    [
        T('2019-01-02T00:00:00', -3.0, 2),
        T('2019-02-01T00:00:00', -4.0, 3),
        T('2019-02-01T01:00:00', -5.0, 4),
    ],
    [
        T('2019-01-01T00:00:00', -1.0),
        T('2019-01-01T01:00:00', -2.0),
        T('2019-01-02T00:00:00', -3.0),
        T('2019-02-01T00:00:00', -4.5,),  # <--- This one differs from the stored ones
        T('2019-02-01T01:00:00', -5.0),
        T('2019-02-02T00:00:00', -6.0),
    ],
    T('2019-02-01T00:00:00', -4.0, 3),
]


def match_fields(*fields):
    def _eq(value0, value1):
        # print('Comparing {} == {}'.format(value0, value1))
        return eq(value0, value1)

    def match(tr0, tr1):
        return all(map(
            _eq,
            map(lambda field: getattr(tr0, field), fields),
            map(lambda field: getattr(tr1, field), fields)
        ))
    return match


@pytest.mark.parametrize(
    'current_db_transactions, fetched_transactions, expected_db_transactions',
    list(database_tests.values()), ids=list(database_tests.keys()))
def test_database_update_success(db_from_transactions, current_db_transactions, fetched_transactions, expected_db_transactions):
    db = db_from_transactions(credit_card_transactions=current_db_transactions)
    update_credit_card_transactions(db, TEST_CREDIT_CARD_NUMBER, fetched_transactions)

    stored_db_transactions = list(map(
        decode_transaction,
        db.credit_card_transactions.find(
            {'card.number': TEST_CREDIT_CARD_NUMBER},
            sort=[('_seq', 1)]
        )
    ))

    assert len(stored_db_transactions) == len(expected_db_transactions)
    assert all(map(
        match_fields('_seq', 'transaction_date', 'amount'),
        stored_db_transactions, expected_db_transactions
    ))


@pytest.mark.parametrize(
    'current_db_transactions, fetched_transactions, diverged_transaction',
    list(failing_database_tests.values()), ids=list(failing_database_tests.keys()))
def test_database_update_failures(db_from_transactions, current_db_transactions, fetched_transactions, diverged_transaction):
    db = db_from_transactions(credit_card_transactions=current_db_transactions)

    with pytest.raises(Exception) as excinfo:
        update_credit_card_transactions(db, TEST_CREDIT_CARD_NUMBER, fetched_transactions)

    stored_db_transactions = list(map(
        decode_transaction,
        db.credit_card_transactions.find(
            {'card.number': TEST_CREDIT_CARD_NUMBER},
            sort=[('_seq', 1)]
        )
    ))

    assert match_fields('_seq', 'transaction_date', 'amount')(excinfo.value.transaction, diverged_transaction)

    assert len(stored_db_transactions) == len(current_db_transactions)
    assert all(map(
        match_fields('_seq', 'transaction_date', 'amount'),
        stored_db_transactions, current_db_transactions
    ))
