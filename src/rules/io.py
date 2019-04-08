
from itertools import chain
from functools import partial, reduce
from copy import deepcopy


from . import domain
from .domain import AND, OR

import datatypes
import re


def set_field_changed(movement, field):
    setattr(movement.flags, field, datatypes.DataOrigin.RULES)


def run_action(movement, action):
    new_movement = deepcopy(movement)
    if isinstance(action, domain.setIssuer):
        new_movement.source = datatypes.Issuer(action.value.format(details=movement.details))
        set_field_changed(new_movement, 'source')
        return new_movement
    if isinstance(action, domain.setRecipient):
        formatted_value = action.value.format(details=movement.details)
        if action.regex_group is not None:
            new_destination = re.search(formatted_value, movement.destination.name).groups()[action.regex_group]
        else:
            new_destination = formatted_value
        new_movement.destination = datatypes.Recipient(new_destination)
        set_field_changed(new_movement, 'destination')
        return new_movement
    if isinstance(action, domain.setComment):
        comment = action.value.format(details=movement.details)
        if action.regex is not None:
            comment = re.search(action.regex, comment).groups()[action.regex_group]
        new_movement.comment = comment
        set_field_changed(new_movement, 'comment')
        return new_movement
    if isinstance(action, domain.setCategory):
        new_movement.category = action.value.format(details=movement.details)
        set_field_changed(new_movement, 'category')
        return new_movement
    if isinstance(action, domain.setTag):
        new_movement.tags.append(action.value.format(details=movement.details))
        set_field_changed(new_movement, 'tags')
        return new_movement


def initial_value(operator):
    if operator == AND:
        return True
    if operator == OR:
        return False


def check_condition(movement, condition):

    if isinstance(condition, domain.MatchTransactionType):
        return movement.type is condition.type
    if isinstance(condition, domain.MatchKeywords):
        def included(ok, keyword):
            return condition.operator(
                ok,
                keyword in movement.keywords
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
        detail_value = movement.details.get(condition.detail_id)
        return (
            False if detail_value is None
            else (re.search(r'{}'.format(condition.value), detail_value, re.IGNORECASE) is not None)
        )

    if isinstance(condition, domain.MatchFieldMulti):
        field = getattr(movement, condition.field_id)
        if isinstance(field, datatypes.TransactionSubject):
            field_value = field.name
        else:
            field_value = str(field)

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
        field = getattr(movement, condition.field_id)
        if isinstance(field, datatypes.TransactionSubject):
            field_value = field.name
        else:
            field_value = str(field)

        return False if field_value is None else re.search(r'{}'.format(condition.value), field_value, re.IGNORECASE)


def matching_rules(user_rules, movement):
    for rule in user_rules:
        if all(map(partial(check_condition, movement), rule.conditions)):
            yield rule


def apply_rules_to_movement(user_rules, movement):
    updated_movement = reduce(
        run_action,
        chain.from_iterable(
            (rule.actions for rule in matching_rules(user_rules, movement))
        ),
        movement
    )
    return updated_movement
