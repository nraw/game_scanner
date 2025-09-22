"""
Telegram-specific API handlers for the game scanner service.
Contains handlers for Mini App registration and static file serving.
"""

import json
import os
import hashlib
import hmac
from urllib.parse import unquote


class TelegramHandlers:
    """Handles Telegram-specific API endpoints."""

    def __init__(self, request_handler):
        """Initialize with reference to the main request handler."""
        self.handler = request_handler

    def handle_telegram_registration(self, params):
        """Handle Telegram Mini App registration."""
        print(f"handle_telegram_registration called with method: {self.handler.command}")

        # Get JSON data from params (already parsed in main handler)
        if self.handler.command == 'POST':
            raw_post_data = params.get('_raw_post_data')
            print(f"Raw POST data: {raw_post_data[:200] if raw_post_data else 'None'}...")

            if raw_post_data:
                try:
                    json_data = json.loads(raw_post_data)

                    bgg_username = json_data.get('bgg_username')
                    bgg_password = json_data.get('bgg_password')
                    telegram_user_id = json_data.get('telegram_user_id')
                    telegram_first_name = json_data.get('telegram_first_name', '')
                    init_data = json_data.get('init_data', '')

                    print(f"Parsed data - username: {bgg_username}, telegram_id: {telegram_user_id}")

                except (json.JSONDecodeError, UnicodeDecodeError) as e:
                    print(f"JSON decode error: {e}")
                    self.handler._send_json({'error': f'Invalid JSON data: {str(e)}'}, status=400)
                    return
            else:
                print("No POST data received")
                self.handler._send_json({'error': 'Missing request body'}, status=400)
                return
        else:
            print(f"Method {self.handler.command} not allowed")
            self.handler._send_json({'error': 'Method not allowed. Use POST.'}, status=405)
            return

        # Validate required parameters
        if not all([bgg_username, bgg_password, telegram_user_id]):
            self.handler._send_json({
                'error': 'Missing required parameters: bgg_username, bgg_password, telegram_user_id'
            }, status=400)
            return

        # Validate Telegram init_data (optional but recommended for security)
        # For now, we'll skip validation but it should be implemented in production
        # TODO: Validate init_data hash using bot token

        try:
            # Use the existing telegram registration function
            from game_scanner.telegram_utils import register_telegram_user

            api_key = register_telegram_user(int(telegram_user_id), bgg_username, bgg_password)

            if api_key:
                self.handler._send_json({
                    'success': True,
                    'message': 'Registration successful',
                    'api_key': api_key,
                    'bgg_username': bgg_username
                })
            else:
                self.handler._send_json({'error': 'Registration failed. Please check your BGG credentials.'}, status=400)

        except Exception as e:
            error_msg = str(e)
            if "already registered" in error_msg:
                self.handler._send_json({
                    'error': 'This BGG username is already registered. Try logging in with different credentials or contact support.'
                }, status=409)
            else:
                self.handler._send_json({'error': f'Registration failed: {error_msg}'}, status=500)

    def handle_mini_app_static(self, endpoint):
        """Serve static files for Telegram Mini App."""
        # Remove /telegram_mini_app prefix and get filename
        file_path = endpoint.replace('/telegram_mini_app/', '')

        # Security: only allow specific files
        allowed_files = ['register.html']
        if file_path not in allowed_files:
            self.handler._send_error('File not found', 404)
            return

        try:
            # Get the full path to the mini app file
            current_dir = os.path.dirname(__file__)
            project_root = os.path.dirname(current_dir)  # Go up one level from api/
            mini_app_dir = os.path.join(project_root, 'telegram_mini_app')
            full_path = os.path.join(mini_app_dir, file_path)

            # Read and serve the file
            with open(full_path, 'r', encoding='utf-8') as f:
                content = f.read()

            # Determine content type
            if file_path.endswith('.html'):
                content_type = 'text/html'
            elif file_path.endswith('.js'):
                content_type = 'application/javascript'
            elif file_path.endswith('.css'):
                content_type = 'text/css'
            else:
                content_type = 'text/plain'

            self.handler._send_response(content, content_type)

        except FileNotFoundError:
            self.handler._send_error('File not found', 404)
        except Exception as e:
            self.handler._send_error(f'Error serving file: {str(e)}', 500)

    def validate_telegram_init_data(self, init_data, bot_token):
        """
        Validate Telegram Web App init data.

        Args:
            init_data: The init data from Telegram Web App
            bot_token: The bot token to validate against

        Returns:
            bool: True if valid, False otherwise
        """
        # TODO: Implement proper Telegram init_data validation
        # This should verify the hash to ensure the data comes from Telegram
        # For now, we're skipping this validation

        if not init_data:
            return False

        try:
            # Parse the init_data
            params = dict(param.split('=', 1) for param in init_data.split('&'))

            # Extract hash and create data string for verification
            received_hash = params.pop('hash', '')
            if not received_hash:
                return False

            # Create data string (sorted parameters)
            data_check_string = '\n'.join(f'{key}={value}' for key, value in sorted(params.items()))

            # Create secret key
            secret_key = hmac.new(
                b'WebAppData',
                bot_token.encode(),
                hashlib.sha256
            ).digest()

            # Calculate expected hash
            expected_hash = hmac.new(
                secret_key,
                data_check_string.encode(),
                hashlib.sha256
            ).hexdigest()

            return expected_hash == received_hash

        except Exception as e:
            print(f"Error validating init_data: {e}")
            return False