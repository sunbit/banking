
from itertools import chain
from functools import partial, reduce
from copy import deepcopy


from . import domain
from .domain import AND, OR

import datatypes
import re


def set_field_changed(transaction, field):
    setattr(transaction.flags, field, datatypes.DataOrigin.RULES)


def run_action(transaction, action):
    new_transaction = deepcopy(transaction)
    if isinstance(action, domain.setIssuer):
        new_transaction.source = datatypes.Issuer(action.value.format(details=transaction.details))
        set_field_changed(new_transaction, 'source')
        return new_transaction
    if isinstance(action, domain.setRecipient):
        formatted_value = action.value.format(details=transaction.details)
        if action.regex_group is not None:
            new_destination = re.search(formatted_value, transaction.destination.name).groups()[action.regex_group]
        else:
            new_destination = formatted_value
        new_transaction.destination = datatypes.Recipient(new_destination)
        set_field_changed(new_transaction, 'destination')
        return new_transaction
    if isinstance(action, domain.setComment):
        try:
            comment = action.value.format(details=transaction.details)
        except Exception as exc:
            print('WARNING: Failed to run action {} "{}": {}'.format(action.__class__.__name__, action.value, exc.__repr__()))
            return transaction
        if action.regex is not None:
            match = re.search(action.regex, comment)
            if not match:
                print('WARNING: Failed to run action {} "{}": Regex match failed'.format(action.__class__.__name__, action.value))
                return transaction
            comment = match.groups()[action.regex_group]
        new_transaction.comment = comment
        set_field_changed(new_transaction, 'comment')
        return new_transaction
    if isinstance(action, domain.setCategory):
        new_transaction.category = action.value.format(details=transaction.details)
        set_field_changed(new_transaction, 'category')
        return new_transaction
    if isinstance(action, domain.setTag):
        new_transaction.tags.append(action.value.format(details=transaction.details))
        set_field_changed(new_transaction, 'tags')
        return new_transaction


def initial_value(operator):
    if operator == AND:
        return True
    if operator == OR:
        return False


def check_condition(transaction, condition):

    if isinstance(condition, domain.MatchTransactionType):
        return transaction.type is condition.type
    if isinstance(condition, domain.MatchKeywords):
        def included(ok, keyword):
            return condition.operator(
                ok,
                keyword in transaction.keywords
            )
        return reduce(
            included,
            condition.keywords,
            {
                AND: True,
                OR: False
            }.get(condition.operator)
        )
    if isinstance(condition, domain.MatchDetail):
        detail_value = transaction.details.get(condition.detail_id)
        return (
            False if detail_value is None
            else (re.search(r'{}'.format(condition.value), detail_value, re.IGNORECASE) is not None)
        )

    if isinstance(condition, domain.MatchFieldMulti):
        field = getattr(transaction, condition.field_id)
        if isinstance(field, datatypes.TransactionSubject):
            field_value = field.name
        else:
            field_value = str(field)

        if field_value is None:
            return False

        def matches(ok, condition_value):
            return condition.operator(
                ok,
                bool(re.search(r'{}'.format(condition_value), field_value, re.IGNORECASE)),
            )

        return reduce(
            matches,
            condition.values,
            {
                AND: True,
                OR: False
            }.get(condition.operator)
        )

    if isinstance(condition, domain.MatchField):
        field = getattr(transaction, condition.field_id)
        if isinstance(field, datatypes.TransactionSubject):
            field_value = field.name
        else:
            field_value = str(field)

        return False if field_value is None else re.search(r'{}'.format(condition.value), field_value, re.IGNORECASE)


def matching_rules(user_rules, transaction):
    for rule in user_rules:
        if all(map(partial(check_condition, transaction), rule.conditions)):
            yield rule


def apply_rules_to_transaction(user_rules, transaction):
    updated_transaction = reduce(
        run_action,
        chain.from_iterable(
            (rule.actions for rule in matching_rules(user_rules, transaction))
        ),
        transaction
    )
    return updated_transaction
