from unittest.mock import MagicMock, patch

from telegram_app import *


def test_telegram():
    message = MagicMock()
    message.from_user.id = 1901217395
    message.text = "Played Spirit Island"
    message.reply_to_message = None

    # Act
    next_step(message)
