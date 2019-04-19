from rules.io import Set, SetFromCapture, Add
from rules.io import _run_ValueSetter, _run_ValueAdder

from .helpers import make_transaction, TestClass
import datatypes


def test_default_value_setter():

    transaction = make_transaction()
    action = Set('comment', 'A comment')

    new_transaction = _run_ValueSetter(action, transaction)

    assert isinstance(new_transaction.comment, str)
    assert new_transaction.comment == 'A comment'
    assert new_transaction.comment != transaction.comment


def test_wrapped_source_field_setter():

    transaction = make_transaction()
    action = Set('source', 'My issuer')

    new_transaction = _run_ValueSetter(action, transaction)

    assert isinstance(new_transaction.source, datatypes.Issuer)
    assert new_transaction.source.name == 'My issuer'
    assert new_transaction.source != transaction.source


def test_wrapped_destination_field_setter():

    transaction = make_transaction()
    action = Set('destination', 'My recipient')

    new_transaction = _run_ValueSetter(action, transaction)

    assert isinstance(new_transaction.destination, datatypes.Recipient)
    assert new_transaction.destination.name == 'My recipient'
    assert new_transaction.destination != transaction.destination


def test_value_adder():

    transaction = make_transaction(tags=['tag0'])

    action_0 = Add('tags', 'tag1')
    action_1 = Add('tags', 'tag0', 'tag1')

    new_transaction = _run_ValueAdder(action_0, transaction)

    assert set(new_transaction.tags) == set(['tag0', 'tag1'])
    assert set(new_transaction.tags) != set(transaction.tags)

    new_transaction = _run_ValueAdder(action_1, transaction)

    assert set(new_transaction.tags) == set(['tag0', 'tag1'])
    assert set(new_transaction.tags) != set(transaction.tags)


def test_value_format_without_wrapper():
    transaction = make_transaction(details={'field1': 'foo'})
    action = Set('comment', 'A comment with detail: {details[field1]}')

    new_transaction = _run_ValueSetter(action, transaction)

    assert isinstance(new_transaction.comment, str)
    assert new_transaction.comment == 'A comment with detail: foo'
    assert new_transaction.comment != transaction.comment


def test_value_format_without_wrapper_attribute():
    transaction = make_transaction(source=datatypes.Issuer('Test Issuer'))
    action = Set('comment', 'Source: {transaction.source.name}')

    new_transaction = _run_ValueSetter(action, transaction)

    assert isinstance(new_transaction.comment, str)
    assert new_transaction.comment == 'Source: Test Issuer'
    assert new_transaction.comment != transaction.comment


def test_value_format_with_wrapper():
    transaction = make_transaction(details={'field1': 'foo'})
    action = Set('source', 'Source with detail: {details[field1]}')

    new_transaction = _run_ValueSetter(action, transaction)

    assert isinstance(new_transaction.source, datatypes.Issuer)
    assert new_transaction.source.name == 'Source with detail: foo'
    assert new_transaction.source != transaction.source


def test_value_format_missing_detail():
    transaction = make_transaction(details={'field1': 'foo'})
    action = Set('comment', 'A comment with detail: {details[field2]}')

    new_transaction = _run_ValueSetter(action, transaction)

    assert new_transaction.comment == transaction.comment


def test_value_format_missing_field():
    transaction = make_transaction()
    action = Set('comment', 'A comment with detail: {transaction.source.unknown}')

    new_transaction = _run_ValueSetter(action, transaction)

    assert new_transaction.comment == transaction.comment


def test_value_format_from_capture():
    transaction = make_transaction(destination=datatypes.Recipient('PAYPAL *MOLESKINE'))
    action = SetFromCapture('destination', source='destination.name', regex=r'Paypal\s+\*(.*)')

    new_transaction = _run_ValueSetter(action, transaction)

    assert isinstance(new_transaction.destination, datatypes.Recipient)
    assert new_transaction.destination.name == 'MOLESKINE'
    assert new_transaction.destination != transaction.destination
