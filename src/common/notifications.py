import telegram


def get_notifier(notifications_config):

    def send(text):
        bot = telegram.Bot(token=notifications_config.telegram_api_key)
        bot.send_message(
            chat_id=notifications_config.telegram_chat_id,
            text=text,
            parse_mode=telegram.ParseMode.MARKDOWN
        )

    return send
