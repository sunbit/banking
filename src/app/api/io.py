from copy import deepcopy
from dataclasses import is_dataclass
from enum import Enum
from datetime import datetime


def encode_date(dt):
    return dt.strftime('%Y-%m-%dT%H:%M:%S')


def encode_account(account_config, include_children=True):
    account = deepcopy(account_config.__dict__)
    if not include_children:
        account.pop('cards', None)
    return account


def encode_transaction(transaction):
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

    return recurse(transaction)
