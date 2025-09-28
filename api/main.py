import os
import sys
import json
from http.server import BaseHTTPRequestHandler
from urllib.parse import parse_qs, urlparse

# Add parent directory to path to import game_scanner modules
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

try:
    import telebot
    from loguru import logger
    import sentry_sdk
    from sentry_sdk.integrations.logging import LoggingIntegration

    from game_scanner.barcode2bgg import barcode2bgg
    from game_scanner.commands import process_register_response
    from game_scanner.db import retrieve_document
    from game_scanner.register_play import register_play
    from game_scanner.save_bgg_id import save_bgg_id
    from game_scanner.user_auth import (
        authenticate_user,
        get_user_by_api_key,
        get_user_bgg_credentials,
        verify_api_key,
        list_all_users,
        delete_user
    )
    from .telegram_handlers import TelegramHandlers
    HAS_MODULES = True

    # Initialize Sentry for distributed tracing
    SENTRY_DSN = os.getenv('SENTRY_DSN')
    if SENTRY_DSN:
        import logging
        sentry_logging = LoggingIntegration(
            level=logging.INFO,  # Capture info and above as breadcrumbs
            event_level=logging.ERROR  # Send errors as events
        )
        sentry_sdk.init(
            dsn=SENTRY_DSN,
            integrations=[sentry_logging],
            traces_sample_rate=1.0,  # Capture 100% of transactions for performance monitoring
            profiles_sample_rate=1.0,  # Profile 100% of transactions
            environment=os.getenv('SENTRY_ENVIRONMENT', 'development')
        )
        logger.info("Sentry initialized for API")
    else:
        logger.warning("SENTRY_DSN not set, distributed tracing disabled")

except ImportError as e:
    HAS_MODULES = False
    IMPORT_ERROR = str(e)

class handler(BaseHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        # Initialize telegram handlers
        self.telegram_handlers = None
        super().__init__(*args, **kwargs)

    def do_GET(self):
        self._handle_request()

    def do_POST(self):
        self._handle_request()

    def _handle_request(self):
        # Start a new transaction for this request (if Sentry is available)
        transaction = None
        if HAS_MODULES and sentry_sdk:
            transaction = sentry_sdk.start_transaction(
                op="http.server",
                name=f"{self.command} {self.path}",
                source="url"
            )

            # Extract trace headers from client if present
            sentry_trace = self.headers.get('sentry-trace')

            if sentry_trace:
                sentry_sdk.set_tag("client_trace_id", sentry_trace.split('-')[0] if '-' in sentry_trace else sentry_trace)

            sentry_sdk.set_context("request", {
                "method": self.command,
                "path": self.path,
                "headers": dict(self.headers),
                "client_address": self.client_address[0] if self.client_address else None
            })

        try:
            # Parse URL and query parameters
            parsed_url = urlparse(self.path)
            endpoint = parsed_url.path
            query_params = parse_qs(parsed_url.query)
            
            # Flatten query parameters (parse_qs returns lists)
            query_params = {k: v[0] if v else '' for k, v in query_params.items()}
            
            # Handle POST data
            raw_post_data = None
            if self.command == 'POST':
                content_length = int(self.headers.get('Content-Length', 0))
                if content_length > 0:
                    raw_post_data = self.rfile.read(content_length).decode('utf-8')

                    # Check content type to decide how to parse
                    content_type = self.headers.get('Content-Type', '')

                    if 'application/json' in content_type:
                        # For JSON requests, don't parse as form data
                        query_params['_raw_post_data'] = raw_post_data
                    else:
                        # For form requests, parse as usual
                        form_data = parse_qs(raw_post_data)
                        # Merge form data with query params
                        for k, v in form_data.items():
                            query_params[k] = v[0] if v else ''
            
            print(f"Method: {self.command}, Endpoint: {endpoint}, Params: {query_params}")
            
            # Check if modules loaded successfully
            if not HAS_MODULES:
                self._send_error(f"Import error: {IMPORT_ERROR}")
                return

            # Initialize telegram handlers if not already done
            if self.telegram_handlers is None and HAS_MODULES:
                self.telegram_handlers = TelegramHandlers(self)

            # Route to different endpoints
            if endpoint == "/register":
                self._handle_user_registration(query_params)
            elif endpoint == "/register_telegram":
                if self.telegram_handlers:
                    self.telegram_handlers.handle_telegram_registration(query_params)
                else:
                    self._send_error("Telegram handlers not available")
            elif endpoint == "/delete_account":
                self._handle_delete_account(query_params)
            elif endpoint == "/users":
                self._handle_list_users(query_params)
            elif endpoint.startswith("/lookup"):
                self._handle_lookup(query_params)
            elif endpoint.startswith("/play"):
                self._handle_play_registration(query_params)
            elif endpoint == "/wishlist":
                self._handle_wishlist_addition(query_params)
            elif endpoint == "/owned":
                self._handle_owned_addition(query_params)
            elif endpoint.startswith("/telegram_mini_app"):
                if self.telegram_handlers:
                    self.telegram_handlers.handle_mini_app_static(endpoint)
                else:
                    self._send_error("Telegram handlers not available")
            else:
                # Default: backward compatibility with existing interface
                self._handle_legacy_request(query_params)
                
        except Exception as e:
            print(f"Handler error: {e}")
            import traceback
            traceback.print_exc()

            # Capture exception in Sentry if available
            if HAS_MODULES and sentry_sdk:
                sentry_sdk.capture_exception(e)
                if transaction:
                    transaction.set_status("internal_error")

            self._send_json({'error': str(e), 'type': type(e).__name__}, status=500)

        finally:
            # Finish the transaction
            if transaction:
                transaction.finish()

    def _handle_user_registration(self, params):
        """Handle user authentication (login or register)."""
        bgg_username = params.get("bgg_username")
        bgg_password = params.get("bgg_password")
        
        if not all([bgg_username, bgg_password]):
            self._send_json({
                'error': 'Missing required parameters: bgg_username, bgg_password'
            }, status=400)
            return
            
        try:
            api_key = authenticate_user(bgg_username, bgg_password)
            self._send_json({
                'message': 'Authentication successful',
                'api_key': api_key,
                'bgg_username': bgg_username,
                'instructions': 'Save this API key! Use it in all future requests as ?api_key=YOUR_KEY'
            })
        except ValueError as e:
            self._send_json({'error': str(e)}, status=401)
        except Exception as e:
            self._send_json({'error': f'Authentication failed: {str(e)}'}, status=500)

    def _handle_delete_account(self, params):
        """Handle account deletion."""
        api_key = params.get("api_key")
        confirm_delete = params.get("confirm_delete")
        
        if not api_key:
            self._send_json({
                'error': 'Missing required parameter: api_key'
            }, status=400)
            return
            
        if not confirm_delete:
            self._send_json({
                'error': 'Confirmation required: confirm_delete parameter must be present'
            }, status=400)
            return
            
        # Verify API key exists and get user info before deletion
        user_data = get_user_by_api_key(api_key)
        if not user_data:
            self._send_json({'error': 'Invalid API key'}, status=401)
            return
            
        try:
            success = delete_user(api_key)
            if success:
                self._send_json({
                    'message': 'Account deleted successfully',
                    'deleted_user': user_data.get('bgg_username', 'Unknown'),
                    'warning': 'All your data has been permanently removed'
                })
            else:
                self._send_json({'error': 'Failed to delete account'}, status=500)
                
        except Exception as e:
            self._send_json({'error': f'Account deletion failed: {str(e)}'}, status=500)
    
    def _handle_list_users(self, params):
        """Handle listing all users (admin endpoint)."""
        try:
            users = list_all_users()
            self._send_json({'users': users, 'count': len(users)})
        except Exception as e:
            self._send_json({'error': f'Failed to list users: {str(e)}'}, status=500)
    
    def _handle_lookup(self, params):
        """Handle barcode/game lookup (free feature)."""
        query = params.get("query")
        bgg_id = params.get("bgg_id")
        bg_name = params.get("bg_name")
        is_redirect = "redirect" in params
        
        if not query:
            self._send_json({'error': 'Missing query parameter'}, status=400)
            return
            
        try:
            game_id = self._get_game_id(bgg_id, bg_name, query)
            
            # Save the mapping
            save_bgg_id(query, game_id, extra={"auto": not ((bgg_id or bg_name) and query)})
            
            url = f"https://www.boardgamegeek.com/boardgame/{game_id}"
            
            if is_redirect:
                self._send_redirect(url)
                return
                
            self._send_json({'game_id': game_id, 'url': url})
            
        except Exception as e:
            print(f"Error in lookup: {e}")

            # Check if it's a "not found" case vs actual error
            error_msg = str(e).lower()
            if 'nothing found' in error_msg or 'not found' in error_msg or 'no results' in error_msg:
                # This is expected - barcode not in database, don't spam Sentry
                print(f"Game not found for barcode: {query}")
                self._send_json({'error': 'Game not found for this barcode - please identify manually'}, status=404)
            else:
                # Actual server error - capture in Sentry
                if HAS_MODULES and sentry_sdk:
                    sentry_sdk.set_context("lookup_error", {
                        "query": query,
                        "bgg_id": bgg_id,
                        "bg_name": bg_name,
                        "error_type": type(e).__name__
                    })
                    sentry_sdk.capture_exception(e)
                self._send_json({'error': 'Game lookup failed - please try again or identify manually'}, status=500)
    
    def _handle_play_registration(self, params):
        """Handle play registration (premium feature requiring API key)."""
        api_key = params.get("api_key")
        query = params.get("query")
        bgg_id = params.get("bgg_id")
        bg_name = params.get("bg_name")
        
        # Check API key
        if not api_key:
            self._send_json({
                'error': 'API key required for play registration',
                'instructions': 'Get an API key by registering at /register'
            }, status=401)
            return
            
        if not verify_api_key(api_key):
            self._send_json({'error': 'Invalid API key'}, status=401)
            return
            
        if not query:
            self._send_json({'error': 'Missing query parameter'}, status=400)
            return
            
        try:
            # Get game ID
            game_id = self._get_game_id(bgg_id, bg_name, query)
            
            # Get user's BGG credentials
            bgg_credentials = get_user_bgg_credentials(api_key)
            if not bgg_credentials:
                self._send_json({'error': 'Failed to retrieve user credentials'}, status=500)
                return
                
            username, password = bgg_credentials
            
            # Register the play with user's credentials
            result = register_play(game_id, username, password)
            print(f"Play registration result: {result}")
            
            # Save the mapping
            save_bgg_id(query, game_id, extra={"auto": not ((bgg_id or bg_name) and query)})
            
            self._send_json({
                'message': 'Play registered successfully',
                'game_id': game_id,
                'url': f"https://www.boardgamegeek.com/boardgame/{game_id}"
            })
            
        except Exception as e:
            print(f"Error in play registration: {e}")

            # Capture exception in Sentry with context but send generic error to client
            if HAS_MODULES and sentry_sdk:
                sentry_sdk.set_context("play_registration_error", {
                    "query": query,
                    "bgg_id": bgg_id,
                    "bg_name": bg_name,
                    "has_api_key": bool(api_key),
                    "error_type": type(e).__name__
                })
                sentry_sdk.capture_exception(e)

            self._send_json({'error': 'Play registration failed - please try again'}, status=500)

    def _handle_wishlist_addition(self, params):
        """Handle adding games to user's wishlist (premium feature requiring API key)."""
        api_key = params.get("api_key")
        query = params.get("query")
        bgg_id = params.get("bgg_id")
        bg_name = params.get("bg_name")
        game_id = params.get("game_id")  # Direct game ID parameter

        # Check API key
        if not api_key:
            self._send_json({
                'error': 'API key required for wishlist operations',
                'instructions': 'Get an API key by registering at /register'
            }, status=401)
            return

        if not verify_api_key(api_key):
            self._send_json({'error': 'Invalid API key'}, status=401)
            return

        # Need either query, game_id, or identifiers to determine the game
        if not any([query, game_id, bgg_id, bg_name]):
            self._send_json({
                'error': 'Missing required parameter: query, game_id, bgg_id, or bg_name'
            }, status=400)
            return

        try:
            # Get game ID if not directly provided
            if game_id:
                final_game_id = game_id
            else:
                final_game_id = self._get_game_id(bgg_id, bg_name, query)

            # Get user's BGG credentials
            bgg_credentials = get_user_bgg_credentials(api_key)
            if not bgg_credentials:
                self._send_json({'error': 'Failed to retrieve user credentials'}, status=500)
                return

            username, password = bgg_credentials

            # Add to user's wishlist
            from game_scanner.add_wishlist import add_wishlist
            result = add_wishlist(final_game_id, username, password)
            print(f"Wishlist addition result: {result}")

            # Save the mapping if we looked up a game
            if query and not game_id:
                save_bgg_id(query, final_game_id, extra={"auto": not ((bgg_id or bg_name) and query)})

            self._send_json({
                'success': True,
                'message': 'Game added to wishlist successfully',
                'game_id': final_game_id,
                'bgg_username': username,
                'url': f"https://www.boardgamegeek.com/boardgame/{final_game_id}"
            })

        except Exception as e:
            print(f"Error in wishlist addition: {e}")

            # Capture exception in Sentry with context but send generic error to client
            if HAS_MODULES and sentry_sdk:
                sentry_sdk.set_context("wishlist_error", {
                    "query": query,
                    "game_id": game_id,
                    "has_api_key": bool(api_key),
                    "error_type": type(e).__name__
                })
                sentry_sdk.capture_exception(e)

            self._send_json({'error': 'Wishlist addition failed - please try again'}, status=500)

    def _handle_owned_addition(self, params):
        """Handle adding games to user's owned collection (premium feature requiring API key)."""
        api_key = params.get("api_key")
        query = params.get("query")
        bgg_id = params.get("bgg_id")
        bg_name = params.get("bg_name")
        game_id = params.get("game_id")  # Direct game ID parameter

        # Check API key
        if not api_key:
            self._send_json({
                'error': 'API key required for collection operations',
                'instructions': 'Get an API key by registering at /register'
            }, status=401)
            return

        if not verify_api_key(api_key):
            self._send_json({'error': 'Invalid API key'}, status=401)
            return

        # Need either query, game_id, or identifiers to determine the game
        if not any([query, game_id, bgg_id, bg_name]):
            self._send_json({
                'error': 'Missing required parameter: query, game_id, bgg_id, or bg_name'
            }, status=400)
            return

        try:
            # Get game ID if not directly provided
            if game_id:
                final_game_id = game_id
            else:
                final_game_id = self._get_game_id(bgg_id, bg_name, query)

            # Get user's BGG credentials
            bgg_credentials = get_user_bgg_credentials(api_key)
            if not bgg_credentials:
                self._send_json({'error': 'Failed to retrieve user credentials'}, status=500)
                return

            username, password = bgg_credentials

            # Add to user's owned collection
            from game_scanner.add_wishlist import add_owned
            result = add_owned(final_game_id, username, password)
            print(f"Owned collection addition result: {result}")

            # Save the mapping if we looked up a game
            if query and not game_id:
                save_bgg_id(query, final_game_id, extra={"auto": not ((bgg_id or bg_name) and query)})

            self._send_json({
                'success': True,
                'message': 'Game added to owned collection successfully',
                'game_id': final_game_id,
                'bgg_username': username,
                'url': f"https://www.boardgamegeek.com/boardgame/{final_game_id}"
            })

        except Exception as e:
            print(f"Error in owned collection addition: {e}")

            # Capture exception in Sentry with context but send generic error to client
            if HAS_MODULES and sentry_sdk:
                sentry_sdk.set_context("collection_error", {
                    "query": query,
                    "game_id": game_id,
                    "has_api_key": bool(api_key),
                    "error_type": type(e).__name__
                })
                sentry_sdk.capture_exception(e)

            self._send_json({'error': 'Collection addition failed - please try again'}, status=500)

    def _handle_legacy_request(self, params):
        """Handle legacy requests for backward compatibility."""
        query = params.get("query")
        play = "play" in params
        is_redirect = "redirect" in params
        bgg_id = params.get("bgg_id")
        bg_name = params.get("bg_name")
        
        # If no query provided, return HTML form
        if not query:
            self._send_html_form()
            return

        try:
            game_id = self._get_game_id(bgg_id, bg_name, query)
        except Exception as e:
            print(f"Error getting game ID: {e}")
            self._send_json({'error': f'Failed to get game ID: {str(e)}'})
            return
        
        # Save the mapping
        try:
            save_bgg_id(query, game_id, extra={"auto": not ((bgg_id or bg_name) and query)})
        except Exception as e:
            print(f"Error saving BGG ID: {e}")
        
        url = f"https://www.boardgamegeek.com/boardgame/{game_id}"
        print(f"Game URL: {url}")
        
        # Handle play registration (legacy - uses service account)
        if play:
            print("Registering play (legacy mode)")
            try:
                r = register_play(game_id)  # Uses service account credentials
                print(f"Play registration result: {r}")
                message, play_url = process_register_response(r)
                bot = telebot.TeleBot(os.environ.get("TELEGRAM_TOKEN", ""), parse_mode="Markdown")
                bot.send_message(
                    chat_id=os.getenv("TELEGRAM_CHAT_ID", -4108154376), text=message
                )
            except Exception as e:
                print(f"Error registering play: {e}")
        
        # Handle redirect
        if is_redirect:
            print("Redirecting to BGG")
            self._send_redirect(url)
            return
        
        # Return JSON response
        self._send_json({'game_id': game_id, 'url': url})

    def _get_game_id(self, bgg_id, bg_name, query):
        if bgg_id:
            return bgg_id
        if bg_name:
            return barcode2bgg(bg_name)
        saved_bgg_id = retrieve_document(query)
        if saved_bgg_id:
            return saved_bgg_id
        return barcode2bgg(query)
    
    def _send_html_form(self):
        try:
            # Read the HTML file from the same directory
            html_file_path = os.path.join(os.path.dirname(__file__), 'index.html')
            with open(html_file_path, 'r', encoding='utf-8') as f:
                html_content = f.read()
            self._send_response(html_content, 'text/html')
        except FileNotFoundError:
            # Fallback to simple HTML if file not found
            fallback_html = """
            <h1>Game Scanner API</h1>
            <p>HTML template not found. Please use the API endpoints directly:</p>
            <ul>
                <li>GET /lookup?query=BARCODE</li>
                <li>GET /play?query=BARCODE&api_key=YOUR_KEY</li>
                <li>POST /register</li>
            </ul>
            """
            self._send_response(fallback_html, 'text/html')
    
    def _send_json(self, data, status=200):
        self._send_response(json.dumps(data), 'application/json', status)
    
    def _send_redirect(self, url):
        self.send_response(302)
        self.send_header('Location', url)
        self.end_headers()
    
    def _send_error(self, message, status=500):
        self._send_json({'error': message}, status)
    
    def _send_response(self, content, content_type='text/plain', status=200):
        self.send_response(status)
        self.send_header('Content-Type', content_type)

        # Add trace headers for distributed tracing
        if HAS_MODULES and sentry_sdk:
            # Get current span and add trace headers
            span = sentry_sdk.get_current_span()
            if span:
                trace_header = span.to_traceparent()
                self.send_header('sentry-trace', trace_header)

                # Add trace id to response for client correlation
                trace_id = span.trace_id
                if trace_id:
                    self.send_header('X-Trace-ID', trace_id)

        self.end_headers()
        self.wfile.write(content.encode('utf-8'))