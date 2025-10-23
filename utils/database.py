"""
Simple user database for tracking bot subscribers.
Stores user information in memory (can be upgraded to real DB later).
"""
import logging
from typing import Set, List, Dict
from datetime import datetime

logger = logging.getLogger(__name__)


class UserDatabase:
    """Manages bot users/subscribers."""
    
    def __init__(self):
        self._users: Dict[int, dict] = {}  # user_id -> user_info
    
    def add_user(self, user_id: int, username: str = None, first_name: str = None):
        """Add or update a user in the database."""
        if user_id not in self._users:
            self._users[user_id] = {
                'user_id': user_id,
                'username': username,
                'first_name': first_name,
                'joined_at': datetime.now().isoformat(),
                'last_active': datetime.now().isoformat()
            }
            logger.info(f"New user added: {user_id} (@{username})")
        else:
            # Update last active time
            self._users[user_id]['last_active'] = datetime.now().isoformat()
            if username:
                self._users[user_id]['username'] = username
            if first_name:
                self._users[user_id]['first_name'] = first_name
    
    def get_all_user_ids(self) -> List[int]:
        """Get list of all user IDs."""
        return list(self._users.keys())
    
    def get_user_count(self) -> int:
        """Get total number of users."""
        return len(self._users)
    
    def get_user_info(self, user_id: int) -> dict:
        """Get information about a specific user."""
        return self._users.get(user_id, {})
    
    def remove_user(self, user_id: int):
        """Remove a user from the database."""
        if user_id in self._users:
            del self._users[user_id]
            logger.info(f"User removed: {user_id}")


# Global user database instance
user_db = UserDatabase()
