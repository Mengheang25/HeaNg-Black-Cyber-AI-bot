# HeaNg[Black-Cyber] Bot - Complete Setup Guide

## 📋 Table of Contents

1. [Local Development Setup](#local-development-setup)
2. [Getting Required Credentials](#getting-required-credentials)
3. [Running Locally](#running-locally)
4. [Deploying to Render.com](#deploying-to-rendercom)
5. [Troubleshooting](#troubleshooting)

---

## Local Development Setup

### Requirements

- Python 3.9+ ([Download](https://www.python.org/downloads/))
- Git ([Download](https://git-scm.com/))
- A text editor (VS Code, PyCharm, etc.)

### Step 1: Clone Repository

```bash
# Clone the repository
git clone https://github.com/Mengheang25/HeaNg-Black-Cyber-AI-bot.git
cd HeaNg-Black-Cyber-AI-bot

# Or download as ZIP and extract
```

### Step 2: Create Virtual Environment

```bash
# On Windows
python -m venv venv
venv\Scripts\activate

# On macOS/Linux
python3 -m venv venv
source venv/bin/activate
```

### Step 3: Install Dependencies

```bash
pip install -r requirements.txt
```

Output should show:
```
Successfully installed requests-2.32.3 python-dotenv-1.0.1 python-telegram-bot-21.3 ...
```

### Step 4: Create Environment File

```bash
# Copy example to actual .env file
cp .env.example .env

# On Windows PowerShell
Copy-Item .env.example .env
```

---

## Getting Required Credentials

### 1. Telegram Bot Token

1. **Open Telegram** and search for [@BotFather](https://t.me/botfather)
2. **Send `/start`** to begin
3. **Send `/newbot`** to create a new bot
4. **Enter bot name** (e.g., "HeaNg[Black-Cyber] Demo")
5. **Enter bot username** (must end with "bot", e.g., "wormgpt_demo_bot")
6. **Copy the token** that BotFather sends you

Example token format: `7858963821:AAHYj0scgNGGBWbYUUImAZoDOsXEQKLFnlY`

### 2. OpenRouter API Key

1. **Visit [OpenRouter.io](https://openrouter.io)**
2. **Click "Sign in"** (create account if needed)
3. **Go to [Dashboard → Keys](https://openrouter.io/keys)**
4. **Click "Create Key"**
5. **Copy the API key**

Example key format: `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`

---

## Running Locally

### Step 1: Configure Environment

Edit `.env` file with your credentials:

```env
TELEGRAM_TOKEN=your_token_here
OPENROUTER_KEY=your_key_here
MODEL_NAME=deepseek/deepseek-v4-flash
BASE_URL=https://openrouter.ai/api/v1
DATABASE_PATH=date_user.db
ENABLE_HISTORY=true
```

### Step 2: Run Preflight Check

```bash
python preflight_check.py
```

Expected output:
```
==================================================
HeaNg[Black-Cyber] Bot - Pre-flight Check
==================================================
[CHECK] Verifying Python dependencies...
[OK] telegram installed
[OK] requests installed
[OK] dotenv installed

[CHECK] Verifying environment variables...
[OK] Found: TELEGRAM_TOKEN
[OK] Found: OPENROUTER_KEY

[CHECK] Verifying system prompt...
[OK] System prompt found (XXX bytes)

[CHECK] Verifying database configuration...
[INFO] Database will be created on first run: date_user.db

==================================================
PRE-FLIGHT CHECK SUMMARY
==================================================
[OK] Dependencies
[OK] Environment
[OK] System Prompt
[OK] Database

[OK] All checks passed! Bot is ready to start.
```

### Step 3: Start Bot

```bash
python main.py
```

Expected output:
```
[OK] Database initialized successfully

=============================================
-> Bot is now active ->
** Time: 14:30:45
(!) Running on Render.com (!)
=============================================
```

Bot is now running and waiting for Telegram messages!

### Step 4: Test Bot

1. **Open Telegram**
2. **Find your bot** by username
3. **Send `/start`** - you should see the welcome message
4. **Send a message** - bot should respond
5. **Send `/history`** - you should see your conversation

### Step 5: Stop Bot

Press `Ctrl+C` in the terminal to stop the bot.

---

## Deploying to Render.com

See [RENDER_DEPLOYMENT.md](RENDER_DEPLOYMENT.md) for complete deployment guide.

### Quick Deploy Checklist

1. **Push code to GitHub**
   ```bash
   git add .
   git commit -m "HeaNg[Black-Cyber] Bot ready for deployment"
   git push origin main
   ```

2. **Create Render Service**
   - Go to [render.com](https://render.com)
   - Connect GitHub account
   - Create new Web Service
   - Select your repository

3. **Configure Service**
   - Build Command: `pip install -r requirements.txt`
   - Start Command: `python main.py`
   - Add environment variables (TELEGRAM_TOKEN, OPENROUTER_KEY)
   - Add persistent disk at `/var/data`

4. **Deploy**
   - Click "Create Web Service"
   - Wait 2-3 minutes for deployment
   - Check logs to verify bot started

---

## Troubleshooting

### "ModuleNotFoundError: No module named 'telegram'"

**Solution**: Install dependencies
```bash
pip install -r requirements.txt
```

### "UnicodeEncodeError" or special character errors

**Solution**: Already fixed in current version. If you see it:
```bash
# Windows
$env:PYTHONIOENCODING = "utf-8"
python main.py

# Linux/Mac
export PYTHONIOENCODING=utf-8
python main.py
```

### "Missing required environment variables"

**Solution**: Check .env file is configured
```bash
# Verify .env exists
ls -la .env          # Linux/Mac
dir .env             # Windows

# Verify it has content
cat .env             # Linux/Mac
type .env            # Windows
```

### Bot not responding to messages

**Solution**: 
1. Verify bot is running (check terminal)
2. Verify `TELEGRAM_TOKEN` is correct
3. Check Telegram: Find bot by username and send message
4. Review logs for errors

### "sqlite3.OperationalError: database is locked"

**Solution**: 
1. Ensure only one bot instance is running
2. If stuck, delete `date_user.db` and restart (will lose history)
3. Backup database: `cp date_user.db date_user_backup.db`

### "Connection refused" errors

**Solution**:
1. Check internet connection
2. Verify API keys are correct
3. Check OpenRouter API status
4. Try with different model: `MODEL_NAME=gpt-3.5-turbo`

### Database not persisting on Render.com

**Solution**:
1. Verify persistent disk is mounted at `/var/data`
2. Check `DATABASE_PATH=/var/data/date_user.db` in environment
3. Check service logs for database errors
4. Use Render dashboard to inspect disk

---

## File Structure

```
HeaNg-Black-Cyber-AI-bot/
├── main.py                  # Main bot code
├── preflight_check.py       # Pre-deployment checks
├── requirements.txt         # Python dependencies
├── Procfile                 # Render deployment
├── render.yaml              # Render configuration
├── .env                     # Environment variables (created locally)
├── .env.example             # Template for .env
├── .gitignore               # Git ignore rules
├── system_prompt.b          # AI system prompt
├── date_user.db             # SQLite database (created on first run)
├── .github/
│   └── workflows/
│       └── preflight.yml    # GitHub Actions CI/CD
├── README.md                # Project documentation
├── SECURITY.md              # Security guide
├── RENDER_DEPLOYMENT.md     # Detailed deployment guide
├── IMPLEMENTATION.md        # Technical details
└── SETUP.md                 # This file
```

---

## Next Steps

### Local Development
- Explore bot features
- Test with different prompts
- View conversation history
- Monitor database growth

### Prepare for Production
- Push code to GitHub
- Set up Render.com account
- Configure environment variables securely
- Deploy using [RENDER_DEPLOYMENT.md](RENDER_DEPLOYMENT.md)

### Advanced Configuration
- Modify system prompt in `system_prompt.b`
- Change AI model in `.env`
- Add custom commands to `main.py`
- Implement additional features

---

## Support

- **Documentation**: See README.md and other .md files
- **Telegram**: Find bot by username in Telegram
- **Issues**: Check troubleshooting section above
- **Deployment**: See RENDER_DEPLOYMENT.md

## ⏱️ Expected Time

- **Setup**: 10 minutes
- **Getting credentials**: 5 minutes
- **First test**: 2 minutes
- **Render deployment**: 10 minutes

**Total: ~30 minutes from start to production**

---

**Ready to get started?**

1. Clone repository: `git clone ...`
2. Create environment: `python -m venv venv && venv\Scripts\activate`
3. Install packages: `pip install -r requirements.txt`
4. Configure credentials: `cp .env.example .env && edit .env`
5. Run locally: `python main.py`
6. Deploy to Render: Follow RENDER_DEPLOYMENT.md
