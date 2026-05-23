# HeaNg[Black-Cyber] Bot - Implementation Guide

## 📋 Overview

This guide documents the security and conversation history improvements made to the HeaNg[Black-Cyber] Telegram Bot.

## 🔐 Security Improvements

### Problem: Exposed Credentials
**Before**: Credentials were hardcoded in `main.py`
```python
TELEGRAM_TOKEN = "7858963821:AAHYj0scgNGGBWbYUUImAZoDOsXEQKLFnlY"
OPENROUTER_KEY = "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"
```

**Risk**: Source code commits expose sensitive credentials

### Solution: Environment Variables
**After**: Credentials loaded from `.env` file
```python
import os
from dotenv import load_dotenv

load_dotenv()
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
OPENROUTER_KEY = os.getenv("OPENROUTER_KEY")
```

**Benefits**:
- ✅ Credentials never committed to repository
- ✅ Different configs per environment
- ✅ Easy credential rotation
- ✅ Industry standard approach

## 💾 Conversation History System

### Problem: Lost Messages
**Before**: User messages only stored in memory
```python
user_last_messages = {}  # Lost on bot restart
```

**Issues**:
- ❌ Conversations lost on bot restart
- ❌ No historical data for users
- ❌ Can't retrieve past discussions

### Solution: SQLite Database
**After**: Persistent database storage
```python
class ConversationDB:
    def init_db(self):
        """Initialize SQLite database"""
    
    def save_message(self, user_id, message_type, content):
        """Store message in database"""
    
    def get_user_history(self, user_id, limit=20):
        """Retrieve conversation history"""
```

**Benefits**:
- ✅ Persistent storage
- ✅ User history available anytime
- ✅ Timestamps for all messages
- ✅ Easy data export

## 📊 Database Schema

### Users Table
Stores information about bot users:
```sql
CREATE TABLE users (
    user_id INTEGER PRIMARY KEY,
    first_name TEXT,
    username TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
)
```

### Conversations Table
Stores all messages:
```sql
CREATE TABLE conversations (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    message_type TEXT,          -- 'user' or 'ai'
    content TEXT,               -- Message content
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(user_id)
)
```

## 🎯 New Features

### /history Command
View your conversation history with timestamps.

**Implementation**:
```python
async def show_history(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /history command to show conversation history"""
    user_id = update.message.from_user.id
    history = db.get_user_history(user_id, limit=20)
    # Format and send history to user
```

**Usage**:
```
User: /history
Bot: Shows last 20 messages with timestamps
```

### Automatic Message Saving
All messages are automatically saved to database:

```python
# In handle_message()
db.save_message(uid, "user", text)      # Save user message
reply = ask_model(text)
db.save_message(uid, "ai", reply)       # Save AI response
```

### User Registration
User info stored on first interaction:

```python
# In start command
db.add_user(user_id, user_name, username)
```

## 🔧 Configuration

### Environment Variables
Create `.env` file with:
```env
TELEGRAM_TOKEN=your_bot_token
OPENROUTER_KEY=your_api_key
MODEL_NAME=deepseek/deepseek-v4-flash
BASE_URL=https://openrouter.ai/api/v1
DATABASE_PATH=date_user.db
ENABLE_HISTORY=true
```

### .env.example
Template file for new installations - copy and modify:
```bash
cp .env.example .env
# Edit .env with your credentials
```

### .gitignore
Prevents accidental commits of sensitive files:
- `.env` - Never commit secrets
- `*.db` - Never commit user data
- `__pycache__/` - Python cache
- `venv/` - Virtual environment

## 🚀 Installation

### 1. Install Dependencies
```bash
pip install -r requirements.txt
```

Or use the setup script:
```bash
# Windows
setup.bat

# Linux/Mac
bash setup.sh
```

### 2. Configure Environment
```bash
cp .env.example .env
# Edit .env with your credentials
```

### 3. Run Bot
```bash
python main.py
```

## 📝 Code Changes Summary

### main.py Changes

**Added Imports**:
```python
import os
import sqlite3
from datetime import datetime
from pathlib import Path
from dotenv import load_dotenv
```

**Added Configuration**:
```python
load_dotenv()
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
OPENROUTER_KEY = os.getenv("OPENROUTER_KEY")
# ... more config from environment
```

**Added Database Class**:
```python
class ConversationDB:
    def __init__(self, db_path=DATABASE_PATH):
        self.db_path = db_path
        self.init_db()
    # ... implementation
```

**Updated start() Function**:
```python
db.add_user(user_id, user_name, username)
```

**Added show_history() Function**:
```python
async def show_history(update, context):
    history = db.get_user_history(user_id, limit=20)
    # ... format and send
```

**Updated handle_message() Function**:
```python
db.save_message(uid, "user", text)      # Save user message
reply = ask_model(text)
db.save_message(uid, "ai", reply)       # Save AI response
```

**Updated callback() Function**:
```python
db.save_message(uid, "ai", reply)       # Save AI response
```

**Updated App Configuration**:
```python
app.add_handler(CommandHandler("history", show_history))
```

### requirements.txt Changes
```
python-dotenv==1.0.1  # NEW
```

## 🔍 Usage Examples

### View Conversation History
```
User: /history
Bot: Shows last 20 messages with timestamps and user/AI indicators
```

### Automatic Saving
```
User: How do I use Python?
Bot: [Saves user message + AI response to database]
     Here's how to use Python...
```

### Message Format in Database
```
user_id: 12345
message_type: 'user'
content: 'How do I use Python?'
timestamp: '2026-05-23 14:30:45'
```

## 🛡️ Security Best Practices

1. **Never commit .env**:
   - .gitignore protects against accidental commits
   - If accidentally committed, rotate all credentials immediately

2. **Use strong API keys**:
   - Generated by services like OpenRouter
   - Rotate periodically

3. **Protect database file**:
   - Contains user conversations
   - Don't share or backup insecurely

4. **Environment-specific configs**:
   - Development .env
   - Production .env (different credentials)

5. **Audit database**:
   - Regularly check who has access
   - Monitor for unauthorized access

## 📊 Database Backup

### Manual Backup
```bash
cp date_user.db date_user_backup_$(date +%Y%m%d).db
```

### View Database Contents
```python
import sqlite3

conn = sqlite3.connect('date_user.db')
cursor = conn.cursor()

# View all conversations
cursor.execute('SELECT * FROM conversations')
for row in cursor.fetchall():
    print(row)

conn.close()
```

### Export Conversations
```python
import sqlite3
import json

conn = sqlite3.connect('date_user.db')
cursor = conn.cursor()

cursor.execute('SELECT * FROM conversations')
conversations = cursor.fetchall()

with open('export.json', 'w') as f:
    json.dump(conversations, f, indent=2)

conn.close()
```

## 🐛 Troubleshooting

### Missing .env file
```
Error: Missing required environment variables
Solution: Copy .env.example to .env and fill in credentials
```

### Database locked
```
Error: database is locked
Solution: Ensure only one instance of bot is running
```

### API Key not working
```
Error: API Error
Solution: Check OPENROUTER_KEY in .env file
```

### History not saving
```
Check: ENABLE_HISTORY=true in .env
Check: Proper database permissions
Check: date_user.db file exists and is writable
```

## ✅ Testing Checklist

- [ ] .env file created and configured
- [ ] Dependencies installed (`pip install -r requirements.txt`)
- [ ] Bot starts without errors
- [ ] /start command works
- [ ] Messages are saved to database
- [ ] /history command shows messages
- [ ] Bot restarts preserve history
- [ ] .env file not in git

## 📚 References

- [python-dotenv Documentation](https://python-dotenv.readthedocs.io/)
- [SQLite Documentation](https://www.sqlite.org/docs.html)
- [Telegram Bot API](https://core.telegram.org/bots/api)
- [OpenRouter API](https://openrouter.ai/docs)

## 🤝 Support

For issues or questions:
1. Check SECURITY.md for setup instructions
2. Review this guide for troubleshooting
3. Check bot logs for error messages
4. Verify .env file configuration

---

**Version**: 2.0
**Last Updated**: 2026-05-23
**Status**: ✅ Complete
