from common.utils import get_nested_item
from functools import partial
from itertools import chain


import re
import unicodedata


def parse_bool(b):
    return {
        'true': True,
        'false': False,
        '1': True,
        '0': False
    }.get(str(b).lower(), bool(b))


def normalize(text):
    normalized = (
        unicodedata.normalize('NFKD', text)
        .encode('ASCII', errors='ignore')
        .decode('utf-8')
        .upper()
    )
    return normalized


def cleanup(text):
    character_replacement = re.sub(r'\.', '', text)
    character_cleanup = re.sub(r'[^A-Z0-9 ]', ' ', character_replacement)
    dup_space_cleanup = re.sub(r' +', ' ', character_cleanup)
    return dup_space_cleanup


def tokenize(text):
    return text.split(' ')


def extract_keywords(literals):
    valid_literals = filter(lambda literal: literal is not None, literals)
    normalized_literals = map(normalize, valid_literals)
    clean_literals = map(cleanup, normalized_literals)
    tokenized = map(tokenize, clean_literals)
    unique_keywords = set(chain.from_iterable(tokenized))
    filter_single_chars = filter(lambda token: len(token) > 2, unique_keywords)
    return list(filter_single_chars)


def extract_literals(movement, field_list):
    literals = map(
        partial(get_nested_item, movement),
        field_list
    )

    return literals
