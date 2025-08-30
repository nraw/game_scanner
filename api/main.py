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
            
            print(f"Method: {self.command}, Params: {query_params}")
            
            # Check if modules loaded successfully
            if not HAS_MODULES:
                self._send_error(f"Import error: {IMPORT_ERROR}")
                return
            
            query = query_params.get("query")
            play = "play" in query_params
            is_redirect = "redirect" in query_params
            bgg_id = query_params.get("bgg_id")
            bg_name = query_params.get("bg_name")
            
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
            
            # Handle play registration
            if play:
                print("Registering play")
                try:
                    r = register_play(game_id)
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
                
        except Exception as e:
            print(f"Handler error: {e}")
            import traceback
            traceback.print_exc()
            self._send_json({'error': str(e), 'type': type(e).__name__}, status=500)

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
<head><title>Game Scanner</title></head>
<body>
    <h1>Barcode to BGG Mapper</h1>
    <form method="post">
        <label>Barcode/Query: <input type="text" name="query" required></label><br><br>
        <label>BGG ID (optional): <input type="text" name="bgg_id"></label><br><br>
        <label>Game Name (optional): <input type="text" name="bg_name"></label><br><br>
        <input type="checkbox" name="play"> Register Play<br><br>
        <input type="checkbox" name="redirect"> Redirect to BGG<br><br>
        <input type="submit" value="Submit">
    </form>
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