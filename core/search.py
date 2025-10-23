"""
Multi-platform music search engine for the Musifyyy Bot.
Searches across SoundCloud, YouTube, and other music platforms.
"""
import logging
from typing import List, Tuple
import yt_dlp

from config.settings import COOKIES_FILE

logger = logging.getLogger(__name__)


class MusicSearchEngine:
    """Handles music search across multiple platforms."""
    
    def __init__(self):
        self.cookies_file = COOKIES_FILE
    
    def search(self, query: str, n: int = 30) -> List[Tuple[str, str, str]]:
        """
        Search for music across multiple platforms.
        
        Args:
            query: Search query string
            n: Number of results to return (default 30 for pagination)
            
        Returns:
            List of tuples: (title, url, platform)
        """
        logger.info(f"Searching for: {query} (requesting {n} results)")
        
        all_results = []
        
        # Try SoundCloud first - get more results
        soundcloud_results = self._search_soundcloud(query, n)
        all_results.extend(soundcloud_results)
        
        # If we have enough results, return them
        if len(all_results) >= n:
            logger.info(f"Total results: {len(all_results[:n])}")
            return all_results[:n]
        
        # Try YouTube as fallback to fill remaining slots
        remaining = n - len(all_results)
        youtube_results = self._search_youtube(query, remaining)
        all_results.extend(youtube_results)
        
        logger.info(f"Total results: {len(all_results)}")
        return all_results[:n] if all_results else []
    
    def _search_soundcloud(self, query: str, n: int) -> List[Tuple[str, str, str]]:
        """Search SoundCloud for music."""
        results = []
        
        try:
            logger.info("Searching SoundCloud...")
            opts = {
                "quiet": True,
                "extract_flat": "in_playlist",
                "default_search": "auto",
                "ignoreerrors": True,
            }
            
            with yt_dlp.YoutubeDL(opts) as ydl:
                info = ydl.extract_info(f"scsearch{n}:{query}", download=False)
            
            if info and "entries" in info:
                for entry in info["entries"]:
                    if not entry:
                        continue
                    
                    title = entry.get("title", "Unknown title")
                    url = entry.get("url") or entry.get("webpage_url") or entry.get("id")
                    
                    if url and title != "Unknown title":
                        # Format title with duration
                        formatted_title = self._format_title(
                            title, 
                            entry.get("duration"),
                            "🎵"
                        )
                        results.append((formatted_title, url, "soundcloud"))
            
            logger.info(f"SoundCloud: Found {len(results)} results")
        except Exception as e:
            logger.warning(f"SoundCloud search failed: {e}")
        
        return results
    
    def _search_youtube(self, query: str, n: int) -> List[Tuple[str, str, str]]:
        """Search YouTube for music."""
        results = []
        
        try:
            logger.info("Searching YouTube...")
            opts = {
                "quiet": True,
                "extract_flat": "in_playlist",
                "default_search": "ytsearch",
                "ignoreerrors": True,
                "extractor_args": {
                    "youtube": {
                        "player_client": ["ios", "web"],
                    }
                }
            }
            
            if self.cookies_file:
                opts["cookiefile"] = self.cookies_file
            
            with yt_dlp.YoutubeDL(opts) as ydl:
                info = ydl.extract_info(f"ytsearch{n}:{query}", download=False)
            
            if info and "entries" in info:
                for entry in info["entries"]:
                    if not entry:
                        continue
                    
                    title = entry.get("title", "Unknown title")
                    url = entry.get("url") or entry.get("webpage_url") or entry.get("id")
                    
                    # Ensure YouTube URL is complete
                    if url and not url.startswith("http"):
                        url = f"https://www.youtube.com/watch?v={url}"
                    
                    if url and title != "Unknown title":
                        # Format title with duration
                        formatted_title = self._format_title(
                            title, 
                            entry.get("duration"),
                            "📺"
                        )
                        results.append((formatted_title, url, "youtube"))
            
            logger.info(f"YouTube: Found {len(results)} results")
        except Exception as e:
            logger.warning(f"YouTube search failed: {e}")
        
        return results
    
    @staticmethod
    def _format_title(title: str, duration: int, emoji: str) -> str:
        """Format title with duration and emoji."""
        if duration:
            mins = int(duration // 60)
            secs = int(duration % 60)
            return f"{emoji} {title} ({mins}:{secs:02d})"
        return f"{emoji} {title}"


# Global search engine instance
search_engine = MusicSearchEngine()
