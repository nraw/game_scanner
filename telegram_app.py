import os

import telebot
from loguru import logger

from game_scanner.commands import set_it, spike_it
from game_scanner.db import retrieve_messages, save_document
from game_scanner.errors import NoGoogleMatchesError
from game_scanner.parse_chat import parse_chat
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


@bot.message_handler(commands=["play"])
def send_play(message):
    logger.info(message)
    message.text = " ".join(message.text.split()[1:])
    perform_step(message)


@bot.message_handler(commands=["version"])
def get_sha(message):
    logger.info(message)
    sha = os.popen("git rev-parse HEAD").read().strip()
    bot.reply_to(message, str(sha))


@bot.message_handler(func=lambda message: True)
def next_step(message: telebot.types.Message):
    logger.info(message)
    perform_step(message)


def perform_step(message):
    user_id = message.from_user.id
    #  chat_id = message.chat.id
    is_user, credit = check_is_user(user_id)
    if not is_user:
        bot.reply_to(message, "Sorry, I was told not to talk to you... (｡ŏ_ŏ)")
        return
    if credit <= 0:
        bot.reply_to(message, "Sorry, it seems you don't have any credit left ⊙﹏⊙")
        return

    message_text = message.text
    messages = [{"role": "user", "content": message_text}]
    if message.reply_to_message:
        previous_message_id = message.reply_to_message.id
        previous_messages = retrieve_messages(previous_message_id)
        messages = previous_messages + messages
    try:
        messages, answer = parse_chat(messages, message_id=message.id)
    except NoGoogleMatchesError as e:
        bot.reply_to(message, str(e))
        return
    #  button_spike = telebot.types.InlineKeyboardButton(
    #      "Spike it!", callback_data="pl-" + str(message.id)
    #  )
    #  button_set = telebot.types.InlineKeyboardButton(
    #      "Set it!", callback_data="wl-" + str(message.id)
    #  )
    keyboard = telebot.types.InlineKeyboardMarkup()
    #  keyboard.add(button_spike)
    #  keyboard.add(button_set)
    reply = bot.reply_to(message, str(answer), reply_markup=keyboard)
    reply_id = reply.id
    save_document(
        {"message_id": reply_id, "messages": messages}, collection_name="messages"
    )


if __name__ == "__main__":
    bot.infinity_polling()
