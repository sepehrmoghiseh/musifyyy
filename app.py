import os
import tempfile
from typing import List
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import (
    Application,
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    ContextTypes,
    filters
)
import yt_dlp


# === Environment variables ===
BOT_TOKEN = os.environ.get("BOT_TOKEN", "")
WEBHOOK_BASE_URL = os.environ.get("WEBHOOK_BASE_URL", "")  # e.g. https://musifyyy.onrender.com
PORT = int(os.environ.get("PORT", 8080))
SEARCH_RESULTS = 6  # how many options to show


# === SoundCloud search ===
def sc_search(query: str, n: int = 5):
    """Use yt-dlp SoundCloud search. Returns list of (title, url)."""
    opts = {"quiet": True, "extract_flat": "in_playlist"}
    with yt_dlp.YoutubeDL(opts) as ydl:
        info = ydl.extract_info(f"scsearch{n}:{query}", download=False)
    results = []
    if info and "entries" in info:
        for e in info["entries"]:
            title = e.get("title")
            url = e.get("url") or e.get("webpage_url")
            if title and url:
                results.append((title, url))
    return results


# === Commands & handlers ===
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "👋 Send me a song or artist name (e.g. *lady gaga shallow*)\n"
        "I’ll search SoundCloud for you 🎶",
        parse_mode="Markdown"
    )


async def search_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = (update.message.text or "").strip()
    if not query or query.startswith("/"):
        return
    msg = await update.message.reply_text(f"Searching SoundCloud for “{query}”…")

    try:
        results = sc_search(query, n=SEARCH_RESULTS)
        if not results:
            await msg.edit_text("😕 No results found.")
            return

        buttons = [[InlineKeyboardButton(title[:60], callback_data=url)] for title, url in results]
        await msg.edit_text("Choose a track:", reply_markup=InlineKeyboardMarkup(buttons))
    except Exception as e:
        await msg.edit_text(f"⚠️ Error while searching: {e}")


async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    url = query.data

    status = await query.edit_m_
