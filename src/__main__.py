"""
Banking

Usage:
  banking get <bank> (account|card) transactions [options]
  banking update <bank> (account|card) transactions [options]
  banking load <bank> (account|card) transactions [options]
  banking load all transactions [--filter=<filters>]
  banking remove <bank> (account|card) transaction <seq> [options]
  banking apply rules
  banking load <bank> (account|card) raw transactions <raw-filename> [options]
  banking run server [options]
  banking (-h | --help)
  banking --version

Options:
  -h --help              Show this screen.
  --version              Show version.
  --filter=<filters>     Filter table by visible text
  --from=<from-date>     Query start date
  --to=<to-date>         Query to date
  --save=<filename>      Save the scrapped transactions in raw format to a json file
  --update               Update the database with the new collected records
  --debug-browser        Shows the selenium task in a browser
  --keep-browser-open    Prevent to close the selenium browser after a crash
  --use-cache            Use cached raw transactions if any
  --no-initial-update    When running the server, don't run the initial scheduler

"""

# ps aux | grep "python src" | grep -v grep | tr -s " " | cut -d" " -f2 | xargs kill -9
#  ps aux | grep -i chrome | grep webdriver | tr -s " " | cut -d" " -f2 | xargs kill -9

from datetime import datetime
from docopt import docopt
from itertools import chain
from operator import attrgetter
from tabulate import tabulate

import json
import os
import sys
import traceback

from common import utils

import app
import bank
import database
import datatypes
import scrapper
import exceptions
import rules

# from dataclasses import dataclass

# @dataclasses
# class TableConfig():
#     date: bool,
#     amount: bool,
#     balance: bool,
#     type: bool,
#     category: bool,
#     card: bool,


def table(records, show_balance=True):
    headers = ['Date', 'Amount', 'Balance', 'Type', 'Category', 'Card', 'Source', 'Recipient', 'Tags', 'Comment']

    if show_balance is False:
        headers.remove('Balance')

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
        row.append(record.transaction_date.strftime('%Y/%m/%d'))
        row.append(record.amount)
        if show_balance:
            row.append(record.balance)
        row.append(record.type.value if record.type is not None else '--')
        row.append(record.category.name if record.category is not None else '--')
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


def table_all(records, filters=[], show_balance=False):
    headers = ["Seq", 'Date', 'Origin', 'Amount', 'Balance', 'Type', 'Source', 'Destination', 'Category', 'Tags', 'Comment']

    if show_balance is False:
        headers.remove('Balance')

    def format_destination(destination):
        if destination is None:
            return '--'
        elif isinstance(destination, datatypes.UnknownSubject):
            return '??'
        elif isinstance(destination, datatypes.UnknownWallet):
            return '??'
        else:
            return destination.name

    def prepare_row(record):

        record_type = 'card' if isinstance(record, datatypes.BankCreditCardTransaction) else 'account'
        method = {
            ('account', False): 'account',
            ('account', True): 'debit card',
            ('card', False): 'credit card',
            ('card', True): 'credit card',
        }[(record_type, record.card is not None)]
        bank = 'BBVA' if 'BBVA' in getattr(record, record_type).name.upper() else 'BANKIA'

        row = []
        row.append(record._seq)
        row.append(record.transaction_date.strftime('%Y/%m/%d'))
        row.append('{}:{}'.format(bank, method))
        row.append(record.amount)
        if show_balance:
            row.append(record.balance)

        row.append(record.type.value if record.type is not None else '--')
        row.append(format_destination(record.source))
        row.append(format_destination(record.destination))
        row.append(record.category.name if record.category is not None else '--')
        row.append(', '.join(record.tags))
        row.append(record.comment)
        return row

    rows = [
        prepare_row(record) for record in records
    ]

    filtered = [
        row for row in rows if any(map(lambda f: f in str(row).lower(), filters))
    ]

    return tabulate(filtered, headers=headers, tablefmt='presto')


def parse_date(date_string):
    """
        Dates from cli are expected as yyyy-mm-dd
    """
    if not date_string:
        return None

    year, month, day = map(int, date_string.split('-'))

    return datetime(year, month, day)


if __name__ == '__main__':
    arguments = docopt(__doc__, version='Banking 1.0')
    banking_configuration = bank.load_config(bank.env()['main_config_file'])

    action = list(filter(lambda action: arguments[action] is True, ['get', 'load', 'apply', 'update', 'run', 'remove']))[0]
    target = list(filter(lambda target: arguments[target] is True, ['account', 'card', 'server', 'all']))[0]

    load_raw = arguments['raw']
    load_all = arguments['all']

    headless = not arguments['--debug-browser']
    close_browser = not arguments['--keep-browser-open']
    update_accounts_on_start = not arguments['--no-initial-update']

    os.environ["BANKING_HEADLESS_BROWSER"] = str(headless)
    os.environ["BANKING_CLOSE_BROWSER"] = str(close_browser)
    os.environ["BANKING_UPDATE_ACCOUNTS_ON_START"] = str(update_accounts_on_start)

    if action == "run" and arguments['server']:
        app.run(banking_configuration)
        sys.exit(0)

    if action == 'load' and load_all:
        db = database.load(bank.env()['database_folder'])
        account_transactions = database.io.find_account_transactions(db)
        credit_card_transactions = database.io.find_credit_card_transactions(db)

        all_transactions = sorted(chain(account_transactions, credit_card_transactions), key=attrgetter('transaction_date'))

        filters_argument = arguments['--filter'] if arguments['--filter'] is not None else ''
        parsed_filters = list(map(lambda f: f.lower(), filters_argument.split(',')))
        print(table_all(all_transactions, filters=parsed_filters))
        sys.exit(0)

    if action == 'apply' and arguments['rules']:
        db = database.load(bank.env()['database_folder'])
        account_transactions = database.io.find_account_transactions(db)
        credit_card_transactions = database.io.find_credit_card_transactions(db)

        all_transactions = sorted(chain(account_transactions, credit_card_transactions), key=attrgetter('transaction_date'))

        processed_transactions = rules.apply(rules.load(), all_transactions)

        changed = 0
        for old_transaction, new_transaction in zip(all_transactions, processed_transactions):
            if old_transaction != new_transaction:
                database.update_transaction(db, new_transaction)
                changed += 1

        print('Updated {} of {} transactions'.format(changed, len(processed_transactions)))

        sys.exit(1)

    bank_id = arguments['<bank>']

    if action in ['get', 'update']:
        try:
            from_date = parse_date(arguments['--from'])
            if from_date is None:
                print('From date is required')
                sys.exit(1)
        except:
            print('From date format error, should be yyyy-mm-dd')
            sys.exit(1)

        try:
            to_date = parse_date(arguments['--to'])
            if to_date is None:
                to_date = datetime.now()
        except:
            print('To date format error, should be yyyy-mm-dd')
            sys.exit(1)

    bank_config = banking_configuration.banks[bank_id]
    bank_module = bank.load_module(bank_id)

    # Assuming we have only one account
    account_config = list(bank_config.accounts.values())[0]

    # Assuming we pick the first credit card available
    credit_card_config = list(filter(
        lambda card: card.type == 'credit' and card.active,
        account_config.cards.values()
    ))[0]

    if action == 'remove':
        sequence_number = int(arguments['<seq>'])
        db = database.load(bank.env()['database_folder'])
        card = datatypes.Card.from_config(credit_card_config)
        transactions = database.find_transactions(db, card, _seq=int(arguments['<seq>']))
        database.remove_transactions(db, transactions)

    if action == 'update':
        try:
            if target == 'account':
                db = database.load(bank.env()['database_folder'])
                removed, added = bank.update_bank_account_transactions(db, bank_config, account_config, from_date, to_date)
            if target == 'card':
                db = database.load(bank.env()['database_folder'])
                removed, added = bank.update_bank_credit_card_transactions(db, bank_config, account_config, credit_card_config, from_date, to_date)

        except database.DivergedHistoryError as exc:
            if target == 'account':
                print("\nERROR while adding new account transactions: {}\n".format(exc.message))
            if target == 'card':
                print("\nERROR while adding new credit card transactions: {}\n".format(exc.message))
            sys.exit(1)
        except database.DatabaseError as exc:
            if target == 'account':
                print("\nERROR in database consistency while adding new account transactions: {}\n".format(exc.args[0]))
            if target == 'card':
                print("\nERROR in database consistency while adding new credit card transactions: {}\n".format(exc.args[0]))
            sys.exit(1)
        except exceptions.InteractionError as exc:
            print(exc.message)
            sys.exit(1)
        except exceptions.SomethingChangedError as exc:
            print("Somthing has changed: ", exc.message)
            input()
            sys.exit(1)
        except Exception:
            print(traceback.format_exc())
            sys.exit(1)

        else:
            if target == 'account':
                print('Added {added} new transactions for *{bank.name}* account *{account.id}*'.format(
                    bank=bank_config,
                    account=account_config,
                    added=added
                ))
            if target == 'card':
                print('Added {added} new transactions for *{bank.name}* card *{card.number}*'.format(
                    bank=bank_config,
                    card=credit_card_config,
                    added=added
                ))
            sys.exit(0)

    if action == 'get':
        cache_filename = '.cache/{bank}_{source}_{id}_{from_date}_{to_date}.json'.format(
            bank=bank_config.id,
            source=target,
            id=account_config.id if target == 'account' else credit_card_config.number,
            from_date=arguments['--from'],
            to_date=arguments['--to']
        )

        if arguments['--use-cache'] and os.path.exists(cache_filename):
            print('> Loading raw transactions from cache')
            raw_transactions = json.load(open(cache_filename))
        else:
            try:
                browser = scrapper.new('./chromedriver', headless=headless)
                bank_module.login(browser, bank_config.username, bank_config.password)

                if target == 'account':
                    raw_transactions = bank_module.get_account_transactions(
                        browser,
                        account_config.id,
                        from_date,
                        to_date
                    )

                elif target == 'card':
                    raw_transactions = bank_module.get_credit_card_transactions(
                        browser,
                        credit_card_config.number,
                        from_date,
                        to_date
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

        files_to_write = []
        if arguments['--use-cache']:
            files_to_write.append(cache_filename)
        if arguments['--save']:
            files_to_write.append(arguments['--save'])

        for filename in files_to_write:
            with open(filename, 'w') as export_file:
                json.dump(raw_transactions, export_file, indent=4)

    if action == 'load' and not load_raw:
        db = database.load(bank.env()['database_folder'])

        if target == 'account':
            transactions = database.io.find_account_transactions(db, account_number=account_config.id)
        elif target == 'card':
            transactions = database.io.find_credit_card_transactions(db, credit_card_number=credit_card_config.number)

        filters_argument = arguments['--filter'] if arguments['--filter'] is not None else ''
        parsed_filters = list(map(lambda f: f.lower(), filters_argument.split(',')))
        print(table_all(transactions, filters=parsed_filters, show_balance=target == 'account'))
        sys.exit(0)

    if action == 'load' and load_raw:
        raw_transactions = json.load(open(arguments['<raw-filename>']))

        if target == 'account':
            parsed_transactions = bank.parse_account_transactions(bank_module, bank_config, account_config, raw_transactions)

        elif target == 'card':
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

        print(table(processed_transactions, show_balance=target == 'account'))
