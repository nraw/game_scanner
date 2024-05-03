from game_scanner.commands import *


def test_set_it():
    message_id = 0
    message = set_it(message_id)
    message = (
        f"You love [it](https://boardgamegeek.com/boardgame/{game_id}) now! ٩(ˊᗜˋ*)و"
    )


def test_sending_set_it():
    message = "You love [it](https://boardgamegeek.com/boardgame/162886) now! ٩(◕‿◕*)۶"
    import os

    import telebot

    user_id = 1901217395

    bot = telebot.TeleBot(os.environ["TELEGRAM_TOKEN"], parse_mode="Markdown")
    bot.send_message(chat_id=user_id, text=message)
