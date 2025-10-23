"""
Musifyyy Bot - Multi-Platform Music Downloader
Main application entry point.

A Telegram bot that searches and downloads music from SoundCloud, YouTube, 
and other platforms. Supports both direct messaging and inline mode.

Author: Sepehr Moghiseh
Telegram: @musifyyyybot
GitHub: https://github.com/sepehrmoghiseh/musifyyy
"""
import logging
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    InlineQueryHandler,
    ChosenInlineResultHandler,
    filters
)

from config.settings import BOT_TOKEN, WEBHOOK_BASE_URL, PORT, validate_config
from handlers.commands import start, stats, search, broadcast, users
from handlers.inline import inline_query, chosen_inline_result
from handlers.callbacks import button_callback, error_handler

# Configure logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)


def build_application():
    """
    Build and configure the Telegram bot application.
    
    Returns:
        Application: Configured Telegram bot application
    """
    # Validate configuration
    validate_config()
    
    # Build application
    app = ApplicationBuilder().token(BOT_TOKEN).build()
    
    # Add command handlers
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("stats", stats))
    app.add_handler(CommandHandler("broadcast", broadcast))
    app.add_handler(CommandHandler("users", users))
    
    # Add inline mode handlers
    app.add_handler(InlineQueryHandler(inline_query))
    app.add_handler(ChosenInlineResultHandler(chosen_inline_result))
    
    # Add callback query handler for button clicks
    app.add_handler(CallbackQueryHandler(button_callback))
    
    # Add message handler for search queries
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, search))
    
    # Add error handler
    app.add_error_handler(error_handler)
    
    logger.info("✅ Application built successfully")
    return app


def main():
    """Main entry point for the bot."""
    logger.info("🎵 Starting Musifyyy Bot...")
    logger.info("=" * 50)
    
    # Build the application
    app = build_application()
    
    # Run with webhook or polling
    if WEBHOOK_BASE_URL:
        # Webhook mode (for production on Render, Heroku, etc.)
        base_url = WEBHOOK_BASE_URL.rstrip('/')
        webhook_url = f"{base_url}/webhook"
        
        logger.info("🚀 WEBHOOK MODE")
        logger.info(f"   URL: {webhook_url}")
        logger.info(f"   Port: {PORT}")
        logger.info("=" * 50)
        
        app.run_webhook(
            listen="0.0.0.0",
            port=PORT,
            url_path="webhook",
            webhook_url=webhook_url,
            drop_pending_updates=True
        )
    else:
        # Polling mode (for local development)
        logger.info("⚙️ POLLING MODE (Local Development)")
        logger.info("=" * 50)
        app.run_polling(drop_pending_updates=True)


if __name__ == "__main__":
    main()
