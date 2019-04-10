import importlib
import yaml

from functools import partial

from .io import decode


def load_config(filename):
    with open(filename) as config_file:
        configuration = yaml.load(config_file, Loader=yaml.FullLoader)
    return configuration


def load_bank(configuration, bank_id):
    bank_config = list(filter(
        lambda bank: bank['id'] == bank_id,
        configuration
    ))[0]
    return decode(bank_config)


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
