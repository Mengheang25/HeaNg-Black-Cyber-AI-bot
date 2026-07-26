# HeaNg[Black-Cyber] Bot - Render.com Deployment Guide

## 🚀 Deploy to Render.com

This guide provides step-by-step instructions to deploy your HeaNg[Black-Cyber] bot on Render.com.

### Prerequisites

1. **GitHub Account**: Push code to GitHub (Render deploys from GitHub)
2. **Render.com Account**: [Sign up at render.com](https://render.com)
3. **Telegram Bot Token**: From [@BotFather](https://t.me/botfather)
4. **OpenRouter API Key**: From [OpenRouter](https://openrouter.ai)

## Step 1: Push Code to GitHub

```bash
# Initialize git repository
git init

# Add all files
git add .

# Commit changes
git commit -m "HeaNg-Black-Cyber-AI-bot - Render.com deployment ready"

# Add remote repository
git remote add origin https://github.com/Mengheang25/HeaNg-Black-Cyber-AI-bot.git

# Push to GitHub
git push -u origin main
```

## Step 2: Create Render.com Service

1. **Go to [Render Dashboard](https://dashboard.render.com)**
2. **Click "New +"** → Select **"Web Service"**
3. **Connect GitHub Repository**
   - Click "Connect account" if not already connected
   - Select your **wormgpt-demo** repository
   - Click "Connect"

## Step 3: Configure Web Service

### Basic Settings
- **Name**: `wormgpt-bot`
- **Environment**: `Python 3.11`
- **Build Command**: `pip install -r requirements.txt`
- **Start Command**: `python main.py`
- **Plan**: Free or Paid (based on your preference)

### Environment Variables

Add these environment variables in Render dashboard:

```env
TELEGRAM_TOKEN=your_telegram_bot_token_here
OPENROUTER_KEY=your_openrouter_api_key_here
MODEL_NAME=deepseek/deepseek-v4-flash
BASE_URL=https://openrouter.ai/api/v1
DATABASE_PATH=/var/data/date_user.db
ENABLE_HISTORY=true
PYTHONUNBUFFERED=1
```

### Disk Configuration

For database persistence, add a persistent disk:

1. **Click "Add Disk"** in the Render dashboard
2. **Mount Path**: `/var/data`
3. **Size**: 1 GB (sufficient for conversation history)

### Settings to Verify

- **Auto-Deploy**: Enabled (auto-redeploy on git push)
- **Health Check Path**: Leave empty (Telegram bot doesn't need HTTP health check)
- **Instance Count**: 1

## Step 4: Deploy

1. **Click "Create Web Service"**
2. **Wait for deployment** (typically 2-3 minutes)
3. **Check logs** to verify bot started successfully

Expected log output:
```
[OK] Database initialized successfully

==========================================
-> Bot is now active ->
** Time: HH:MM:SS
(!) Running on Render.com (!)
==========================================
```

## Step 5: Verify Bot is Working

1. **Open Telegram** and find your bot
2. **Send `/start`** to the bot
3. **Bot should respond** with welcome message
4. **Send a test message** and verify AI response
5. **Use `/history`** to check conversation storage

## 📊 Understanding Render.com Deployment

### Procfile
Tells Render.com how to start your application:
```
web: python main.py
```

### Persistent Storage
- Database file `/var/data/date_user.db` is preserved across restarts
- Free tier services restart after 15 minutes of inactivity
- With persistent disk, your conversation history survives

### Environment Variables
- Securely stored in Render dashboard
- Never exposed in logs or code
- Can be updated without redeploying

### Auto-Deployment
- Push changes to GitHub
- Render automatically detects changes
- Redeploys application with new code
- No manual intervention needed

## 🔄 Managing Your Deployment

### View Logs
```
Render Dashboard → Your Service → Logs
```

### Update Code
```bash
git add .
git commit -m "Update bot features"
git push origin main
# Render automatically redeploys
```

### Update Environment Variables
1. Go to Render Dashboard
2. Select your service
3. Go to "Environment"
4. Update variables
5. Click "Save"
6. Service automatically restarts

### Restart Service
```
Render Dashboard → Your Service → Manual Restart
```

### Monitor Resource Usage
```
Render Dashboard → Your Service → Metrics
```

## ⚠️ Important Considerations

### Free Tier Limitations
- Service spins down after 15 minutes of inactivity
- Cold starts may take 30-60 seconds
- Limited CPU/RAM (sufficient for bot)
- 1 GB persistent disk included

### Upgrade to Paid Plan
For continuous uptime without spin-down:
- Paid tier starts at $7/month
- Supports multiple processes
- Better resource allocation
- Production-ready reliability

### Database Limits
- Free tier: 1 GB persistent disk
- Estimated capacity: ~100,000 messages
- Monitor usage in Render dashboard

### Telegram Webhook vs Long Polling
Current setup uses **long polling** (simpler, no webhook needed):
- Works on free tier
- No IP whitelisting needed
- Slightly higher latency
- Perfectly fine for personal bot

## 🐛 Troubleshooting

### Bot Not Responding
1. Check Telegram token in environment variables
2. Verify bot is running: check Logs
3. Restart service manually
4. Check Render Dashboard status

### Database Not Persisting
1. Verify persistent disk is mounted at `/var/data`
2. Check `DATABASE_PATH` is set to `/var/data/date_user.db`
3. Review logs for database errors

### API Errors
1. Verify `OPENROUTER_KEY` is correct
2. Check API rate limits
3. Review error logs for specific issues

### Memory/CPU Issues
1. Monitor service metrics
2. Optimize code if needed
3. Upgrade to paid plan for better resources

## 📝 Deployment Checklist

- [ ] Code pushed to GitHub
- [ ] Render.com account created
- [ ] GitHub repository connected to Render
- [ ] Web service created
- [ ] Environment variables configured
- [ ] Persistent disk added (for database)
- [ ] Service deployed successfully
- [ ] Bot responds to `/start` command
- [ ] `/history` command works
- [ ] Database persisting across restarts
- [ ] Auto-deployment verified (test git push)

## 🔐 Security Notes

1. **Never commit .env file** ✅ (.gitignore prevents this)
2. **Use Render environment variables** ✅ (not in code)
3. **Rotate API keys regularly** ⚠️ (manual process)
4. **Monitor logs for errors** ⚠️ (user responsibility)
5. **Keep dependencies updated** ⚠️ (update requirements.txt)

## 📞 Support

- **Render Docs**: [docs.render.com](https://docs.render.com)
- **Telegram Bot API**: [core.telegram.org/bots/api](https://core.telegram.org/bots/api)
- **OpenRouter**: [openrouter.ai/docs](https://openrouter.ai/docs)

## 🎉 Next Steps

1. Deploy bot on Render.com using this guide
2. Monitor logs and metrics
3. Test all features (start, history, messages)
4. Share bot with users
5. Monitor usage and upgrade if needed

---

**Estimated Deployment Time**: 5-10 minutes
**Estimated Monthly Cost**: Free (with limitations) or $7+ (with guarantees)
**Maintenance**: Minimal (automatic redeploys)
