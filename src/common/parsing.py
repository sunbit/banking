from functools import reduce, partial
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


def get_nested_item(dictionary, xpath, default=None):

    def getitem(d, key):
        match = re.match(r'\[(\d+)\]', key)
        if match:
            index = int(match.groups()[0])
            return d[index]
        else:
            return d.get(key)
    try:
        return reduce(getitem, xpath.split('.'), dictionary)
    except TypeError:
        return default
    except AttributeError:
        return default


def extract_keywords(literals):
    valid_literals = filter(lambda literal: literal is not None, literals)
    normalized_literals = map(normalize, valid_literals)
    clean_literals = map(cleanup, normalized_literals)
    tokenized = map(tokenize, clean_literals)
    unique_keywords = set(chain.from_iterable(tokenized))
    filter_single_chars = filter(lambda token: len(token) > 2, unique_keywords)
    return list(filter_single_chars)


def extract_details(movement, detail_specs):

    def get_value(detail):
        value = get_nested_item(movement, detail.item_path)
        if value is None:
            return None

        if detail.regex is not None:
            match = re.search(detail.regex, value)
            return match.groups()[0] if match else None
        else:
            return value

    values = filter(
        lambda detail: detail[1] is not None,
        zip(
            map(lambda detail: detail.detail_id, detail_specs),
            map(
                get_value,
                detail_specs
            )
        )
    )

    return dict(set(values))


def extract_literals(movement, field_list):
    def unrolled_field_list():
        for field in field_list:
            if '[]' in field:
                for i in range(len(get_nested_item(movement, field.split('.[]')[0]))):
                    yield field.replace('[]', '[{}]'.format(i))
            else:
                yield field

    literals = map(
        partial(get_nested_item, movement),
        unrolled_field_list()
    )

    return literals
