# 🔐 Admin Guide - Musifyyy Bot

This guide explains how to use the admin features of the bot.

## 📋 Admin Commands

### `/broadcast` - Send Message to All Users
Send a message to all bot subscribers at once.

**Usage:**
```
/broadcast Your message here
```

**Examples:**
```
/broadcast 🎉 New features available! Try searching now!

/broadcast ⚠️ The bot will be under maintenance for 30 minutes.

/broadcast 🎵 We now support 30 search results with pagination!
```

**Features:**
- ✅ Sends to all active users
- ✅ Automatically removes blocked users
- ✅ Shows delivery statistics
- ✅ Supports Markdown formatting

**Response:**
```
✅ Broadcast Complete

📊 Results:
• Sent successfully: 1,234
• Blocked/Deactivated: 5
• Failed: 2
• Total attempted: 1,241
```

---

### `/users` - View User Statistics
See how many users are subscribed to your bot.

**Usage:**
```
/users
```

**Response:**
```
👥 User Statistics

Total subscribers: 1,234

Use /broadcast message to send a message to all users.
```

---

## 🔧 Setup Admin Access

### Method 1: Environment Variable (Recommended for Production)

1. **Get your Telegram User ID:**
   - Message [@userinfobot](https://t.me/userinfobot) on Telegram
   - Copy your user ID (e.g., `123456789`)

2. **Set environment variable:**

**Locally (PowerShell):**
```powershell
$env:ADMIN_USER_ID="123456789"
```

**On Render:**
- Go to your service dashboard
- Environment → Add Environment Variable
- Key: `ADMIN_USER_ID`
- Value: `123456789`

### Method 2: Direct Code (For Development)

Edit `config/settings.py`:

```python
ADMIN_USER_IDS = [
    123456789,  # Your user ID
    987654321,  # Another admin (optional)
]
```

---

## 📊 User Tracking

The bot automatically tracks users when they:
- Send `/start` command
- Search for music
- Use inline mode

**User data stored:**
- User ID
- Username
- First name
- Join date
- Last active date

**Note:** Currently stored in memory. For persistent storage, upgrade to database (PostgreSQL, SQLite, etc.)

---

## 🚨 Security Best Practices

### 1. Keep Admin ID Private
- Never commit admin IDs to public repositories
- Use environment variables in production
- Don't share your admin access

### 2. Test Broadcasts Carefully
- Send test broadcast to yourself first
- Check message formatting
- Avoid spamming users

### 3. Broadcast Guidelines
- ✅ Important updates
- ✅ New features
- ✅ Maintenance notifications
- ❌ Spam
- ❌ Advertisements (unless relevant)
- ❌ Too frequent messages

---

## 💡 Broadcast Tips

### Use Markdown Formatting
```
/broadcast *Bold text* _Italic text_ `Code`
```

### Add Emojis
```
/broadcast 🎉 Exciting news! 🎵 New platform support!
```

### Keep Messages Short
Users prefer concise updates:
```
✅ "🆕 30 search results now available!"
❌ "Hello everyone, we are pleased to announce..."
```

### Include Call-to-Action
```
/broadcast 🎵 Try the new pagination! Search for your favorite artist now!
```

---

## 📈 Analytics & Monitoring

### View Bot Statistics
Use `/stats` to see:
- Total searches
- Total downloads
- Popular queries
- Platform usage

### Monitor User Growth
- Use `/users` regularly
- Track subscriber growth
- Monitor blocked users

### Check Logs
Review bot logs for:
- Broadcast success rates
- Error messages
- User activity patterns

---

## 🔄 Upgrading to Database

Currently, users are stored in memory (lost on restart). To upgrade:

### Option 1: SQLite (Simple)
```python
# utils/database.py
import sqlite3

class UserDatabase:
    def __init__(self):
        self.conn = sqlite3.connect('users.db')
        # Create table, etc.
```

### Option 2: PostgreSQL (Production)
```python
# requirements.txt
psycopg2-binary

# utils/database.py
import psycopg2
# Connect to PostgreSQL...
```

### Option 3: MongoDB (NoSQL)
```python
# requirements.txt
pymongo

# utils/database.py
from pymongo import MongoClient
# Connect to MongoDB...
```

---

## 🐛 Troubleshooting

### "This command is only available to administrators"
- Check your user ID is correct
- Verify `ADMIN_USER_ID` environment variable
- Restart bot after adding admin ID

### Broadcast fails for some users
- Normal! Users may have:
  - Blocked the bot
  - Deleted their account
  - Changed privacy settings
- Blocked users are automatically removed

### No users in database
- Users are added when they:
  - Start the bot (`/start`)
  - Search for music
  - Use inline mode
- Old users before this feature won't be tracked

---

## 📞 Support

Need help with admin features?
- Check bot logs for errors
- Review this guide
- Test commands in private chat with bot

---

## 🎯 Future Admin Features (Roadmap)

- [ ] Schedule broadcasts
- [ ] User segmentation (active vs inactive)
- [ ] Analytics dashboard
- [ ] Export user list
- [ ] Automated welcome messages
- [ ] User feedback collection
- [ ] A/B testing for messages

---

**Admin Commands Summary:**

| Command | Description | Admin Only |
|---------|-------------|------------|
| `/broadcast <message>` | Send to all users | ✅ |
| `/users` | View subscriber count | ✅ |
| `/start` | Start bot | ❌ |
| `/stats` | View statistics | ❌ |

---

*Last updated: October 23, 2025*
