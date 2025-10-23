"""
Callback query handlers for the Musifyyy Bot.
Handles button clicks and downloads from search results.
"""
import os
import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes

from core.downloader import downloader
from core.analytics import analytics
from utils.helpers import search_cache, format_platform_summary, truncate_title
from config.settings import RESULTS_PER_PAGE

logger = logging.getLogger(__name__)


async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle button callbacks - download selected track/album or navigate pages."""
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
    
    # Handle album download
    if callback_data.startswith("album_"):
        try:
            track_index = int(callback_data.split("_")[1])
        except (ValueError, IndexError):
            await query.edit_message_text("❌ Invalid selection. Please search again.")
            return
        
        # Download album
        await _download_album(query, user_id, track_index)
        return
    
    # Handle single track download
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
    
    # Download single track
    await _download_single_track(query, user_id, track_index)


async def _download_single_track(query, user_id: int, track_index: int):
    """Download and send a single track."""
    try:
        # Check if user has cached results
        if not search_cache.has(user_id):
            await query.edit_message_text("❌ Track not found. Please search again.")
            return
        
        results = search_cache.get(user_id)
        
        if track_index >= len(results):
            await query.edit_message_text("❌ Track not found. Please search again.")
            return
        
        title, url, platform, content_type = results[track_index]
        
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
        # Check file size (Telegram limit is 50MB)
        file_size = os.path.getsize(file_path)
        max_size = 50 * 1024 * 1024  # 50MB in bytes
        
        if file_size > max_size:
            size_mb = file_size / (1024 * 1024)
            await status.edit_text(
                f"⚠️ *File too large to send*\n\n"
                f"📊 Size: {size_mb:.1f} MB (Telegram limit: 50 MB)\n\n"
                f"💡 This appears to be a full album in one file.\n"
                f"Try searching for individual tracks instead.",
                parse_mode="Markdown"
            )
            downloader.cleanup_files(file_path)
            return
        
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


async def _download_album(query, user_id: int, track_index: int):
    """Download and send all tracks from an album."""
    try:
        # Check if user has cached results
        if not search_cache.has(user_id):
            await query.edit_message_text("❌ Album not found. Please search again.")
            return
        
        results = search_cache.get(user_id)
        
        if track_index >= len(results):
            await query.edit_message_text("❌ Album not found. Please search again.")
            return
        
        title, url, platform, content_type = results[track_index]
        
        logger.info(f"Album download requested from {platform}: {url}")
        status = await query.edit_message_text(
            f"💿 Downloading album from {platform}...\n"
            f"⏳ This may take a few minutes..."
        )
        
        # Track download
        analytics.track_download(platform)
        
        # Download all tracks from album
        album_tracks = downloader.download_album(url, platform)
        
        if not album_tracks:
            await status.edit_text(
                f"⚠️ Couldn't download album from {platform}.\n\n"
                "Try another album or search again."
            )
            return
        
        # Send all tracks one by one
        successful = 0
        failed = 0
        
        await status.edit_text(
            f"💿 Sending {len(album_tracks)} tracks...\n"
            f"⏳ Please wait..."
        )
        
        for idx, (file_path, track_title, artist) in enumerate(album_tracks, 1):
            if not file_path:
                failed += 1
                continue
            
            try:
                with open(file_path, "rb") as audio_file:
                    await query.message.reply_audio(
                        audio=audio_file,
                        title=track_title,
                        performer=artist,
                        caption=f"🎵 {track_title}\n📍 Track {idx}/{len(album_tracks)}\n📍 Source: {platform.title()}"
                    )
                successful += 1
                
                # Update progress
                if idx % 3 == 0:  # Update every 3 tracks
                    await status.edit_text(
                        f"💿 Sending tracks... ({idx}/{len(album_tracks)})\n"
                        f"✅ Sent: {successful} | ⚠️ Failed: {failed}"
                    )
                
                # Cleanup this track
                downloader.cleanup_files(file_path)
                
            except Exception as e:
                failed += 1
                logger.error(f"Failed to send track {idx}: {e}")
        
        # Final status
        await status.edit_text(
            f"✅ *Album Download Complete!*\n\n"
            f"📊 Results:\n"
            f"• Total tracks: {len(album_tracks)}\n"
            f"• Sent successfully: {successful}\n"
            f"• Failed: {failed}\n"
            f"📍 Source: {platform.title()}",
            parse_mode="Markdown"
        )
        
    except Exception as e:
        logger.error(f"Album download error: {e}")
        await query.edit_message_text(f"⚠️ Album download failed: {str(e)[:100]}")


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
        title, url, platform, content_type = results[i]
        display_title = truncate_title(title)
        
        # Different callback for albums vs tracks
        if content_type == "album":
            buttons.append([
                InlineKeyboardButton(display_title, callback_data=f"album_{i}")
            ])
        else:
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
