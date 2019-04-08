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
class ValueSetter():
    pass


@dataclass
class MatchKeywords(RuleCondition):
    keywords: list
    operator: object


@dataclass
class MatchDetail(RuleCondition):
    detail_id: str
    value: str


@dataclass
class MatchField(RuleCondition):
    field_id: str
    value: str


@dataclass
class MatchFieldMulti(RuleCondition):
    field_id: str
    values: object
    operator: object


@dataclass
class MatchTransactionType(RuleCondition):
    type: object


@dataclass
class setIssuer(RuleAction):
    value: str


@dataclass
class setRecipient(RuleAction):
    value: str
    regex_group: int = None


@dataclass
class setBankRecipient(RuleAction):
    value: str


@dataclass
class setCategory(RuleAction):
    value: str

@dataclass
class setTag(RuleAction):
    value: str


@dataclass
class setComment(RuleAction):
    value: str
    regex: str = None
    regex_group: str = None


@dataclass
class FormattedString(ValueSetter):
    template: str
