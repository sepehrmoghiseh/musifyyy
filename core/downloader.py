"""
Audio downloader module for the Musifyyy Bot.
Handles downloading and converting audio from various platforms.
"""
import os
import tempfile
import logging
import subprocess
import shutil
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
        self.telegram_limit_bytes = 50 * 1_000_000  # Telegram bot upload limit (bytes)
    
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
                
                # Handle playlist/album with multiple entries
                if "entries" in info and info["entries"]:
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
                
                # Handle single video (mis-identified as album)
                # This is a full album in one video, treat as single track
                elif not info.get("entries"):
                    logger.warning("This appears to be a single video, not a playlist. Treating as single track.")
                    base_path = ydl.prepare_filename(info)
                    file_path = base_path.rsplit('.', 1)[0] + f'.{self.audio_format}'
                    track_title = info.get("title", "Album")
                    artist = info.get("artist") or info.get("uploader", "Unknown Artist")
                    
                    if os.path.exists(file_path):
                        downloaded_tracks.append((file_path, track_title, artist))
                        logger.info(f"Single album file downloaded: {track_title}")
            
            logger.info(f"Album download complete: {len(downloaded_tracks)} tracks")
            return downloaded_tracks
            
        except Exception as e:
            logger.error(f"Album download error: {e}")
            return []

    def ensure_telegram_filesize(
        self,
        file_path: str,
        max_size_bytes: Optional[int] = None
    ) -> Tuple[int, Optional[int], bool]:
        """
        Ensure an audio file fits within Telegram's upload limit.

        Args:
            file_path: Path to the audio file.
            max_size_bytes: Optional override for the size limit.

        Returns:
            Tuple of (final_size_bytes, applied_bitrate, within_limit).
            applied_bitrate is None when no re-encoding occurred.
        """
        if not file_path or not os.path.exists(file_path):
            return 0, None, False

        limit = max_size_bytes or self.telegram_limit_bytes
        current_size = os.path.getsize(file_path)

        if current_size <= limit:
            return current_size, None, True

        if not shutil.which("ffmpeg"):
            logger.warning("ffmpeg not available; cannot reduce file size for Telegram.")
            return current_size, None, False

        bitrates = [160, 128, 96, 64]
        base, ext = os.path.splitext(file_path)

        for bitrate in bitrates:
            temp_path = f"{base}_{bitrate}{ext}"
            command = [
                "ffmpeg",
                "-y",
                "-i",
                file_path,
                "-b:a",
                f"{bitrate}k",
                temp_path,
            ]

            try:
                subprocess.run(
                    command,
                    check=True,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                )
            except subprocess.CalledProcessError as exc:
                stderr_output = exc.stderr.decode(errors="ignore") if exc.stderr else str(exc)
                logger.error(
                    "Failed to re-encode %s at %s kbps: %s",
                    file_path,
                    bitrate,
                    stderr_output[:500],
                )
                if os.path.exists(temp_path):
                    os.remove(temp_path)
                continue
            except FileNotFoundError:
                logger.error("ffmpeg binary not found while attempting re-encode.")
                if os.path.exists(temp_path):
                    os.remove(temp_path)
                break

            new_size = os.path.getsize(temp_path)

            if new_size <= limit:
                os.replace(temp_path, file_path)
                logger.info(
                    "Reduced %s to %.1f MB using %d kbps bitrate to satisfy Telegram limit.",
                    file_path,
                    new_size / (1024 * 1024),
                    bitrate,
                )
                return new_size, bitrate, True

            os.remove(temp_path)

        final_report_size = os.path.getsize(file_path) / (1024 * 1024)
        logger.warning(
            "Unable to reduce %s below Telegram's %.1f MB limit (current size %.1f MB).",
            file_path,
            limit / (1024 * 1024),
            final_report_size,
        )
        return os.path.getsize(file_path), None, False

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
