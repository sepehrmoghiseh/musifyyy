"""
Callback query handlers for the Musifyyy Bot.
Handles button clicks and downloads from search results.
"""
import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes

from core.downloader import downloader
from core.analytics import analytics
from utils.helpers import search_cache, format_platform_summary, truncate_title
from config.settings import RESULTS_PER_PAGE

logger = logging.getLogger(__name__)


async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle button callbacks - download selected track or navigate pages."""
    query = update.callback_query
    await query.answer()
    
    callback_data = query.data
    user_id = update.effective_user.id
    
    # Handle pagination
    if callback_data.startswith("page_"):
        if callback_data == "page_info":
            # Just show current page info, do nothing
            return
        
        try:
            page = int(callback_data.split("_")[1])
            
            # Get cached results
            if not search_cache.has(user_id):
                await query.edit_message_text("❌ Search expired. Please search again.")
                return
            
            results = search_cache.get(user_id)
            await _show_results_page(query.message, results, page)
            return
            
        except (ValueError, IndexError) as e:
            logger.error(f"Page navigation error: {e}")
            return
    
    # Handle download
    if callback_data.startswith("download_"):
        try:
            track_index = int(callback_data.split("_")[1])
        except (ValueError, IndexError):
            await query.edit_message_text("❌ Invalid selection. Please search again.")
            return
    else:
        # Legacy support for old format (just numbers)
        try:
            track_index = int(callback_data)
        except ValueError:
            await query.edit_message_text("❌ Invalid selection. Please search again.")
            return
    
    # Download the track
    try:
        user_id = update.effective_user.id
        
        # Check if user has cached results
        if not search_cache.has(user_id):
            await query.edit_message_text("❌ Track not found. Please search again.")
            return
        
        results = search_cache.get(user_id)
        
        if track_index >= len(results):
            await query.edit_message_text("❌ Track not found. Please search again.")
            return
        
        title, url, platform = results[track_index]
        
    except (ValueError, KeyError):
        await query.edit_message_text("❌ Invalid selection. Please search again.")
        return
    
    logger.info(f"Download requested from {platform}: {url}")
    status = await query.edit_message_text(f"⏳ Downloading from {platform}...")
    
    # Track download
    analytics.track_download(platform)
    
    # Download the audio
    file_path, track_title, artist = downloader.download(url, platform)
    
    if not file_path:
        await status.edit_text(
            f"⚠️ Couldn't download from {platform}.\n\n"
            "Try another track or search again."
        )
        return
    
    # Send the audio file
    try:
        with open(file_path, "rb") as audio_file:
            await query.message.reply_audio(
                audio=audio_file,
                title=track_title,
                performer=artist,
                caption=f"🎵 {track_title}\n📍 Source: {platform.title()}"
            )
        
        await status.edit_text(
            f"✅ Sent: *{track_title}*\n📍 From: {platform.title()}", 
            parse_mode="Markdown"
        )
        
        # Cleanup
        downloader.cleanup_files(file_path)
        
    except Exception as e:
        logger.error(f"Failed to send audio: {e}")
        await status.edit_text(f"⚠️ Downloaded but couldn't send: {str(e)[:50]}")


async def _show_results_page(message, results: list, page: int):
    """Display a paginated page of search results."""
    total_results = len(results)
    total_pages = (total_results + RESULTS_PER_PAGE - 1) // RESULTS_PER_PAGE
    
    # Calculate start and end indices for this page
    start_idx = page * RESULTS_PER_PAGE
    end_idx = min(start_idx + RESULTS_PER_PAGE, total_results)
    
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


async def error_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Log errors."""
    logger.error(f"Update {update} caused error {context.error}")
