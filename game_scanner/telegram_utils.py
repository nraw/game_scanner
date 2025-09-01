from typing import Optional, Tuple
from loguru import logger

from game_scanner.db import get_collection


def check_is_user(telegram_user_id: int) -> Tuple[bool, int]:
    """Check if a Telegram user ID is registered and return their credit balance."""
    users_collection = get_collection("users")
    
    try:
        # Query for user with this telegram_user_id
        query = users_collection.where("telegram_user_id", "==", telegram_user_id).limit(1)
        docs = list(query.get())
        
        if docs:
            user_data = docs[0].to_dict()
            tier = user_data.get("tier", "free")
            
            # Determine credits based on tier
            if tier == "premium":
                credits = 1000  # Premium users get more credits
            else:
                credits = 100   # Free tier users
                
            return True, credits
            
        # User not found
        return False, 0
        
    except Exception as e:
        logger.error(f"Error checking user {telegram_user_id}: {e}")
        return False, 0


def register_telegram_user(telegram_user_id: int, bgg_username: str, bgg_password: str) -> Optional[str]:
    """Register a new Telegram user with their BGG credentials."""
    from game_scanner.user_auth import create_user
    
    try:
        # Create user account with BGG credentials
        api_key = create_user(bgg_username, bgg_password)
        
        # Update the user document to include telegram_user_id
        users_collection = get_collection("users")
        user_doc = users_collection.document(api_key)
        user_doc.update({"telegram_user_id": telegram_user_id})
        
        logger.info(f"Registered Telegram user {telegram_user_id} with BGG username {bgg_username}")
        return api_key
        
    except ValueError as e:
        if "already registered" in str(e):
            # Check if this is an existing user without telegram_user_id
            logger.info(f"BGG username {bgg_username} already exists, checking if we can link to Telegram user {telegram_user_id}")
            return try_link_existing_user(telegram_user_id, bgg_username, bgg_password)
        else:
            logger.error(f"Error registering Telegram user {telegram_user_id}: {e}")
            return None
    except Exception as e:
        logger.error(f"Error registering Telegram user {telegram_user_id}: {e}")
        return None


def try_link_existing_user(telegram_user_id: int, bgg_username: str, bgg_password: str) -> Optional[str]:
    """Try to link an existing user account that doesn't have a telegram_user_id yet."""
    from game_scanner.user_auth import get_user_bgg_credentials
    
    try:
        users_collection = get_collection("users")
        
        # Find user by BGG username
        query = users_collection.where("bgg_username", "==", bgg_username).limit(1)
        docs = list(query.get())
        
        if not docs:
            logger.error(f"No user found with BGG username {bgg_username}")
            return None
            
        user_doc = docs[0]
        api_key = user_doc.id
        user_data = user_doc.to_dict()
        
        # Check if user already has a telegram_user_id (someone else might have claimed it)
        if user_data.get("telegram_user_id"):
            logger.error(f"User {bgg_username} already linked to Telegram user {user_data['telegram_user_id']}")
            return None
        
        # Verify the password matches by trying to decrypt credentials
        stored_creds = get_user_bgg_credentials(api_key)
        if not stored_creds or stored_creds[1] != bgg_password:
            logger.error(f"Password verification failed for {bgg_username}")
            return None
        
        # Link this telegram user to the existing account
        user_doc.reference.update({"telegram_user_id": telegram_user_id})
        
        logger.info(f"Successfully linked existing user {bgg_username} to Telegram user {telegram_user_id}")
        return api_key
        
    except Exception as e:
        logger.error(f"Error linking existing user {bgg_username} to Telegram user {telegram_user_id}: {e}")
        return None


def get_user_by_telegram_id(telegram_user_id: int) -> Optional[dict]:
    """Get user data by Telegram user ID."""
    users_collection = get_collection("users")
    
    try:
        query = users_collection.where("telegram_user_id", "==", telegram_user_id).limit(1)
        docs = list(query.get())
        
        if docs:
            return docs[0].to_dict()
        return None
        
    except Exception as e:
        logger.error(f"Error retrieving user by Telegram ID {telegram_user_id}: {e}")
        return None
