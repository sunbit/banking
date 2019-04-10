from dataclasses import is_dataclass
from difflib import Differ
from enum import Enum
from hashlib import sha1
from operator import itemgetter

import re

import datatypes


class DatabaseMatchError(Exception):
    pass


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

        custom_type_class, custom_type_name = obj.pop('__type__').split('::')

        if custom_type_class == 'dataclass':
            CustomDataclass = getattr(datatypes, custom_type_name)
            return CustomDataclass(**obj)
        elif custom_type_class == 'enum':
            CustomEnum = getattr(datatypes, custom_type_name)
            return CustomEnum[obj['name']]
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

    decoded = recurse(document)
    return decoded


def find_transaction(collection, account_number, transaction):
    results = list(collection.find(
        {
            'account.number': account_number,
            'transaction_date': transaction.transaction_date,
            'amount': transaction.amount,
            'balance': transaction.balance
        },
        sort=[('_seq', 1)]
    ))

    if not results:
        return None

    if len(results) > 1:
        raise DatabaseMatchError('Found more than one match for a transaction, check the algorithm')

    return decode_transaction(results[0])


def find_transactions_since(collection, account_number, transaction):
    if transaction is None:
        return []

    results = list(collection.find(
        {
            'account.number': account_number,
            '_seq': {"$gte": transaction._seq}
        },
        sort=[('_seq', 1)]
    ))

    if not results:
        return []

    return list(map(decode_transaction, results))


def transactions_match(transaction_1, transaction_2):
    if transaction_1 is None or transaction_2 is None:
        return False

    def field_equals(field):
        return getattr(transaction_1, field) == getattr(transaction_2, field)

    return all(
        map(
            field_equals,
            ['transaction_date', 'amount', 'balance']
        )
    )


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


def select_new_transactions(fetched_transactions, db_transactions):

    def transaction_string(transaction):
        return '{m.transaction_date} {m.amount} {m.balance}'.format(m=transaction).encode('utf-8')

    hashed_fetched_transactions = [
        (
            sha1(transaction_string(transaction)).hexdigest(),
            transaction,
        )
        for transaction in fetched_transactions
    ]

    hashed_db_transactions = [
        (
            sha1(transaction_string(transaction)).hexdigest(),
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

    from pprint import pprint
    pprint(diff)
    print()

    for item in diff:

        action = item[0]
        transaction_hash = item[2:]

        if transaction_hash == hashed_fetched_transactions[-1][0]:
            print('! Last fetched item')
            all_fetched_processed = True

        if action == '+':
            # We have a transaction in fetched that it's not on the database
            transaction = fetched_transactions_by_hash[transaction_hash]
            new_transaction = datatypes.AccountTransaction(_seq=next_seq_number, **transaction.__dict__)
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
            updated_transaction = datatypes.AccountTransaction(**stored_transaction.__dict__)
            updated_transaction._seq = next_seq_number
            yield ('update', updated_transaction)
            next_seq_number += 1
            log_action(updated_transaction, 'u')

        elif action == '-' and all_fetched_processed and sequence_change_needed:
            # this transaction is only on db but as something happened
            # that changed the sequence, so we need to update it
            stored_transaction = db_transactions_by_hash[transaction_hash]
            updated_transaction = datatypes.AccountTransaction(**stored_transaction.__dict__)
            updated_transaction._seq = next_seq_number
            yield ('update', updated_transaction)
            next_seq_number += 1
            log_action(updated_transaction, 'u-')

        elif action == '-' and all_fetched_processed and not sequence_change_needed:
            # This will never happen, as the last conditional in the loop breaks it
            # the as soon as all fetched items are processed
            log_action(transaction, '?')
            pass

        elif action == '-' and not all_fetched_processed:
            # This will never happen, as the last conditional in the loop breaks it
            # the as soon as all fetched items are processed
            raise DatabaseMatchError('transaction history has diverged')

        # After processing the last fetched transaction, if we didn't do
        # anything that broke the sequence numbering, we can stop
        if all_fetched_processed and not sequence_change_needed:
            print('X Quitting, all fetched processed')
            break

    # import ipdb;ipdb.set_trace()

    # next_seq_number = 0 if current_db_transaction is None else current_db_transaction._seq

    # while current_fetched_transaction is not None:
    #     # If both iterators turn None at the same time, the loop will exit, so if we have a
    #     # negative match because a None, it can be only because the db iterator yielded none
    #     # otherwise we would have left the loop

    #     if transactions_match(current_fetched_transaction, current_db_transaction):
    #         # We have a match, so we don't need to add anything, an we can skip both
    #         # iterators to the next one
    #         if current_db_transaction._seq != next_seq_number:
    #             current_db_transaction._seq = next_seq_number
    #             yield ('update', current_db_transaction)

    #         current_fetched_transaction = next(fetched, None)
    #         current_db_transaction = next(on_db, None)
    #         next_seq_number += 1

    #     elif current_db_transaction is None:
    #         # We reached a point where all the iterated items until here exist on the database
    #         # so, starting now, all fetched items should be added to the database and pick the next one
    #         yield ('insert', datatypes.AccountTransaction(_seq=next_seq_number, **current_fetched_transaction.__dict__))
    #         current_fetched_transaction = next(fetched, None)
    #         next_seq_number += 1

    #     elif current_fetched_transaction is None:
    #         # This will never happen
    #         pass
    #     else:
    #         # For now we assume that when this happens it can only be because missing
    #         # transactions are added, in any position of the sequence, but sequence is not changed
    #         yield ('insert', datatypes.AccountTransaction(_seq=next_seq_number, **current_fetched_transaction.__dict__))
    #         current_fetched_transaction = next(fetched, None)
    #         next_seq_number += 1

    #         #raise DatabaseMatchError('transaction history has diverged')
