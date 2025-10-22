"""
Command handlers for the Musifyyy Bot.
Handles /start and /stats commands.
"""
import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes

from core.search import search_engine
from core.analytics import analytics
from utils.helpers import search_cache, format_platform_summary, truncate_title
from config.settings import SEARCH_RESULTS

logger = logging.getLogger(__name__)


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /start command."""
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
    """Handle /stats command - show bot statistics."""
    logger.info("Stats command received")
    stats_text = analytics.get_stats_summary()
    await update.message.reply_text(stats_text, parse_mode="Markdown")


async def search(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle text messages - search for music."""
    query = (update.message.text or "").strip()
    
    # Ignore commands
    if not query or query.startswith("/"):
        return
    
    logger.info(f"Search query received: {query}")
    msg = await update.message.reply_text(
        f"🔍 Searching across platforms for *{query}*...", 
        parse_mode="Markdown"
    )
    
    try:
        # Track the search
        analytics.track_search(query)
        
        # Perform search
        results = search_engine.search(query, n=SEARCH_RESULTS)
        
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
        
        # Store results in cache
        user_id = update.effective_user.id
        search_cache.store(user_id, results)
        
        # Create inline keyboard buttons
        buttons = []
        for i, (title, url, platform) in enumerate(results):
            display_title = truncate_title(title)
            buttons.append([
                InlineKeyboardButton(display_title, callback_data=f"{i}")
            ])
        
        # Format summary
        summary = format_platform_summary(results)
        
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
