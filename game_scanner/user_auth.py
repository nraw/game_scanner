import hashlib
import secrets
import base64
from typing import Optional, Dict, Tuple
from cryptography.fernet import Fernet
from loguru import logger

from game_scanner.db import get_collection


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