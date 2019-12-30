from datatypes import BankConfig, LocalAccountConfig, AccountConfig, CardConfig, NotificationsConfig, SchedulerConfig


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
        account_config['id'],
        cards
    )


def decode_local_account(account_config, **kwargs):
    return LocalAccountConfig(
        account_config['type'],
        account_config['id'],
        account_config['name'],
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


def decode_notifications(notifications_config):
    return NotificationsConfig(
        notifications_config['telegram_api_key'],
        notifications_config['telegram_chat_id']
    )


def decode_scheduler_configuration(scheduler_config):
    return SchedulerConfig(
        scheduler_config['scrapping_hours'],
        scheduler_config['update_timeout_seconds'],
    )
