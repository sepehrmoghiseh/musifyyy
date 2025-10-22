"""
Callback query handlers for the Musifyyy Bot.
Handles button clicks and downloads from search results.
"""
import logging
from telegram import Update
from telegram.ext import ContextTypes

from core.downloader import downloader
from core.analytics import analytics
from utils.helpers import search_cache

logger = logging.getLogger(__name__)


async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle button callbacks - download selected track."""
    query = update.callback_query
    await query.answer()
    
    try:
        track_index = int(query.data)
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


async def error_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Log errors."""
    logger.error(f"Update {update} caused error {context.error}")
