import os
import tempfile
import logging
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

# Enable logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# ========== CONFIG ==========
BOT_TOKEN = os.environ.get("BOT_TOKEN", "")
WEBHOOK_BASE_URL = os.environ.get("WEBHOOK_BASE_URL", "")
PORT = int(os.environ.get("PORT", "8080"))
SEARCH_RESULTS = 6


# ========== SOUND SEARCH ==========
def sc_search(query: str, n: int = 5):
    """Search SoundCloud via yt-dlp."""
    logger.info(f"Searching SoundCloud for: {query}")
    opts = {"quiet": True, "extract_flat": "in_playlist"}
    try:
        with yt_dlp.YoutubeDL(opts) as ydl:
            info = ydl.extract_info(f"scsearch{n}:{query}", download=False)
        results = []
        if info and "entries" in info:
            for e in info["entries"]:
                title = e.get("title", "Unknown title")
                url = e.get("url") or e.get("webpage_url")
                if url:
                    results.append((title, url))
        logger.info(f"Found {len(results)} results")
        return results
    except Exception as e:
        logger.error(f"Search error: {e}")
        return []


# ========== HANDLERS ==========
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    logger.info("Start command received")
    await update.message.reply_text(
        "👋 Send me a song or artist name (e.g. *lady gaga shallow*)\n"
        "I'll search SoundCloud for you 🎵",
        parse_mode="Markdown"
    )


async def search(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = (update.message.text or "").strip()
    if not q or q.startswith("/"):
        return
    
    logger.info(f"Search query received: {q}")
    msg = await update.message.reply_text(f'🔍 Searching SoundCloud for "{q}"…')
    
    try:
        results = sc_search(q, n=SEARCH_RESULTS)
        if not results:
            await msg.edit_text("❌ No results found.")
            return

        buttons = [[InlineKeyboardButton(title[:60], callback_data=url)] for title, url in results]
        await msg.edit_text("🎵 Choose a track:", reply_markup=InlineKeyboardMarkup(buttons))
    except Exception as e:
        logger.error(f"Search handler error: {e}")
        await msg.edit_text(f"⚠️ Error: {e}")


async def button(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    url = q.data
    
    logger.info(f"Download requested: {url}")
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

        with open(file_path, "rb") as audio_file:
            await q.message.reply_audio(audio=audio_file, title=title)
        await status.edit_text(f"✅ Sent: {title}")
        logger.info(f"Successfully sent: {title}")
    except Exception as e:
        logger.error(f"Download error: {e}")
        await status.edit_text(f"⚠️ Couldn't send audio.\n{e}\nLink: {url}")


async def error_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Log errors."""
    logger.error(f"Update {update} caused error {context.error}")


# ========== MAIN APP ==========
async def setup_webhook(app: Application):
    """Setup webhook after application starts."""
    await app.bot.set_webhook(
        url=f"{WEBHOOK_BASE_URL}/webhook",
        allowed_updates=Update.ALL_TYPES
    )
    logger.info(f"✅ Webhook set to: {WEBHOOK_BASE_URL}/webhook")


def build_app() -> Application:
    if not BOT_TOKEN:
        raise RuntimeError("❌ BOT_TOKEN is missing.")
    
    app = ApplicationBuilder().token(BOT_TOKEN).build()
    
    # Add handlers
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(button))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, search))
    app.add_error_handler(error_handler)
    
    return app


if __name__ == "__main__":
    logger.info("Starting bot...")
    app = build_app()

    if WEBHOOK_BASE_URL:
        base_url = WEBHOOK_BASE_URL.rstrip('/')
        webhook_url = f"{base_url}/webhook"
        
        logger.info(f"🚀 Webhook mode enabled")
        logger.info(f"   URL: {webhook_url}")
        logger.info(f"   Port: {PORT}")
        
        # Start webhook with proper configuration
        app.run_webhook(
            listen="0.0.0.0",
            port=PORT,
            url_path="webhook",
            webhook_url=webhook_url,
            drop_pending_updates=True
        )
    else:
        logger.info("⚙️ Polling mode (local)")
        app.run_polling()