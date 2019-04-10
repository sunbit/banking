from functools import partial

from .io import apply_rules_to_transaction


def apply(rules, transactions):
    return list(
        map(
            partial(
                apply_rules_to_transaction,
                rules
            ),
            transactions
        )
    )


def load():
    from rules.user import _rules
    return _rules
