import hashlib
import secrets
import base64
import json
import requests
from typing import Optional, Dict, Tuple
from cryptography.fernet import Fernet
from loguru import logger

from game_scanner.db import get_collection


def validate_bgg_credentials(username: str, password: str) -> bool:
    """Validate BGG credentials by attempting login."""
    login_payload = {"credentials": {"username": username, "password": password}}
    headers = {"content-type": "application/json"}
    
    try:
        with requests.Session() as s:
            response = s.post(
                "https://boardgamegeek.com/login/api/v1",
                data=json.dumps(login_payload),
                headers=headers,
                timeout=10
            )
            # BGG login returns 200 for both success and failure
            # Check response content to determine success
            if response.status_code == 200:
                # BGG returns empty response body on successful login
                return len(response.text.strip()) == 0
            return False
    except Exception as e:
        logger.error(f"BGG credential validation failed: {e}")
        return False


def generate_api_key() -> str:
    """Generate a secure API key for a user."""
    return secrets.token_urlsafe(32)


def generate_encryption_key() -> bytes:
    """Generate an encryption key for credential storage."""
    return Fernet.generate_key()


def encrypt_credentials(username: str, password: str, encryption_key: bytes) -> str:
    """Encrypt BGG credentials for secure storage."""
    fernet = Fernet(encryption_key)
    credentials = f"{username}:{password}"
    encrypted = fernet.encrypt(credentials.encode())
    return base64.b64encode(encrypted).decode()


def decrypt_credentials(encrypted_creds: str, encryption_key: bytes) -> Tuple[str, str]:
    """Decrypt BGG credentials."""
    fernet = Fernet(encryption_key)
    encrypted_bytes = base64.b64decode(encrypted_creds.encode())
    decrypted = fernet.decrypt(encrypted_bytes).decode()
    username, password = decrypted.split(':', 1)
    return username, password


def login_user(bgg_username: str, bgg_password: str) -> Optional[str]:
    """Login existing user with BGG credentials and return their API key."""
    users_collection = get_collection("users")
    
    # Find user by BGG username
    existing_users = users_collection.where("bgg_username", "==", bgg_username).limit(1).get()
    user_docs = list(existing_users)
    
    if not user_docs:
        return None
    
    user_doc = user_docs[0]
    user_data = user_doc.to_dict()
    
    try:
        # Decrypt and verify password
        encryption_key = base64.b64decode(user_data["encryption_key"].encode())
        stored_username, stored_password = decrypt_credentials(
            user_data["encrypted_credentials"], encryption_key
        )
        
        if stored_password == bgg_password:
            logger.info(f"User {bgg_username} logged in successfully")
            return user_data["api_key"]
        else:
            logger.warning(f"Invalid password for user {bgg_username}")
            return None
            
    except Exception as e:
        logger.error(f"Error during login for user {bgg_username}: {e}")
        return None


def create_user(bgg_username: str, bgg_password: str) -> str:
    """Create a new user with encrypted BGG credentials."""
    users_collection = get_collection("users")
    
    # Check if user already exists
    existing_user = users_collection.where("bgg_username", "==", bgg_username).limit(1).get()
    if list(existing_user):
        raise ValueError("BGG username already registered")
    
    # Generate API key and encryption key
    api_key = generate_api_key()
    encryption_key = generate_encryption_key()
    
    # Encrypt BGG credentials
    encrypted_creds = encrypt_credentials(bgg_username, bgg_password, encryption_key)
    
    # Store user data
    user_data = {
        "bgg_username": bgg_username,
        "api_key": api_key,
        "encrypted_credentials": encrypted_creds,
        "encryption_key": base64.b64encode(encryption_key).decode(),
        "tier": "free",  # New users start as free tier
        "created_at": "2025-08-30",  # You could use firestore.SERVER_TIMESTAMP
    }
    
    # Use API key as document ID for easy lookup
    users_collection.document(api_key).set(user_data)
    
    logger.info(f"Created user with BGG username {bgg_username}")
    return api_key


def authenticate_user(bgg_username: str, bgg_password: str) -> str:
    """Authenticate user: login if exists, otherwise create new account."""
    # Try to login first
    api_key = login_user(bgg_username, bgg_password)
    if api_key:
        return api_key
    
    # If login fails, validate BGG credentials before creating new user
    if not validate_bgg_credentials(bgg_username, bgg_password):
        raise ValueError("Invalid BGG credentials")
    
    # If BGG credentials are valid, try to create new user
    try:
        return create_user(bgg_username, bgg_password)
    except ValueError:
        # User exists but wrong password (shouldn't happen after login_user check)
        raise ValueError("Invalid credentials")


def get_user_by_api_key(api_key: str) -> Optional[Dict]:
    """Retrieve user data by API key."""
    if not api_key:
        return None
        
    users_collection = get_collection("users")
    try:
        user_doc = users_collection.document(api_key).get()
        if user_doc.exists:
            return user_doc.to_dict()
        return None
    except Exception as e:
        logger.error(f"Error retrieving user: {e}")
        return None


def get_user_bgg_credentials(api_key: str) -> Optional[Tuple[str, str]]:
    """Get decrypted BGG credentials for a user."""
    user = get_user_by_api_key(api_key)
    if not user:
        return None
        
    try:
        encryption_key = base64.b64decode(user["encryption_key"].encode())
        return decrypt_credentials(user["encrypted_credentials"], encryption_key)
    except Exception as e:
        logger.error(f"Error decrypting credentials: {e}")
        return None


def verify_api_key(api_key: str) -> bool:
    """Verify if an API key is valid."""
    return get_user_by_api_key(api_key) is not None


def delete_user(api_key: str) -> bool:
    """Delete a user account and all associated data."""
    try:
        users_collection = get_collection("users")
        user_doc = users_collection.document(api_key)
        
        # Check if user exists
        if not user_doc.get().exists:
            logger.warning(f"User with API key {api_key} not found")
            return False
        
        # Delete user document
        user_doc.delete()
        logger.info(f"Deleted user with API key {api_key}")
        return True
        
    except Exception as e:
        logger.error(f"Error deleting user {api_key}: {e}")
        return False


def delete_user_by_telegram_id(telegram_user_id: int) -> bool:
    """Delete a user account by Telegram ID."""
    try:
        users_collection = get_collection("users")
        
        # Find user by telegram_user_id
        query = users_collection.where("telegram_user_id", "==", telegram_user_id).limit(1)
        docs = list(query.get())
        
        if not docs:
            logger.warning(f"User with Telegram ID {telegram_user_id} not found")
            return False
        
        # Delete the user document
        doc_id = docs[0].id
        users_collection.document(doc_id).delete()
        
        logger.info(f"Deleted user with Telegram ID {telegram_user_id}")
        return True
        
    except Exception as e:
        logger.error(f"Error deleting user with Telegram ID {telegram_user_id}: {e}")
        return False


def list_all_users() -> list:
    """List all users (for admin purposes)."""
    users_collection = get_collection("users")
    users = []
    for doc in users_collection.stream():
        user_data = doc.to_dict()
        # Don't return sensitive data
        users.append({
            "api_key": doc.id,
            "bgg_username": user_data.get("bgg_username"),
            "tier": user_data.get("tier"),
            "created_at": user_data.get("created_at")
        })
    return users