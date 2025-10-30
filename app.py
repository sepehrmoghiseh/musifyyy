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
import asyncio
from threading import Thread
from flask import Flask, request, jsonify
from telegram import Update
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
    telegram_app = build_application()
    
    # Run with webhook or polling
    if WEBHOOK_BASE_URL:
        # Webhook mode (for production on Render, Heroku, etc.)
        base_url = WEBHOOK_BASE_URL.rstrip('/')
        webhook_url = f"{base_url}/webhook"
        
        logger.info("🚀 WEBHOOK MODE")
        logger.info(f"   URL: {webhook_url}")
        logger.info(f"   Port: {PORT}")
        logger.info("=" * 50)
        
        # Create event loop for async operations
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        # Initialize the bot and set webhook
        async def setup_webhook():
            await telegram_app.initialize()
            await telegram_app.bot.set_webhook(url=webhook_url, drop_pending_updates=True)
            logger.info(f"✅ Webhook set to: {webhook_url}")
        
        # Run setup in the event loop
        loop.run_until_complete(setup_webhook())
        
        # Start event loop in a separate thread
        def run_event_loop():
            asyncio.set_event_loop(loop)
            loop.run_forever()
        
        event_thread = Thread(target=run_event_loop, daemon=True)
        event_thread.start()
        logger.info("🔄 Event loop started in background thread")
        
        # Create Flask app for health checks and webhook
        flask_app = Flask(__name__)
        
        @flask_app.route('/')
        def health_check():
            """Health check endpoint for monitoring services like cron-job.org"""
            return jsonify({
                'status': 'ok',
                'bot': 'Musifyyy Bot',
                'message': 'Bot is running! 🎵',
                'webhook': 'active'
            }), 200
        
        @flask_app.route('/webhook', methods=['POST'])
        def webhook():
            """Handle incoming webhook updates from Telegram"""
            try:
                update = Update.de_json(request.get_json(force=True), telegram_app.bot)
                # Schedule update processing in the event loop
                asyncio.run_coroutine_threadsafe(
                    telegram_app.process_update(update),
                    loop
                )
                return jsonify({'ok': True}), 200
            except Exception as e:
                logger.error(f"Error processing webhook: {e}", exc_info=True)
                return jsonify({'error': str(e)}), 500
        
        # Run Flask app
        logger.info("🌐 Starting Flask web server...")
        flask_app.run(host="0.0.0.0", port=PORT)
        
    else:
        # Polling mode (for local development)
        logger.info("⚙️ POLLING MODE (Local Development)")
        logger.info("=" * 50)
        telegram_app.run_polling(drop_pending_updates=True)


if __name__ == "__main__":
    main()
