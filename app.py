import os
import tempfile
from typing import List

from telegram import (
    InlineKeyboardButton, InlineKeyboardMarkup, Update
)
from telegram.ext import (
    Application, ApplicationBuilder, CommandHandler,
    MessageHandler, CallbackQueryHandler, ContextTypes, filters
)
import yt_dlp

BOT_TOKEN = os.environ.get("BOT_TOKEN", "")
WEBHOOK_BASE_URL = os.environ.get("WEBHOOK_BASE_URL")  # e.g., https://your-service.onrender.com
PORT = int(os.environ.get("PORT", 8080))

SEARCH_RESULTS = 6  # how many options to show

def sc_search(query: str, n: int = 5):
    """Use yt-dlp's SoundCloud search. Returns list of (title, url)."""
    opts = {"quiet": True, "extract_flat": "in_playlist"}
    with yt_dlp.YoutubeDL(opts) as ydl:
        info = ydl.extract_info(f"scsearch{n}:{query}", download=False)
    entries = info.get("entries", []) if info else []
    out = []
    for e in entries:
        title = e.get("title") or "Unknown title"
        url = e.get("url") or e.get("webpage_url")
        if url:
            out.append((title, url))
    return out

async def start(update: Update, _: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Send me a song/artist (e.g., `lady gaga shallow`).\n"
        "I’ll search SoundCloud and let you pick 🎧",
        parse_mode="Markdown"
    )

async def help_cmd(update: Update, _: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Just type your query (song, artist, etc.).\n"
        "Example: `bruno mars grenade`", parse_mode="Markdown"
    )

async def search_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = (update.message.text or "").strip()
    if not q or q.startswith("/"):
        return
    msg = await update.message.reply_text(f"Searching SoundCloud for “{q}”…")
    try:
        results = sc_search(q, n=SEARCH_RESULTS)
        if not results:
            await msg.edit_text("No results found on SoundCloud 😕")
            return

        buttons = [[InlineKeyboardButton(title[:60], callback_data=url)]
                   for title, url in results]
        await msg.edit_text(
            "Choose a track:",
            reply_markup=InlineKeyboardMarkup(buttons)
        )
    except Exception as e:
        await msg.edit_text(f"Search failed: {e}")

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    url = q.data

    status = await q.edit_message_text("Fetching audio… this can take some seconds ⏳")

    # Download best available audio; avoid forcing ffmpeg (keeps deploy simple)
    tmpdir = tempfile.mkdtemp()
    ydl_opts = {
        "format": "bestaudio/best",
        "outtmpl": os.path.join(tmpdir, "track.%(ext)s"),
        "noplaylist": True,
        "quiet": True,
    }

    file_path = None
    title = None
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
            title = info.get("title", "SoundCloud Track")
            file_path = ydl.prepare_filename(info)

        # Try sending as audio; if Telegram can’t sniff codec, send as document
        try:
            await q.message.reply_audio(
                audio=open(file_path, "rb"),
                title=title
            )
        except Exception:
            await q.message.reply_document(
                document=open(file_path, "rb"),
                caption=title
            )

        await status.edit_text(f"✅ Sent: {title}")
    except Exception as e:
        # Fallback: share the page URL
        await status.edit_text(f"Couldn’t send the file. Here’s the link:\n{url}\n\nError: {e}")

async def health(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("OK")

def build_app() -> Application:
    if not BOT_TOKEN:
        raise RuntimeError("BOT_TOKEN env var is missing")
    app = ApplicationBuilder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_cmd))
    app.add_handler(CommandHandler("health", health))
    app.add_handler(CallbackQueryHandler(button_handler))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, search_handler))
    return app

if __name__ == "__main__":
    app = build_app()
    if WEBHOOK_BASE_URL:
        # Webhook mode for production
        url = f"{WEBHOOK_BASE_URL}/webhook"
        app.run_webhook(
            listen="0.0.0.0",
            port=PORT,
            secret_token=None,
            webhook_url=url
        )
    else:
        # Local dev: polling
        app.run_polling()
