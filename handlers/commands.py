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
from utils.database import user_db
from config.settings import SEARCH_RESULTS_TOTAL, RESULTS_PER_PAGE, ADMIN_USER_IDS

logger = logging.getLogger(__name__)


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /start command."""
    user = update.effective_user
    logger.info(f"Start command received from user {user.id}")
    
    # Add user to database
    user_db.add_user(user.id, user.username, user.first_name)
    
    await update.message.reply_text(
        "🎵 *Music Downloader Bot*\n\n"
        "**Example: just send ** `lady gaga | مهستی| مایکل جکسون`\n",
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
    
    # Track user activity
    user = update.effective_user
    user_db.add_user(user.id, user.username, user.first_name)
    
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


async def broadcast(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Handle /broadcast command - Admin only.
    Usage: /broadcast Your message here
    """
    user_id = update.effective_user.id
    
    # Check if user is admin
    if user_id not in ADMIN_USER_IDS:
        await update.message.reply_text("❌ This command is only available to administrators.")
        return
    
    # Get message to broadcast
    if not context.args:
        await update.message.reply_text(
            "📢 *Broadcast Message*\n\n"
            "Usage: `/broadcast Your message here`\n\n"
            "This will send your message to all bot users.\n\n"
            "Example:\n"
            "`/broadcast 🎉 New features available! Try searching now!`",
            parse_mode="Markdown"
        )
        return
    
    broadcast_text = " ".join(context.args)
    
    # Get all users
    all_users = user_db.get_all_user_ids()
    total_users = len(all_users)
    
    if total_users == 0:
        await update.message.reply_text("No users to broadcast to.")
        return
    
    # Confirm broadcast
    confirm_msg = await update.message.reply_text(
        f"📢 Broadcasting to {total_users} users...\n"
        f"Message: _{broadcast_text}_\n\n"
        f"⏳ Please wait...",
        parse_mode="Markdown"
    )
    
    # Send to all users
    success_count = 0
    failed_count = 0
    blocked_count = 0
    
    for user_id in all_users:
        try:
            await context.bot.send_message(
                chat_id=user_id,
                text=f"📢 *Message from Musifyyy Bot*\n\n{broadcast_text}",
                parse_mode="Markdown"
            )
            success_count += 1
        except Exception as e:
            error_msg = str(e).lower()
            if "blocked" in error_msg or "user is deactivated" in error_msg:
                blocked_count += 1
                # Remove blocked users from database
                user_db.remove_user(user_id)
            else:
                failed_count += 1
            logger.warning(f"Failed to send broadcast to {user_id}: {e}")
    
    # Send summary
    await confirm_msg.edit_text(
        f"✅ *Broadcast Complete*\n\n"
        f"📊 Results:\n"
        f"• Sent successfully: {success_count}\n"
        f"• Blocked/Deactivated: {blocked_count}\n"
        f"• Failed: {failed_count}\n"
        f"• Total attempted: {total_users}",
        parse_mode="Markdown"
    )
    
    logger.info(f"Broadcast completed: {success_count}/{total_users} successful")


async def users(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Handle /users command - Admin only.
    Shows user statistics.
    """
    user_id = update.effective_user.id
    
    # Check if user is admin
    if user_id not in ADMIN_USER_IDS:
        await update.message.reply_text("❌ This command is only available to administrators.")
        return
    
    total_users = user_db.get_user_count()
    
    await update.message.reply_text(
        f"👥 *User Statistics*\n\n"
        f"Total subscribers: {total_users}\n\n"
        f"Use `/broadcast message` to send a message to all users.",
        parse_mode="Markdown"
    )

