from functools import reduce
import re
from dataclasses import is_dataclass
from enum import Enum, EnumMeta
from json import JSONEncoder, JSONDecoder
import datatypes
import time
import traceback
from functools import wraps
from exceptions import RetryException


def parse_bool(value):
    return str(value).upper() in ('1', 'TRUE')


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


def traceback_summary(original_traceback, original_exception):
    """
        Returns a one line summary of the exception focusing on the last line of the codebase
        that triggered the exception.
    """
    exception_lines = re.findall(r'File\s+".*?src/(.*?).py".*?line\s+(\d+),\s+in\s+(.*?)\n\s+([^\n]+)\n', original_traceback, re.MULTILINE | re.DOTALL)
    if len(exception_lines) == 0:
        return "Couldn't parse traceback, here's the raw one:\n" + original_traceback
    file, line, function, code = exception_lines[-1]

    return "{exception}: {message}. Triggered at {module}.{function}L{line} [`{code}`]".format(
        exception=original_exception.__class__.__name__,
        message=str(original_exception),
        module=file.replace('/', '.'),
        function=function,
        line=line,
        code=code
    )


def retry(exceptions, tries=4, delay=3, backoff=2, logger=None, do_raise=True):
    def deco_retry(f):

        @wraps(f)
        def f_retry(*args, **kwargs):
            mtries, mdelay = tries, delay
            while mtries > 1:
                try:
                    return f(*args, **kwargs)
                except exceptions as exc:
                    msg = '{}, Retrying in {} seconds...'.format(exc, mdelay)
                    if logger:
                        logger.warning(msg)
                    else:
                        print(msg)
                    time.sleep(mdelay)
                    mtries -= 1
                    mdelay *= backoff
                    last_raised_exception = exc
                    last_raised_traceback = traceback.format_exc()

            # If we reach here, all retries have failed
            # raise the custom exception or trigger the original one
            if do_raise:
                raise RetryException("Exception raised after {tries} tries: {trigger}".format(
                    tries=tries,
                    trigger=traceback_summary(last_raised_traceback, last_raised_exception)
                ))

            return f(*args, **kwargs)
        return f_retry
    return deco_retry
