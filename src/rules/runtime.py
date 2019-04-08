from functools import partial

from .io import apply_rules_to_movement


def apply(rules, movements):
    return list(
        map(
            partial(
                apply_rules_to_movement,
                rules
            ),
            movements
        )
    )


def load():
    from rules.user import _rules
    return _rules
