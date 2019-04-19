from datatypes import TransactionType, Issuer
from rules.io import _check_MatchCondition
from rules.io import Match, MatchAny, MatchAll

from .helpers import make_transaction


def test_match_unset_value_field():
    transaction_0 = make_transaction(transaction_id=None)

    condition_single = Match('transaction_id', 'test_id')
    condition_any = MatchAny('transaction_id', 'test_id')
    condition_all = MatchAll('transaction_id', 'test_id')

    assert _check_MatchCondition(condition_single, transaction_0) is False
    assert _check_MatchCondition(condition_any, transaction_0) is False
    assert _check_MatchCondition(condition_all, transaction_0) is False


def test_match_one_single_value_field():
    transaction_0 = make_transaction(type=TransactionType.PURCHASE)
    transaction_1 = make_transaction(type=TransactionType.ATM_WITHDRAWAL)
    condition = Match('type', TransactionType.PURCHASE)

    assert _check_MatchCondition(condition, transaction_0) is True
    assert _check_MatchCondition(condition, transaction_1) is False


def test_match_any_single_value_field():
    transaction_0 = make_transaction(type=TransactionType.PURCHASE)
    transaction_1 = make_transaction(type=TransactionType.ATM_WITHDRAWAL)
    transaction_2 = make_transaction(type=TransactionType.ISSUED_TRANSFER)

    condition = MatchAny('type', TransactionType.PURCHASE, TransactionType.ATM_WITHDRAWAL)

    assert _check_MatchCondition(condition, transaction_0) is True
    assert _check_MatchCondition(condition, transaction_1) is True
    assert _check_MatchCondition(condition, transaction_2) is False


def test_match_all_single_value_field():
    transaction_0 = make_transaction(type=TransactionType.PURCHASE)

    condition = MatchAll('type', TransactionType.PURCHASE, TransactionType.ATM_WITHDRAWAL)

    assert _check_MatchCondition(condition, transaction_0) is False


def test_match_one_list_value_field():
    transaction_0 = make_transaction(keywords=['ONE', 'TWO', 'THREE'])
    transaction_1 = make_transaction(keywords=['FOUR', 'FIVE', 'SIX'])
    condition = Match('keywords', 'ONE')

    assert _check_MatchCondition(condition, transaction_0) is True
    assert _check_MatchCondition(condition, transaction_1) is False


def test_match_any_list_value_field():
    transaction_0 = make_transaction(keywords=['ONE', 'TWO', 'THREE'])
    transaction_1 = make_transaction(keywords=['FOUR', 'FIVE', 'SIX'])
    transaction_2 = make_transaction(keywords=['SEVEN', 'EIGHT', 'NINE'])

    condition = MatchAny('keywords', 'ONE', 'TWO', 'FOUR')

    assert _check_MatchCondition(condition, transaction_0) is True
    assert _check_MatchCondition(condition, transaction_1) is True
    assert _check_MatchCondition(condition, transaction_2) is False


def test_match_all_list_value_field():
    transaction_0 = make_transaction(keywords=['ONE', 'TWO', 'THREE'])
    transaction_1 = make_transaction(keywords=['ONE', 'TWO', 'THREE', 'FOUR'])
    transaction_2 = make_transaction(keywords=['TWO', 'THREE', 'FOUR'])

    condition = MatchAll('keywords', 'ONE', 'TWO', 'THREE')

    assert _check_MatchCondition(condition, transaction_0) is True
    assert _check_MatchCondition(condition, transaction_1) is True
    assert _check_MatchCondition(condition, transaction_2) is False


def test_match_nested_field():
    transaction_0 = make_transaction(details={'detail1': 'ONE', 'detail2': 'TWO'})

    condition = Match('details.detail1', 'ONE')

    assert _check_MatchCondition(condition, transaction_0) is True


def test_match_regex_value_search():
    transaction_0 = make_transaction(source=Issuer(' xx MatchWord1 MatchWord2 yy'))

    condition_single = Match('source', 'MatchWord1', regex='search')
    condition_any = MatchAny('source', 'MatchWord1', 'MatchWord3', regex='search')
    condition_all = MatchAll('source', 'MatchWord1', 'MatchWord2', regex='search')

    assert _check_MatchCondition(condition_single, transaction_0) is True
    assert _check_MatchCondition(condition_any, transaction_0) is True
    assert _check_MatchCondition(condition_all, transaction_0) is True


def test_match_regex_value_match():
    transaction_0 = make_transaction(source=Issuer('MatchWord125'))

    condition_single = Match('source', r'MatchWord\d+', regex='match')
    condition_any = MatchAny('source', r'MatchWord1\d+', r'MatchWord2\d+', regex='match')
    condition_all = MatchAll('source', r'MatchWord1\d+', r'MatchWord\d+5', regex='match')

    assert _check_MatchCondition(condition_single, transaction_0) is True
    assert _check_MatchCondition(condition_any, transaction_0) is True
    assert _check_MatchCondition(condition_all, transaction_0) is True

