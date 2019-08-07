from scrapper.scripts import xhr_intercept_response
from common.logging import get_logger
from itertools import chain
from common.utils import retry

import json
import time


from selenium.common.exceptions import (
    TimeoutException,
    WebDriverException
)

FIX_NULL_DATE_ACCOUNT = """
try {{
  arg = JSON.parse(arguments[0]);
  if (arg.hasOwnProperty('filter')) {{
        arg.filter.dates.from = '{from_date}'
        arg.filter.dates.to = '{to_date}'
        arguments[0] = JSON.stringify(arg)

        document.createElement('div');
        fixed.id = 'fixed_date';
        document.body.appendChild(fixed);
  }}
}}
catch (e) {{
    console.log('PASS')
}}
"""

FIX_NULL_DATE_CREDIT_CARD = """
try {{
  arg = JSON.parse(arguments[0]);
  if (arg.hasOwnProperty('searchFilters')) {{
        arg.searchFilters.transactionDate.from = '{from_date}'
        arg.searchFilters.transactionDate.to = '{to_date}'
        arguments[0] = JSON.stringify(arg)

        document.createElement('div');
        fixed.id = 'fixed_date';
        document.body.appendChild(fixed);
  }}
}}
catch (e) {{
    console.log('PASS')
}}
"""

logger = get_logger(name='scrapper')


def log(text):
    logger.debug(text)


def encode_date(dt):
    return dt.strftime('%d/%m/%Y')


@retry(exceptions=(TimeoutException, WebDriverException), logger=logger)
def login(browser, username, password):
    log('Loading BBVA main page')
    browser.get('https://www.bbva.es')
    browser.find_element_by_css_selector('#aceptarGDPR', visible=True).click()

    log('Opening login form')
    browser.find_elements_by_tag_name('button').filter(lambda button: 'entrar' in button.text.lower())[0].click()

    log('Filling login form')
    browser.find_element_by_name('text_eai_user').send_keys(username)
    browser.find_element_by_name('text_eai_password').send_keys(password)

    log('Submitting login')
    browser.find_element_by_name('acceder').click()

    log('Waiting login to finish')
    browser.find_element_by_css_selector('#t-main-content', visible=True, timeout=20)


@retry(exceptions=(TimeoutException, WebDriverException), logger=logger)
def get_account_transactions(browser, account_number, from_date, to_date):

    browser.get('https://web.bbva.es/index.html')

    log('Loading BBVA account page')
    browser.find_elements_by_css_selector('p[role=link').filter(lambda element: account_number in element.text)[0].forced_click()

    log('Loading account advanced search')
    browser.find_element_by_css_selector('ul.menuPestanas span.consultas').forced_click()
    browser.find_element_by_css_selector('.busquedaAvanzada[role=button]', visible=True).click()

    log('Filling date query parameters')
    browser.find_element_by_id('fechaDesdeQuery').focus().clear().send_keys(encode_date(from_date))
    browser.find_element_by_id('fechaHastaQuery').focus().clear().send_keys(encode_date(to_date))

    time.sleep(2)  # To try to avoid the null values in the date filter request
    log('Setting up XHR request interceptor')

    script = xhr_intercept_response(
        match_url="accountTransactionsAdvancedSearch",
        output="interceptedResponse",
        # This will modify the date in the request so the full hour is set and we get all transactions
        request_intercept_script=FIX_NULL_DATE_ACCOUNT.format(
            from_date=from_date.strftime('%Y-%m-%dT00:00:00Z'),
            to_date=to_date.strftime('%Y-%m-%dT%H:%M:%SZ')
        )
    )
    browser.driver.execute_script(script)

    log('Launching the initial search')
    browser.find_elements_by_css_selector('*[role=link').filter(lambda element: 'Buscar' in element.text)[0].focus().click()

    intercepted_responses = []
    intercepted_responses_count = 0
    still_have_results = True

    # Iterate trough all the infinite scrolling pagination
    while still_have_results:
        while intercepted_responses_count == len(intercepted_responses):
            # Inner Loop to wait for the page to load and push the new transactions
            browser.find_element_by_id("interceptedResponse")
            intercepted_json = browser.execute_script("return JSON.stringify(document.getElementById('interceptedResponse').responses)")
            intercepted_responses = json.loads(intercepted_json)
            time.sleep(0.1)

        intercepted_responses_count = len(intercepted_responses)
        still_have_results = False if intercepted_responses[-1] is None else intercepted_responses[-1]['pagination'].get('nextPage', False)

        # Trigger infinte scrolling by going to the page bottom
        browser.execute_script("window.scrollTo(0, document.body.scrollHeight);")
        log('Loading more results')

        time.sleep(0.1)

    fixed_date = browser.execute_script("return document.getElementById('fixed_date')")
    log('Fixed date: {}'.format(fixed_date))

    # Results come from newer to older, we want it the other way around, that why we reverse them
    results = list(reversed(list((chain.from_iterable([response['accountTransactions'] for response in intercepted_responses if response is not None])))))
    return results


@retry(exceptions=(TimeoutException, WebDriverException), logger=logger)
def get_credit_card_transactions(browser, card_number, from_date, to_date):

    browser.get('https://web.bbva.es/index.html')

    log('Locate card and load it\'s detail page')
    browser.find_element_by_xpath('//p[@role="link"][contains(text(), "{}")]'.format(card_number)).forced_click()

    log('Open advanced search')
    browser.find_element_by_xpath('//span[contains(@class, "consulta")]').forced_click()
    browser.find_element_by_css_selector('p.busquedaAvanzada[role="button"]', visible=True).forced_click()

    log('Filling date query parameters')
    browser.find_element_by_css_selector('input#fechaDesde').focus().clear().send_keys(encode_date(from_date))
    browser.find_element_by_css_selector('input#fechaHasta').focus().clear().send_keys(encode_date(to_date))

    time.sleep(2)
    log('Setting up XHR request interceptor')
    script = xhr_intercept_response(
        match_url="listIntegratedCardTransactions",
        output="interceptedResponse",
        request_intercept_script=FIX_NULL_DATE_CREDIT_CARD.format(
            from_date=from_date.strftime('%Y-%m-%dT00:00:00Z'),
            to_date=to_date.strftime('%Y-%m-%dT%H:%M:%SZ')
        )
    )
    browser.driver.execute_script(script)

    log('Launching the initial search')
    time.sleep(2)
    browser.find_element_by_xpath('//*[@role="link"][contains(text(), "Buscar")]').focus().click()

    intercepted_responses = []
    intercepted_responses_count = 0
    still_have_results = True

    # Iterate trough all the infinite scrolling pagination
    while still_have_results:
        while intercepted_responses_count == len(intercepted_responses):
            # Inner Loop to wait for the page to load and push the new transactions
            browser.find_element_by_id("interceptedResponse")
            intercepted_json = browser.execute_script("return JSON.stringify(document.getElementById('interceptedResponse').responses)")
            intercepted_responses = json.loads(intercepted_json)
            time.sleep(0.1)

        intercepted_responses_count = len(intercepted_responses)
        still_have_results = False if intercepted_responses[-1] is None else intercepted_responses[-1].get('moreResults', False)

        # Trigger infinte scrolling by going to the page bottom
        browser.execute_script("window.scrollTo(0, document.body.scrollHeight);")
        log('Loading more results')
        time.sleep(0.1)

    # Results come from newer to older, we want it the other way around, that why we reverse them
    results = list(reversed(list(chain.from_iterable([response['cardsTransactions'] for response in intercepted_responses if response is not None]))))
    return results
