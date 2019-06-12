
from datetime import datetime
from dataclasses import is_dataclass
from difflib import Differ
from enum import Enum
from operator import itemgetter
from copy import deepcopy

import re

import datatypes
from common.utils import get_nested_item

from .domain import SortDirection


class DatabaseError(Exception):
    pass


class DivergedHistoryError(DatabaseError):
    def __init__(self, diverged_transaction, extra_message=''):
        self.transaction = diverged_transaction
        self.message = 'Transaction history has diverged on {transaction_date}, "{type} {amount} {source} --> {destination}". {extra}'.format(
            transaction_date=diverged_transaction.transaction_date.strftime('%Y/%m/%d'),
            type=diverged_transaction.type.value,
            amount=diverged_transaction.amount,
            source=getattr(diverged_transaction.source, 'name', 'Unknown'),
            destination=getattr(diverged_transaction.destination, 'name', 'Unknown'),
            extra=extra_message
        )


def diverged_history(diverged_transaction, extra_message=''):
    raise DatabaseError(
        'Transaction history has diverged on {transaction_date}, "{type} {amount} {source} --> {destination}". {extra}'.format(
            transaction_date=diverged_transaction.transaction_date.strftime('%Y/%m/%d'),
            type=diverged_transaction.type.value,
            amount=diverged_transaction.amount,
            source=getattr(diverged_transaction.source, 'name', 'Unknown'),
            destination=getattr(diverged_transaction.destination, 'name', 'Unknown'),
            extra=extra_message
        )
    )


def encode_date(dt):
    return dt.strftime('%Y-%m-%dT%H:%M:%S')


def encode_transaction(parsed_transaction):
    def encode(obj):
        if is_dataclass(obj):
            encoded = obj.__dict__
            encoded['__type__'] = 'dataclass::{}'.format(obj.__class__.__name__)
            return encoded
        elif isinstance(obj, Enum):
            return {
                '__type__': 'enum::{}'.format(obj.__class__.__name__),
                'name': obj.name
            }
        elif isinstance(obj, datetime):
            return {
                '__type__': 'datetime',
                'date': encode_date(obj)
            }
        else:
            return obj

    def recurse(obj):
        encoded = encode(obj)
        if isinstance(encoded, dict):
            new = {}
            for key, value in encoded.items():
                new[key] = recurse(value)
            return new

        elif isinstance(encoded, list):
            new = []
            for item in encoded:
                new.append(recurse(item))
            return new
        else:
            return encoded

    return recurse(parsed_transaction)


def decode_transaction(document):

    if document is None:
        return None

    def decode(obj):
        if not isinstance(obj, dict):
            return obj

        if '__type__' not in obj:
            return obj

        custom_type_class, custom_type_name = re.match(r'([^:]+)(?:::(.*))?', obj.pop('__type__')).groups()

        if custom_type_class == 'dataclass':
            CustomDataclass = getattr(datatypes, custom_type_name)
            return CustomDataclass(**obj)
        elif custom_type_class == 'enum':
            CustomEnum = getattr(datatypes, custom_type_name)
            return CustomEnum[obj['name']]
        elif custom_type_class == 'datetime':
            return datetime.strptime(obj['date'], '%Y-%m-%dT%H:%M:%S')
        else:
            return obj

    def recurse(obj):
        decoded = decode(obj)
        if is_dataclass(decoded):
            for key, value in decoded.__dict__.items():
                setattr(decoded, key, recurse(value))
            return decoded
        elif isinstance(decoded, dict):
            new = {}
            for key, value in decoded.items():
                new[key] = recurse(value)
            return new

        elif isinstance(decoded, list):
            new = []
            for item in decoded:
                new.append(recurse(item))
            return new

        else:
            return decoded

    decoded = recurse(deepcopy(document))
    return decoded


def find_local_account_transactions(db, account_id=None, since_date=None, sort_direction=SortDirection.NEWEST_TRANSACTION_LAST):
    collection = db.local_account_transactions
    query = {}

    if account_id is not None:
        query['account.id'] = account_id

    if since_date is not None:
        query['transaction_date.date'] = {'$gte': encode_date(since_date)}

    results = list(map(
        decode_transaction,
        collection.find(
            query,
            sort=[('_seq', sort_direction.value)]
        )
    ))

    return results


def insert_local_account_transaction(db, transaction):
    collection = db.local_account_transactions
    return collection.insert_one(encode_transaction(transaction))


def find_matching_account_transaction(db, account_number, transaction):
    collection = db.account_transactions
    results = list(collection.find(
        {
            'account.id': account_number,
            'transaction_date.date': encode_date(transaction.transaction_date),
            'amount': transaction.amount,
            'balance': transaction.balance
        },
        sort=[('_seq', 1)]
    ))

    if not results:
        return None

    if len(results) > 1:
        raise DatabaseError('Found more than one match for a transaction, check the algorithm')

    return decode_transaction(results[0])


def find_one_account_transaction(db, account_number, sort_seq=1):
    collection = db.account_transactions
    results = list(collection.find(
        {
            'account.id': account_number,
        },
        sort=[('_seq', sort_seq)]
    ))

    if not results:
        return None

    return decode_transaction(results[0])


def find_account_transactions(db, account_number=None, since_seq_number=None, since_date=None):
    collection = db.account_transactions
    query = {}

    if account_number is not None:
        query['account.id'] = account_number

    if since_seq_number is not None:
        query['_seq'] = {"$gte": since_seq_number}

    if since_date is not None:
        query['transaction_date.date'] = {'$gte': encode_date(since_date)}

    results = list(map(
        decode_transaction,
        collection.find(
            query,
            sort=[('_seq', 1)]
        )
    ))

    return results


def insert_account_transaction(db, transaction):
    collection = db.account_transactions
    return collection.insert_one(encode_transaction(transaction))


def count_account_transactions(db, account_number):
    collection = db.account_transactions
    query = {}
    query['account.id'] = account_number
    return collection.find(query).count()


def update_account_transaction(db, transaction):
    collection = db.account_transactions
    return collection.update({'_id': transaction._id}, encode_transaction(transaction))


def find_matching_credit_card_transaction(db, credit_card_number, transaction):
    collection = db.credit_card_transactions
    results = list(collection.find(
        {
            'card.number': credit_card_number,
            'transaction_date.date': encode_date(transaction.transaction_date),
            'amount': transaction.amount,
            'transaction_id': transaction.transaction_id
        },
        sort=[('_seq', 1)]
    ))

    if not results:
        return None

    if len(results) > 1:
        raise DatabaseError('Found more than one match for a transaction, check the algorithm')

    return decode_transaction(results[0])


def find_one_credit_card_transaction(db, credit_card_number, sort_seq=1):
    collection = db.credit_card_transactions
    results = list(collection.find(
        {
            'card.number': credit_card_number,
        },
        sort=[('_seq', sort_seq)]
    ))

    if not results:
        return None

    return decode_transaction(results[0])


def find_credit_card_transactions(db, credit_card_number=None, since_seq_number=None, since_date=None):
    collection = db.credit_card_transactions
    query = {}

    if credit_card_number is not None:
        query['card.number'] = credit_card_number

    if since_seq_number is not None:
        query['_seq'] = {"$gte": since_seq_number}

    if since_date is not None:
        query['transaction_date.date'] = {'$gte': encode_date(since_date)}

    results = list(map(
        decode_transaction,
        collection.find(
            query,
            sort=[('_seq', 1)]
        )
    ))

    return results


def insert_credit_card_transaction(db, transaction):
    collection = db.credit_card_transactions
    return collection.insert_one(encode_transaction(transaction))


def count_credit_card_transactions(db, credit_card_number):
    collection = db.credit_card_transactions
    query = {}
    query['card.number'] = credit_card_number
    return collection.find(query).count()


def update_credit_card_transaction(db, transaction):
    collection = db.credit_card_transactions
    return collection.update({'_id': transaction._id}, encode_transaction(transaction))


def align_decimal(number):
    number, zeros = re.match(r'(.*?)(0*)$', '{amount:.3f}'.format(amount=number)).groups()
    if number.endswith('.'):
        number += '0'
        zeros = zeros[:-1]
    aligned = '{lpad}{number}{rpad}'.format(number=number, lpad=' ' * (10 - len(zeros) - len(number)), rpad=zeros.replace('0', ' '))
    return aligned


def log_action(transaction, action):
    print('> {action:2}  {m._seq:02}  {m.transaction_date}  {amount} '.format(
        m=transaction,
        action=action,
        amount=align_decimal(transaction.amount)
    ))


def check_balance_consistency(db, account_number):
    collection = db.account_transactions
    results = find_account_transactions(collection, account_number)

    last_balance = results[0].balance

    for transaction in results[1:]:
        # Fucking python floating point precission shit ...
        is_consistent = round(last_balance + transaction.amount, 2) == transaction.balance
        if not is_consistent:
            return transaction
        last_balance = transaction.balance

    return None


def select_new_transactions(fetched_transactions, db_transactions, transaction_key_fields):

    def transaction_string(transaction):
        return ' '.join(
            map(
                lambda field: get_nested_item(transaction, field).__repr__(),
                transaction_key_fields
            )
        )

    hashed_fetched_transactions = [
        (
            transaction_string(transaction),
            transaction,
        )
        for transaction in fetched_transactions
    ]

    hashed_db_transactions = [
        (
            transaction_string(transaction),
            transaction,
        )
        for transaction in db_transactions
    ]

    fetched_transactions_by_hash = dict(hashed_fetched_transactions)
    db_transactions_by_hash = dict(hashed_db_transactions)

    # TODO Check for duplicate hashes

    diff = list(Differ().compare(
        list(map(itemgetter(0), hashed_db_transactions)),
        list(map(itemgetter(0), hashed_fetched_transactions))
    ))

    next_seq_number = 0
    sequence_change_needed = False
    all_fetched_processed = False

    # from pprint import pprint
    # print()
    # pprint(diff)
    # print()

    for item in diff:

        action = item[0]
        transaction_hash = item[2:]

        if transaction_hash == hashed_fetched_transactions[-1][0]:
            all_fetched_processed = True

        if action == '+':
            # We have a transaction in fetched that it's not on the database
            transaction = fetched_transactions_by_hash[transaction_hash]
            new_transaction = deepcopy(transaction)
            new_transaction._seq = next_seq_number
            yield ('insert', new_transaction)
            next_seq_number += 1
            sequence_change_needed = True
            # log_action(new_transaction, '+')

        elif action == ' ' and not sequence_change_needed:
            # this transaction is on both db and fetched transactions
            # so here we only set the next sequence number, that will be
            # be used if we have new fetched transactions at the tail
            # or we need to cascade change sequence numbers
            next_seq_number = db_transactions_by_hash[transaction_hash]._seq + 1
            # log_action(db_transactions_by_hash[transaction_hash], 's')

        elif sequence_change_needed and action == ' ':
            # this transaction is on both db and fetched transactions but we inserted
            # something that changed the sequence, so we need to update it
            stored_transaction = db_transactions_by_hash[transaction_hash]
            updated_transaction = deepcopy(stored_transaction)
            updated_transaction._seq = next_seq_number
            yield ('update', updated_transaction)
            next_seq_number += 1
            # log_action(updated_transaction, 'u')

        elif action == '-' and all_fetched_processed and sequence_change_needed:
            # this transaction is only on db but as something happened
            # that changed the sequence, so we need to update it
            stored_transaction = db_transactions_by_hash[transaction_hash]
            updated_transaction = deepcopy(stored_transaction)
            updated_transaction._seq = next_seq_number
            yield ('update', updated_transaction)
            next_seq_number += 1
            # log_action(updated_transaction, 'u-')

        elif action == '-' and all_fetched_processed and not sequence_change_needed:
            # This will never happen, as the last conditional in the loop breaks it
            # the as soon as all fetched items are processed
            # log_action(transaction, '?')
            pass

        elif action == '-' and not all_fetched_processed:
            raise DivergedHistoryError(db_transactions_by_hash[transaction_hash])

        # After processing the last fetched transaction, if we didn't do
        # anything that broke the sequence numbering, we can stop
        if all_fetched_processed and not sequence_change_needed:
            # print('X Quitting, all fetched processed')
            break
