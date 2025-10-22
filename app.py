import os
import tempfile
import shutil
import logging
import threading
from flask import Flask, jsonify
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

# Find cookies.txt file - try multiple locations
COOKIES_FILE = None
secret_cookie_path = "/etc/secrets/cookies.txt"

# If cookies exist in read-only secrets, copy to writable location
if os.path.exists(secret_cookie_path):
    try:
        # Create a writable copy in /tmp
        writable_cookie_path = "/tmp/cookies.txt"
        shutil.copy(secret_cookie_path, writable_cookie_path)
        COOKIES_FILE = writable_cookie_path
        logger.info(f"✅ Copied cookies from {secret_cookie_path} to {writable_cookie_path}")
    except Exception as e:
        logger.error(f"Failed to copy cookies: {e}")
else:
    # Try other locations
    possible_paths = [
        "cookies.txt",
        os.path.join(os.path.dirname(__file__), "cookies.txt"),
        "/app/cookies.txt",
        os.path.join(os.getcwd(), "cookies.txt"),
    ]
    
    for path in possible_paths:
        if os.path.exists(path):
            COOKIES_FILE = path
            logger.info(f"✅ Found cookies.txt at: {COOKIES_FILE}")
            break

if not COOKIES_FILE:
    logger.warning(f"⚠️ cookies.txt not found. Bot will work with limited functionality.")


# Store search results temporarily
search_cache = {}


# ========== FLASK HEALTH ENDPOINT ==========
flask_app = Flask(__name__)

@flask_app.route('/')
@flask_app.route('/health')
def health():
    """Health check endpoint to prevent Render from sleeping"""
    cookie_status = "with_cookies" if COOKIES_FILE and os.path.exists(COOKIES_FILE) else "no_cookies"
    return jsonify({
        'status': 'alive',
        'service': 'Music Downloader Bot',
        'cookies': cookie_status
    }), 200

def run_flask():
    """Run Flask server in a separate thread"""
    flask_app.run(host='0.0.0.0', port=PORT, debug=False, use_reloader=False)


# ========== MUSIC SEARCH ==========
def music_search(query: str, n: int = 6):
    """Search for music using YouTube (more reliable than SoundCloud)."""
    logger.info(f"Searching for: {query}")
    
    # Try YouTube first (most reliable)
    opts = {
        "quiet": True,
        "extract_flat": "in_playlist",
        "default_search": "ytsearch",
    }

    # Add cookies if available
    if COOKIES_FILE and os.path.exists(COOKIES_FILE):
        opts["cookiefile"] = COOKIES_FILE
    
    try:
        with yt_dlp.YoutubeDL(opts) as ydl:
            info = ydl.extract_info(f"ytsearch{n}:{query}", download=False)
        
        results = []
        if info and "entries" in info:
            for e in info["entries"]:
                title = e.get("title", "Unknown title")
                url = e.get("url") or e.get("webpage_url") or e.get("id")
                
                # Make sure we have a valid URL
                if url and not url.startswith("http"):
                    url = f"https://www.youtube.com/watch?v={url}"
                
                if url:
                    # Add duration if available
                    duration = e.get("duration")
                    if duration:
                        mins = int(duration // 60)
                        secs = int(duration % 60)
                        title = f"{title} ({mins}:{secs:02d})"
                    results.append((title, url))
        
        logger.info(f"Found {len(results)} results")
        return results
    except Exception as e:
        logger.error(f"Search error: {e}")
        return []


# ========== HANDLERS ==========
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    logger.info("Start command received")
    cookie_status = "✅ With cookies" if COOKIES_FILE and os.path.exists(COOKIES_FILE) else "⚠️ Without cookies (limited)"
    await update.message.reply_text(
        f"🎵 *Music Downloader Bot* {cookie_status}\n\n"
        "Send me a song or artist name and I'll find it for you!\n\n"
        "Example: `lady gaga shallow`\n\n"
        "I search YouTube Music for the best quality audio.",
        parse_mode="Markdown"
    )


async def search(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = (update.message.text or "").strip()
    if not q or q.startswith("/"):
        return
    
    logger.info(f"Search query received: {q}")
    msg = await update.message.reply_text(f"🔍 Searching for *{q}*...", parse_mode="Markdown")

    try:
        results = music_search(q, n=SEARCH_RESULTS)
        if not results:
            await msg.edit_text("❌ No results found. Try a different search.")
            return

        # Store results with short IDs
        user_id = update.effective_user.id
        search_cache[user_id] = results
        
        # Create buttons with index
        buttons = []
        for i, (title, url) in enumerate(results):
            buttons.append([InlineKeyboardButton(title[:65], callback_data=f"{i}")])
        
        await msg.edit_text(
            "🎵 *Choose a track:*",
            reply_markup=InlineKeyboardMarkup(buttons),
            parse_mode="Markdown"
        )
    except Exception as e:
        logger.error(f"Search handler error: {e}")
        await msg.edit_text(f"⚠️ Error: {e}")


async def button(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    
    # Get the track index from callback data
    try:
        track_index = int(q.data)
        user_id = update.effective_user.id
        
        # Retrieve URL from cache
        if user_id not in search_cache or track_index >= len(search_cache[user_id]):
            await q.edit_message_text("❌ Track not found. Please search again.")
            return
        
        title, url = search_cache[user_id][track_index]
        
    except (ValueError, KeyError):
        await q.edit_message_text("❌ Invalid selection. Please search again.")
        return
    
    logger.info(f"Download requested: {url}")
    status = await q.edit_message_text("⏳ Downloading... This may take a minute.")

    tmpdir = tempfile.mkdtemp()
    ydl_opts = {
        "format": "bestaudio/best",
        "outtmpl": os.path.join(tmpdir, "%(title)s.%(ext)s"),
        "quiet": False,
        "no_warnings": False,
        "noplaylist": True,
        "extractor_args": {
            "youtube": {
                # Use multiple clients for better compatibility - iOS works without cookies
                "player_client": ["ios", "default", "web_safari"],
                "player_js_version": ["actual"],
            }
        },
        "postprocessors": [{
            "key": "FFmpegExtractAudio",
            "preferredcodec": "mp3",
            "preferredquality": "192",
        }],
        "prefer_ffmpeg": True,
        "keepvideo": False
    }
    
    # Add cookies if available (will be used as primary method)
    if COOKIES_FILE and os.path.exists(COOKIES_FILE):
        ydl_opts["cookiefile"] = COOKIES_FILE
        logger.info("Using cookies for download")
    else:
        logger.info("Using cookieless download (iOS client)")

    try:
        logger.info(f"Starting download from: {url}")
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
            # Find the output file
            base_path = ydl.prepare_filename(info)
            file_path = base_path.rsplit('.', 1)[0] + '.mp3'
            track_title = info.get("title", "Audio Track")
            artist = info.get("artist") or info.get("uploader", "Unknown Artist")

        logger.info(f"Download complete: {file_path}")
        
        # Send the audio file
        with open(file_path, "rb") as audio_file:
            await q.message.reply_audio(
                audio=audio_file,
                title=track_title,
                performer=artist,
                caption=f"🎵 {track_title}"
            )
        
        await status.edit_text(f"✅ Sent: *{track_title}*", parse_mode="Markdown")
        logger.info(f"Successfully sent: {track_title}")
        
        # Cleanup
        try:
            os.remove(file_path)
            if os.path.exists(base_path):
                os.remove(base_path)
        except:
            pass
            
    except Exception as e:
        logger.error(f"Download error: {e}")
        await status.edit_text(
            f"⚠️ Couldn't download the audio.\n\n"
            f"Error: {str(e)[:100]}\n\n"
            f"Try another track or search again."
        )


async def error_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Log errors."""
    logger.error(f"Update {update} caused error {context.error}")


# ========== MAIN APP ==========
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
    logger.info("Starting Music Bot...")
    
    # Start Flask health check server in separate thread
    logger.info("Starting health check endpoint...")
    flask_thread = threading.Thread(target=run_flask, daemon=True)
    flask_thread.start()
    
    # Build Telegram bot
    app = build_app()

    if WEBHOOK_BASE_URL:
        base_url = WEBHOOK_BASE_URL.rstrip('/')
        webhook_url = f"{base_url}/webhook"
        
        logger.info(f"🚀 Webhook mode enabled")
        logger.info(f"   URL: {webhook_url}")
        logger.info(f"   Port: {PORT}")
        
        # Start webhook
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
