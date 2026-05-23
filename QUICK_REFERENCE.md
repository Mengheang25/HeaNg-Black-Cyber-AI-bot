# HeaNg[Black-Cyber] Bot - Quick Reference

## 🔐 Security Setup

### Step 1: Create .env File
```bash
cp .env.example .env
```

### Step 2: Edit .env with Your Credentials
```env
TELEGRAM_TOKEN=your_telegram_bot_token
OPENROUTER_KEY=your_openrouter_api_key
MODEL_NAME=deepseek/deepseek-v4-flash
BASE_URL=https://openrouter.ai/api/v1
DATABASE_PATH=date_user.db
ENABLE_HISTORY=true
```

### Step 3: Install Dependencies
```bash
pip install -r requirements.txt
```

### Step 4: Run Bot
```bash
python main.py
```

## 📱 Bot Commands

| Command | Description | Example |
|---------|-------------|---------|
| `/start` | Initialize bot and get welcome message | `/start` |
| `/history` | View last 20 conversation messages | `/history` |

## 📊 Database Files

- **date_user.db** - SQLite database with conversations
- **Backup**: `cp date_user.db date_user_backup.db`

## 🔑 Environment Variables

| Variable | Required | Default |
|----------|----------|---------|
| TELEGRAM_TOKEN | ✅ Yes | - |
| OPENROUTER_KEY | ✅ Yes | - |
| MODEL_NAME | ❌ No | deepseek/deepseek-v4-flash |
| BASE_URL | ❌ No | https://openrouter.ai/api/v1 |
| DATABASE_PATH | ❌ No | date_user.db |
| ENABLE_HISTORY | ❌ No | true |

## 🗄️ Database Tables

### users
- user_id (PRIMARY KEY)
- first_name
- username
- created_at

### conversations
- id (PRIMARY KEY, AUTO INCREMENT)
- user_id (FOREIGN KEY)
- message_type ('user' or 'ai')
- content
- timestamp

## 🚀 Features

✅ **Security**
- Environment variable configuration
- .env file encryption recommended
- .gitignore prevents credential leaks

✅ **History**
- Persistent SQLite database
- User information tracking
- Timestamped conversations
- `/history` command retrieval

✅ **AI Integration**
- OpenRouter API support
- Multiple model support
- Code snippet formatting
- HTML Telegram integration

## 📝 File Structure

```
wormgpt-demo/
├── main.py                 # Main bot code
├── requirements.txt        # Python dependencies
├── system-prompt.txt       # AI system prompt
├── wormgpt_config.json     # Configuration (legacy)
├── .env                    # Configuration (secret - git ignored)
├── .env.example            # Configuration template
├── .gitignore              # Git ignore rules
├── setup.sh                # Linux/Mac setup script
├── setup.bat               # Windows setup script
├── SECURITY.md             # Security documentation
├── IMPLEMENTATION.md       # Implementation details
└── QUICK_REFERENCE.md      # This file
```

## ⚠️ Important Notes

1. **Never commit .env** - It's in .gitignore
2. **Keep tokens secret** - Don't share TELEGRAM_TOKEN or OPENROUTER_KEY
3. **Backup database** - Regularly backup date_user.db
4. **Rotate credentials** - Change keys periodically
5. **Monitor history** - Check database for data privacy

## 🔧 Common Commands

### Check Python Version
```bash
python --version
```

### Create Virtual Environment
```bash
python -m venv venv
source venv/bin/activate  # Linux/Mac
# or
venv\Scripts\activate  # Windows
```

### List Installed Packages
```bash
pip list
```

### Update Dependencies
```bash
pip install -r requirements.txt --upgrade
```

## 🐛 Quick Troubleshooting

| Issue | Solution |
|-------|----------|
| Missing .env | Copy .env.example to .env |
| API key error | Check OPENROUTER_KEY in .env |
| Bot doesn't start | Check TELEGRAM_TOKEN in .env |
| History not saving | Check ENABLE_HISTORY=true in .env |
| Database locked | Ensure only one bot instance |

## 📞 Support Resources

- **SECURITY.md** - Complete security setup guide
- **IMPLEMENTATION.md** - Detailed implementation reference
- **main.py comments** - Inline code documentation

## ✨ Key Improvements

### v2.0 (Current)
- ✅ Environment variable configuration
- ✅ SQLite conversation storage
- ✅ /history command
- ✅ Automatic message persistence
- ✅ User registration

### v1.0 (Original)
- Memory-based messaging
- Hardcoded credentials
- No history retention

---

**Get started in 4 steps:**
1. `cp .env.example .env` - Create config
2. Edit `.env` - Add your tokens
3. `pip install -r requirements.txt` - Install deps
4. `python main.py` - Run bot!

**For detailed guides, see SECURITY.md or IMPLEMENTATION.md**
