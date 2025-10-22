"""
Analytics tracking module for the Musifyyy Bot.
Tracks searches, downloads, and platform usage statistics.
"""
from collections import defaultdict
from typing import Dict, List, Tuple


class Analytics:
    """Manages bot usage analytics and statistics."""
    
    def __init__(self):
        self.total_searches = 0
        self.total_downloads = 0
        self.popular_queries = defaultdict(int)
        self.platform_usage = defaultdict(int)
        self.inline_selections = defaultdict(int)
    
    def track_search(self, query: str):
        """Track a search query."""
        self.total_searches += 1
        self.popular_queries[query.lower()] += 1
    
    def track_download(self, platform: str):
        """Track a download from a specific platform."""
        self.total_downloads += 1
        self.platform_usage[platform] += 1
    
    def track_inline_selection(self, query: str):
        """Track an inline mode selection."""
        self.inline_selections[query.lower()] += 1
    
    def get_top_queries(self, limit: int = 5) -> List[Tuple[str, int]]:
        """Get top search queries."""
        return sorted(
            self.popular_queries.items(), 
            key=lambda x: x[1], 
            reverse=True
        )[:limit]
    
    def get_top_inline_selections(self, limit: int = 5) -> List[Tuple[str, int]]:
        """Get top inline selections."""
        return sorted(
            self.inline_selections.items(), 
            key=lambda x: x[1], 
            reverse=True
        )[:limit]
    
    def get_platform_stats(self) -> Dict[str, int]:
        """Get platform usage statistics."""
        return dict(self.platform_usage)
    
    def get_stats_summary(self) -> str:
        """Generate a formatted statistics summary."""
        top_queries = self.get_top_queries()
        top_inline = self.get_top_inline_selections()
        
        stats_text = (
            "📊 *Bot Statistics*\n\n"
            f"🔍 Total Searches: {self.total_searches}\n"
            f"⬇️ Total Downloads: {self.total_downloads}\n\n"
            "*Top Search Queries:*\n"
        )
        
        if top_queries:
            for i, (query, count) in enumerate(top_queries, 1):
                stats_text += f"{i}. {query} ({count}x)\n"
        else:
            stats_text += "_No data yet_\n"
        
        stats_text += "\n*Top Inline Selections:*\n"
        
        if top_inline:
            for i, (query, count) in enumerate(top_inline, 1):
                stats_text += f"{i}. {query} ({count}x)\n"
        else:
            stats_text += "_No data yet_\n"
        
        stats_text += "\n*Platform Usage:*\n"
        
        if self.platform_usage:
            for platform, count in self.platform_usage.items():
                stats_text += f"• {platform}: {count} downloads\n"
        else:
            stats_text += "_No data yet_\n"
        
        return stats_text


# Global analytics instance
analytics = Analytics()
