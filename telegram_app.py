import os

import telebot
from loguru import logger

from game_scanner.commands import set_it, spike_it
from game_scanner.db import retrieve_messages, save_document
from game_scanner.parse_chat import parse_chat, reply_with_last_bot_query
from game_scanner.telegram_utils import (check_is_user, consume_credit,
                                         get_user_by_telegram_id,
                                         get_user_tier, register_telegram_user,
                                         upgrade_to_premium)

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

    # Upgrade request handlers
    elif call.data.startswith("request_upgrade_"):
        handle_upgrade_request_callback(call)
    elif call.data.startswith("approve_upgrade_"):
        handle_approve_upgrade_callback(call)
    elif call.data.startswith("deny_upgrade_"):
        handle_deny_upgrade_callback(call)


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

Need more help? Just ask! 🤖"""

    else:
        response = "Unknown command. Try /help for assistance."

    bot.send_message(call.message.chat.id, response)


def handle_upgrade_request_callback(call):
    """Handle upgrade request from user."""
    bot.answer_callback_query(call.id)

    # Extract user ID from callback data
    user_id = int(call.data.split("_")[-1])

    # Get user info
    user_data = get_user_by_telegram_id(user_id)
    if not user_data:
        bot.send_message(
            call.message.chat.id, "❌ Error retrieving your account information."
        )
        return

    # Check if already premium
    current_tier = get_user_tier(user_id)
    if current_tier == "premium":
        bot.send_message(call.message.chat.id, "You're already premium! 🌟")
        return

    # Send confirmation to user
    user_first_name = call.from_user.first_name or "User"
    bgg_username = user_data.get("bgg_username", "Unknown")

    user_confirmation = f"""✅ **Premium Upgrade Request Sent**

Hi {user_first_name}! Your premium upgrade request has been sent to our admin for review.

**Request Details:**
• Account: {bgg_username}
• Current Tier: Free
• Requested: Premium Upgrade

You'll receive a notification once your request is processed. Thank you for your patience! 🙏"""

    bot.send_message(call.message.chat.id, user_confirmation)

    # Send admin notification
    admin_chat_id = os.getenv("TELEGRAM_CHAT_ID", -4108154376)

    admin_notification = f"""🚀 **Premium Upgrade Request**

**User Details:**
• Name: {user_first_name}
• Telegram ID: {user_id}
• BGG Username: {bgg_username}
• Current Tier: Free
• Requested: Premium Upgrade

**Actions:**"""

    # Create admin approval buttons
    admin_markup = telebot.types.InlineKeyboardMarkup()
    admin_markup.add(
        telebot.types.InlineKeyboardButton(
            "✅ Approve", callback_data=f"approve_upgrade_{user_id}"
        ),
        telebot.types.InlineKeyboardButton(
            "❌ Deny", callback_data=f"deny_upgrade_{user_id}"
        ),
    )

    bot.send_message(admin_chat_id, admin_notification, reply_markup=admin_markup)


def handle_approve_upgrade_callback(call):
    """Handle admin approval of upgrade request."""
    bot.answer_callback_query(call.id, "Processing upgrade...")

    # Extract user ID from callback data
    user_id = int(call.data.split("_")[-1])

    # Perform the upgrade
    success = upgrade_to_premium(user_id)

    if success:
        # Update admin message
        bot.edit_message_text(
            chat_id=call.message.chat.id,
            message_id=call.message.message_id,
            text=f"{call.message.text}\n\n✅ **APPROVED** - User {user_id} upgraded to Premium",
        )

        # Notify the user
        try:
            user_notification = """🎉 **Premium Upgrade Approved!**

Congratulations! Your premium upgrade request has been approved.

**New Status:**
• ⭐ **Premium Tier**
• 💳 **1000 Credits** available
• 🚀 **All features unlocked**

Ready to explore? Try:
• "I played Wingspan with friends yesterday"
• "Add Gloomhaven to my wishlist"
• "Show my games for 3 players"

/credits - Check your new balance
/help - See all available features

Thank you for upgrading! 🎯"""

            bot.send_message(user_id, user_notification)
        except Exception as e:
            logger.error(f"Could not notify user {user_id} of approval: {e}")
            bot.send_message(
                call.message.chat.id,
                f"⚠️ Upgrade successful but couldn't notify user {user_id}",
            )
    else:
        bot.send_message(call.message.chat.id, f"❌ Failed to upgrade user {user_id}")


def handle_deny_upgrade_callback(call):
    """Handle admin denial of upgrade request."""
    bot.answer_callback_query(call.id, "Request denied")

    # Extract user ID from callback data
    user_id = int(call.data.split("_")[-1])

    # Update admin message
    bot.edit_message_text(
        chat_id=call.message.chat.id,
        message_id=call.message.message_id,
        text=f"{call.message.text}\n\n❌ **DENIED** - Request for user {user_id} rejected",
    )

    # Notify the user
    try:
        user_notification = """❌ **Premium Upgrade Request Denied**

Unfortunately, your premium upgrade request has been denied at this time.

**Next Steps:**
• Contact support for more information
• Ensure payment has been processed if applicable
• Try again later if this was due to a temporary issue

If you believe this was an error, please contact support directly.

Thank you for your understanding. 🙏"""

        bot.send_message(user_id, user_notification)
    except Exception as e:
        logger.error(f"Could not notify user {user_id} of denial: {e}")
        bot.send_message(
            call.message.chat.id, f"⚠️ Request denied but couldn't notify user {user_id}"
        )


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
/credits - Check your credit balance and account info
/upgrade - View premium upgrade options
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


@bot.message_handler(commands=["credits"])
def handle_credits(message):
    logger.info(message)
    user_id = message.from_user.id
    first_name = message.from_user.first_name or "there"

    is_user, credit = check_is_user(user_id)
    if not is_user:
        bot.reply_to(
            message, "Please register first with /register to check your credits."
        )
        return

    user_data = get_user_by_telegram_id(user_id)
    if user_data:
        tier = user_data.get("tier", "free")
        bgg_username = user_data.get("bgg_username", "Unknown")

        credit_text = f"""💳 **Credit Status for {first_name}**

**BGG Account:** {bgg_username}
**Tier:** {tier.title()}
**Available Credits:** {credit}

**Credit Info:**
• Premium users start with 1000 credits
• Free users start with 4 credits  
• Each AI interaction consumes 1 credit
• Commands like /help, /credits, /start are free

**Need more credits?** 
• Free users: /upgrade to see premium options
    else:
        credit_text = f"""💳 **Credit Status**

**Available Credits:** {credit}

Unable to retrieve detailed account information."""

    bot.reply_to(message, credit_text)


@bot.message_handler(commands=["upgrade"])
def handle_upgrade(message):
    logger.info(message)
    user_id = message.from_user.id
    first_name = message.from_user.first_name or "there"

    is_user, current_credits = check_is_user(user_id)
    if not is_user:
        bot.reply_to(message, "Please register first with /register before upgrading.")
        return

    current_tier = get_user_tier(user_id)

    if current_tier == "premium":
        bot.reply_to(
            message,
            f"You're already premium, {first_name}! 🌟\n\nUse /credits to see your current balance.",
        )
        return

    # Show upgrade information with request option
    upgrade_text = f"""⭐ **Upgrade to Premium**

Hi {first_name}! Ready to unlock the full experience?

**Current Status:**
• Tier: Free ({current_credits} credits remaining)
• Limited to basic features

**Premium Benefits:**
• 🚀 **1000 credits** (vs 4 for free users)

**How to Upgrade:**
Click "Request Premium" below to send an upgrade request to our admin for manual approval.

⚠️ **Note:** This command only shows upgrade information. The button below will send your upgrade request for admin review."""

    # Add inline button for upgrade request
    markup = telebot.types.InlineKeyboardMarkup()
    markup.add(
        telebot.types.InlineKeyboardButton(
            "🚀 Request Premium Upgrade", callback_data=f"request_upgrade_{user_id}"
        )
    )

    bot.reply_to(message, upgrade_text, reply_markup=markup)


@bot.message_handler(commands=["admin_upgrade"])
def handle_admin_upgrade(message):
    """Admin-only command to upgrade users. Requires admin authorization."""
    logger.info(message)
    user_id = message.from_user.id

    # Check if user is admin (you would implement proper admin check here)
    ADMIN_USER_IDS = [1901217395, 6200147668]  # Replace with actual admin IDs

    if user_id not in ADMIN_USER_IDS:
        bot.reply_to(message, "❌ Access denied. Admin privileges required.")
        return

    # Parse target user ID from command
    parts = message.text.split()
    if len(parts) != 2:
        bot.reply_to(message, "Usage: `/admin_upgrade TELEGRAM_USER_ID`")
        return

    try:
        target_user_id = int(parts[1])
    except ValueError:
        bot.reply_to(message, "❌ Invalid user ID format.")
        return

    # Check if target user exists
    is_user, _ = check_is_user(target_user_id)
    if not is_user:
        bot.reply_to(message, f"❌ User {target_user_id} not found in database.")
        return

    current_tier = get_user_tier(target_user_id)
    if current_tier == "premium":
        bot.reply_to(message, f"User {target_user_id} is already premium.")
        return

    # Perform the upgrade
    success = upgrade_to_premium(target_user_id)

    if success:
        bot.reply_to(
            message, f"✅ Successfully upgraded user {target_user_id} to premium."
        )

        # Notify the upgraded user
        try:
            notification = """🎉 **Congratulations!**

Your account has been upgraded to **Premium**!

**New Status:**
• ⭐ **Premium Tier** 
• 💳 **1000 Credits** available
• 🚀 **All features unlocked**

/credits - Check your new balance
/help - See all available features"""

            bot.send_message(target_user_id, notification)
        except Exception as e:
            logger.error(f"Could not notify user {target_user_id}: {e}")

    else:
        bot.reply_to(message, f"❌ Failed to upgrade user {target_user_id}.")


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
        # Consume a credit for this AI interaction
        credit_consumed = consume_credit(user_id, 1)
        if not credit_consumed:
            bot.reply_to(
                message,
                "❌ Unable to process request - credit system error. Please try /credits to check your balance.",
            )
            return

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
