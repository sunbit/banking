from copy import deepcopy
from functools import partial
from tinymongo import TinyMongoClient

from . import io
from datatypes import BankAccountTransaction, BankCreditCardTransaction, LocalAccountTransaction
from datatypes import LocalAccount, Card, AccessCode

from collections import namedtuple


def load(database_folder):
    connection = TinyMongoClient(database_folder)
    db = getattr(connection, 'banking')
    return db


def get_account_access_code(db, account):
    code = io.get_account_access_code(db, account.id)
    return code


def update_account_access_code(db, account, access_code):
    return io.update_account_access_code(db, account.id, access_code)


def last_account_transaction_date(db, account_number):
    collection = db.account_transactions
    results = io.find_account_transactions(collection, account_number, sort_field='transaction_date.date')
    return results[-1].transaction_date if results else None


def last_credit_card_transaction_date(db, credit_card_number):
    collection = db.credit_card_transactions
    results = io.find_credit_card_transactions(collection, credit_card_number, sort_field='transaction_date.date')
    return results[-1].transaction_date if results else None


def find_transactions(db, account, **query):
    if isinstance(account, LocalAccount):
        return io.find_local_account_transactions(db, account_id=account.id, **query)
    if isinstance(account, Card):
        return io.find_credit_card_transactions(db, credit_card_number=account.number, **query)


def get_account_balance(db, account):
    if isinstance(account, LocalAccount):
        results = io.find_local_account_transactions(db, account.id)
        return results[-1].balance if results else 0


def insert_transaction(db, transaction):
    if isinstance(transaction.account, LocalAccount):
        return io.insert_local_account_transaction(db, transaction)


def remove_transactions(db, transactions):
    list(map(partial(remove_transaction, db), transactions))


def remove_transaction(db, transaction):
    if isinstance(transaction, BankCreditCardTransaction):
        return io.remove_credit_card_transaction(db, transaction)


def update_credit_card_transactions(db, credit_card_number, raw_fetched_transactions):
    removed, inserted, updated = update_transactions(
        db,
        TransactionDataclass=BankCreditCardTransaction,
        transaction_grouping_id=credit_card_number,
        transaction_key_fields=['transaction_date', 'value_date', 'amount', 'type.name'],
        operations=namedtuple('TransactionOperations', 'insert, update, find, find_one, find_matching, count, remove')(
            io.insert_credit_card_transaction,
            io.update_credit_card_transaction,
            io.find_credit_card_transactions,
            io.find_one_credit_card_transaction,
            io.find_matching_credit_card_transaction,
            io.count_credit_card_transactions,
            io.remove_credit_card_transaction
        ),
        raw_fetched_transactions=raw_fetched_transactions
    )

    duplicated_sequence_found = io.check_credit_card_sequence_numbering_consistency(db, credit_card_number)

    if duplicated_sequence_found:
        raise io.DatabaseError('Duplicated sequence numbers detected: {}'.format(
            str(duplicated_sequence_found))
        )

    return (removed, inserted, updated)


def update_account_transactions(db, account_number, raw_fetched_transactions):
    removed, inserted, updated = update_transactions(
        db,
        TransactionDataclass=BankAccountTransaction,
        transaction_grouping_id=account_number,
        transaction_key_fields=['transaction_date', 'value_date', 'amount', 'balance'],
        operations=namedtuple('TransactionOperations', 'insert, update, find, find_one, find_matching, count, remove')(
            io.insert_account_transaction,
            io.update_account_transaction,
            io.find_account_transactions,
            io.find_one_account_transaction,
            io.find_matching_account_transaction,
            io.count_account_transactions,
            io.remove_account_transaction
        ),
        raw_fetched_transactions=raw_fetched_transactions
    )

    inconsistent_transaction = io.check_balance_consistency(db, account_number)

    if inconsistent_transaction:
        raise io.DatabaseError(
            'Balance is inconsistent at {transaction.transaction_date} [balance={transaction.balance}, amount={transaction.amount}]'.format(
                transaction=inconsistent_transaction)
        )

    duplicated_sequence_found = io.check_account_sequence_numbering_consistency(db, account_number)

    if duplicated_sequence_found:
        raise io.DatabaseError('Duplicated sequence numbers detected: {}'.format(
            str(duplicated_sequence_found))
        )

    return (removed, inserted, updated)


def update_transactions(db, TransactionDataclass, transaction_grouping_id, transaction_key_fields, operations, raw_fetched_transactions):

    if not raw_fetched_transactions:
        return

    actions = {
        'remove': [],
        'insert': [],
        'update': []
    }

    def sequence_transactions(transactions, first_seq):
        for seq, transaction in enumerate(transactions, first_seq):
            _transaction = deepcopy(transaction)
            _transaction._seq = seq
            yield _transaction

    def process_actions():
        removed = list(map(partial(operations.remove, db), actions['remove']))
        inserted = list(map(partial(operations.insert, db), actions['insert']))
        updated = list(map(partial(operations.update, db), actions['update']))
        return (len(removed), len(inserted), len(updated))

    fetched_transactions = list(map(
        lambda transaction: TransactionDataclass(**transaction.__dict__),
        raw_fetched_transactions
    ))

    # First use case: All fetched transactions are new
    # (in other words, we don't have any stored transaction yet)

    transaction_count = operations.count(db, transaction_grouping_id)
    if transaction_count == 0:
        actions['insert'].extend(
            sequence_transactions(fetched_transactions, first_seq=0)
        )
        return process_actions()

    # Next we process all use cases that we add a block of completely new
    # transactions either on the head or on the tail, no overlaps

    first_stored_transaction = operations.find_one(db, transaction_grouping_id, sort_seq=1)
    last_stored_transaction = operations.find_one(db, transaction_grouping_id, sort_seq=-1)

    first_fetched_transaction = fetched_transactions[0]
    last_fetched_transaction = fetched_transactions[-1]

    # All fetched transactions are newer
    if first_fetched_transaction.transaction_date > last_stored_transaction.transaction_date:
        actions['insert'].extend(
            sequence_transactions(
                fetched_transactions,
                first_seq=last_stored_transaction._seq + 1
            )
        )
        return process_actions()

    # All fetched transactions are older
    if last_fetched_transaction.transaction_date < first_stored_transaction.transaction_date:
        existing_transactions = operations.find(
            db, transaction_grouping_id
        )

        actions['insert'].extend(
            sequence_transactions(
                fetched_transactions,
                first_seq=0
            )
        )
        actions['update'].extend(
            sequence_transactions(
                existing_transactions,
                first_seq=actions['insert'][-1]._seq + 1
            )
        )
        return process_actions()

    # At this point, we will have some kind of overlap. This overlap can match
    # all, some or none of the fetched transactions on the database:

    overlapping_transactions = list(filter(
        bool,
        map(
            partial(operations.find_matching, db, transaction_grouping_id),
            fetched_transactions
        )
    ))

    # All transactions are newer and neither in the tail or head
    # so we have a diverged history
    if not overlapping_transactions:
        raise io.DivergedHistoryError(first_fetched_transaction, 'All transactions overlap without matches')

    # We have at least one overlapping, so at this point, the
    # diff algorithm will take care of extracting the insertions, updates or
    # diverged history events as needed

    existing_transactions = operations.find(
        db, transaction_grouping_id,
        since_date=overlapping_transactions[0].transaction_date
    )

    for action, transaction in io.select_new_transactions(fetched_transactions, existing_transactions, transaction_key_fields):
        actions[action].append(transaction)

    return process_actions()


def update_transaction(db, transaction):
    {
        BankAccountTransaction: io.update_account_transaction,
        BankCreditCardTransaction: io.update_credit_card_transaction
    }[transaction.__class__](db, transaction)

