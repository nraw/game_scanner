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

    from game_scanner.barcode2bgg import barcode2bgg
    from game_scanner.commands import process_register_response
    from game_scanner.db import retrieve_document
    from game_scanner.register_play import register_play
    from game_scanner.save_bgg_id import save_bgg_id
    from game_scanner.user_auth import (
        create_user, 
        get_user_by_api_key, 
        get_user_bgg_credentials,
        verify_api_key,
        list_all_users
    )
    HAS_MODULES = True
except ImportError as e:
    HAS_MODULES = False
    IMPORT_ERROR = str(e)

class handler(BaseHTTPRequestHandler):
    def do_GET(self):
        self._handle_request()
    
    def do_POST(self):
        self._handle_request()
    
    def _handle_request(self):
        try:
            # Parse URL and query parameters
            parsed_url = urlparse(self.path)
            endpoint = parsed_url.path
            query_params = parse_qs(parsed_url.query)
            
            # Flatten query parameters (parse_qs returns lists)
            query_params = {k: v[0] if v else '' for k, v in query_params.items()}
            
            # Handle POST form data
            if self.command == 'POST':
                content_length = int(self.headers.get('Content-Length', 0))
                if content_length > 0:
                    post_data = self.rfile.read(content_length).decode('utf-8')
                    form_data = parse_qs(post_data)
                    # Merge form data with query params
                    for k, v in form_data.items():
                        query_params[k] = v[0] if v else ''
            
            print(f"Method: {self.command}, Endpoint: {endpoint}, Params: {query_params}")
            
            # Check if modules loaded successfully
            if not HAS_MODULES:
                self._send_error(f"Import error: {IMPORT_ERROR}")
                return
            
            # Route to different endpoints
            if endpoint == "/register":
                self._handle_user_registration(query_params)
            elif endpoint == "/users":
                self._handle_list_users(query_params)
            elif endpoint.startswith("/lookup"):
                self._handle_lookup(query_params)
            elif endpoint.startswith("/play"):
                self._handle_play_registration(query_params)
            else:
                # Default: backward compatibility with existing interface
                self._handle_legacy_request(query_params)
                
        except Exception as e:
            print(f"Handler error: {e}")
            import traceback
            traceback.print_exc()
            self._send_json({'error': str(e), 'type': type(e).__name__}, status=500)

    def _handle_user_registration(self, params):
        """Handle new user registration."""
        bgg_username = params.get("bgg_username")
        bgg_password = params.get("bgg_password")
        
        if not all([bgg_username, bgg_password]):
            self._send_json({
                'error': 'Missing required parameters: bgg_username, bgg_password'
            }, status=400)
            return
            
        try:
            api_key = create_user(bgg_username, bgg_password)
            self._send_json({
                'message': 'User created successfully',
                'api_key': api_key,
                'bgg_username': bgg_username,
                'instructions': 'Save this API key! Use it in all future requests as ?api_key=YOUR_KEY'
            })
        except ValueError as e:
            self._send_json({'error': str(e)}, status=400)
        except Exception as e:
            self._send_json({'error': f'Registration failed: {str(e)}'}, status=500)
    
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
            self._send_json({'error': f'Lookup failed: {str(e)}'}, status=500)
    
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
            self._send_json({'error': f'Play registration failed: {str(e)}'}, status=500)
    
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
        html_form = """
<!DOCTYPE html>
<html>
<head><title>Game Scanner API</title></head>
<body>
    <h1>Game Scanner API</h1>
    
    <h2>Quick Lookup (Free)</h2>
    <form method="post">
        <label>Barcode/Query: <input type="text" name="query" required></label><br><br>
        <label>BGG ID (optional): <input type="text" name="bgg_id"></label><br><br>
        <label>Game Name (optional): <input type="text" name="bg_name"></label><br><br>
        <input type="checkbox" name="redirect"> Redirect to BGG<br><br>
        <input type="submit" value="Look Up Game">
    </form>
    
    <hr>
    
    <h2>API Endpoints</h2>
    <ul>
        <li><strong>GET /lookup?query=BARCODE</strong> - Look up game by barcode (free)</li>
        <li><strong>GET /play?query=BARCODE&api_key=YOUR_KEY</strong> - Register play (requires API key)</li>
        <li><strong>POST /register</strong> - Register new user account</li>
    </ul>
    
    <h2>Register for API Access</h2>
    <form method="post" action="/register">
        <label>BGG Username: <input type="text" name="bgg_username" required></label><br><br>
        <label>BGG Password: <input type="password" name="bgg_password" required></label><br><br>
        <input type="submit" value="Register">
    </form>
    
    <h2>Examples</h2>
    <p><strong>Free lookup:</strong><br>
    <code>curl "https://gamescanner.vercel.app/lookup?query=nemesis"</code></p>
    
    <p><strong>Register play:</strong><br>
    <code>curl "https://gamescanner.vercel.app/play?query=nemesis&api_key=YOUR_API_KEY"</code></p>
</body>
</html>
        """
        self._send_response(html_form, 'text/html')
    
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
        self.end_headers()
        self.wfile.write(content.encode('utf-8'))