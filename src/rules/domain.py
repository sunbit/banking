from operator import and_ as AND
from operator import or_ as OR

from dataclasses import dataclass


@dataclass
class Rule():
    conditions: list
    actions: list


@dataclass
class RuleCondition():
    pass


@dataclass
class RuleAction():
    pass


@dataclass
class MatchCondition(RuleCondition):
    fieldname: str
    values: list
    operator: object
    regex: str = None


@dataclass
class MatchNumericCondition(RuleCondition):
    fieldname: str
    value: list
    operator: object
    absolute: bool = False


@dataclass
class ValueSetter(RuleAction):
    fieldname: str
    get_value: callable
    wrap: callable


@dataclass
class ValueAdder(RuleAction):
    fieldname: str
    values: list
