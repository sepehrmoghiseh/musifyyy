# 🚀 Quick Start Guide

Get the Musifyyy Bot running locally in 5 minutes!

## Prerequisites

- Python 3.11 or higher
- Git
- FFmpeg installed on your system
- A Telegram Bot Token from [@BotFather](https://t.me/botfather)

## Step 1: Clone the Repository

```bash
git clone https://github.com/sepehrmoghiseh/musifyyy.git
cd musifyyy
```

## Step 2: Create Virtual Environment

### Windows (PowerShell)
```powershell
python -m venv .venv
.venv\Scripts\activate
```

### Linux/macOS
```bash
python3 -m venv .venv
source .venv/bin/activate
```

## Step 3: Install Dependencies

```bash
pip install -r requirements.txt
```

## Step 4: Set Up Bot Token

### Windows (PowerShell)
```powershell
$env:BOT_TOKEN="paste_your_bot_token_here"
```

### Linux/macOS
```bash
export BOT_TOKEN="paste_your_bot_token_here"
```

## Step 5: Run the Bot

```bash
python app.py
```

You should see:
```
🎵 Starting Musifyyy Bot...
==================================================
⚙️ POLLING MODE (Local Development)
==================================================
✅ Configuration validated successfully
✅ Application built successfully
```

## 🎉 That's It!

Your bot is now running! Test it:
1. Open Telegram
2. Search for your bot
3. Send `/start`
4. Try searching: "lady gaga poker face"

## 🐛 Troubleshooting

### Import Errors
Make sure you're in the virtual environment:
```powershell
# Windows
.venv\Scripts\activate

# Linux/macOS
source .venv/bin/activate
```

### FFmpeg Not Found
- **Windows**: Download from https://ffmpeg.org/download.html
- **Linux**: `sudo apt-get install ffmpeg`
- **macOS**: `brew install ffmpeg`

### Bot Token Invalid
- Get a new token from [@BotFather](https://t.me/botfather)
- Make sure there are no extra spaces
- Token format: `1234567890:ABCdefGHIjklMNOpqrsTUVwxyz`

### Module Not Found
Reinstall dependencies:
```bash
pip install --upgrade -r requirements.txt
```

## 📁 Project Structure

```
musifyyy/
├── app.py              # Main entry point (start here!)
├── config/             # Configuration settings
├── core/               # Business logic (search, download, analytics)
├── handlers/           # Telegram message handlers
└── utils/              # Helper functions
```

## 🔧 Development Tips

1. **Check logs**: The bot logs everything to console
2. **Test inline mode**: Type `@your_bot_username song` in any chat
3. **View stats**: Send `/stats` to your bot
4. **Code changes**: Just restart the bot to apply changes

## 📚 Next Steps

- Read [ARCHITECTURE.md](ARCHITECTURE.md) for code structure
- Check [README.md](README.md) for deployment options
- Browse the `handlers/` folder to understand bot commands
- Explore `core/` to see how search and download work

## 🤝 Contributing

Found a bug? Have an idea? 
1. Create an issue on GitHub
2. Fork the repo
3. Make your changes
4. Submit a pull request

Happy coding! 🎵
