"""
Audio downloader module for the Musifyyy Bot.
Handles downloading and converting audio from various platforms.
"""
import os
import tempfile
import logging
from typing import Tuple, Optional
import yt_dlp

from config.settings import COOKIES_FILE, AUDIO_QUALITY, AUDIO_FORMAT

logger = logging.getLogger(__name__)


class AudioDownloader:
    """Handles audio downloading and conversion."""
    
    def __init__(self):
        self.cookies_file = COOKIES_FILE
        self.audio_quality = AUDIO_QUALITY
        self.audio_format = AUDIO_FORMAT
    
    def download(
        self, 
        url: str, 
        platform: str
    ) -> Tuple[Optional[str], Optional[str], Optional[str]]:
        """
        Download audio from a URL.
        
        Args:
            url: URL to download from
            platform: Platform name (soundcloud, youtube, etc.)
            
        Returns:
            Tuple of (file_path, track_title, artist) or (None, None, None) on error
        """
        tmpdir = tempfile.mkdtemp()
        
        ydl_opts = self._get_download_options(tmpdir, platform)
        
        try:
            logger.info(f"Downloading from {platform}: {url}")
            
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=True)
                base_path = ydl.prepare_filename(info)
                file_path = base_path.rsplit('.', 1)[0] + f'.{self.audio_format}'
                track_title = info.get("title", "Audio Track")
                artist = info.get("artist") or info.get("uploader", "Unknown Artist")
            
            logger.info(f"Download complete: {file_path}")
            return file_path, track_title, artist
            
        except Exception as e:
            logger.error(f"Download error: {e}")
            return None, None, None
    
    def _get_download_options(self, output_dir: str, platform: str) -> dict:
        """
        Get yt-dlp download options based on platform.
        
        Args:
            output_dir: Directory to save downloaded files
            platform: Platform name
            
        Returns:
            Dictionary of yt-dlp options
        """
        opts = {
            "format": "bestaudio/best",
            "outtmpl": os.path.join(output_dir, "%(title)s.%(ext)s"),
            "quiet": False,
            "no_warnings": False,
            "noplaylist": True,
            "postprocessors": [{
                "key": "FFmpegExtractAudio",
                "preferredcodec": self.audio_format,
                "preferredquality": self.audio_quality,
            }],
            "prefer_ffmpeg": True,
            "keepvideo": False
        }
        
        # Platform-specific options
        if platform == "youtube":
            opts["extractor_args"] = {
                "youtube": {
                    "player_client": ["ios", "web"],
                    "skip": ["hls"],
                }
            }
            if self.cookies_file:
                opts["cookiefile"] = self.cookies_file
        
        return opts
    
    @staticmethod
    def cleanup_files(*file_paths: str):
        """
        Clean up downloaded files.
        
        Args:
            *file_paths: Variable number of file paths to delete
        """
        for file_path in file_paths:
            if file_path and os.path.exists(file_path):
                try:
                    os.remove(file_path)
                    logger.debug(f"Cleaned up: {file_path}")
                except Exception as e:
                    logger.warning(f"Failed to cleanup {file_path}: {e}")


# Global downloader instance
downloader = AudioDownloader()
