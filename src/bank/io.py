from datatypes import BankConfig, AccountConfig, CardConfig


def decode_bank(bank_config, accounts=[]):
    return BankConfig(
        bank_config['id'],
        bank_config['name'],
        bank_config['credentials']['username'],
        bank_config['credentials']['password'],
        accounts
    )


def decode_account(account_config, cards=[]):
    return AccountConfig(
        account_config['type'],
        account_config['bank_id'],
        account_config['name'],
        account_config['number'],
        cards
    )


def decode_card(card_config):
    return CardConfig(
        card_config['type'],
        card_config['name'],
        card_config['number'],
        card_config['owner'],
        card_config['active'],
        card_config['account'],
    )
