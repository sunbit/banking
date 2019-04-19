
import pytest

from common.utils import get_nested_item
from .helpers import TestClass


TEST_DICT = {
    "root_value": 0,
    "level_1": {
        "value": 1,
        "level1_list": [
            {"value": 2},
            {"value": 3},
            {"value": 4}
        ],
        "level2": {
            "value": 5,
            "level_3": {"value": 6}
        }
    },
    "level_1_dataclass": TestClass(att1='test', att2={'value': 7})
}

TEST_DATACLASS = TestClass(
    att1='0',
    att2={
        'field_0': 0,
        'level_1': {'value': 1},
        'level_2': TestClass(att1='test', att2={'value': 2})
    }
)

testdata = {
    "Get value at root": [TEST_DICT, 'root_value', 0],
    "Get value level1": [TEST_DICT, 'level_1.value', 1],
    "Get value level3": [TEST_DICT, 'level_1.level2.level_3.value', 6],
    "Get value level1 list": [TEST_DICT, 'level_1.level1_list.[1].value', 3],
    "Get level 1 dataclass attribute": [TEST_DICT, 'level_1_dataclass.att2.value', 7],

    "Get dataclass value at root": [TEST_DATACLASS, 'att1', '0'],
    "Get dataclass value at level 0": [TEST_DATACLASS, 'att2.field_0', 0],
    "Get dataclass value at level 1": [TEST_DATACLASS, 'att2.level_1.value', 1],
    "Get dataclass value at dataclass level": [TEST_DATACLASS, 'att2.level_2.att2.value', 2],

}

testdata_values = list(testdata.values())
testdata_ids = list(testdata.keys())


@pytest.mark.parametrize("obj,path,value", testdata_values, ids=testdata_ids)
def test_nested_item_with_dict(obj, path, value):
    assert get_nested_item(obj, path) == value
