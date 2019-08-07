from selenium import webdriver
from selenium.common.exceptions import ElementNotVisibleException, WebDriverException
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.remote.webelement import WebElement


from functools import partial, wraps

import time

from exceptions import InteractionError, SomethingChangedError
import bank


def catch_selenium_exceptions(original_function):
    @wraps(original_function)
    def element_html(func):
        return func.__self__.get_attribute('outerHTML')

    def wrapped(*args, **kwargs):
        try:
            result = original_function(*args, **kwargs)
        except WebDriverException as exc:
            if 'Other element would receive the click' in exc.msg:
                raise InteractionError(
                    action=original_function.__name__,
                    element=element_html(original_function),
                    suggestion="There's another element visualy over it. It may be a scroll problem or a popup. You can try forcing the click with .forced_click()")
            else:
                raise(exc)
        except ElementNotVisibleException:
            raise InteractionError(
                action=original_function.__name__,
                element=element_html(original_function),
                suggestion="if this element is supposed to be visible at some point, you can add 'visible=True' in the find command that returned the element in first place")
        return result
    return wrapped


def forced_click(element):
    element.parent.execute_script("arguments[0].click()", element)


def wrapped_result(_result):
    def method_wrapper(original_method, *args, **kwargs):
        chain = kwargs.pop('chain', True)
        timeout = kwargs.pop('timeout', 10)
        t0 = time.time()
        while True:
            try:
                action_result = original_method(*args, **kwargs)
            except:
                pass
            else:
                break

            time.sleep(0.1)
            if timeout and (time.time() - t0) > timeout:
                return None
        return wrapped_result(action_result) if chain else action_result

    def filter_wrapper(elements, filter_function):
        return list(map(wrapped_result, filter(filter_function, elements)))

    def focus_wrapper(element):
        element.send_keys(Keys.NULL)
        return wrapped_result(element) if isinstance(element, WebElement) else element

    def select_wrapper(element):
        element.send_keys(Keys.SPACE)
        return wrapped_result(element) if isinstance(element, WebElement) else element

    def clear_wrapper(element):
        element.clear()
        return wrapped_result(element) if isinstance(element, WebElement) else element

    def forced_click_wrapper(element):
        forced_click(element)
        return wrapped_result(element) if isinstance(element, WebElement) else element

    class result_wrapper:
        def __getattr__(self, attribute):
            nonlocal _result

            if attribute == 'filter':
                return partial(
                    filter_wrapper,
                    _result
                )

            if attribute == 'focus':
                return partial(
                    focus_wrapper,
                    _result
                )

            if attribute == 'select':
                return partial(
                    select_wrapper,
                    _result
                )

            if attribute == 'clear':
                return partial(
                    clear_wrapper,
                    _result
                )

            if attribute == 'forced_click':
                return partial(
                    forced_click_wrapper,
                    _result
                )

            attr = getattr(_result, attribute)

            if callable(attr):
                if attr.__name__.startswith('find'):
                    return partial(
                        method_wrapper,
                        attr
                    )
                else:
                    return catch_selenium_exceptions(attr)

            else:
                return attr

    wrapper = result_wrapper()
    result_wrapper.result = _result

    return wrapper


def new(*args, **kwargs):
    headless = kwargs.pop('headless', True)

    chrome_options = Options()
    chrome_options.add_argument("--window-size=1920x800")
    if headless:
        chrome_options.add_argument("--headless")
        chrome_options.add_argument("--disable-extensions")
        chrome_options.add_argument("--disable-dev-shm-usage")
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-gpu")
        chrome_options.add_argument("--disable-impl-side-painting")
        chrome_options.add_argument("--disable-gpu-sandbox")
        chrome_options.add_argument("--disable-accelerated-2d-canvas")
        chrome_options.add_argument("--disable-accelerated-jpeg-decoding")

    _driver = webdriver.Chrome(*args, chrome_options=chrome_options, **kwargs)

    def method_wrapper(original_method, *args, **kwargs):
        timeout = kwargs.pop('timeout', 10)
        wait_until_visible = kwargs.pop('visible', False)
        raise_if_not_found = kwargs.pop('do_raise', True)

        t0 = time.time()
        while True:
            try:
                element = original_method(*args, **kwargs)
            except:
                pass
            else:
                if element:
                    if not wait_until_visible:
                        break
                    else:
                        if element.is_displayed():
                            break

            time.sleep(0.1)
            if timeout and (time.time() - t0) > timeout:
                if raise_if_not_found:
                    raise SomethingChangedError(args[0])
                else:
                    return None

        return wrapped_result(element)

    class driver_wrapper:
        def __getattr__(self, attribute):
            nonlocal _driver
            attr = getattr(_driver, attribute)

            if attribute.startswith('find'):
                return partial(
                    method_wrapper,
                    attr
                )
            else:
                return attr

    @property
    def driver(self):
        return _driver

    wrapper = driver_wrapper()
    wrapper.driver = _driver

    return wrapper


