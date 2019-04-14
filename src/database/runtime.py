from tinymongo import TinyMongoClient

import re

from . import io


def load():
    connection = TinyMongoClient('database')
    db = getattr(connection, 'banking')
    return db


def update_account_transactions(db, account_number, fetched_transactions):
    if not fetched_transactions:
        return

    collection = db.account_transactions

    # Get from the database all the transactions starting with the
    # first one that matches the first fetched transaction
    first_fetched_transaction = io.find_transaction(collection, account_number, fetched_transactions[0])
    if first_fetched_transaction is not None:
        existing_transactions = io.find_transactions_since(collection, account_number, first_fetched_transaction)
    else:
        existing_transactions = list(map(
            io.decode_transaction,
            collection.find(
                {
                    'account.id': account_number,
                    'transaction_date': {'$gte': fetched_transactions[0].transaction_date}
                },
                sort=[('_seq', 1)]
            )
        ))

    added = 0
    updated = 0
    for action, transaction in io.select_new_transactions(fetched_transactions, existing_transactions):
        if action == 'insert':
            collection.insert_one(io.encode_transaction(transaction))
            added += 1
        elif action == 'update':
            collection.update({'_id': transaction._id}, io.encode_transaction(transaction))
            updated += 1

    inconsistent_transaction = io.check_balance_consistency(collection, account_number)

    if inconsistent_transaction:
        raise io.DatabaseError(
            'Balance is inconsistent at {transaction.transaction_date} [balance={transaction.balance}, amount={transaction.amount}]'.format(
                transaction=inconsistent_transaction)
        )
