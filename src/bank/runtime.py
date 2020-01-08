import importlib
import json
import traceback
import yaml
import os

from copy import deepcopy
from datetime import datetime
from functools import partial
from dateutil.relativedelta import relativedelta

from .io import decode_bank, decode_card, decode_account, decode_local_account, decode_notifications, decode_scheduler_configuration
from datatypes import Configuration, Category
from common.logging import get_logger
from common.notifications import get_notifier
from common.utils import parse_bool, traceback_summary, get_nested_item


import scrapper
import database
import rules
import exceptions

logger = get_logger(name='bank')


def env():
    return {
        'database_folder': os.getenv('BANKING_DATABASE_FOLDER', './database'),
        'main_config_file': os.getenv('BANKING_CONFIG_FILE', './banking.yaml'),
        'metadata_file': os.getenv('BANKING_METADATA_FILE', './metadata.yaml'),
        'categories_file': os.getenv('BANKING_CATEGORIES_FILE', './categories.yaml'),
        'headless_browser': parse_bool(os.getenv('BANKING_HEADLESS_BROWSER', True)),
        'close_browser': parse_bool(os.getenv('BANKING_CLOSE_BROWSER', True)),
        'update_accounts_on_start': parse_bool(os.getenv('BANKING_UPDATE_ACCOUNTS_ON_START', True)),
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
    browser = scrapper.new('./chromedriver', headless=env()['headless_browser'])
    bank_module.login(browser, bank_config.username, bank_config.password)
    transactions = bank_module.get_account_transactions(
        browser,
        account_config.id,
        from_date,
        to_date
    )

    if env()['close_browser']:
        browser.close()
        browser.quit()

    return transactions


def scrap_bank_credit_card_transactions(bank_module, bank_config, card_config, from_date, to_date):
    browser = scrapper.new('./chromedriver', headless=env()['headless_browser'])
    bank_module.login(browser, bank_config.username, bank_config.password)
    transactions = bank_module.get_credit_card_transactions(
        browser,
        card_config.number,
        from_date,
        to_date
    )

    if env()['close_browser']:
        browser.close()
        browser.quit()

    return transactions


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
    filtered_transactions = list(filter(
        lambda transaction: transaction.transaction_date >= from_date and transaction.transaction_date <= to_date,
        parsed_transactions
    ))
    discarded_transactions_count = len(parsed_transactions) - len(filtered_transactions)
    filtered_info = ' ({} out of date range got filtered)'.format(discarded_transactions_count) if discarded_transactions_count > 0 else ''
    logger.info('{} transactions parsed{}'.format(len(parsed_transactions), filtered_info))

    processed_transactions = rules.apply(rules.load(), filtered_transactions)
    logger.info('Rules applied to {} transactions'.format(len(processed_transactions)))

    removed, added, _ = database.update_account_transactions(db, account_config.id, processed_transactions)
    if added:
        logger.info('Successfully added {} account transactions to the database.'.format(added))
    else:
        logger.info('There are no new account transactions to add'.format(len(raw_transactions)))
    if removed:
        logger.info('Successfully removed {} transactions from the database'.format(removed))
    return (removed, added)


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
    filtered_transactions = list(filter(
        lambda transaction: transaction.transaction_date >= from_date and transaction.transaction_date <= to_date,
        parsed_transactions
    ))
    discarded_transactions_count = len(parsed_transactions) - len(filtered_transactions)
    filtered_info = ' ({} out of date range got filtered)'.format(discarded_transactions_count) if discarded_transactions_count > 0 else ''
    logger.info('{} transactions parsed{}'.format(len(parsed_transactions), filtered_info))

    processed_transactions = rules.apply(rules.load(), filtered_transactions)
    logger.info('Rules applied to {} transactions'.format(len(processed_transactions)))

    removed, added, _ = database.update_credit_card_transactions(db, card_config.number, processed_transactions)
    if added:
        logger.info('Successfully added {} credit card transactions to the database.'.format(added))
    else:
        logger.info('There are no new card transactions to add'.format(len(raw_transactions)))
    if removed:
        logger.info('Successfully removed {} transactions from the database'.format(removed))
    return (removed, added)


EXCEPTION_MESSAGE = """While updating *{bank.name}* {source} *{id}* transactions the following error occurred:

```
{message}
```
"""


def get_metadata(metadata_filename):
    if not os.path.exists(metadata_filename):
        return {}

    with open(metadata_filename) as metadata_file:
        metadata = yaml.load(metadata_file, Loader=yaml.FullLoader)

    return metadata


def save_metadata(metadata_filename, metadata):
    with open(metadata_filename, 'w') as metadata_file:
        yaml.dump(metadata, metadata_file)


def get_last_update_time(metadata, bank, account_type, identifier):
    return get_nested_item(metadata, '{}.{}.{}.updated'.format(bank, account_type, identifier))


def set_last_update_time(metadata, bank, account_type, identifier, date):
    _metadata = deepcopy(metadata) if metadata is not None else {}
    bank_level = _metadata.setdefault(bank, {})
    type_level = bank_level.setdefault(account_type, {})
    account_level = type_level.setdefault(identifier, {})
    account_level['updated'] = date
    return _metadata


def update_all(banking_config, env):
    success = []
    failure = []

    db = database.load(env['database_folder'])
    metadata_file = env['metadata_file']
    min_updated_elapsed = banking_config.scheduler.update_timeout_seconds

    def already_updated(bank_id, account_type, account_number):
        last_update = get_last_update_time(
            get_metadata(metadata_file),
            bank_id, 'account', account_number
        )
        if last_update is None:
            return False

        elapsed = (datetime.utcnow() - last_update).seconds
        elapsed_hours = int(elapsed / 3600)
        elapsed_minutes = int((elapsed - (elapsed_hours * 3600)) / 60)
        if elapsed < min_updated_elapsed:
            logger.warning(
                "Canceling update of {} {} {} as it was updated already {}h:{}m ago".format(
                    bank_id, account_type, account_number, elapsed_hours, elapsed_minutes
                )
            )
            return True
        else:
            return False

    def update_last_update_time(bank_id, account_type, account_number):
        save_metadata(
            metadata_file,
            set_last_update_time(get_metadata(metadata_file), bank_id, account_type, account_number, datetime.utcnow())
        )

    for bank_id, bank in banking_config.banks.items():
        for account_number, account in bank.accounts.items():

            if already_updated(bank_id, 'account', account_number):
                continue

            try:
                last_transaction_date = database.last_account_transaction_date(db, account.id)
                if last_transaction_date is None:
                    # Query from beginning of previous year
                    from_date = datetime.now() + relativedelta(month=1, day=1, years=-1, minute=0, hour=0, second=0, microsecond=0)
                else:
                    # Query from beginning of previous day
                    from_date = last_transaction_date - relativedelta(days=1, minute=0, hour=0, second=0, microsecond=0)

                # Query until current day and hour
                to_date = datetime.now()
                removed, added = update_bank_account_transactions(db, bank, account, from_date, to_date)

                if added:
                    success.append('Added {added} new transactions for *{bank.name}* account *{account.id}*'.format(
                        bank=bank,
                        account=account,
                        added=added
                    ))
                if added:
                    success.append('Removed {removed} transactions for *{bank.name}* account *{account.id}*'.format(
                        bank=bank,
                        account=account,
                        removed=removed
                    ))

                update_last_update_time(bank_id, 'account', account_number)

            except database.DivergedHistoryError as exc:
                failure.append(EXCEPTION_MESSAGE.format(bank=bank, source='account', id=account.id, message=exc.message))
                logger.error(exc.message)
            except database.DatabaseError as exc:
                failure.append(EXCEPTION_MESSAGE.format(bank=bank, source='account', id=account.id, message=str(exc)))
                logger.error(str(exc))
            except (exceptions.SomethingChangedError, exceptions.InteractionError) as exc:
                failure.append(EXCEPTION_MESSAGE.format(bank=bank, source='account', id=account.id, message=str(exc)))
                logger.error(exc.message)
            except Exception as exc:
                failure.append(EXCEPTION_MESSAGE.format(bank=bank, source='account', id=account.id, message=traceback.format_exc()))
                logger.error(traceback_summary(traceback.format_exc(), exc))

    for card_number, card in banking_config.cards.items():
        if card.type == 'credit' and card.active:

            if already_updated(banking_config.accounts[card.account_number].bank_id, 'card', card_number):
                continue

            try:
                last_transaction_date = database.last_credit_card_transaction_date(db, card.number)
                if last_transaction_date is None:
                    # Query from beginning of current year
                    from_date = datetime.now() + relativedelta(month=1, day=1, years=-1, minute=0, hour=0, second=0, microsecond=0)
                else:
                    # Query from beginning of previous day
                    from_date = last_transaction_date - relativedelta(days=1, minute=0, hour=0, second=0, microsecond=0)

                # Query until current day
                to_date = datetime.now()

                card_account = banking_config.accounts[card.account_number]
                card_bank = banking_config.banks[card_account.bank_id]
                removed, added = update_bank_credit_card_transactions(db, card_bank, card_account, card, from_date, to_date)

                if added:
                    success.append('Added {added} new transactions for *{bank.name}* card *{card.number}*'.format(
                        bank=card_bank,
                        card=card,
                        added=added
                    ))
                if removed:
                    success.append('Removed {removed} transactions for *{bank.name}* card *{card.number}*'.format(
                        bank=card_bank,
                        card=card,
                        removed=removed
                    ))

                update_last_update_time(banking_config.accounts[card.account_number].bank_id, 'card', card_number)

            except database.DivergedHistoryError as exc:
                failure.append(EXCEPTION_MESSAGE.format(bank=card_bank, source='card', id=card.number, message=exc.message))
                logger.error(exc.message)
            except database.DatabaseError as exc:
                failure.append(EXCEPTION_MESSAGE.format(bank=card_bank, source='card', id=card.number, message=str(exc)))
                logger.error(str(exc))
            except (exceptions.SomethingChangedError, exceptions.InteractionError) as exc:
                failure.append(EXCEPTION_MESSAGE.format(bank=card_bank, source='card', id=card.number, message=str(exc)))
                logger.error(exc.message)
            except (exceptions.ParsingError) as exc:
                failure.append(EXCEPTION_MESSAGE.format(bank=card_bank, source='card', id=card.number, message=str(exc)))
                logger.error(exc.message)
            except Exception as exc:
                failure.append(EXCEPTION_MESSAGE.format(bank=card_bank, source='card', id=card.number, message=traceback.format_exc()))
                logger.error(traceback_summary(traceback.format_exc(), exc))

    notifier = get_notifier(banking_config.notifications)

    for item in success:
        notifier(item)

    for item in failure:
        notifier(item)
