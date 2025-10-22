"""
Inline mode handlers for the Musifyyy Bot.
Handles inline queries and chosen inline results.
"""
import logging
from uuid import uuid4
from telegram import (
    Update, 
    InlineQueryResultArticle, 
    InputTextMessageContent,
    InputMediaAudio
)
from telegram.ext import ContextTypes

from core.search import search_engine
from core.downloader import downloader
from core.analytics import analytics
from utils.helpers import inline_result_cache, clean_title

logger = logging.getLogger(__name__)


async def inline_query(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle inline queries - show search results in dropdown."""
    query = update.inline_query.query
    
    # Require at least 3 characters
    if not query or len(query) < 3:
        return
    
    logger.info(f"Inline query received: {query}")
    
    try:
        # Track search
        analytics.track_search(query)
        
        # Perform search
        results = search_engine.search(query, n=10)
        
        if not results:
            return
        
        # Build inline results
        inline_results = []
        
        for title, url, platform in results:
            result_id = str(uuid4())
            
            # Store result info for later tracking
            inline_result_cache.store(result_id, {
                "title": title,
                "url": url,
                "platform": platform,
                "query": query
            })
            
            # Extract clean title
            title_clean = clean_title(title)
            platform_emoji = "🎵" if platform == "soundcloud" else "📺"
            
            # Create inline result as ARTICLE
            inline_result = InlineQueryResultArticle(
                id=result_id,
                title=title_clean,
                description=f"From {platform} - Tap to send",
                input_message_content=InputTextMessageContent(
                    message_text=f"{platform_emoji} *{title_clean}*\n\n"
                                f"🎵 Downloading from {platform}...\n"
                                f"⏳ Please wait, this may take a moment.",
                    parse_mode="Markdown"
                )
            )
            
            inline_results.append(inline_result)
        
        # Answer inline query
        await update.inline_query.answer(
            inline_results,
            cache_time=300,
            is_personal=True
        )
        
        logger.info(f"Answered inline query with {len(inline_results)} results")
        
    except Exception as e:
        logger.error(f"Inline query error: {e}")


async def chosen_inline_result(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle when user selects an inline result - download and send audio."""
    result = update.chosen_inline_result
    result_id = result.result_id
    query = result.query
    inline_message_id = result.inline_message_id
    
    # Get result details from cache
    if not inline_result_cache.has(result_id):
        logger.warning(f"Result {result_id} not found in cache")
        return
    
    result_info = inline_result_cache.get(result_id)
    platform = result_info["platform"]
    title = result_info["title"]
    url = result_info["url"]
    
    # Track analytics
    analytics.track_inline_selection(query)
    analytics.track_download(platform)
    
    logger.info(f"📊 INLINE DOWNLOAD REQUEST:")
    logger.info(f"   User: {result.from_user.username or result.from_user.id}")
    logger.info(f"   Query: {query}")
    
    try:
        # Download the audio
        file_path, track_title, artist = downloader.download(url, platform)
        
        if not file_path:
            raise Exception("Download failed")
        
        logger.info(f"Download complete: {file_path}")
        
        # Upload to Telegram and get file_id
        with open(file_path, "rb") as audio_file:
            message = await context.bot.send_audio(
                chat_id=result.from_user.id,
                audio=audio_file,
                title=track_title,
                performer=artist
            )
            
            audio_file_id = message.audio.file_id
        
        # Edit the inline message to show the actual audio
        try:
            await context.bot.edit_message_media(
                inline_message_id=inline_message_id,
                media=InputMediaAudio(
                    media=audio_file_id,
                    title=track_title,
                    performer=artist,
                    caption=f"🎵 via @musifyyyybot"
                )
            )
            logger.info("Successfully edited inline message with audio")
        except Exception as e:
            logger.error(f"Could not edit inline message with audio: {e}")
            # Fallback: update text
            title_clean = clean_title(title)
            platform_emoji = "🎵" if platform == "soundcloud" else "📺"
            
            await context.bot.edit_message_text(
                inline_message_id=inline_message_id,
                text=f"{platform_emoji} *{title_clean}*\n\n"
                     f"✅ Downloaded! Check your chat with @musifyyyybot\n"
                     f"📍 Source: {platform}",
                parse_mode="Markdown"
            )
        
        # Cleanup
        downloader.cleanup_files(file_path)
        inline_result_cache.delete(result_id)
        
    except Exception as e:
        logger.error(f"Inline download failed: {e}")
        try:
            await context.bot.edit_message_text(
                inline_message_id=inline_message_id,
                text=f"⚠️ Download failed: {str(e)[:100]}\n\n"
                     f"Try searching again with @musifyyyybot",
                parse_mode="Markdown"
            )
        except:
            pass
