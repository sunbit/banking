import importlib
import traceback
import yaml
import os

from datetime import datetime
from functools import partial
from dateutil.relativedelta import relativedelta

from .io import decode_bank, decode_card, decode_account, decode_local_account, decode_notifications, decode_scheduler_configuration
from datatypes import Configuration, Category
from common.logging import get_logger
from common.notifications import get_notifier


import scrapper
import database
import rules
import exceptions

logger = get_logger(name='bank')


def env():
    return {
        'database_folder': os.getenv('BANKING_DATABASE_FOLDER', './database'),
        'main_config_file': os.getenv('BANKING_CONFIG_FILE', './banking.yaml'),
        'categories_file': os.getenv('BANKING_CATEGORIES_FILE', './categories.yaml'),
    }


def get_account_decoder(raw_account_config):
    if raw_account_config['type'] == 'bank_account':
        return decode_account
    elif raw_account_config['type'] == 'local_account':
        return decode_local_account


def load_config(filename):
    with open(filename) as config_file:
        raw_configuration = yaml.load(config_file, Loader=yaml.FullLoader)

        cards = {card.number: card for card in map(decode_card, raw_configuration['cards'])}

        accounts = {
            account['id']: get_account_decoder(account)(
                account,
                cards={
                    card_number: card
                    for card_number, card in cards.items()
                    if card.account_number == account['id']
                }
            )
            for account in raw_configuration['accounts']
        }
        banks = {
            bank['id']: decode_bank(
                bank,
                accounts={
                    account_number: account
                    for account_number, account in accounts.items()
                    if getattr(account, 'bank_id', None) == bank['id']
                }
            )
            for bank in raw_configuration['banks']
        }
        return Configuration(
            banks=banks,
            accounts=accounts,
            cards=cards,
            notifications=decode_notifications(raw_configuration['notifications']),
            scheduler=decode_scheduler_configuration(raw_configuration['scheduler'])
        )


def load_categories(filename):
    def find_categories(categories, parent=None):
        for category_config in raw_categories:
            yield Category(
                id=category_config['id'],
                name=category_config['name'],
                parent=parent
            )
            for subcategory_config in category_config.get('subcategories', []):
                yield Category(
                    id=subcategory_config['id'],
                    name=subcategory_config['name'],
                    parent=category_config['id']
                )

    with open(filename) as categories_file:
        raw_categories = yaml.load(categories_file, Loader=yaml.FullLoader)
        return {category.id: category for category in find_categories(raw_categories)}


def load_module(bank_id):
    return importlib.import_module('bank.{}'.format(bank_id))


def parse_account_transactions(bank_module, bank_config, account_config, transactions):
    return list(
        filter(
            bool,
            map(
                partial(
                    bank_module.parse_account_transaction,
                    bank_config,
                    account_config
                ),
                transactions
            )
        )
    )


def parse_credit_card_transactions(bank_module, bank_config, account_config, credit_card_config, transactions):
    return list(
        filter(
            bool,
            map(
                partial(
                    bank_module.parse_credit_card_transaction,
                    bank_config,
                    account_config,
                    credit_card_config
                ),
                transactions
            )
        )
    )


def scrap_bank_account_transactions(bank_module, bank_config, account_config, from_date, to_date):
    browser = scrapper.new('./chromedriver', headless=True)
    bank_module.login(browser, bank_config.username, bank_config.password)
    return bank_module.get_account_transactions(
        browser,
        account_config.id,
        from_date,
        to_date
    )


def scrap_bank_credit_card_transactions(bank_module, bank_config, card_config, from_date, to_date):
    browser = scrapper.new('./chromedriver', headless=True)
    bank_module.login(browser, bank_config.username, bank_config.password)
    return bank_module.get_credit_card_transactions(
        browser,
        card_config.number,
        from_date,
        to_date
    )


def update_bank_account_transactions(db, bank_config, account_config, from_date, to_date):
    logger.info('Updating {bank.name} account {account.id} transactions from {from_date} to {to_date}'.format(
        bank=bank_config,
        account=account_config,
        from_date=from_date.strftime('%d/%m/%Y'),
        to_date=to_date.strftime('%d/%m/%Y')
    ))

    bank_module = load_module(bank_config.id)

    raw_transactions = scrap_bank_account_transactions(bank_module, bank_config, account_config, from_date, to_date)
    logger.info('{} transactions fetched'.format(len(raw_transactions)))

    parsed_transactions = parse_account_transactions(bank_module, bank_config, account_config, raw_transactions)
    logger.info('{} transactions parsed'.format(len(parsed_transactions)))

    processed_transactions = rules.apply(rules.load(), parsed_transactions)
    logger.info('Rules applied to {} transactions'.format(len(processed_transactions)))

    added, _ = database.update_account_transactions(db, account_config.id, processed_transactions)
    if added:
        logger.info('Successfully updated account transactions database')
    else:
        logger.info('There are no new account transactions to update'.format(len(raw_transactions)))
    return added


def update_bank_credit_card_transactions(db, bank_config, account_config, card_config, from_date, to_date):
    logger.info('Updating {bank.name} card {card.number} transactions from {from_date} to {to_date}'.format(
        bank=bank_config,
        card=card_config,
        from_date=from_date.strftime('%d/%m/%Y'),
        to_date=to_date.strftime('%d/%m/%Y')
    ))

    bank_module = load_module(bank_config.id)

    raw_transactions = scrap_bank_credit_card_transactions(bank_module, bank_config, card_config, from_date, to_date)
    logger.info('{} transactions fetched'.format(len(raw_transactions)))

    parsed_transactions = parse_credit_card_transactions(bank_module, bank_config, account_config, card_config, raw_transactions)
    logger.info('{} transactions parsed'.format(len(parsed_transactions)))

    processed_transactions = rules.apply(rules.load(), parsed_transactions)
    logger.info('Rules applied to {} transactions'.format(len(processed_transactions)))

    added, _ = database.update_credit_card_transactions(db, card_config.number, processed_transactions)
    if added:
        logger.info('Successfully updated credit card transactions database')
    else:
        logger.info('There are no new card transactions to update'.format(len(raw_transactions)))
    return added


UPDATE_EXCEPTION_MESSAGE = """While updating *{bank.name}* {source} *{id}* transactions the following error occurred:

{message}
"""
UNKNOWN_UPDATE_EXCEPTION_MESSAGE = """While updating *{bank.name}* {source} *{id}* transactions the following error occurred:

```
{traceback}
```
"""


def update_all(banking_config, env):
    success = []
    failure = []

    db = database.load(env['database_folder'])
    for bank_id, bank in banking_config.banks.items():
        for account_number, account in bank.accounts.items():
            try:
                last_transaction_date = database.last_account_transaction_date(db, account.id)
                if last_transaction_date is None:
                    # Query from beginning of previous year
                    from_date = (datetime.now() + relativedelta(month=1, day=1, years=-1)).date()
                else:
                    # Query from beginning of previous day
                    from_date = (last_transaction_date - relativedelta(days=1)).date()

                # Query until current day
                to_date = datetime.now().date()
                added = update_bank_account_transactions(db, bank, account, from_date, to_date)

                if added:
                    success.append('Added {added} new transactions for *{bank.name}* account *{account.id}*'.format(
                        bank=bank,
                        account=account,
                        added=added
                    ))
            except database.DatabaseError as exc:
                failure.append(UPDATE_EXCEPTION_MESSAGE.format(bank=bank, source='account', id=account.id, message=str(exc)))
                logger.error(str(exc))
            except Exception as exc:
                failure.append(UNKNOWN_UPDATE_EXCEPTION_MESSAGE.format(bank=bank, source='account', id=account.id, traceback=traceback.format_exc()))
                logger.error(str(exc))
            except (exceptions.SomethingChangedError, exceptions.SomethingChangedError) as exc:
                failure.append(UPDATE_EXCEPTION_MESSAGE.format(bank=bank, source='account', id=account.id, message=str(exc)))
                logger.error(exc.message)

    for card_number, card in banking_config.cards.items():
        if card.type == 'credit' and card.active:
            try:
                last_transaction_date = database.last_credit_card_transaction_date(db, card.number)
                if last_transaction_date is None:
                    # Query from beginning of current year
                    from_date = (datetime.now() + relativedelta(datetime.now(), day=1, month=1)).date()
                else:
                    # Query from beginning of previous day
                    from_date = (last_transaction_date - relativedelta(days=1)).date()

                # Query until current day
                to_date = datetime.now().date()
                card_account = banking_config.accounts[card.account_number]
                card_bank = banking_config.banks[card_account.bank_id]
                added = update_bank_credit_card_transactions(db, card_bank, card_account, card, from_date, to_date)

                if added:
                    success.append('Added {added} new transactions for *{bank.name}* card *{card.number}*'.format(
                        bank=bank,
                        card=card,
                        added=added
                    ))
            except database.DatabaseError as exc:
                failure.append(UPDATE_EXCEPTION_MESSAGE.format(bank=bank, source='card', id=account.id, message=str(exc)))
                logger.error(str(exc))
            except Exception as exc:
                failure.append(UNKNOWN_UPDATE_EXCEPTION_MESSAGE.format(bank=bank, source='card', id=account.id, traceback=traceback.format_exc()))
                logger.error(str(exc))
            except (exceptions.SomethingChangedError, exceptions.SomethingChangedError) as exc:
                failure.append(UPDATE_EXCEPTION_MESSAGE.format(bank=bank, source='account', id=account.id, message=str(exc)))
                logger.error(exc.message)

    notifier = get_notifier(banking_config.notifications)

    for item in success:
        notifier(item)

    for item in failure:
        notifier(item)
