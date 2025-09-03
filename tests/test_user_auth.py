"""Test user authentication functions."""
import pytest
from unittest.mock import Mock, patch
from game_scanner.user_auth import login_user, authenticate_user, create_user


class TestLoginUser:
    """Test the login_user function."""
    
    @patch('game_scanner.user_auth.get_collection')
    def test_login_success(self, mock_get_collection):
        """Test successful login with correct credentials."""
        # Mock Firestore collection and document
        mock_collection = Mock()
        mock_get_collection.return_value = mock_collection
        
        mock_doc = Mock()
        mock_doc.to_dict.return_value = {
            "api_key": "test_api_key_123",
            "encrypted_credentials": "mock_encrypted_creds",
            "encryption_key": "bW9ja19rZXk="  # base64 encoded "mock_key"
        }
        mock_collection.where.return_value.limit.return_value.get.return_value = [mock_doc]
        
        # Mock decrypt_credentials to return matching password
        with patch('game_scanner.user_auth.decrypt_credentials') as mock_decrypt:
            mock_decrypt.return_value = ("test_user", "correct_password")
            
            result = login_user("test_user", "correct_password")
            
            assert result == "test_api_key_123"
            mock_collection.where.assert_called_with("bgg_username", "==", "test_user")

    @patch('game_scanner.user_auth.get_collection')
    def test_login_wrong_password(self, mock_get_collection):
        """Test login with wrong password."""
        mock_collection = Mock()
        mock_get_collection.return_value = mock_collection
        
        mock_doc = Mock()
        mock_doc.to_dict.return_value = {
            "api_key": "test_api_key_123",
            "encrypted_credentials": "mock_encrypted_creds",
            "encryption_key": "bW9ja19rZXk="
        }
        mock_collection.where.return_value.limit.return_value.get.return_value = [mock_doc]
        
        with patch('game_scanner.user_auth.decrypt_credentials') as mock_decrypt:
            mock_decrypt.return_value = ("test_user", "stored_password")
            
            result = login_user("test_user", "wrong_password")
            
            assert result is None

    @patch('game_scanner.user_auth.get_collection')
    def test_login_user_not_found(self, mock_get_collection):
        """Test login when user doesn't exist."""
        mock_collection = Mock()
        mock_get_collection.return_value = mock_collection
        mock_collection.where.return_value.limit.return_value.get.return_value = []
        
        result = login_user("nonexistent_user", "any_password")
        
        assert result is None


class TestAuthenticateUser:
    """Test the authenticate_user function."""
    
    @patch('game_scanner.user_auth.login_user')
    def test_authenticate_existing_user(self, mock_login):
        """Test authentication of existing user."""
        mock_login.return_value = "existing_api_key"
        
        result = authenticate_user("existing_user", "password")
        
        assert result == "existing_api_key"
        mock_login.assert_called_with("existing_user", "password")

    @patch('game_scanner.user_auth.create_user')
    @patch('game_scanner.user_auth.login_user')
    def test_authenticate_new_user(self, mock_login, mock_create):
        """Test authentication creates new user when login fails."""
        mock_login.return_value = None  # Login fails
        mock_create.return_value = "new_api_key"
        
        result = authenticate_user("new_user", "password")
        
        assert result == "new_api_key"
        mock_login.assert_called_with("new_user", "password")
        mock_create.assert_called_with("new_user", "password")

    @patch('game_scanner.user_auth.create_user')
    @patch('game_scanner.user_auth.login_user')
    def test_authenticate_wrong_password(self, mock_login, mock_create):
        """Test authentication with wrong password for existing user."""
        mock_login.return_value = None  # Login fails
        mock_create.side_effect = ValueError("BGG username already registered")
        
        with pytest.raises(ValueError, match="Invalid credentials"):
            authenticate_user("existing_user", "wrong_password")