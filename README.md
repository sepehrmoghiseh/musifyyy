# SoundCloud Telegram Bot

Searches SoundCloud, lets users pick a result, and sends the audio in chat.

## Local dev
```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
export BOT_TOKEN=YOUR_TOKEN
python app.py
```

## Deploy on Render
1. Fork this repo.
2. Create a new **Web Service** on Render from this repo.
3. Set environment variables:
   - BOT_TOKEN
   - WEBHOOK_BASE_URL
4. Deploy.
