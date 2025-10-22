"""
Configuration settings for the Musifyyy Bot.
Manages environment variables and bot configuration.
"""
import os
import logging

logger = logging.getLogger(__name__)


# ========== BOT CONFIGURATION ==========
BOT_TOKEN = os.environ.get("BOT_TOKEN", "")
WEBHOOK_BASE_URL = os.environ.get("WEBHOOK_BASE_URL", "")
PORT = int(os.environ.get("PORT", "8080"))

# ========== SEARCH CONFIGURATION ==========
SEARCH_RESULTS = 6  # Number of search results to display

# ========== DOWNLOAD CONFIGURATION ==========
AUDIO_QUALITY = "192"  # MP3 quality in kbps
AUDIO_FORMAT = "mp3"

# ========== YT-DLP CONFIGURATION ==========
def get_cookies_file():
    """
    Find and return the path to cookies.txt file.
    Checks multiple possible locations.
    """
    secret_cookie_path = "/etc/secrets/cookies.txt"
    
    # Try secret path first (for Render)
    if os.path.exists(secret_cookie_path):
        try:
            import shutil
            writable_cookie_path = "/tmp/cookies.txt"
            shutil.copy(secret_cookie_path, writable_cookie_path)
            logger.info(f"✅ Copied cookies from {secret_cookie_path} to {writable_cookie_path}")
            return writable_cookie_path
        except Exception as e:
            logger.error(f"Failed to copy cookies: {e}")
    
    # Try other common locations
    possible_paths = [
        "cookies.txt",
        os.path.join(os.path.dirname(__file__), "..", "cookies.txt"),
        "/app/cookies.txt",
        os.path.join(os.getcwd(), "cookies.txt"),
    ]
    
    for path in possible_paths:
        if os.path.exists(path):
            logger.info(f"✅ Found cookies.txt at: {path}")
            return path
    
    logger.warning("⚠️ cookies.txt not found. YouTube downloads may be limited.")
    return None


COOKIES_FILE = get_cookies_file()


def validate_config():
    """Validate that required configuration is present."""
    if not BOT_TOKEN:
        raise RuntimeError("❌ BOT_TOKEN environment variable is required.")
    
    logger.info("✅ Configuration validated successfully")
    return True
