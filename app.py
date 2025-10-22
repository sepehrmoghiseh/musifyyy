import os
import tempfile
import shutil
import logging
from datetime import datetime
from collections import defaultdict
from telegram import (
    InlineKeyboardButton, 
    InlineKeyboardMarkup, 
    Update, 
    InlineQueryResultArticle,
    InputTextMessageContent
)
from telegram.ext import (
    Application,
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    InlineQueryHandler,
    ChosenInlineResultHandler,
    ContextTypes,
    filters
)
import yt_dlp
from uuid import uuid4


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

# Analytics storage
analytics = {
    "total_searches": 0,
    "total_downloads": 0,
    "popular_queries": defaultdict(int),
    "platform_usage": defaultdict(int),
    "inline_selections": defaultdict(int)
}

# Find cookies.txt file
COOKIES_FILE = None
secret_cookie_path = "/etc/secrets/cookies.txt"

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
inline_result_cache = {}


# ========== MUSIC SEARCH ==========
def music_search(query: str, n: int = 6):
    """Search across multiple music platforms."""
    logger.info(f"Searching for: {query}")
    analytics["total_searches"] += 1
    analytics["popular_queries"][query.lower()] += 1
    
    all_results = []
    
    # Try SoundCloud first
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
    
    if len(all_results) >= n:
        return all_results[:n]
    
    # Try YouTube as fallback
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
    
    logger.info(f"Total results: {len(all_results)}")
    return all_results[:n] if all_results else []


# ========== INLINE MODE HANDLERS ==========
async def inline_query(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle inline queries - FIXED to send actual messages."""
    query = update.inline_query.query
    
    if not query or len(query) < 3:
        return
    
    logger.info(f"Inline query received: {query}")
    
    try:
        results = music_search(query, n=10)
        
        if not results:
            return
        
        inline_results = []
        
        for title, url, platform in results:
            result_id = str(uuid4())
            
            # Store result info for later tracking
            inline_result_cache[result_id] = {
                "title": title,
                "url": url,
                "platform": platform,
                "query": query
            }
            
            # Extract clean title
            clean_title = title.replace("🎵 ", "").replace("📺 ", "")
            platform_emoji = "🎵" if platform == "soundcloud" else "📺"
            
            # Create inline result as ARTICLE (not audio)
            inline_result = InlineQueryResultArticle(
                id=result_id,
                title=clean_title,
                description=f"From {platform} - Tap to send",
                input_message_content=InputTextMessageContent(
                    message_text=f"{platform_emoji} *{clean_title}*\n\n"
                                f"🎵 Downloading from {platform}...\n"
                                f"⏳ Please wait, this may take a moment.",
                    parse_mode="Markdown"
                )
                # Removed thumb_url - it's optional
            )
            
            inline_results.append(inline_result)
        
        await update.inline_query.answer(
            inline_results,
            cache_time=300,
            is_personal=True
        )
        
        logger.info(f"Answered inline query with {len(inline_results)} results")
        
    except Exception as e:
        logger.error(f"Inline query error: {e}")


async def chosen_inline_result(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle when user selects inline result - Download and send the actual audio."""
    result = update.chosen_inline_result
    result_id = result.result_id
    query = result.query
    inline_message_id = result.inline_message_id
    
    # Track the selection
    analytics["inline_selections"][query.lower()] += 1
    
    # Get result details from cache
    if result_id not in inline_result_cache:
        logger.warning(f"Result {result_id} not found in cache")
        return
    
    result_info = inline_result_cache[result_id]
    platform = result_info["platform"]
    title = result_info["title"]
    url = result_info["url"]
    
    analytics["platform_usage"][platform] += 1
    analytics["total_downloads"] += 1
    
    logger.info(f"📊 INLINE DOWNLOAD REQUEST:")
    logger.info(f"   User: {result.from_user.username or result.from_user.id}")
    logger.info(f"   Query: {query}")
    logger.info(f"   Selected: {title}")
    logger.info(f"   Platform: {platform}")
    
    # Download the actual audio file
    tmpdir = tempfile.mkdtemp()
    
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
    
    if platform == "youtube":
        ydl_opts["extractor_args"] = {
            "youtube": {
                "player_client": ["ios", "web"],
                "skip": ["hls"],
            }
        }
        if COOKIES_FILE and os.path.exists(COOKIES_FILE):
            ydl_opts["cookiefile"] = COOKIES_FILE
    
    try:
        logger.info(f"Downloading from {platform}: {url}")
        
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
            base_path = ydl.prepare_filename(info)
            file_path = base_path.rsplit('.', 1)[0] + '.mp3'
            track_title = info.get("title", "Audio Track")
            artist = info.get("artist") or info.get("uploader", "Unknown Artist")
        
        logger.info(f"Download complete: {file_path}")
        
        # Edit the inline message to show completion
        try:
            clean_title = title.replace("🎵 ", "").replace("📺 ", "")
            platform_emoji = "🎵" if platform == "soundcloud" else "📺"
            
            await context.bot.edit_message_text(
                inline_message_id=inline_message_id,
                text=f"{platform_emoji} *{clean_title}*\n\n"
                     f"✅ Downloaded from {platform}!\n"
                     f"🎵 via @musifyyyybot",
                parse_mode="Markdown"
            )
        except Exception as e:
            logger.warning(f"Could not edit inline message: {e}")
        
        # Send the actual audio file to the user
        try:
            with open(file_path, "rb") as audio_file:
                await context.bot.send_audio(
                    chat_id=result.from_user.id,
                    audio=audio_file,
                    title=track_title,
                    performer=artist,
                    caption=f"🎵 {track_title}\n📍 Source: {platform.title()}\n🤖 via @musifyyyybot"
                )
            logger.info(f"Sent audio to user {result.from_user.id}")
        except Exception as e:
            logger.error(f"Could not send audio to user: {e}")
        
        # Cleanup
        try:
            os.remove(file_path)
            if os.path.exists(base_path):
                os.remove(base_path)
        except:
            pass
        
        # Clean up cache
        del inline_result_cache[result_id]
        
    except Exception as e:
        logger.error(f"Download failed for inline result: {e}")
        try:
            await context.bot.edit_message_text(
                inline_message_id=inline_message_id,
                text=f"⚠️ Download failed: {str(e)[:100]}\n\n"
                     f"Try searching again with @musifyyyybot",
                parse_mode="Markdown"
            )
        except:
            pass


# ========== HANDLERS ==========
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    logger.info("Start command received")
    await update.message.reply_text(
        "🎵 *Multi-Platform Music Downloader Bot*\n\n"
        "**Two ways to use me:**\n\n"
        "1️⃣ *Direct mode:* Send me a song name here\n"
        "2️⃣ *Inline mode:* Type `@musifyyyybot song name` in any chat\n\n"
        "**Search Priority:**\n"
        "🎵 SoundCloud (primary)\n"
        "🎸 Bandcamp\n"
        "🎼 VK Music\n"
        "🎧 Mixcloud\n"
        "📺 YouTube (fallback)\n\n"
        "**Example:** `lady gaga`\n"
        "**Inline:** `@musifyyyybot lady gaga`\n\n"
        "Type /stats to see usage statistics!",
        parse_mode="Markdown"
    )


async def stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show bot statistics."""
    logger.info("Stats command received")
    
    top_queries = sorted(analytics["popular_queries"].items(), key=lambda x: x[1], reverse=True)[:5]
    top_inline = sorted(analytics["inline_selections"].items(), key=lambda x: x[1], reverse=True)[:5]
    
    stats_text = (
        "📊 *Bot Statistics*\n\n"
        f"🔍 Total Searches: {analytics['total_searches']}\n"
        f"⬇️ Total Downloads: {analytics['total_downloads']}\n\n"
        "*Top Search Queries:*\n"
    )
    
    for i, (query, count) in enumerate(top_queries, 1):
        stats_text += f"{i}. {query} ({count}x)\n"
    
    stats_text += "\n*Top Inline Selections:*\n"
    
    for i, (query, count) in enumerate(top_inline, 1):
        stats_text += f"{i}. {query} ({count}x)\n"
    
    stats_text += "\n*Platform Usage:*\n"
    for platform, count in analytics["platform_usage"].items():
        stats_text += f"• {platform}: {count} downloads\n"
    
    await update.message.reply_text(stats_text, parse_mode="Markdown")


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
                "• Song title only\n\n"
                "Or use inline mode: `@musifyyyybot song name`",
                parse_mode="Markdown"
            )
            return

        user_id = update.effective_user.id
        search_cache[user_id] = results
        
        buttons = []
        for i, (title, url, platform) in enumerate(results):
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
    
    try:
        track_index = int(q.data)
        user_id = update.effective_user.id
        
        if user_id not in search_cache or track_index >= len(search_cache[user_id]):
            await q.edit_message_text("❌ Track not found. Please search again.")
            return
        
        title, url, platform = search_cache[user_id][track_index]
        
    except (ValueError, KeyError):
        await q.edit_message_text("❌ Invalid selection. Please search again.")
        return
    
    logger.info(f"Download requested from {platform}: {url}")
    status = await q.edit_message_text(f"⏳ Downloading from {platform}...")

    analytics["total_downloads"] += 1
    analytics["platform_usage"][platform] += 1

    tmpdir = tempfile.mkdtemp()
    
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
    
    if platform == "youtube":
        ydl_opts["extractor_args"] = {
            "youtube": {
                "player_client": ["ios", "web"],
                "skip": ["hls"],
            }
        }
        if COOKIES_FILE and os.path.exists(COOKIES_FILE):
            ydl_opts["cookiefile"] = COOKIES_FILE
    
    success = False
    
    try:
        logger.info(f"Starting download from {platform}: {url}")
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
            base_path = ydl.prepare_filename(info)
            file_path = base_path.rsplit('.', 1)[0] + '.mp3'
            track_title = info.get("title", "Audio Track")
            artist = info.get("artist") or info.get("uploader", "Unknown Artist")

        logger.info(f"Download complete: {file_path}")
        success = True
            
    except Exception as e:
        logger.error(f"Download error: {e}")
        await status.edit_text(
            f"⚠️ Couldn't download from {platform}.\n\n"
            f"Error: {str(e)[:100]}\n\n"
            "Try another track or search again."
        )
        return
    
    if success:
        try:
            with open(file_path, "rb") as audio_file:
                await q.message.reply_audio(
                    audio=audio_file,
                    title=track_title,
                    performer=artist,
                    caption=f"🎵 {track_title}\n📍 Source: {platform.title()}"
                )
            
            await status.edit_text(f"✅ Sent: *{track_title}*\n📍 From: {platform.title()}", parse_mode="Markdown")
            
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
    
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("stats", stats))
    app.add_handler(InlineQueryHandler(inline_query))
    app.add_handler(ChosenInlineResultHandler(chosen_inline_result))
    app.add_handler(CallbackQueryHandler(button))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, search))
    app.add_error_handler(error_handler)
    
    return app


if __name__ == "__main__":
    logger.info("Starting Multi-Platform Music Bot with Analytics...")
    app = build_app()

    if WEBHOOK_BASE_URL:
        base_url = WEBHOOK_BASE_URL.rstrip('/')
        webhook_url = f"{base_url}/webhook"
        
        logger.info(f"🚀 Webhook mode enabled")
        logger.info(f"   URL: {webhook_url}")
        logger.info(f"   Port: {PORT}")
        
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
