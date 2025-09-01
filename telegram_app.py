import os

import telebot
from loguru import logger

from game_scanner.commands import set_it, spike_it
from game_scanner.db import retrieve_messages, save_document
from game_scanner.parse_chat import parse_chat, reply_with_last_bot_query
from game_scanner.telegram_utils import (
    check_is_user,
    get_user_by_telegram_id,
    register_telegram_user,
)

bot = telebot.TeleBot(os.environ["TELEGRAM_TOKEN"], parse_mode="Markdown")


@bot.message_handler(commands=["start"])
def send_welcome(message):
    logger.info(message)
    user_id = message.from_user.id
    first_name = message.from_user.first_name or "there"

    is_user, credit = check_is_user(user_id)

    if not is_user:
        welcome_text = f"""🎲 Hello {first_name}! Welcome to BGG Logger Bot!

I'm your personal board game assistant. I can help you:
• 📋 Log plays to BoardGameGeek  
• 📚 Manage your game collection
• ❤️ Add games to your wishlist
• 📊 Track your gaming statistics

To get started, you'll need to connect your BoardGameGeek account:

/register - Connect your BGG account
/help - See all available commands

Ready to level up your board gaming? 🚀"""

        bot.reply_to(message, welcome_text)
        return

    if credit <= 0:
        bot.reply_to(
            message,
            f"Welcome back {first_name}! Unfortunately, you're out of credits. ⊙﹏⊙",
        )
        return

    # Returning user
    user_data = get_user_by_telegram_id(user_id)
    bgg_username = user_data.get("bgg_username", "there") if user_data else "there"

    welcome_back_text = f"""🎲 Welcome back, {first_name}!

Connected to BGG as: *{bgg_username}*
Available credits: *{credit}*

What would you like to do today?

Quick actions:
• Just tell me about a game you played!
• "Add [game] to wishlist"
• "Show my games for 4 players"

/commands - See all available features
/help - Get detailed help"""

    bot.reply_to(message, welcome_back_text)


@bot.callback_query_handler(func=lambda call: True)
def callback_query(call):
    logger.info(call)

    # Legacy callback handlers
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

    # New command menu handlers
    elif call.data.startswith("cmd_"):
        handle_command_callback(call)


def handle_command_callback(call):
    """Handle callbacks from the /commands menu."""
    bot.answer_callback_query(call.id)

    if call.data == "cmd_log_play":
        response = """📋 *Log a Play*

You can log plays in several ways:

*Natural Language:*
• "I played Wingspan yesterday with Alice and Bob"
• "Log Azul, 45 minutes, great game!"
• "Played Catan on 2025-08-30"

*Direct Command:*
• `/play Wingspan`

Just tell me about your game and I'll handle the rest! 🎲"""

    elif call.data == "cmd_wishlist":
        response = """❤️ *Add to Wishlist*

Tell me which games you want to add:

*Examples:*
• "Add Gloomhaven to my wishlist"
• "Wishlist Spirit Island"
• "I want Wingspan"

I'll find the game and add it to your BGG wishlist! 🎯"""

    elif call.data == "cmd_collection":
        response = """📚 *Your Collection*

View and filter your games:

*Examples:*
• "Show my games"
• "Games for 4 players"
• "Show my games for 2-3 players"
• "What games do I own?"

I'll show your collection with filtering options! 📖"""

    elif call.data == "cmd_recent":
        response = """📊 *Recent Plays*

View your play history:

*Examples:*
• "Show my recent plays"
• "List my last 10 plays"
• "Plays since last week"
• "Show plays of Wingspan"

I can also help you delete plays if needed! 📈"""

    elif call.data == "cmd_find":
        response = """🔍 *Find Games*

I can help you discover games:

*Examples:*
• "Tell me about Wingspan"
• "Find games like Azul"
• "Recommend games for 3 players"

I'll use BoardGameGeek to find information! 🎮"""

    elif call.data == "cmd_help":
        response = """❓ *Help & Tips*

*Commands:*
/help - Full help guide
/start - Main menu
/register - Connect BGG account

*Pro Tips:*
• Just talk naturally about board games
• I understand context from previous messages
• Use reply to continue conversations
• I can handle barcodes in photos

Need more help? Just ask! 🤖"""

    else:
        response = "Unknown command. Try /help for assistance."

    bot.send_message(call.message.chat.id, response)


@bot.message_handler(commands=["play"])
def send_play(message):
    logger.info(message)
    message.text = " ".join(message.text.split()[1:])
    perform_step(message)


@bot.message_handler(commands=["register"])
def handle_register(message):
    logger.info(message)
    user_id = message.from_user.id
    first_name = message.from_user.first_name or "there"

    is_user, _ = check_is_user(user_id)
    if is_user:
        bot.reply_to(
            message,
            f"You're already registered, {first_name}! 🎉\n\nUse /start to see your dashboard.",
        )
        return

    register_text = """🔗 Let's connect your BoardGameGeek account!

*Option 1: Register with BGG credentials*
Send me a message in this format:
`/register_with_bgg YOUR_USERNAME YOUR_PASSWORD`

Example: `/register_with_bgg johnsmith mypassword123`

*Option 2: Use existing API key*
If you already have an API key from our web interface:
`/register_with_api YOUR_API_KEY`

Example: `/register_with_api abc123xyz789...`

⚠️ *Security note:* Your credentials are encrypted and stored securely. I only use them to interact with BGG on your behalf.

Don't have a BGG account yet? Create one at boardgamegeek.com first!"""

    bot.reply_to(message, register_text)


@bot.message_handler(commands=["register_with_bgg"])
def handle_register_with_bgg(message):
    logger.info(message)
    user_id = message.from_user.id
    first_name = message.from_user.first_name or "there"

    # Parse the command arguments
    parts = message.text.split()
    if len(parts) != 3:
        bot.reply_to(
            message, "❌ Please use the format: `/register_with_bgg USERNAME PASSWORD`"
        )
        return

    bgg_username = parts[1]
    bgg_password = parts[2]

    # Delete the message for security
    try:
        bot.delete_message(message.chat.id, message.message_id)
    except Exception:
        pass  # Ignore if we can't delete

    bot.send_chat_action(message.chat.id, "typing")

    try:
        api_key = register_telegram_user(user_id, bgg_username, bgg_password)
        if api_key:
            success_text = f"""🎉 Registration successful, {first_name}!

Your BGG account *{bgg_username}* is now connected.

🔑 **Your API Key:** `{api_key}`

⚠️ **IMPORTANT:** Save this API key! You can use it to:
• Access our web interface
• Register on other devices
• Recover your account if needed

🚀 Let's get started! Try these:
• "I played Wingspan yesterday"
• "Add Gloomhaven to my wishlist"  
• "Show my games for 2 players"

/help - See all commands
/commands - Quick action menu"""

            bot.send_message(message.chat.id, success_text)
        else:
            bot.send_message(
                message.chat.id,
                "❌ Registration failed. Please check your BGG username and password, then try again.",
            )

    except Exception as e:
        logger.error(f"Registration error: {e}")
        if "already registered" in str(e):
            recovery_text = """❌ This BGG username is already registered.

If this is your account from our web interface, I tried to link it automatically. If that didn't work, you can:

1. **Use your API key instead:**
   `/register_with_api YOUR_API_KEY`

2. **Double-check your password** and try again

3. **Contact support** if you're still having trouble

Note: Each BGG account can only be linked to one Telegram user for security."""
            bot.send_message(message.chat.id, recovery_text)
        else:
            bot.send_message(message.chat.id, f"❌ Registration failed: {str(e)}")


@bot.message_handler(commands=["register_with_api"])
def handle_register_with_api(message):
    logger.info(message)
    user_id = message.from_user.id
    first_name = message.from_user.first_name or "there"

    # Check if already registered
    is_user, _ = check_is_user(user_id)
    if is_user:
        bot.reply_to(
            message,
            f"You're already registered, {first_name}! 🎉\n\nUse /start to see your dashboard.",
        )
        return

    # Parse the API key
    parts = message.text.split()
    if len(parts) != 2:
        bot.reply_to(
            message, "❌ Please use the format: `/register_with_api YOUR_API_KEY`"
        )
        return

    api_key = parts[1]

    # Delete the message for security
    try:
        bot.delete_message(message.chat.id, message.message_id)
    except Exception:
        pass  # Ignore if we can't delete

    bot.send_chat_action(message.chat.id, "typing")

    try:
        # Verify the API key exists and get user data
        from game_scanner.user_auth import get_user_by_api_key

        user_data = get_user_by_api_key(api_key)

        if not user_data:
            bot.send_message(
                message.chat.id, "❌ Invalid API key. Please check and try again."
            )
            return

        # Link this Telegram user to the existing account
        from game_scanner.db import get_collection

        users_collection = get_collection("users")
        user_doc = users_collection.document(api_key)
        user_doc.update({"telegram_user_id": user_id})

        bgg_username = user_data.get("bgg_username", "Unknown")
        success_text = f"""🎉 API key linked successfully, {first_name}!

Your existing BGG account *{bgg_username}* is now connected to this Telegram account.

🚀 Let's get started! Try these:
• "I played Wingspan yesterday"
• "Add Gloomhaven to my wishlist"  
• "Show my games for 2 players"

/help - See all commands
/commands - Quick action menu"""

        bot.send_message(message.chat.id, success_text)
        logger.info(f"Linked existing API key {api_key} to Telegram user {user_id}")

    except Exception as e:
        logger.error(f"API key registration error: {e}")
        bot.send_message(message.chat.id, f"❌ Registration failed: {str(e)}")


@bot.message_handler(commands=["help"])
def handle_help(message):
    logger.info(message)
    help_text = """🎲 *BGG Logger Bot Help*

*Main Commands:*
/start - Welcome screen and status
/register - Connect your BGG account (shows options)
/help - Show this help message
/commands - Interactive command menu
/version - Show bot version

*Registration Commands:*
/register_with_bgg - Register with BGG username/password
/register_with_api - Link existing API key

*Natural Language Examples:*
• "I played Wingspan with Alice and Bob"
• "Log Azul, played yesterday, 45 minutes"
• "Add Gloomhaven to wishlist"
• "Show my games for 4 players"
• "List my recent plays"
• "Delete play #123"

*Direct Commands:*
/play [game details] - Log a play directly

*Features:*
• 📋 Log plays to BoardGameGeek
• 📚 Browse your game collection  
• ❤️ Manage your wishlist
• 🔍 Barcode scanning support
• 📊 View play history
• 🎯 Filter games by player count

Just talk to me naturally about board games and I'll understand what you want to do! 🤖"""

    bot.reply_to(message, help_text)


@bot.message_handler(commands=["commands"])
def handle_commands(message):
    logger.info(message)
    user_id = message.from_user.id
    is_user, _ = check_is_user(user_id)

    if not is_user:
        bot.reply_to(
            message, "Please register first with /register to access all commands."
        )
        return

    markup = telebot.types.InlineKeyboardMarkup()
    markup.add(
        telebot.types.InlineKeyboardButton(
            "📋 Log a Play", callback_data="cmd_log_play"
        ),
        telebot.types.InlineKeyboardButton(
            "❤️ Add to Wishlist", callback_data="cmd_wishlist"
        ),
    )
    markup.add(
        telebot.types.InlineKeyboardButton(
            "📚 My Collection", callback_data="cmd_collection"
        ),
        telebot.types.InlineKeyboardButton(
            "📊 Recent Plays", callback_data="cmd_recent"
        ),
    )
    markup.add(
        telebot.types.InlineKeyboardButton("🔍 Find Game", callback_data="cmd_find"),
        telebot.types.InlineKeyboardButton("❓ Help", callback_data="cmd_help"),
    )

    bot.reply_to(message, "🎮 What would you like to do?", reply_markup=markup)


@bot.message_handler(commands=["version"])
def get_sha(message):
    logger.info(message)
    bot.send_chat_action(message.chat.id, "typing")
    sha = os.popen("git rev-parse HEAD").read().strip()
    bot.reply_to(message, str(sha))


@bot.message_handler(func=lambda message: True)
def next_step(message: telebot.types.Message):
    logger.info(message)
    perform_step(message)


def perform_step(message):
    bot.send_chat_action(message.chat.id, "typing")
    user_id = message.from_user.id
    first_name = message.from_user.first_name or "there"
    message_text = message.text.lower()

    is_user, credit = check_is_user(user_id)

    # Guide unregistered users to registration
    if not is_user:
        response = f"""Hi {first_name}! 👋 

I'd love to help you with board games, but you'll need to register first.

/register - Connect your BoardGameGeek account
/help - Learn what I can do

Ready to get started? 🎲"""

        bot.reply_to(message, response)
        return

    if credit <= 0:
        bot.reply_to(message, f"Sorry {first_name}, you're out of credits! ⊙﹏⊙")
        return

    # Process message for registered users
    message_text = message.text
    messages = [{"role": "user", "content": message_text}]
    if message.reply_to_message:
        previous_message_id = message.reply_to_message.id
        previous_messages = retrieve_messages(previous_message_id)
        messages = previous_messages + messages

    try:
        answer = None
        i = 0
        while answer is None and i < 10:
            messages, answer = parse_chat(messages)
            if answer is None:
                reply = reply_with_last_bot_query(bot, message, messages)
            i += 1
        reply = bot.reply_to(message, str(answer))

    except Exception as e:
        bot.reply_to(message, str(e))
        return

    reply_id = reply.id
    save_document(
        {"message_id": reply_id, "messages": messages}, collection_name="messages"
    )


if __name__ == "__main__":
    sha = os.popen("git rev-parse HEAD").read().strip()
    message = f"Chief, I'm up and running! (≧ω≦)ゞ\nSHA: {sha}"
    bot.send_message(chat_id=os.getenv("TELEGRAM_CHAT_ID", -4108154376), text=message)
    bot.infinity_polling()
