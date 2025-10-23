"""
Audio downloader module for the Musifyyy Bot.
Handles downloading and converting audio from various platforms.
"""
import os
import tempfile
import logging
from typing import Tuple, Optional, List
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
    
    def download_album(
        self, 
        url: str, 
        platform: str
    ) -> List[Tuple[Optional[str], Optional[str], Optional[str]]]:
        """
        Download all tracks from an album/playlist.
        
        Args:
            url: Album/playlist URL
            platform: Platform name
            
        Returns:
            List of tuples: (file_path, track_title, artist) for each track
        """
        tmpdir = tempfile.mkdtemp()
        
        ydl_opts = {
            "format": "bestaudio/best",
            "outtmpl": os.path.join(tmpdir, "%(playlist_index)s - %(title)s.%(ext)s"),
            "quiet": False,
            "no_warnings": False,
            "ignoreerrors": True,  # Continue on errors
            "postprocessors": [{
                "key": "FFmpegExtractAudio",
                "preferredcodec": self.audio_format,
                "preferredquality": self.audio_quality,
            }],
            "prefer_ffmpeg": True,
            "keepvideo": False
        }
        
        if platform == "youtube":
            ydl_opts["extractor_args"] = {
                "youtube": {
                    "player_client": ["ios", "web"],
                    "skip": ["hls"],
                }
            }
            if self.cookies_file:
                ydl_opts["cookiefile"] = self.cookies_file
        
        downloaded_tracks = []
        
        try:
            logger.info(f"Downloading album from {platform}: {url}")
            
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=True)
                
                # Handle playlist/album
                if "entries" in info:
                    for idx, entry in enumerate(info["entries"], 1):
                        if not entry:
                            continue
                        
                        try:
                            base_path = ydl.prepare_filename(entry)
                            file_path = base_path.rsplit('.', 1)[0] + f'.{self.audio_format}'
                            track_title = entry.get("title", f"Track {idx}")
                            artist = entry.get("artist") or entry.get("uploader", "Unknown Artist")
                            
                            if os.path.exists(file_path):
                                downloaded_tracks.append((file_path, track_title, artist))
                                logger.info(f"Track {idx} downloaded: {track_title}")
                        except Exception as e:
                            logger.error(f"Failed to process track {idx}: {e}")
                            downloaded_tracks.append((None, None, None))
            
            logger.info(f"Album download complete: {len(downloaded_tracks)} tracks")
            return downloaded_tracks
            
        except Exception as e:
            logger.error(f"Album download error: {e}")
            return []
    
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
