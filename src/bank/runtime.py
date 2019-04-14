import importlib
import yaml

from functools import partial

from .io import decode_bank, decode_card, decode_account, decode_local_account
from datatypes import Configuration


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
            cards=cards
        )


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
