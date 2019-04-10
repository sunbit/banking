"""
Banking

Usage:
  banking get <bank> (account|card) transactions [options]
  banking load <bank> (account|card) transactions [options]
  banking load <bank> (account|card) raw transactions <raw-filename> [options]
  banking (-h | --help)
  banking --version

Options:
  -h --help            Show this screen.
  --version            Show version.
  --from=<from-date>   Query start date
  --to=<to-date>       Query to date
  --save=<filename>    Save the scrapped transactions in raw format to a json file
  --update             Update the database with the new collected records
  --debug-browser      Shows the selenium task in a browser
  --keep-browser-open  Prevent to close the selenium browser after a crash
  --use-cache          Use cached raw transactions if any

"""

# ps aux | grep "python src" | grep -v grep | tr -s " " | cut -d" " -f2 | xargs kill -9
#  ps aux | grep -i chrome | grep webdriver | tr -s " " | cut -d" " -f2 | xargs kill -9

from docopt import docopt
from tabulate import tabulate

import json
import os
import sys
import traceback

from common import utils

import bank
import database
import datatypes
import scrapper
import exceptions
import rules


def table(records, show_balance=True):
    headers = ['Date', 'Amount', 'Balance', 'Type', 'Category', 'Card', 'Source', 'Recipient', 'Tags', 'Comment']

    if show_balance is False:
        headers.remove(headers.index('Balance'))

    def format_destination(destination):
        if destination is None:
            return '--'
        elif isinstance(destination, datatypes.UnknownSubject):
            return '??'
        elif isinstance(destination, datatypes.UnknownWallet):
            return '??'
        else:
            return destination.name

        # return '{}: {}'.format(
        #     destination.__class__.__name__,
        #     destination.name
        # )

    def prepare_row(record):
        row = []
        row.append(record.transaction_date)
        row.append(record.amount)
        if show_balance:
            row.append(record.balance)
        row.append(record.type.value if record.type is not None else '--')
        row.append(record.category if record.category is not None else '--')
        row.append('{card.name}: {card.number}'.format(card=record.card) if record.card is not None else '')
        row.append(format_destination(record.source))
        row.append(format_destination(record.destination))
        row.append(', '.join(record.tags))
        row.append(record.comment)

        return row

    rows = [
        prepare_row(record) for record in records
    ]

    return tabulate(rows, headers=headers, tablefmt='presto')


if __name__ == '__main__':

    arguments = docopt(__doc__, version='Banking 1.0')
    bank_id = arguments['<bank>']
    action = list(filter(lambda action: arguments[action] is True, ['get', 'load']))[0]
    headless = not arguments['--debug-browser']
    close_browser = not arguments['--keep-browser-open']
    load_raw = arguments['raw']

    if arguments['account'] is True:
        source = 'account'
    elif arguments['card'] is True:
        source = 'card'

    banking_configuration = bank.load_config('banking.yaml')
    bank_config = bank.load_bank(banking_configuration, bank_id)
    bank_module = bank.load_module(bank_id)

    # Assuming we have only one account and one credit card
    account_config = bank_config.accounts[0]
    credit_card_config = list(filter(
        lambda card: card.type == 'credit',
        account_config.cards
    ))[0]

    if action == 'get':

        cache_filename = '.cache/{bank}_{source}_{id}_{from_date}_{to_date}.json'.format(
            bank=bank_config.id,
            source=source,
            id=account_config.number if source == 'account' else credit_card_config.number,
            from_date=arguments['--from'].replace('/', '-'),
            to_date=arguments['--to'].replace('/', '-')
        )

        if arguments['--use-cache'] and os.path.exists(cache_filename):
            print('> Loading raw transactions from cache')
            raw_transactions = json.load(open(cache_filename))
        else:
            try:
                browser = scrapper.new('./chromedriver', headless=headless)
                bank_module.login(browser, bank_config.username, bank_config.password)

                if source == 'account':
                    raw_transactions = bank_module.get_account_transactions(
                        browser,
                        account_config.number,
                        arguments['--from'],
                        arguments['--to']
                    )

                elif source == 'card':
                    raw_transactions = bank_module.get_credit_card_transactions(
                        browser,
                        credit_card_config.number,
                        arguments['--from'],
                        arguments['--to']
                    )

            except exceptions.InteractionError as exc:
                print(exc.message)
                if close_browser:
                    browser.driver.close()
                sys.exit(1)
            except exceptions.SomethingChangedError as exc:
                print(exc.message)
                if close_browser:
                    browser.driver.close()
                sys.exit(1)
            except Exception:
                print(traceback.format_exc())
                if close_browser:
                    browser.driver.close()
                sys.exit(1)

        files_to_write = [cache_filename]
        if arguments['--save']:
            files_to_write.append(arguments['--save'])

        for filename in files_to_write:
            with open(filename, 'w') as export_file:
                json.dump(raw_transactions, export_file, indent=4)

        if arguments['--update']:
            if source == 'account':
                parsed_transactions = bank.parse_account_transactions(bank_module, bank_config, account_config, raw_transactions)
                processed_transactions = rules.apply(rules.load(), parsed_transactions)
                try:
                    database.update_account_transactions(database.load(bank_config), processed_transactions)
                except database.DatabaseMatchError as exc:
                    print("\nERROR in datatbase consistency while adding new records: {}\n".format(exc.args[0]))
                    sys.exit(1)

    if action == 'load' and load_raw:
        raw_transactions = json.load(open(arguments['<raw-filename>']))

        if source == 'account':
            parsed_transactions = bank.parse_account_transactions(bank_module, bank_config, account_config, raw_transactions)

        elif source == 'card':
            parsed_transactions = bank.parse_credit_card_transactions(bank_module, bank_config, account_config, credit_card_config, raw_transactions)

        processed_transactions = rules.apply(rules.load(), parsed_transactions)

        at_least_one = False

        for transaction in processed_transactions:
            if None in (transaction.destination, transaction.source, transaction.type):
                at_least_one = True
                print('-' * 80)
                print(json.dumps(transaction.keywords, indent=4, cls=utils.AutoJSONEncoder))
                print(json.dumps(transaction.details, indent=4, cls=utils.AutoJSONEncoder))

        if at_least_one:
            print('-' * 80)

        print(table(processed_transactions))

