from functools import partial
from tinymongo import TinyMongoClient

from . import io
from datatypes import BankAccountTransaction, BankCreditCardTransaction


def load(database_folder):
    connection = TinyMongoClient(database_folder)
    db = getattr(connection, 'banking')
    return db


def last_account_transaction_date(db, account_number):
    collection = db.account_transactions
    results = io.find_account_transactions(collection, account_number)
    return results[-1].transaction_date if results else None


def last_credit_card_transaction_date(db, credit_card_number):
    collection = db.credit_card_transactions
    results = io.find_credit_card_transactions(collection, credit_card_number)
    return results[-1].transaction_date if results else None


def update_account_transactions(db, account_number, fetched_transactions):
    if not fetched_transactions:
        return

    # Get from the database all the transactions starting with the
    # first one that matches the first fetched transaction
    first_fetched_transaction = io.find_matching_account_transaction(db, account_number, fetched_transactions[0])
    if first_fetched_transaction is not None:
        existing_transactions = io.find_account_transactions(db, account_number, since_seq_number=first_fetched_transaction._seq)
    else:
        existing_transactions = io.find_account_transactions(db, account_number, since_date=fetched_transactions[0].transaction_date)

    added = 0
    updated = 0

    converted_transactions = map(
        lambda transaction: BankAccountTransaction(**transaction.__dict__),
        fetched_transactions
    )

    actions = {
        'insert': [],
        'update': []
    }

    for action, transaction in io.select_new_transactions(converted_transactions, existing_transactions, mode='account'):
        actions[action].append(transaction)

    # If any error raised due to selecting transactions, no action will be still executed
    # we do it now

    inserted = list(map(partial(io.insert_account_transaction, db), actions['insert']))
    updated = list(map(partial(io.update_account_transaction, db), actions['update']))

    inconsistent_transaction = io.check_balance_consistency(db, account_number)

    if inconsistent_transaction:
        raise io.DatabaseError(
            'Balance is inconsistent at {transaction.transaction_date} [balance={transaction.balance}, amount={transaction.amount}]'.format(
                transaction=inconsistent_transaction)
        )

    return (len(inserted), len(updated))


def update_credit_card_transactions(db, credit_card_number, fetched_transactions):
    if not fetched_transactions:
        return

    # Get from the database all the transactions starting with the
    # first one that matches the first fetched transaction
    first_fetched_transaction = io.find_matching_credit_card_transaction(db, credit_card_number, fetched_transactions[0])
    if first_fetched_transaction is not None:
        existing_transactions = io.find_credit_card_transactions(db, credit_card_number, since_seq_number=first_fetched_transaction._seq)
    else:
        existing_transactions = io.find_credit_card_transactions(db, credit_card_number, since_date=fetched_transactions[0].transaction_date)

    converted_transactions = map(
        lambda transaction: BankCreditCardTransaction(**transaction.__dict__),
        fetched_transactions
    )

    actions = {
        'insert': [],
        'update': []
    }
    for action, transaction in io.select_new_transactions(converted_transactions, existing_transactions, mode='credit_card'):
        actions[action].append(transaction)

    # If any error raised due to selecting transactions, no action will be still executed
    # we do it now

    inserted = list(map(partial(io.insert_credit_card_transaction, db), actions['insert']))
    updated = list(map(partial(io.update_credit_card_transaction, db), actions['update']))

    return (len(inserted), len(updated))


def update_transaction(db, transaction):
    {
        BankAccountTransaction: io.update_account_transaction,
        BankCreditCardTransaction: io.update_credit_card_transaction
    }[transaction.__class__](db, transaction)
