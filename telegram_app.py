import os

import telebot
from loguru import logger

from game_scanner.errors import NoGoogleMatchesError
from game_scanner.parse_chat import parse_chat
from game_scanner.spikes import spike_it
from game_scanner.telegram_utils import check_is_user

bot = telebot.TeleBot(os.environ["TELEGRAM_TOKEN"], parse_mode="Markdown")


@bot.message_handler(commands=["start"])
def send_welcome(message):
    logger.info(message)
    user_id = message.from_user.id
    chat_id = message.chat.id
    is_user, credit = check_is_user(user_id)
    if not is_user:
        bot.reply_to(message, "Sorry, I was told not to talk to you... ⊙﹏⊙")
        return
    if credit <= 0:
        bot.reply_to(message, "Sorry, it seems you don't have any credit left ⊙﹏⊙")
        return
    bot.reply_to(
        message,
        "Okay, boss! (≧ω≦)ゞ",
    )


@bot.callback_query_handler(func=lambda call: True)
def callback_query(call):
    logger.info(call)
    if call.data.startswith("pl"):
        bot.answer_callback_query(call.id, "You clicked on Spike it!")
        message_id = int(call.data.split("-")[1])
        spike_response = spike_it(message_id)
        bot.reply_to(call.message, spike_response)
    elif call.data.startswith("wl"):
        bot.answer_callback_query(call.id, "You clicked on Set it!")
        message_id = int(call.data.split("-")[1])
        set_response = set_it(message_id)
        bot.reply_to(call.message, set_response)


@bot.message_handler(func=lambda message: True)
def next_step(message):
    logger.info(message)
    user_id = message.from_user.id
    #  chat_id = message.chat.id
    is_user, credit = check_is_user(user_id)
    if not is_user:
        bot.reply_to(message, "Sorry, I was told not to talk to you... (｡ŏ_ŏ)")
        return
    if credit <= 0:
        bot.reply_to(message, "Sorry, it seems you don't have any credit left ⊙﹏⊙")
        return

    messages = [{"role": "user", "content": message.text}]
    if message.reply_to_message:
        previos_message = [
            {"role": "assistant", "content": message.reply_to_message.text}
        ]
        messages = previos_message + messages
    try:
        answer = parse_chat(messages, message_id=message.id)
    except NoGoogleMatchesError as e:
        bot.reply_to(message, str(e))
        return
    button_foo = telebot.types.InlineKeyboardButton(
        "Spike it!", callback_data="pl-" + str(message.id)
    )
    button_foo = telebot.types.InlineKeyboardButton(
        "Set it!", callback_data="wl-" + str(message.id)
    )
    keyboard = telebot.types.InlineKeyboardMarkup()
    keyboard.add(button_foo)
    bot.reply_to(message, str(answer), reply_markup=keyboard)


if __name__ == "__main__":
    bot.infinity_polling()
