from datatypes import BankConfig, AccountConfig, CardConfig


def decode(bank_config):
    return BankConfig(
        bank_config['id'],
        bank_config['name'],
        bank_config['credentials']['username'],
        bank_config['credentials']['password'],
        [
            AccountConfig(
                bank_config['id'],
                account['name'],
                account['number'],
                [
                    CardConfig(
                        card['type'],
                        card['name'],
                        card['number'],
                        card['owner'],
                        bank_config['id'],
                        account['number']
                    )
                    for card in account['cards']
                ]
            )
            for account in bank_config['accounts']
        ]
    )
