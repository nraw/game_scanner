from typing import Optional, Tuple

import structlog

from game_scanner.db import get_collection
from game_scanner.user_auth import authenticate_user

logger = structlog.get_logger()


def check_is_user(telegram_user_id: int) -> Tuple[bool, int]:
    """Check if a Telegram user ID is registered and return their credit balance."""
    users_collection = get_collection("users")

    try:
        # Query for user with this telegram_user_id
        query = users_collection.where(
            "telegram_user_id", "==", telegram_user_id
        ).limit(1)
        docs = list(query.get())

        if docs:
            user_data = docs[0].to_dict()

            # Get actual credits from database, with fallback to tier-based calculation
            stored_credits = user_data.get("credits")
            if stored_credits is not None:
                return True, stored_credits

            # Fallback: calculate based on tier (for legacy accounts)
            tier = user_data.get("tier", "free")
            if tier == "premium":
                credits = 1000  # Premium users get more credits
            else:
                credits = 4  # Free tier users

            # Initialize credits in database for future use
            doc_id = docs[0].id
            users_collection.document(doc_id).update({"credits": credits})

            return True, credits

        # User not found
        return False, 0

    except Exception as e:
        logger.error("error checking user", telegram_user_id=telegram_user_id, error=str(e))
        return False, 0


def consume_credit(telegram_user_id: int, amount: int = 1) -> bool:
    """Consume credits for a user. Returns True if successful, False if insufficient credits."""
    users_collection = get_collection("users")

    try:
        # Query for user with this telegram_user_id
        query = users_collection.where(
            "telegram_user_id", "==", telegram_user_id
        ).limit(1)
        docs = list(query.get())

        if not docs:
            return False

        user_data = docs[0].to_dict()
        current_credits = user_data.get("credits", 0)

        if current_credits < amount:
            return False  # Insufficient credits

        # Deduct credits
        new_credits = current_credits - amount
        doc_id = docs[0].id
        users_collection.document(doc_id).update({"credits": new_credits})

        logger.info("consumed credits", telegram_user_id=telegram_user_id, amount=amount, remaining=new_credits)
        return True

    except Exception as e:
        logger.error("error consuming credits", telegram_user_id=telegram_user_id, error=str(e))
        return False


def add_credits(telegram_user_id: int, amount: int) -> bool:
    """Add credits to a user account. Returns True if successful."""
    users_collection = get_collection("users")

    try:
        # Query for user with this telegram_user_id
        query = users_collection.where(
            "telegram_user_id", "==", telegram_user_id
        ).limit(1)
        docs = list(query.get())

        if not docs:
            return False

        user_data = docs[0].to_dict()
        current_credits = user_data.get("credits", 0)
        new_credits = current_credits + amount

        doc_id = docs[0].id
        users_collection.document(doc_id).update({"credits": new_credits})

        logger.info("added credits", telegram_user_id=telegram_user_id, amount=amount, new_balance=new_credits)
        return True

    except Exception as e:
        logger.error("error adding credits", telegram_user_id=telegram_user_id, error=str(e))
        return False


def upgrade_to_premium(telegram_user_id: int) -> bool:
    """Upgrade a user to premium tier and give them 1000 credits."""
    users_collection = get_collection("users")

    try:
        # Query for user with this telegram_user_id
        query = users_collection.where(
            "telegram_user_id", "==", telegram_user_id
        ).limit(1)
        docs = list(query.get())

        if not docs:
            return False

        user_data = docs[0].to_dict()
        current_tier = user_data.get("tier", "free")

        if current_tier == "premium":
            logger.info("user already premium", telegram_user_id=telegram_user_id)
            return True  # Already premium

        # Upgrade to premium and give 1000 credits
        doc_id = docs[0].id
        users_collection.document(doc_id).update({"tier": "premium", "credits": 1000})

        logger.info("upgraded to premium", telegram_user_id=telegram_user_id, credits=1000)
        return True

    except Exception as e:
        logger.error("error upgrading to premium", telegram_user_id=telegram_user_id, error=str(e))
        return False


def get_user_tier(telegram_user_id: int) -> str:
    """Get the tier of a user."""
    users_collection = get_collection("users")

    try:
        query = users_collection.where(
            "telegram_user_id", "==", telegram_user_id
        ).limit(1)
        docs = list(query.get())

        if docs:
            user_data = docs[0].to_dict()
            return user_data.get("tier", "free")
        return "unknown"

    except Exception as e:
        logger.error("error getting user tier", telegram_user_id=telegram_user_id, error=str(e))
        return "unknown"


def register_telegram_user(
    telegram_user_id: int, bgg_username: str, bgg_password: str
) -> Optional[str]:
    """Register a new Telegram user with their BGG credentials."""

    try:
        # Create user account with BGG credentials
        api_key = authenticate_user(bgg_username, bgg_password)

        # Update the user document to include telegram_user_id
        users_collection = get_collection("users")
        user_doc = users_collection.document(api_key)
        user_doc.update({"telegram_user_id": telegram_user_id})

        logger.info("registered telegram user", telegram_user_id=telegram_user_id, bgg_username=bgg_username)
        return api_key

    except ValueError as e:
        if "already registered" in str(e):
            # Check if this is an existing user without telegram_user_id
            logger.info("BGG username exists, attempting link", bgg_username=bgg_username, telegram_user_id=telegram_user_id)
            return try_link_existing_user(telegram_user_id, bgg_username, bgg_password)
        else:
            logger.error("error registering telegram user", telegram_user_id=telegram_user_id, error=str(e))
            return None
    except Exception as e:
        logger.error("error registering telegram user", telegram_user_id=telegram_user_id, error=str(e))
        return None


def try_link_existing_user(
    telegram_user_id: int, bgg_username: str, bgg_password: str
) -> Optional[str]:
    """Try to link an existing user account that doesn't have a telegram_user_id yet."""
    from game_scanner.user_auth import get_user_bgg_credentials

    try:
        users_collection = get_collection("users")

        # Find user by BGG username
        query = users_collection.where("bgg_username", "==", bgg_username).limit(1)
        docs = list(query.get())

        if not docs:
            logger.error("no user found", bgg_username=bgg_username)
            return None

        user_doc = docs[0]
        api_key = user_doc.id
        user_data = user_doc.to_dict()

        # Check if user already has a telegram_user_id (someone else might have claimed it)
        if user_data.get("telegram_user_id"):
            logger.error("user already linked to another telegram account", bgg_username=bgg_username, existing_telegram_id=user_data['telegram_user_id'])
            return None

        # Verify the password matches by trying to decrypt credentials
        stored_creds = get_user_bgg_credentials(api_key)
        if not stored_creds or stored_creds[1] != bgg_password:
            logger.error("password verification failed", bgg_username=bgg_username)
            return None

        # Link this telegram user to the existing account
        user_doc.reference.update({"telegram_user_id": telegram_user_id})

        logger.info("linked existing user", bgg_username=bgg_username, telegram_user_id=telegram_user_id)
        return api_key

    except Exception as e:
        logger.error("error linking existing user", bgg_username=bgg_username, telegram_user_id=telegram_user_id, error=str(e))
        return None


def get_user_by_telegram_id(telegram_user_id: int) -> Optional[dict]:
    """Get user data by Telegram user ID."""
    users_collection = get_collection("users")

    try:
        query = users_collection.where(
            "telegram_user_id", "==", telegram_user_id
        ).limit(1)
        docs = list(query.get())

        if docs:
            return docs[0].to_dict()
        return None

    except Exception as e:
        logger.error("error retrieving user", telegram_user_id=telegram_user_id, error=str(e))
        return None
