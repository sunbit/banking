from functools import reduce
import re
from dataclasses import is_dataclass
from enum import Enum, EnumMeta
from json import JSONEncoder, JSONDecoder
import datatypes


def get_nested_item(dictionary, xpath, default=None):

    def getitem(d, key):
        match = re.match(r'\[(\d+)\]', key)
        if match:
            index = int(match.groups()[0])
            return d[index]
        else:
            try:
                return d[key]
            except (KeyError, TypeError):
                try:
                    return getattr(d, key)
                except AttributeError:
                    return None
                except Exception:
                    return None
            except Exception:
                return None
    try:
        return reduce(getitem, xpath.split('.'), dictionary)
    except TypeError:
        return default
    except IndexError:
        # in case we do a xxx.[0].fsdf and the aray is not there
        return default
    except AttributeError:
        return default


class AutoJSONDecoder(JSONDecoder):

    @staticmethod
    def custom_decoder(obj):
        custom_datatype_name = obj.pop('__type__', None)
        if custom_datatype_name is None:
            return obj

        custom_datatype_object = getattr(datatypes, custom_datatype_name)

        if isinstance(custom_datatype_object, EnumMeta):
            return custom_datatype_object[obj['name']]

        if is_dataclass(custom_datatype_object):
            return custom_datatype_object(**obj)

    def __init__(self, *args, **kwargs):
        kwargs['object_hook'] = self.custom_decoder
        return super(AutoJSONDecoder, self).__init__(*args, **kwargs)


class AutoJSONEncoder(JSONEncoder):
    def default(self, obj):

        if isinstance(obj, Enum):
            return {
                'name': obj.name,
                '__type__': obj.__class__.__name__
            }

        if is_dataclass(obj):
            raw_dictionary = obj.__dict__
            raw_dictionary['__type__'] = obj.__class__.__name__
            return raw_dictionary

        return JSONEncoder.default(self, obj)
