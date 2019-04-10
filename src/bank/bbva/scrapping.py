from scrapper.scripts import xhr_intercept_response
from itertools import chain

import json
import time


FIX_NULL_DATE = """
try {{
  arg = JSON.parse(arguments[0]);
  if (arg.hasOwnProperty('filter')) {{
    if (arg.filter.dates.from === null || arg.filter.dates.to === null) {{
        arg.filter.dates.from = '{from_date}T01:00:00.000Z'
        arg.filter.dates.to = '{to_date}T01:00:00.000Z'
        arguments[0] = JSON.stringify(arg)

        document.createElement('div');
        fixed.id = 'fixed_date';
        document.body.appendChild(fixed);

    }}
  }}
}}
catch (e) {{
    console.log('PASS')
}}
"""


def log(text):
    print('> ' + text)


def login(browser, username, password):
    log('Loading main page')
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


def get_account_transactions(browser, account_number, from_date, to_date):

    browser.get('https://web.bbva.es/index.html')

    log('Loading account page')
    browser.find_elements_by_css_selector('p[role=link').filter(lambda element: account_number in element.text)[0].click()

    log('Loading account advanced search')
    browser.find_element_by_css_selector('ul.menuPestanas span.consultas').click()
    browser.find_element_by_css_selector('.busquedaAvanzada[role=button]', visible=True).click()

    log('Filling date query parameters')
    browser.find_element_by_id('fechaDesdeQuery').focus().clear().send_keys(from_date)
    browser.find_element_by_id('fechaHastaQuery').focus().clear().send_keys(to_date)

    time.sleep(2)  # To try to avoid the null values in the date filter request
    log('Setting up XHR request interceptor')
    script = xhr_intercept_response(
        match_url="accountTransactionsAdvancedSearch",
        output="interceptedResponse",
        request_intercept_script=FIX_NULL_DATE.format(
            from_date='-'.join(reversed(from_date.split('/'))),
            to_date='-'.join(reversed(to_date.split('/')))
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
    log('Found {} transactions'.format(len(results)))
    return results


def get_credit_card_transactions(browser, card_number, from_date, to_date):

    browser.get('https://web.bbva.es/index.html')

    log('Locate card and load it\'s detail page')
    browser.find_element_by_xpath('//p[@role="link"][contains(text(), "{}")]'.format(card_number)).forced_click()

    log('Open advanced search')
    browser.find_element_by_xpath('//span[contains(@class, "consulta")]').click()
    browser.find_element_by_css_selector('p.busquedaAvanzada[role="button"]', visible=True).click()

    log('Filling date query parameters')
    browser.find_element_by_css_selector('input#fechaDesde').focus().clear().send_keys(from_date)
    browser.find_element_by_css_selector('input#fechaHasta').focus().clear().send_keys(to_date)

    time.sleep(2)
    log('Setting up XHR request interceptor')
    script = xhr_intercept_response(
        match_url="listIntegratedCardTransactions",
        output="interceptedResponse",
    )
    browser.driver.execute_script(script)

    log('Launching the initial search')
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
    log('Found {} transactions'.format(len(results)))
    return results
