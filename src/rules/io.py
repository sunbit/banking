from itertools import chain
from functools import partial, reduce
from copy import deepcopy

import operator as operator_module

from common.utils import get_nested_item
from common.logging import get_logger
from . import domain
from .domain import AND, OR
from .domain import MatchCondition, MatchNumericCondition, ValueSetter, ValueAdder

import datatypes
import re


logger = get_logger(name='rules')

FIELD_WRAPPERS = {
    'source': datatypes.Issuer,
    'destination': datatypes.Recipient,
    'category': lambda x: x
}

DEFAULT_FIELD_WRAPPER = str


def Set(fieldname, value):

    return ValueSetter(
        fieldname,
        lambda _: value,
        FIELD_WRAPPERS.get(fieldname, DEFAULT_FIELD_WRAPPER)
    )


def SetFromCapture(fieldname, source, regex, capture_group=0):

    def capture_value(source, regex, transaction):
        field = get_nested_item(transaction, source)
        if isinstance(field, datatypes.TransactionSubject):
            source_value = field.name
        elif isinstance(field, datatypes.UnknownSubject):
            return False
        else:
            source_value = field

        match = re.search(regex, source_value, re.IGNORECASE)
        if match:
            try:
                return match.groups()[capture_group]
            except IndexError:
                return source_value
        else:
            return source_value

    return ValueSetter(
        fieldname,
        partial(capture_value, source, regex),
        FIELD_WRAPPERS.get(fieldname, DEFAULT_FIELD_WRAPPER)
    )


def Add(fieldname, *values):
    return ValueAdder(
        fieldname,
        values
    )


def mark_field_changed(transaction, field):
    setattr(transaction.flags, field, datatypes.DataOrigin.RULES)


def _run_ValueSetter(action, transaction):
    transaction_copy = deepcopy(transaction)
    try:
        raw_value = action.get_value(transaction)
        if isinstance(raw_value, str):
            value = raw_value.format(details=transaction.details, transaction=transaction)
        else:
            value = raw_value
    except (KeyError, AttributeError, TypeError) as exc:
        print('WARNING: Failed to run action {} "{}": {}'.format(action.__class__.__name__, action.fieldname, exc.__repr__()))
        return transaction_copy
    wrapped = action.wrap(value)
    setattr(transaction_copy, action.fieldname, wrapped)
    mark_field_changed(transaction_copy, action.fieldname)
    return transaction_copy


def _run_ValueAdder(action, transaction):
    transaction_copy = deepcopy(transaction)
    for value in action.values:
        field_list = getattr(transaction_copy, action.fieldname)
        if value not in field_list:
            field_list.append(value)

    mark_field_changed(transaction_copy, action.fieldname)
    return transaction_copy


def run_action(transaction, action):
    if isinstance(action, domain.ValueSetter):
        return _run_ValueSetter(action, transaction)

    if isinstance(action, domain.ValueAdder):
        return _run_ValueAdder(action, transaction)


def Match(fieldname, value, regex=None):
    return MatchCondition(fieldname, [value], AND, regex)


def MatchAll(fieldname, *values, regex=None):
    return MatchCondition(fieldname, values, AND, regex)


def MatchAny(fieldname, *values, regex=None):
    return MatchCondition(fieldname, values, OR, regex)


def MatchNumeric(fieldname, value, operator, absolute=False):
    return MatchNumericCondition(
        fieldname,
        value,
        getattr(operator_module, operator),
        absolute
    )


def initial_value(operator):
    if operator == AND:
        return True
    if operator == OR:
        return False


def _check_MatchNumericCondition(condition, transaction):
    field_value = get_nested_item(transaction, condition.fieldname)
    field_value = abs(field_value) if condition.absolute else field_value
    return condition.operator(field_value, condition.value)


def _check_MatchCondition(condition, transaction):
    field = get_nested_item(transaction, condition.fieldname)
    if isinstance(field, datatypes.TransactionSubject):
        field_value = field.name
    elif isinstance(field, datatypes.UnknownSubject):
        return False
    else:
        field_value = field

    def included(ok, value):
        return condition.operator(
            ok,
            value in field_value
        )

    def equals(ok, value):
        return condition.operator(
            ok,
            value == field_value
        )

    def match(ok, value):
        return condition.operator(
            ok,
            bool(re.match(value, field_value, re.IGNORECASE))
        )

    def search(ok, value):
        return condition.operator(
            ok,
            bool(re.search(value, field_value, re.IGNORECASE))
        )

    if isinstance(field_value, list):
        value_checker = included
    elif not condition.regex:
        value_checker = equals
    # Cannot do a regex on a None
    elif field_value is None:
        return False
    if condition.regex == 'search':
        value_checker = search
    elif condition.regex == 'match':
        value_checker = match

    return reduce(
        value_checker,
        condition.values,
        initial_value(condition.operator)
    )


def check_condition(transaction, condition):
    if isinstance(condition, domain.MatchCondition):
        return _check_MatchCondition(condition, transaction)
    if isinstance(condition, domain.MatchNumericCondition):
        return _check_MatchNumericCondition(condition, transaction)


def matching_rules(user_rules, transaction):
    for rule in user_rules:
        if all(map(partial(check_condition, transaction), rule.conditions)):
            yield rule


def apply_rules_to_transaction(user_rules, transaction):
    def process(transaction):
        return reduce(
            run_action,
            chain.from_iterable(
                (rule.actions for rule in matching_rules(user_rules, transaction))
            ),
            transaction
        )
    original_transaction = transaction
    updated_transaction = process(original_transaction)

    needs_reprocessing = original_transaction != updated_transaction
    # We need to reprocess all rules for a transaction in case any
    # action has been executed, as maybe now some other rules needs
    # to be applied. The stop poing is when after processing, no changes are detected.

    while needs_reprocessing:
        original_transaction = updated_transaction
        updated_transaction = process(original_transaction)
        needs_reprocessing = original_transaction != updated_transaction

    return updated_transaction
