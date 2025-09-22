# Game Scanner

A multi-user API service for scanning board game barcodes and registering plays to BoardGameGeek (BGG). Convert any barcode to a BGG game ID and register plays directly to your BGG account.

## 🌐 Live Service

**Production URL:** https://gamescanner.vercel.app/

## 🎯 Features

### 🆓 Free Features
- **Barcode Lookup** - Convert any barcode to BGG game ID
- **Game Name Search** - Find games by name instead of barcode
- **Web Interface** - Simple HTML form for quick lookups
- **Redirect to BGG** - Direct links to game pages

### 🔐 Premium Features (API Key Required)
- **Play Registration** - Log plays directly to your BGG account
- **Personal Credentials** - Uses your BGG username/password
- **Secure Storage** - Encrypted credential storage

## 🚀 Quick Start

### 1. Free Lookup (No Registration)
```bash
curl "https://gamescanner.vercel.app/lookup?query=nemesis"
# Returns: {"game_id": "167355", "url": "https://www.boardgamegeek.com/boardgame/167355"}
```

### 2. Get API Key
```bash
curl -X POST "https://gamescanner.vercel.app/register" \
  -d "bgg_username=YOUR_BGG_USERNAME&bgg_password=YOUR_BGG_PASSWORD"
# Returns: {"api_key": "abc123...", "message": "User created successfully"}
```

### 3. Register Plays
```bash
curl "https://gamescanner.vercel.app/play?query=nemesis&api_key=YOUR_API_KEY"
# Returns: {"message": "Play registered successfully", "game_id": "167355"}
```

### 4. Add to Wishlist
```bash
curl -X POST "https://gamescanner.vercel.app/wishlist" \
  -d "query=wingspan&api_key=YOUR_API_KEY"
# Returns: {"success": true, "message": "Game added to wishlist successfully", "game_id": "167355"}
```

### 5. Add to Owned Collection
```bash
curl -X POST "https://gamescanner.vercel.app/owned" \
  -d "query=azul&api_key=YOUR_API_KEY"
# Returns: {"success": true, "message": "Game added to owned collection successfully", "game_id": "178900"}
```

## 📡 API Endpoints

| Endpoint | Method | Description | Auth Required |
|----------|--------|-------------|---------------|
| `/` | GET | HTML interface and documentation | ❌ |
| `/lookup` | GET | Convert barcode/name to BGG ID | ❌ |
| `/register` | POST | Create new user account | ❌ |
| `/play` | GET | Register play to your BGG account | ✅ |
| `/wishlist` | POST | Add game to your BGG wishlist | ✅ |
| `/owned` | POST | Add game to your owned collection | ✅ |
| `/users` | GET | List all users (admin) | ❌ |

### Parameters

**Lookup & Play:**
- `query` - Barcode or game name (required)
- `bgg_id` - Override BGG ID (optional)
- `bg_name` - Override game name (optional)
- `redirect` - Redirect to BGG page instead of JSON (optional)
- `api_key` - Your API key (required for `/play`)

**Wishlist & Owned Collection:**
- `query` - Barcode or game name (optional)
- `game_id` - Direct BGG game ID (optional)
- `bgg_id` - Override BGG ID (optional)
- `bg_name` - Override game name (optional)
- `api_key` - Your API key (required)

**Registration:**
- `bgg_username` - Your BGG username (required)
- `bgg_password` - Your BGG password (required)

## 🏗️ Architecture

### Multi-Interface Design
1. **Vercel Serverless API** - Primary REST API at gamescanner.vercel.app
2. **Google Cloud Function** - Legacy web interface (still active)
3. **Telegram Bot** - Chat interface with AI integration
4. **FastAPI Service** - Local development server

### Core Components
- **`game_scanner/barcode2bgg.py`** - Barcode→BGG conversion using Google Search
- **`game_scanner/user_auth.py`** - Multi-user authentication & credential encryption
- **`game_scanner/register_play.py`** - BGG play registration
- **`game_scanner/db.py`** - Firebase Firestore integration
- **`api/main.py`** - Vercel serverless function handler

### Data Flow
1. **Barcode** → Google Search → BGG page extraction → **BGG ID**
2. **User Registration** → Encrypt BGG credentials → Store in Firestore
3. **Play Registration** → Decrypt user credentials → Log to user's BGG account

## 🔧 Development

### Local Development
```bash
# Install dependencies
pip install -r requirements.txt

# FastAPI development server
make prod  # Runs on port 5000

# Test Flask mapper
make test

# Telegram bot
make telegram
```

### Environment Variables
Required in `.env` file or deployment environment:

```bash
# Google Custom Search (for barcode lookup)
GOOGLE_KEY=your_google_search_api_key
GOOGLE_CX=your_google_search_engine_id

# BGG Service Account (fallback/legacy)
BGG_USERNAME=service_account_username
BGG_PASS=service_account_password

# Telegram Bot (optional)
TELEGRAM_TOKEN=your_telegram_bot_token
TELEGRAM_CHAT_ID=your_telegram_chat_id

# Firebase Firestore
FIRESTORE_KEY={"type":"service_account","project_id":"..."}
# OR place nraw-key.json in project root
```

### Deployment

**Vercel (Primary):**
```bash
vercel --prod
```

**Google Cloud Functions (Legacy):**
```bash
make deploy
```

### Testing
```bash
# Run all tests
pytest

# Run specific test
python -m pytest tests/test_barcode2bgg.py::test_barcode2bgg
```

## 🔒 Security & Privacy

- **Encrypted Credentials** - BGG passwords encrypted with Fernet (AES 128)
- **Secure API Keys** - 32-character URL-safe tokens
- **No Email Collection** - Only BGG username required
- **Individual Accounts** - Each user's plays go to their own BGG account
- **Firestore Security** - Credentials stored encrypted in Google Cloud

## 📊 Data Storage

User data is stored in [Firestore](https://console.cloud.google.com/firestore/databases/-default-/data/panel/users?project=nraw-181921):

```json
{
  "bgg_username": "username",
  "api_key": "secure-token",
  "encrypted_credentials": "encrypted-bgg-password", 
  "encryption_key": "per-user-encryption-key",
  "tier": "premium",
  "created_at": "2025-08-30"
}
```

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests for new functionality
5. Submit a pull request

## 📜 License

MIT License - see LICENSE file for details.