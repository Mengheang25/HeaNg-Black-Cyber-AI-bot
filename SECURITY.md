# HeaNg[Black-Cyber] Bot - Security & History Management Improvements

## 🔐 Security Enhancements

### Environment Variables
All sensitive credentials are now loaded from environment variables instead of being hardcoded in the source code:

- **TELEGRAM_TOKEN**: Your Telegram bot token
- **OPENROUTER_KEY**: Your OpenRouter API key
- **MODEL_NAME**: AI model name (default: `deepseek/deepseek-v4-flash`)
- **BASE_URL**: API base URL (default: `https://openrouter.ai/api/v1`)

### Setup Instructions

1. **Install Required Packages**
   ```bash
   pip install -r requirements.txt
   ```

2. **Create `.env` File**
   Copy the provided `.env.example` and fill in your credentials:
   ```bash
   cp .env.example .env
   ```

3. **Edit `.env` File**
   ```env
   TELEGRAM_TOKEN=your_telegram_bot_token_here
   OPENROUTER_KEY=your_openrouter_api_key_here
   MODEL_NAME=deepseek/deepseek-v4-flash
   BASE_URL=https://openrouter.ai/api/v1
   DATABASE_PATH=date_user.db
   ENABLE_HISTORY=true
   ```

4. **Never Commit `.env` File**
   The `.env` file is already in `.gitignore` to prevent accidental credential leaks.

## 💾 Conversation History Management

### SQLite Database
Conversation history is now automatically stored in SQLite database (`date_user.db`):

- **User Information**: Stores user ID, name, and username
- **Message History**: Stores all messages with timestamps
- **Persistent Storage**: Data survives bot restarts

### Database Tables

**users table**
```sql
- user_id (PRIMARY KEY)
- first_name
- username
- created_at (timestamp)
```

**conversations table**
```sql
- id (PRIMARY KEY, AUTO INCREMENT)
- user_id (FOREIGN KEY)
- message_type ('user' or 'ai')
- content (message text)
- timestamp (when message was created)
```

## 📋 New Commands

### `/history` Command
View your conversation history with the bot. Shows the last 20 messages with timestamps.

**Usage:**
```
/history
```

**Features:**
- Shows last 20 messages by default
- Displays timestamp for each message
- Indicates whether message is from user or AI
- Automatically splits long histories into multiple messages

## 🔧 Configuration Options

| Variable | Default | Description |
|----------|---------|-------------|
| TELEGRAM_TOKEN | Required | Your Telegram bot API token |
| OPENROUTER_KEY | Required | Your OpenRouter API key |
| MODEL_NAME | deepseek/deepseek-v4-flash | AI model to use |
| BASE_URL | https://openrouter.ai/api/v1 | API endpoint |
| DATABASE_PATH | date_user.db | SQLite database file path |
| ENABLE_HISTORY | true | Enable/disable conversation history |

## ✅ Security Best Practices

1. ✅ Never hardcode credentials in code
2. ✅ Use environment variables for secrets
3. ✅ Keep `.env` file private (added to `.gitignore`)
4. ✅ Use `.env.example` as template for new installations
5. ✅ Rotate API keys regularly
6. ✅ Don't share `.env` file or bot token publicly

## 🚀 Running the Bot

```bash
python main.py
```

The bot will:
- Load credentials from `.env`
- Initialize SQLite database
- Start polling for Telegram messages
- Store all conversations automatically

## 📊 Database Backup

To backup your conversation history:
```bash
cp date_user.db date_user_backup.db
```

## 🔍 View Database

To view stored conversations, you can use any SQLite browser or Python:
```python
import sqlite3

conn = sqlite3.connect('date_user.db')
cursor = conn.cursor()
cursor.execute('SELECT * FROM conversations LIMIT 10')
for row in cursor.fetchall():
    print(row)
conn.close()
```

## 📝 Features

- 🤖 AI-Powered Coding Assistance using OpenRouter
- 💬 Persistent Conversation History
- 🔐 Secure Environment Variable Configuration
- 📱 Full Telegram Bot Integration
- 🎨 Beautiful Formatting with Unicode Characters
- 📊 SQLite Database Storage
- 🔍 History Retrieval with `/history` Command

---

**Version**: 2.0 (Security & History Enhanced)
**Last Updated**: 2026-05-23
