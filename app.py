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


# ========== CONFIG ==========
BOT_TOKEN = os.environ.get("BOT_TOKEN", "")
WEBHOOK_BASE_URL = os.environ.get("WEBHOOK_BASE_URL", "")
PORT = int(os.environ.get("PORT", "8080"))
SEARCH_RESULTS = 6


# ========== SOUND SEARCH ==========
def sc_search(query: str, n: int = 5):
    """Search SoundCloud via yt-dlp."""
    opts = {"quiet": True, "extract_flat": "in_playlist"}
    with yt_dlp.YoutubeDL(opts) as ydl:
        info = ydl.extract_info(f"scsearch{n}:{query}", download=False)
    results = []
    if info and "entries" in info:
        for e in info["entries"]:
            title = e.get("title", "Unknown title")
            url = e.get("url") or e.get("webpage_url")
            if url:
                results.append((title, url))
    return results


# ========== HANDLERS ==========
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "👋 Send me a song or artist name (e.g. *lady gaga shallow*)\n"
        "I'll search SoundCloud for you 🎵",
        parse_mode="Markdown"
    )


async def search(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = (update.message.text or "").strip()
    if not q or q.startswith("/"):
        return
    msg = await update.message.reply_text(f"Searching SoundCloud for “{q}”…")

    try:
        results = sc_search(q, n=SEARCH_RESULTS)
        if not results:
            await msg.edit_text("❌ No results found.")
            return

        buttons = [[InlineKeyboardButton(title[:60], callback_data=url)] for title, url in results]
        await msg.edit_text("Choose a track:", reply_markup=InlineKeyboardMarkup(buttons))
    except Exception as e:
        await msg.edit_text(f"⚠️ Error: {e}")


async def button(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    url = q.data

    status = await q.edit_message_text("🎧 Downloading track… please wait")

    tmpdir = tempfile.mkdtemp()
    ydl_opts = {
        "format": "bestaudio/best",
        "outtmpl": os.path.join(tmpdir, "track.%(ext)s"),
        "quiet": True,
        "noplaylist": True
    }

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
            file_path = ydl.prepare_filename(info)
            title = info.get("title", "SoundCloud Track")

        await q.message.reply_audio(audio=open(file_path, "rb"), title=title)
        await status.edit_text(f"✅ Sent: {title}")
    except Exception as e:
        await status.edit_text(f"⚠️ Couldn't send audio.\n{e}\nLink: {url}")


# ========== MAIN APP ==========
def build_app() -> Application:
    if not BOT_TOKEN:
        raise RuntimeError("❌ BOT_TOKEN is missing. Please set it in Render environment variables.")
    app = ApplicationBuilder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(button))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, search))
    return app


if __name__ == "__main__":
    app = build_app()

    if WEBHOOK_BASE_URL:
        # Webhook mode for Render
        webhook_url = f"{WEBHOOK_BASE_URL}/webhook"
        print(f"🚀 Starting webhook at {webhook_url} (port {PORT})")
        app.run_webhook(
            listen="0.0.0.0",
            port=PORT,
            webhook_url=webhook_url
        )
    else:
        # Local dev: polling mode
        print("⚙️ Running in polling mode…")
        app.run_polling()

