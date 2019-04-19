import telegram


def notify(text):
    bot = telegram.Bot(token='***REMOVED***')
    bot.send_message(
        chat_id=***REMOVED***,
        text=text,
        parse_mode=telegram.ParseMode.MARKDOWN
    )
