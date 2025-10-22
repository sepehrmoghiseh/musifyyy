import os
import tempfile
import shutil
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

# Find cookies.txt file - try multiple locations (only needed for YouTube fallback)
COOKIES_FILE = None
secret_cookie_path = "/etc/secrets/cookies.txt"

# If cookies exist in read-only secrets, copy to writable location
if os.path.exists(secret_cookie_path):
    try:
        writable_cookie_path = "/tmp/cookies.txt"
        shutil.copy(secret_cookie_path, writable_cookie_path)
        COOKIES_FILE = writable_cookie_path
        logger.info(f"✅ Copied cookies from {secret_cookie_path} to {writable_cookie_path}")
    except Exception as e:
        logger.error(f"Failed to copy cookies: {e}")
else:
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
    logger.warning(f"⚠️ cookies.txt not found. YouTube downloads may be limited.")


# Store search results temporarily
search_cache = {}


# Platform configurations with emojis and search prefixes
PLATFORMS = [
    {
        "name": "SoundCloud",
        "emoji": "🎵",
        "search_prefix": "scsearch",
        "needs_cookies": False,
        "color": "orange"
    },
    {
        "name": "Bandcamp",
        "emoji": "🎸",
        "search_prefix": None,  # Bandcamp doesn't have search, only direct URLs
        "needs_cookies": False,
        "color": "blue"
    },
    {
        "name": "VK Music",
        "emoji": "🎼",
        "search_prefix": None,  # VK search not well supported
        "needs_cookies": False,
        "color": "blue"
    },
    {
        "name": "Mixcloud",
        "emoji": "🎧",
        "search_prefix": None,  # Mixcloud search limited
        "needs_cookies": False,
        "color": "blue"
    },
    {
        "name": "YouTube",
        "emoji": "📺",
        "search_prefix": "ytsearch",
        "needs_cookies": True,
        "color": "red"
    }
]


# ========== MUSIC SEARCH ==========
def music_search(query: str, n: int = 6):
    """Search across multiple music platforms for better success rate."""
    logger.info(f"Searching for: {query}")
    
    all_results = []
    
    # Try SoundCloud first (most reliable)
    try:
        logger.info("Trying SoundCloud search...")
        opts = {
            "quiet": True,
            "extract_flat": "in_playlist",
            "default_search": "auto",
            "ignoreerrors": True,
        }
        
        with yt_dlp.YoutubeDL(opts) as ydl:
            info = ydl.extract_info(f"scsearch{n}:{query}", download=False)
        
        if info and "entries" in info:
            for e in info["entries"]:
                if not e:
                    continue
                title = e.get("title", "Unknown title")
                url = e.get("url") or e.get("webpage_url") or e.get("id")
                
                if url and title != "Unknown title":
                    duration = e.get("duration")
                    if duration:
                        mins = int(duration // 60)
                        secs = int(duration % 60)
                        title = f"🎵 {title} ({mins}:{secs:02d})"
                    else:
                        title = f"🎵 {title}"
                    
                    all_results.append((title, url, "soundcloud"))
        
        logger.info(f"SoundCloud: Found {len(all_results)} results")
    except Exception as e:
        logger.warning(f"SoundCloud search failed: {e}")
    
    # If we have enough results from SoundCloud, return them
    if len(all_results) >= n:
        return all_results[:n]
    
    # Try YouTube as fallback (with iOS client for better compatibility)
    try:
        logger.info("Trying YouTube search...")
        opts = {
            "quiet": True,
            "extract_flat": "in_playlist",
            "default_search": "ytsearch",
            "ignoreerrors": True,
            "extractor_args": {
                "youtube": {
                    "player_client": ["ios", "web"],
                }
            }
        }
        
        # Add cookies if available
        if COOKIES_FILE and os.path.exists(COOKIES_FILE):
            opts["cookiefile"] = COOKIES_FILE
        
        with yt_dlp.YoutubeDL(opts) as ydl:
            info = ydl.extract_info(f"ytsearch{n - len(all_results)}:{query}", download=False)
        
        if info and "entries" in info:
            for e in info["entries"]:
                if not e:
                    continue
                title = e.get("title", "Unknown title")
                url = e.get("url") or e.get("webpage_url") or e.get("id")
                
                if url and not url.startswith("http"):
                    url = f"https://www.youtube.com/watch?v={url}"
                
                if url and title != "Unknown title":
                    duration = e.get("duration")
                    if duration:
                        mins = int(duration // 60)
                        secs = int(duration % 60)
                        title = f"📺 {title} ({mins}:{secs:02d})"
                    else:
                        title = f"📺 {title}"
                    
                    all_results.append((title, url, "youtube"))
        
        logger.info(f"YouTube: Found {len([r for r in all_results if r[2] == 'youtube'])} results")
    except Exception as e:
        logger.warning(f"YouTube search failed: {e}")
    
    logger.info(f"Total results from all platforms: {len(all_results)}")
    return all_results[:n] if all_results else []


# ========== HANDLERS ==========
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    logger.info("Start command received")
    await update.message.reply_text(
        "🎵 *Multi-Platform Music Downloader Bot*\n\n"
        "Send me a song or artist name and I'll find it for you!\n\n"
        "**Search Priority:**\n"
        "1️⃣ 🎵 SoundCloud (primary)\n"
        "2️⃣ 🎸 Bandcamp\n"
        "3️⃣ 🎼 VK Music\n"
        "4️⃣ 🎧 Mixcloud\n"
        "5️⃣ 📺 YouTube (fallback)\n\n"
        "**Example:** `daft punk`\n\n"
        "High-quality audio downloads from multiple sources!",
        parse_mode="Markdown"
    )


async def search(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = (update.message.text or "").strip()
    if not q or q.startswith("/"):
        return
    
    logger.info(f"Search query received: {q}")
    msg = await update.message.reply_text(f"🔍 Searching across platforms for *{q}*...", parse_mode="Markdown")

    try:
        results = music_search(q, n=SEARCH_RESULTS)
        if not results:
            await msg.edit_text(
                "❌ No results found on any platform.\n\n"
                "Try:\n"
                "• Different search terms\n"
                "• Artist name only\n"
                "• Song title only"
            )
            return

        # Store results with short IDs
        user_id = update.effective_user.id
        search_cache[user_id] = results
        
        # Create buttons with index
        buttons = []
        for i, (title, url, platform) in enumerate(results):
            # Truncate long titles for button display
            display_title = title[:65] + "..." if len(title) > 65 else title
            buttons.append([InlineKeyboardButton(display_title, callback_data=f"{i}")])
        
        platform_counts = {}
        for _, _, platform in results:
            platform_counts[platform] = platform_counts.get(platform, 0) + 1
        
        summary = " • ".join([f"{count} from {platform}" for platform, count in platform_counts.items()])
        
        await msg.edit_text(
            f"🎵 *Found {len(results)} tracks*\n"
            f"_{summary}_\n\n"
            "Choose a track to download:",
            reply_markup=InlineKeyboardMarkup(buttons),
            parse_mode="Markdown"
        )
    except Exception as e:
        logger.error(f"Search handler error: {e}")
        await msg.edit_text(f"⚠️ Error: {str(e)[:100]}")


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
        
        title, url, platform = search_cache[user_id][track_index]
        
    except (ValueError, KeyError):
        await q.edit_message_text("❌ Invalid selection. Please search again.")
        return
    
    logger.info(f"Download requested from {platform}: {url}")
    status = await q.edit_message_text(f"⏳ Downloading from {platform}... This may take a minute.")

    tmpdir = tempfile.mkdtemp()
    
    # Configure download options based on platform
    ydl_opts = {
        "format": "bestaudio/best",
        "outtmpl": os.path.join(tmpdir, "%(title)s.%(ext)s"),
        "quiet": False,
        "no_warnings": False,
        "noplaylist": True,
        "postprocessors": [{
            "key": "FFmpegExtractAudio",
            "preferredcodec": "mp3",
            "preferredquality": "192",
        }],
        "prefer_ffmpeg": True,
        "keepvideo": False
    }
    
    # Add platform-specific options
    if platform == "youtube":
        ydl_opts["extractor_args"] = {
            "youtube": {
                "player_client": ["ios", "web"],
                "skip": ["hls"],
            }
        }
        if COOKIES_FILE and os.path.exists(COOKIES_FILE):
            ydl_opts["cookiefile"] = COOKIES_FILE
            logger.info("Using cookies for YouTube download")
    
    success = False
    
    try:
        logger.info(f"Starting download from {platform}: {url}")
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
            # Find the output file
            base_path = ydl.prepare_filename(info)
            file_path = base_path.rsplit('.', 1)[0] + '.mp3'
            track_title = info.get("title", "Audio Track")
            artist = info.get("artist") or info.get("uploader", "Unknown Artist")

        logger.info(f"Download complete from {platform}: {file_path}")
        success = True
            
    except Exception as e:
        logger.error(f"Download error from {platform}: {e}")
        await status.edit_text(
            f"⚠️ Couldn't download from {platform}.\n\n"
            f"Error: {str(e)[:100]}\n\n"
            f"Try another track or search again."
        )
        return
    
    if success:
        try:
            logger.info(f"Sending audio file: {file_path}")
            
            # Send the audio file
            with open(file_path, "rb") as audio_file:
                await q.message.reply_audio(
                    audio=audio_file,
                    title=track_title,
                    performer=artist,
                    caption=f"🎵 {track_title}\n📍 Source: {platform.title()}"
                )
            
            await status.edit_text(f"✅ Sent: *{track_title}*\n📍 From: {platform.title()}", parse_mode="Markdown")
            logger.info(f"Successfully sent: {track_title}")
            
            # Cleanup
            try:
                os.remove(file_path)
                if os.path.exists(base_path):
                    os.remove(base_path)
            except:
                pass
        except Exception as e:
            logger.error(f"Failed to send audio: {e}")
            await status.edit_text(f"⚠️ Downloaded but couldn't send: {str(e)[:50]}")


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
    logger.info("Starting Multi-Platform Music Bot...")
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
