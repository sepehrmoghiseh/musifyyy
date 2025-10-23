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
from config.settings import SEARCH_RESULTS_TOTAL, RESULTS_PER_PAGE

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
        
        # Perform search - get all results (30)
        results = search_engine.search(query, n=SEARCH_RESULTS_TOTAL)
        
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
        
        # Show first page (5 results)
        await _show_results_page(msg, results, page=0, query=query)
        
    except Exception as e:
        logger.error(f"Search handler error: {e}")
        await msg.edit_text(f"⚠️ Error: {str(e)[:100]}")


async def _show_results_page(message, results: list, page: int, query: str):
    """Display a paginated page of search results."""
    total_results = len(results)
    total_pages = (total_results + RESULTS_PER_PAGE - 1) // RESULTS_PER_PAGE
    
    # Calculate start and end indices for this page
    start_idx = page * RESULTS_PER_PAGE
    end_idx = min(start_idx + RESULTS_PER_PAGE, total_results)
    page_results = results[start_idx:end_idx]
    
    # Create buttons for tracks on this page
    buttons = []
    for i in range(start_idx, end_idx):
        title, url, platform = results[i]
        display_title = truncate_title(title)
        buttons.append([
            InlineKeyboardButton(display_title, callback_data=f"download_{i}")
        ])
    
    # Add navigation buttons
    nav_buttons = []
    if page > 0:
        nav_buttons.append(InlineKeyboardButton("⬅️ Previous", callback_data=f"page_{page-1}"))
    
    nav_buttons.append(InlineKeyboardButton(f"📄 {page+1}/{total_pages}", callback_data="page_info"))
    
    if page < total_pages - 1:
        nav_buttons.append(InlineKeyboardButton("Next ➡️", callback_data=f"page_{page+1}"))
    
    if nav_buttons:
        buttons.append(nav_buttons)
    
    # Format summary
    summary = format_platform_summary(results)
    
    await message.edit_text(
        f"🎵 *Found {total_results} tracks*\n"
        f"_{summary}_\n\n"
        f"📄 Page {page+1}/{total_pages} (showing {start_idx+1}-{end_idx})\n\n"
        "Choose a track to download:",
        reply_markup=InlineKeyboardMarkup(buttons),
        parse_mode="Markdown"
    )

