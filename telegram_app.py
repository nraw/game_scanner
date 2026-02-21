import os

import structlog
import telebot

from game_scanner.logging import setup_logging

setup_logging()
logger = structlog.get_logger()

from game_scanner.commands import set_it, spike_it
from game_scanner.db import retrieve_messages, save_document
from game_scanner.parse_chat import parse_chat, reply_with_last_bot_query
from game_scanner.telegram_utils import (check_is_user, consume_credit,
                                         get_user_by_telegram_id,
                                         get_user_tier, register_telegram_user,
                                         upgrade_to_premium)
from game_scanner.user_auth import delete_user_by_telegram_id

bot = telebot.TeleBot(os.environ["TELEGRAM_TOKEN"], parse_mode="Markdown")


@bot.message_handler(commands=["start"])
def send_welcome(message):
    logger.info("command received", command="start", user_id=message.from_user.id)
    user_id = message.from_user.id
    first_name = message.from_user.first_name or "there"

    is_user, credit = check_is_user(user_id)

    if not is_user:
        welcome_text = f"""🎲 Hello {first_name}! Welcome to BGG Logger Bot!

I'm your personal board game assistant. I can help you:
• 📋 Log plays to BoardGameGeek
• 📚 Manage your game collection
• ❤️ Add games to your wishlist & owned collection
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
• "Add [game] to my collection" or "Add [game] to wishlist"
• "Show my games for 4 players"

/commands - See all available features
/help - Get detailed help"""

    bot.reply_to(message, welcome_back_text)


@bot.callback_query_handler(func=lambda call: True)
def callback_query(call):
    logger.info("callback received", callback_data=call.data, user_id=call.from_user.id)

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
    
    # Account deletion handlers
    elif call.data.startswith("confirm_delete_"):
        handle_confirm_delete_callback(call)
    elif call.data.startswith("cancel_delete_"):
        handle_cancel_delete_callback(call)

    # Registration method selection
    elif call.data == "show_command_registration":
        handle_command_registration_callback(call)


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
        response = """❤️ *Manage Collection & Wishlist*

Tell me which games you want to add:

*Owned Collection Examples:*
• "Add Gloomhaven to my collection"
• "I own Spirit Island"
• "Mark Wingspan as owned"

*Wishlist Examples:*
• "Add Catan to my wishlist"
• "Wishlist Terraforming Mars"
• "I want Azul"

I'll find the game and add it to your BGG collection or wishlist! 🎯"""

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
            logger.error("could not notify user of approval", user_id=user_id, error=str(e))
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
        logger.error("could not notify user of denial", user_id=user_id, error=str(e))
        bot.send_message(
            call.message.chat.id, f"⚠️ Request denied but couldn't notify user {user_id}"
        )


def handle_confirm_delete_callback(call):
    """Handle confirmation of account deletion."""
    bot.answer_callback_query(call.id, "Processing deletion...")
    
    # Extract user ID from callback data
    user_id = int(call.data.split("_")[-1])
    first_name = call.from_user.first_name or "User"
    
    # Verify this is the user's own account
    if call.from_user.id != user_id:
        bot.answer_callback_query(call.id, "❌ Access denied")
        return
    
    # Attempt to delete the account
    success = delete_user_by_telegram_id(user_id)
    
    if success:
        # Update the message to show completion
        bot.edit_message_text(
            chat_id=call.message.chat.id,
            message_id=call.message.message_id,
            text=f"""✅ **Account Deleted Successfully**

{first_name}, your account has been permanently deleted.

**What was deleted:**
• Your BGG account connection
• All stored credentials
• Your credit balance and tier information
• All associated data

Thank you for using BGG Logger Bot. If you ever want to use the service again, you can register a new account with /register.

Goodbye! 👋"""
        )
        logger.info("account deleted", user_id=user_id)
        
    else:
        # Show error message
        bot.edit_message_text(
            chat_id=call.message.chat.id,
            message_id=call.message.message_id,
            text=f"""❌ **Account Deletion Failed**

{first_name}, we encountered an error while trying to delete your account.

**What to do:**
• Try again later with /delete_account
• Contact support if the problem persists
• Check your connection and try again

Your account remains active."""
        )
        logger.error("failed to delete account", user_id=user_id)


def handle_cancel_delete_callback(call):
    """Handle cancellation of account deletion."""
    bot.answer_callback_query(call.id, "Deletion cancelled")
    
    # Extract user ID from callback data
    user_id = int(call.data.split("_")[-1])
    first_name = call.from_user.first_name or "User"
    
    # Verify this is the user's own account
    if call.from_user.id != user_id:
        bot.answer_callback_query(call.id, "❌ Access denied")
        return
    
    # Update the message to show cancellation
    bot.edit_message_text(
        chat_id=call.message.chat.id,
        message_id=call.message.message_id,
        text=f"""✅ **Account Deletion Cancelled**

{first_name}, your account deletion has been cancelled. Your account remains active.

**Your account is safe:**
• No data was deleted
• Your BGG connection is still active
• Your credits and settings are unchanged

Use /help to see what you can do with your account."""
    )


def handle_command_registration_callback(call):
    """Handle fallback to command-based registration."""
    bot.answer_callback_query(call.id)

    command_text = """📝 **Command-based Registration**

Send me a message in this format:
`/register_with_bgg YOUR_USERNAME YOUR_PASSWORD`

Example: `/register_with_bgg johnsmith mypassword123`

⚠️ *Security note:* Your credentials are encrypted and stored securely. I only use them to interact with BGG on your behalf.

Don't have a BGG account yet? Create one at boardgamegeek.com first!

*Tip: The form above is more secure and user-friendly!*"""

    bot.send_message(call.message.chat.id, command_text)


@bot.message_handler(commands=["play"])
def send_play(message):
    logger.info("command received", command="play", user_id=message.from_user.id)
    message.text = " ".join(message.text.split()[1:])
    perform_step(message)


@bot.message_handler(commands=["register"])
def handle_register(message):
    logger.info("command received", command="register", user_id=message.from_user.id)
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

Choose how you'd like to register:"""

    # Create inline keyboard with Mini App option
    markup = telebot.types.InlineKeyboardMarkup()

    # Mini App button (preferred method)
    web_app = telebot.types.WebAppInfo("https://gamescanner.vercel.app/telegram_mini_app/register.html")
    markup.add(telebot.types.InlineKeyboardButton(
        "🎯 Open Registration Form",
        web_app=web_app
    ))

    # Alternative command-based registration
    markup.add(telebot.types.InlineKeyboardButton(
        "📝 Use Command Instead",
        callback_data="show_command_registration"
    ))

    bot.reply_to(message, register_text, reply_markup=markup)


@bot.message_handler(commands=["register_with_bgg"])
def handle_register_with_bgg(message):
    logger.info("command received", command="register_with_bgg", user_id=message.from_user.id)
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
        logger.error("registration error", error=str(e))
        if "already registered" in str(e):
            recovery_text = """❌ This BGG username is already registered.

If this is your account from our web interface, I tried to link it automatically. If that didn't work, you can:

1. **Double-check your password** and try again

2. **Contact support** if you're still having trouble

Note: Each BGG account can only be linked to one Telegram user for security."""
            bot.send_message(message.chat.id, recovery_text)
        else:
            bot.send_message(message.chat.id, f"❌ Registration failed: {str(e)}")




@bot.message_handler(commands=["help"])
def handle_help(message):
    logger.info("command received", command="help", user_id=message.from_user.id)
    help_text = """🎲 *BGG Logger Bot Help*

*Main Commands:*
/start - Welcome screen and status
/register - Connect your BGG account (shows options)
/help - Show this help message
/commands - Interactive command menu
/credits - Check your credit balance and account info
/upgrade - View premium upgrade options
/delete\\_account - Permanently delete your account
/version - Show bot version

*Registration Commands:*
/register\\_with\\_bgg - Register with BGG username/password

*Natural Language Examples:*
• "I played Wingspan with Alice and Bob"
• "Log Azul, played yesterday, 45 minutes"
• "Add Gloomhaven to my collection"
• "Add Catan to wishlist"
• "Show my games for 4 players"
• "List my recent plays"
• "Delete play \\#123"

*Direct Commands:*
/play \\[game details\\] - Log a play directly

*Features:*
• 📋 Log plays to BoardGameGeek
• 📚 Browse your game collection
• ❤️ Manage your wishlist & collection
• 📊 View play history
• 🎯 Filter games by player count

Just talk to me naturally about board games and I'll understand what you want to do! 🤖"""

    bot.reply_to(message, help_text)


@bot.message_handler(commands=["commands"])
def handle_commands(message):
    logger.info("command received", command="commands", user_id=message.from_user.id)
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
            "❤️ Manage Collection", callback_data="cmd_wishlist"
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
    logger.info("command received", command="credits", user_id=message.from_user.id)
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
• Free users: /upgrade to see premium options"""
    else:
        credit_text = f"""💳 **Credit Status**

**Available Credits:** {credit}

Unable to retrieve detailed account information."""

    bot.reply_to(message, credit_text)


@bot.message_handler(commands=["upgrade"])
def handle_upgrade(message):
    logger.info("command received", command="upgrade", user_id=message.from_user.id)
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
    logger.info("command received", command="admin_upgrade", user_id=message.from_user.id)
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
            logger.error("could not notify user", user_id=target_user_id, error=str(e))

    else:
        bot.reply_to(message, f"❌ Failed to upgrade user {target_user_id}.")


@bot.message_handler(commands=["delete_account"])
def handle_delete_account(message):
    logger.info("command received", command="delete_account", user_id=message.from_user.id)
    user_id = message.from_user.id
    first_name = message.from_user.first_name or "there"

    is_user, _ = check_is_user(user_id)
    if not is_user:
        bot.reply_to(
            message, "You don't have an account to delete. Use /register to create one."
        )
        return

    # Get user data for confirmation
    user_data = get_user_by_telegram_id(user_id)
    bgg_username = user_data.get("bgg_username", "Unknown") if user_data else "Unknown"

    # Send confirmation message with inline buttons
    confirmation_text = f"""⚠️ **Account Deletion Confirmation**

Hi {first_name}, you're about to delete your account permanently.

**Account Details:**
• BGG Username: {bgg_username}
• All your data will be permanently deleted
• This action cannot be undone

Are you sure you want to proceed?"""

    markup = telebot.types.InlineKeyboardMarkup()
    markup.add(
        telebot.types.InlineKeyboardButton(
            "❌ Cancel", callback_data=f"cancel_delete_{user_id}"
        ),
        telebot.types.InlineKeyboardButton(
            "🗑️ Delete Account", callback_data=f"confirm_delete_{user_id}"
        ),
    )

    bot.reply_to(message, confirmation_text, reply_markup=markup)


@bot.message_handler(commands=["version"])
def get_sha(message):
    logger.info("command received", command="version", user_id=message.from_user.id)
    bot.send_chat_action(message.chat.id, "typing")
    sha = os.popen("git rev-parse HEAD").read().strip()
    bot.reply_to(message, str(sha))


@bot.message_handler(content_types=['web_app_data'])
def handle_web_app_data(message):
    """Handle data sent from Telegram Mini App."""
    logger.info("received web app data", user_id=message.from_user.id, data=message.web_app_data.data)

    try:
        import json
        data = json.loads(message.web_app_data.data)
        logger.info("parsed web app data", action=data.get('action'))

        if data.get('action') == 'registration_success':
            api_key = data.get('api_key')
            bgg_username = data.get('bgg_username')
            first_name = message.from_user.first_name or 'there'

            logger.info("processing registration success", first_name=first_name, bgg_username=bgg_username)

            success_text = f"""🎉 Registration successful, {first_name}!

Your BGG account *{bgg_username}* is now connected.

🔑 **Your API Key:** `{api_key}`

⚠️ **IMPORTANT:** Save this API key! You can use it to:
• Access our web interface
• Recover your account if needed

🚀 Let's get started! Try these:
• "I played Wingspan yesterday"
• "Add Gloomhaven to my wishlist"
• "Show my games for 2 players"

/help - See all commands
/commands - Quick action menu"""

            reply = bot.reply_to(message, success_text)
            logger.info("sent registration success message", user_id=message.from_user.id, message_id=reply.message_id)

        else:
            logger.warning("unknown web app action", action=data.get('action'))
            bot.reply_to(message, "Unknown web app action received.")

    except json.JSONDecodeError as e:
        logger.error("JSON decode error in web app data", error=str(e))
        bot.reply_to(message, "Invalid data received from web app.")
    except Exception as e:
        logger.error("error handling web app data", error=str(e))
        import traceback
        traceback.print_exc()
        bot.reply_to(message, "An error occurred processing your registration.")


@bot.message_handler(func=lambda message: True)
def next_step(message: telebot.types.Message):
    logger.info("message received", user_id=message.from_user.id, text=message.text)
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

        # Get user's BGG credentials for play logging
        bgg_username = None
        bgg_password = None
        try:
            user_data = get_user_by_telegram_id(user_id)
            if user_data and user_data.get('api_key'):
                from game_scanner.user_auth import get_user_bgg_credentials
                credentials = get_user_bgg_credentials(user_data['api_key'])
                if credentials:
                    bgg_username, bgg_password = credentials
                    logger.info("retrieved BGG credentials", user_id=user_id, bgg_username=bgg_username)
                else:
                    logger.warning("could not decrypt BGG credentials", user_id=user_id)
            else:
                logger.warning("no API key found", user_id=user_id)
        except Exception as e:
            logger.error("error retrieving BGG credentials", user_id=user_id, error=str(e))

        answer = None
        i = 0
        while answer is None and i < 10:
            messages, answer = parse_chat(messages, bgg_username, bgg_password)
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
