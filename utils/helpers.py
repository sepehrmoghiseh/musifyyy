"""
Utility helper functions for the Musifyyy Bot.
Contains cache management and formatting utilities.
"""
from typing import Dict, Any


class SearchCache:
    """Manages temporary storage of search results."""
    
    def __init__(self):
        self._cache: Dict[int, list] = {}
    
    def store(self, user_id: int, results: list):
        """Store search results for a user."""
        self._cache[user_id] = results
    
    def get(self, user_id: int) -> list:
        """Get cached search results for a user."""
        return self._cache.get(user_id, [])
    
    def clear(self, user_id: int):
        """Clear cached results for a user."""
        if user_id in self._cache:
            del self._cache[user_id]
    
    def has(self, user_id: int) -> bool:
        """Check if user has cached results."""
        return user_id in self._cache


class InlineResultCache:
    """Manages temporary storage of inline query results."""
    
    def __init__(self):
        self._cache: Dict[str, Dict[str, Any]] = {}
    
    def store(self, result_id: str, data: Dict[str, Any]):
        """Store inline result data."""
        self._cache[result_id] = data
    
    def get(self, result_id: str) -> Dict[str, Any]:
        """Get cached inline result data."""
        return self._cache.get(result_id, {})
    
    def has(self, result_id: str) -> bool:
        """Check if result is cached."""
        return result_id in self._cache
    
    def delete(self, result_id: str):
        """Delete cached result."""
        if result_id in self._cache:
            del self._cache[result_id]


def format_platform_summary(results: list) -> str:
    """
    Create a summary of platforms in search results.
    
    Args:
        results: List of (title, url, platform) tuples
        
    Returns:
        Formatted platform summary string
    """
    platform_counts = {}
    for _, _, platform in results:
        platform_counts[platform] = platform_counts.get(platform, 0) + 1
    
    return " • ".join([
        f"{count} from {platform}" 
        for platform, count in platform_counts.items()
    ])


def clean_title(title: str) -> str:
    """
    Remove emoji prefixes from track titles.
    
    Args:
        title: Title string with potential emoji prefix
        
    Returns:
        Cleaned title string
    """
    return title.replace("🎵 ", "").replace("📺 ", "")


def truncate_title(title: str, max_length: int = 65) -> str:
    """
    Truncate title to maximum length with ellipsis.
    
    Args:
        title: Title string to truncate
        max_length: Maximum length before truncation
        
    Returns:
        Truncated title
    """
    if len(title) > max_length:
        return title[:max_length] + "..."
    return title


# Global cache instances
search_cache = SearchCache()
inline_result_cache = InlineResultCache()
