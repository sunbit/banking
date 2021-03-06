
from collections import Counter
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


def encode_object(domain_object):
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

    return recurse(domain_object)


def decode_object(document):

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


def get_account_access_code(db, account_number):
    collection = db.account_access_codes
    # In reality this cache problem here is a lack of locking that
    # makes this break when we are continuously querying for access code, and a new code is deleted
    # and inserted, and the empty db after the delte is cached, but not the insertion.
    # maybe trying with the newest tinydb, or the tinyrecord extension.
    try:
        collection.table.clear_cache()
    except AttributeError:
        pass

    results = list(collection.find({"account_id": account_number}))
    return decode_object(results[0]) if results else None


def get_bank_access_code(db, bank_id):
    collection = db.bank_access_codes
    # In reality this cache problem here is a lack of locking that
    # makes this break when we are continuously querying for access code, and a new code is deleted
    # and inserted, and the empty db after the delte is cached, but not the insertion.
    # maybe trying with the newest tinydb, or the tinyrecord extension.
    try:
        collection.table.clear_cache()
    except AttributeError:
        pass

    results = list(collection.find({"bank_id": bank_id}))
    return decode_object(results[0]) if results else None


def update_bank_access_code(db, bank_id, access_code):
    collection = db.bank_access_codes
    collection.remove({"bank_id": bank_id})
    return collection.insert_one(encode_object(access_code))


def update_account_access_code(db, account_number, access_code):
    collection = db.account_access_codes
    collection.remove({"account_id": account_number})
    return collection.insert_one(encode_object(access_code))


def find_local_account_transactions(db, account_id=None, since_date=None, sort_direction=SortDirection.NEWEST_TRANSACTION_LAST):
    collection = db.local_account_transactions
    query = {}

    if account_id is not None:
        query['account.id'] = account_id

    if since_date is not None:
        query['transaction_date.date'] = {'$gte': encode_date(since_date)}

    results = list(map(
        decode_object,
        collection.find(
            query,
            sort=[('_seq', sort_direction.value)]
        )
    ))

    return results


def insert_local_account_transaction(db, transaction):
    collection = db.local_account_transactions
    return collection.insert_one(encode_object(transaction))


def find_matching_account_transaction(db, account_number, transaction):
    collection = db.account_transactions
    results = list(
        filter(
            lambda transaction: not transaction.status_flags.valid_duplicate,
            map(
                decode_object,
                collection.find(
                    {
                        'account.id': account_number,
                        'transaction_date.date': encode_date(transaction.transaction_date),
                        'amount': transaction.amount,
                        'balance': transaction.balance
                    },
                    sort=[('_seq', 1)]
                )
            )
        )
    )

    if not results:
        return None

    if len(results) > 1:
        raise DatabaseError('Found more than one match for a transaction, check the algorithm [{date} {amount}]'.format(
            date=encode_date(transaction.transaction_date),
            amount=transaction.amount
        ))

    return decode_object(results[0])


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

    return decode_object(results[0])


def find_account_transactions(db, account_number=None, since_seq_number=None, since_date=None, sort_field='_seq', sort_direction=1):
    collection = db.account_transactions
    query = {}

    if account_number is not None:
        query['account.id'] = account_number

    if since_seq_number is not None:
        query['_seq'] = {"$gte": since_seq_number}

    if since_date is not None:
        query['transaction_date.date'] = {'$gte': encode_date(since_date)}

    results = list(map(
        decode_object,
        collection.find(
            query,
            sort=[(sort_field, sort_direction)]
        )
    ))

    return results


def remove_account_transaction(db, transaction):
    collection = db.account_transactions
    collection.remove({
        '_id': transaction._id
    })


def insert_account_transaction(db, transaction):
    collection = db.account_transactions
    return collection.insert_one(encode_object(transaction))


def count_account_transactions(db, account_number):
    collection = db.account_transactions
    query = {}
    query['account.id'] = account_number
    return collection.find(query).count()


def update_account_transaction(db, transaction):
    collection = db.account_transactions
    return collection.update({'_id': transaction._id}, encode_object(transaction))


def find_matching_credit_card_transaction(db, credit_card_number, transaction):
    collection = db.credit_card_transactions
    results = list(
        filter(
            lambda transaction: not transaction.status_flags.valid_duplicate,
            map(
                decode_object,
                collection.find(
                    {
                        'card.number': credit_card_number,
                        'transaction_date.date': encode_date(transaction.transaction_date),
                        'amount': transaction.amount,
                        'transaction_id': transaction.transaction_id
                    },
                    sort=[('_seq', 1)]
                )
            )
        )
    )

    if not results:
        return None

    if len(results) > 1:
        raise DatabaseError('Found more than one match for a transaction, check the algorithm [{date} {amount}]'.format(
            date=encode_date(transaction.transaction_date),
            amount=transaction.amount
        ))

    return decode_object(results[0])


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

    return decode_object(results[0])


def find_credit_card_transactions(db, credit_card_number=None, since_seq_number=None, since_date=None, _seq=None, sort_field='_seq', sort_direction=1):
    collection = db.credit_card_transactions
    query = {}

    if credit_card_number is not None:
        query['card.number'] = credit_card_number

    if since_seq_number is not None:
        query['_seq'] = {"$gte": since_seq_number}

    if _seq is not None:
        query['_seq'] = _seq

    if since_date is not None:
        query['transaction_date.date'] = {'$gte': encode_date(since_date)}

    results = list(map(
        decode_object,
        collection.find(
            query,
            sort=[(sort_field, sort_direction)]
        )
    ))

    return results


def remove_credit_card_transaction(db, transaction):
    collection = db.credit_card_transactions
    collection.remove({
        '_id': transaction._id
    })


def insert_credit_card_transaction(db, transaction):
    collection = db.credit_card_transactions
    return collection.insert_one(encode_object(transaction))


def count_credit_card_transactions(db, credit_card_number):
    collection = db.credit_card_transactions
    query = {}
    query['card.number'] = credit_card_number
    return collection.find(query).count()


def update_credit_card_transaction(db, transaction):
    collection = db.credit_card_transactions
    return collection.update({'_id': transaction._id}, encode_object(transaction))


def align_decimal(number):
    number, zeros = re.match(r'(.*?)(0*)$', '{amount:.3f}'.format(amount=number)).groups()
    if number.endswith('.'):
        number += '0'
        zeros = zeros[:-1]
    aligned = '{lpad}{number}{rpad}'.format(number=number, lpad=' ' * (10 - len(zeros) - len(number)), rpad=zeros.replace('0', ' '))
    return aligned


def log_action(transaction, action):
    # print('> {action:2}  {m._seq:02}  {m.transaction_date}  {amount} '.format(
    #     m=transaction,
    #     action=action,
    #     amount=align_decimal(transaction.amount)
    # ))
    pass


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


def check_account_sequence_numbering_consistency(db, account_number):
    collection = db.account_transactions
    results = find_account_transactions(collection, account_number)

    duplicated_seq_numbers = list(map(lambda x: x[0], filter(lambda x: x[1] > 1, Counter([a._seq for a in results]).items())))
    return duplicated_seq_numbers


def check_credit_card_sequence_numbering_consistency(db, credit_card_number):
    collection = db.credit_card_transactions
    results = find_credit_card_transactions(collection, credit_card_number)

    duplicated_seq_numbers = list(map(lambda x: x[0], filter(lambda x: x[1] > 1, Counter([a._seq for a in results]).items())))
    return duplicated_seq_numbers


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

    diff = list(filter(
        lambda x: x[0] != '?',
        list(Differ().compare(
            list(map(itemgetter(0), hashed_db_transactions)),
            list(map(itemgetter(0), hashed_fetched_transactions))
        ))
    ))

    next_seq_number = 0
    sequence_change_needed = False
    all_fetched_processed = False

    # from pprint import pprint
    # print()
    # pprint(diff)
    # print()

    diverged = []

    for item in diff:

        action = item[0]
        transaction_hash = item[2:]
        # This will be set to None when the current transaction is a db transaction
        # that is not present in the fetched ones. This indicates that this batch has
        # a diversion that will be checked, but shouldn't be a problem
        fetched_transaction = fetched_transactions_by_hash.get(transaction_hash)

        if transaction_hash == hashed_fetched_transactions[-1][0]:
            all_fetched_processed = True

        if action == '+' and fetched_transaction.status_flags.invalid:
            # We have detected a fetched transaction that should not be there, we'll skip it
            # and also try to delete it's counterpart if any diverged transaction has been found so far:
            matching_diverged = list(filter(
                lambda diverged_transaction: diverged_transaction.amount == fetched_transaction.amount and diverged_transaction.transaction_date == fetched_transaction.transaction_date,
                diverged
            ))

            if len(matching_diverged) > 1:
                raise DivergedHistoryError(matching_diverged[0], "Multiple matches found while trying to resolve a diverged history")

            if len(matching_diverged) == 0:
                # Just skip
                break

            yield ('remove', matching_diverged[0])
            diverged = list(filter(lambda diverged_transaction: diverged_transaction != matching_diverged[0], diverged))

        elif action == '+':
            # We have a transaction in fetched that it's not on the database
            new_transaction = deepcopy(fetched_transaction)
            new_transaction._seq = next_seq_number
            yield ('insert', new_transaction)
            next_seq_number += 1
            sequence_change_needed = True
            log_action(new_transaction, '+')

        elif action == ' ' and not sequence_change_needed:
            # this transaction is on both db and fetched transactions
            # so here we only set the next sequence number, that will be
            # be used if we have new fetched transactions at the tail
            # or we need to cascade change sequence numbers
            next_seq_number = db_transactions_by_hash[transaction_hash]._seq + 1
            log_action(db_transactions_by_hash[transaction_hash], 's')

        elif sequence_change_needed and action == ' ':
            # this transaction is on both db and fetched transactions but we inserted
            # something that changed the sequence, so we need to update it
            stored_transaction = db_transactions_by_hash[transaction_hash]
            updated_transaction = deepcopy(stored_transaction)
            updated_transaction._seq = next_seq_number
            yield ('update', updated_transaction)
            next_seq_number += 1
            log_action(updated_transaction, 'u')

        elif action == '-' and all_fetched_processed and sequence_change_needed:
            # this transaction is only on db but as something happened
            # that changed the sequence, so we need to update it
            stored_transaction = db_transactions_by_hash[transaction_hash]
            updated_transaction = deepcopy(stored_transaction)
            updated_transaction._seq = next_seq_number
            yield ('update', updated_transaction)
            next_seq_number += 1
            log_action(updated_transaction, 'u-')

        elif action == '-' and all_fetched_processed and not sequence_change_needed:
            # This will never happen, as the last conditional in the loop breaks it
            # the as soon as all fetched items are processed
            log_action(fetched_transaction, '?')
            pass

        elif action == '-' and not all_fetched_processed:
            diverged.append(db_transactions_by_hash[transaction_hash])

        # After processing the last fetched transaction, if we didn't do
        # anything that broke the sequence numbering, we can stop
        if all_fetched_processed and not sequence_change_needed:
            # print('X Quitting, all fetched processed')
            break

    if diverged:
        raise DivergedHistoryError(db_transactions_by_hash[transaction_hash])
