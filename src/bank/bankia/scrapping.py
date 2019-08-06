from itertools import chain

import json
import re
import time

from common.logging import get_logger
from exceptions import ScrappingError
from scrapper.scripts import xhr_intercept_response
from scrapper.driver import forced_click


logger = get_logger(name='scrapper')


def log(text):
    logger.debug(text)


def encode_date(dt):
    return dt.strftime('%d/%m/%Y')


def login(browser, username, password):
    log('Loading BANKIA main page')
    browser.get('https://www.bankia.es')
    try:
        browser.driver.find_element_by_css_selector('a#CybotCookiebotDialogBodyButtonAccept').click()
    except:
        log('Timeout trying to click on cookie accept button, continuing anyway')

    log('Opening login form')
    browser.find_element_by_css_selector('a.fc-openLogin').click()
    browser.driver.switch_to_frame(browser.find_element_by_id('login-iframe').result)

    log('Filling login form')
    browser.find_element_by_css_selector('form[name=formLogin] input#user').send_keys(username)
    browser.find_element_by_css_selector('form[name=formLogin] input#password').send_keys(password)

    log('Submitting login')
    browser.find_element_by_css_selector('form[name=formLogin] button[type=submit]').click()

    # Close popup if any
    log('Waiting for popups to close them')
    modal_close_buttons = browser.find_elements_by_css_selector('div.modal button', timeout=10, do_raise=False)
    if modal_close_buttons:
        buttons = modal_close_buttons.filter(lambda el: 'cerrar' in el.text.lower())
        if buttons:
            buttons[0].forced_click()
            log('Popup closed')
        else:
            log('No popups found')
    else:
        log('No popups found')


def get_account_transactions(browser, account_number, from_date, to_date):

    log('Loading BANKIA account list page')
    browser.get('https://www.bankia.es/oficina/particulares/#/cuentas')

    # Wait for page rendering all elements, otherwise the next queries change at some
    # point and the resulting elements are inusable afterwards
    time.sleep(1)

    log('Locating account row')
    account_matcher = re.compile(r'.*?' + ''.join([r'\s*{}'.format(a) for a in account_number]), re.DOTALL)
    account_rows = browser.find_elements_by_css_selector('table tr.table__detail').result

    for row in account_rows:
        if account_matcher.match(row.get_attribute('innerHTML')):
            account_row = row

    log('Loading account advanced search')
    forced_click(account_row.find_element_by_css_selector('div[role=button].dropdown'))
    browser.find_element_by_css_selector('li a[href="#/cuentas/movimientos"]').forced_click()
    browser.find_element_by_css_selector('oip-drop-section-search div[role="button"] i').forced_click()

    log('Filling date query parameters')
    browser.find_element_by_css_selector('input#campoDesdeBuscador', visible=True).clear().send_keys(encode_date(from_date))
    browser.find_element_by_css_selector('input#campoHastaBuscador').clear().send_keys(encode_date(to_date))

    log('Setting up XHR request interceptor')
    script = xhr_intercept_response(
        match_url="cuenta.movimiento",
        output="interceptedResponse",
    )
    browser.driver.execute_script(script)

    log('Launching the initial search')
    browser.find_elements_by_css_selector('button').filter(lambda element: 'Buscar' in element.text)[0].focus().forced_click()

    intercepted_responses = []
    intercepted_responses_count = 0
    still_have_results = True

    # Iterate trough all the infinite scrolling pagination
    while still_have_results:
        t0 = time.time()
        while intercepted_responses_count == len(intercepted_responses):
            # Inner Loop to wait for the page to load and push the new transactions

            # This scrolling command is just a visual debug aid
            browser.execute_script("window.scrollTo(0, document.body.scrollHeight);")
            browser.find_element_by_id("interceptedResponse")
            intercepted_json = browser.execute_script("return JSON.stringify(document.getElementById('interceptedResponse').responses)")
            intercepted_responses = json.loads(intercepted_json)
            time.sleep(0.1)

            still_have_results = False if intercepted_responses[-1] is None else intercepted_responses[-1]['indicadorMasRegistros']
            t1 = time.time()
            if t1 - t0 > 20:
                raise ScrappingError('bankia account', account_number, 'Timeout while waiting to load more results')

        intercepted_responses_count = len(intercepted_responses)

        # Weirdest pagination on earth, where you do a request with 40 results, but you do two paginations of 20 results
        # in between. Each time we exit the inner loop because we intercepted a new request, we'll do this extra pagination click,
        # except when the more results indicator is false. In this case, the browser won't show the last records, but we'll already
        # have it in the intercepted request
        if still_have_results:
            log('Loading more results (preloaded)')
            browser.find_element_by_css_selector('oip-pagination').forced_click()

            log('Loading more results')
            browser.find_element_by_css_selector('oip-pagination').forced_click()
            time.sleep(0.1)

    # Results come from newer to older, we want it the other way around, that why we reverse them
    results = list(reversed(list(chain.from_iterable([response['movimientos'] for response in intercepted_responses if response is not None]))))
    return results


def get_credit_card_transactions(browser, card_number, from_date, to_date):

    log('Open dedicated account page')
    browser.get('https://www.bankia.es/oficina/particulares/#/tarjetas/mis-tarjetas')

    log('Locating card row')
    credit_card_number_element = (
        browser
        .find_elements_by_css_selector('.oip-tarjetas-posicion table table ul li')
        .filter(lambda el: card_number == re.sub(r'[^\w]', '', el.get_attribute('textContent')))
        [0]
    )

    log('Opening card options menu')
    credit_card_row = credit_card_number_element.find_element_by_xpath('ancestor-or-self::tr[contains(@class, "table-data")]')
    credit_card_row.find_element_by_css_selector('oip-commons-vertical-operate button').forced_click()

    log('Load advanced search')
    credit_card_row.find_element_by_css_selector('ul li a[href*="movimientos"]').click()
    browser.find_element_by_css_selector('form#formFiltroMovimientosTarjetas div[role="button"]').forced_click()

    log('Filling date query parameters')
    time.sleep(2)
    browser.find_element_by_css_selector('form#formFiltroMovimientosTarjetas input#optionsRadios2').select()  # Select find between dates option
    browser.find_element_by_css_selector('input#desde').clear().send_keys(encode_date(from_date))
    browser.find_element_by_css_selector('input#hasta').clear().send_keys(encode_date(to_date))

    # Execute search

    log('Setting up XHR request interceptor')
    script = xhr_intercept_response(
        match_url="tarjetas/movimientos",
        output="interceptedResponse",
    )
    browser.driver.execute_script(script)

    log('Launching the initial search')
    browser.find_elements_by_css_selector('form#formFiltroMovimientosTarjetas button').filter(lambda el: 'Buscar' in el.text)[0].click()

    intercepted_responses = []
    intercepted_responses_count = 0
    still_have_results = True

    # Iterate trough all the infinite scrolling pagination
    while still_have_results:
        while intercepted_responses_count == len(intercepted_responses):
            # Inner Loop to wait for the page to load and push the new transactions

            # The  scrolling command is just a visual debug aid
            browser.execute_script("window.scrollTo(0, document.body.scrollHeight);")

            browser.find_element_by_id("interceptedResponse")
            intercepted_json = browser.execute_script("return JSON.stringify(document.getElementById('interceptedResponse').responses)")
            intercepted_responses = json.loads(intercepted_json)
            time.sleep(0.1)

        intercepted_responses_count = len(intercepted_responses)
        still_have_results = False if intercepted_responses[-1] is None else intercepted_responses[-1]['indicadorMasMovimientos']

        # Trigger pagination by clicking the "Ver mas resultados" button
        if still_have_results:
            log('Loading more results')
            browser.find_element_by_css_selector('.masMovimientos').forced_click()
            time.sleep(0.1)

    # results already sorted from older to newer, no need to reverse them
    results = list(chain.from_iterable([response['movimientosTarjeta'] for response in intercepted_responses if response is not None]))
    return results
