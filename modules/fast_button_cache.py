"""
Fast Button Cache - Optimized LRU cache with O(1) operations
"""

import logging
from typing import Optional, List
from collections import OrderedDict
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class MessageData:
    """Cached message data."""
    message_id: int
    chat_id: int
    text: str
    buttons: List  # List of ButtonInfo objects

    def __hash__(self):
        return hash(self.message_id)


class FastButtonCache:
    """
    Ultra-fast LRU cache for message buttons.
    Uses OrderedDict for O(1) operations.
    """

    __slots__ = ('max_size', '_cache', '_stats', 'max_messages')

    def __init__(self, max_size: int = 10, max_messages: int = None):
        """
        Initialize cache.

        Args:
            max_size: Maximum number of messages to cache
            max_messages: Alias for max_size (backward compatibility)
        """
        self.max_size = max_messages if max_messages is not None else max_size
        self.max_messages = self.max_size  # Backward compatibility
        self._cache: OrderedDict[int, MessageData] = OrderedDict()
        self._stats = {'hits': 0, 'misses': 0, 'updates': 0}
    
    @property
    def messages_cache(self):
        """Backward compatibility property."""
        return self._cache

    def update_message(
        self,
        message_id: int,
        chat_id: int,
        text: str,
        buttons: List
    ) -> None:
        """
        Update or add message to cache (O(1) operation).

        Args:
            message_id: Message ID
            chat_id: Chat ID
            text: Message text
            buttons: List of ButtonInfo objects
        """
        # Create message data
        msg_data = MessageData(
            message_id=message_id,
            chat_id=chat_id,
            text=text,
            buttons=buttons
        )

        # Update cache (move to end if exists)
        if message_id in self._cache:
            self._cache.move_to_end(message_id)
            self._cache[message_id] = msg_data
        else:
            self._cache[message_id] = msg_data

            # Evict oldest if over limit
            if len(self._cache) > self.max_size:
                self._cache.popitem(last=False)

        self._stats['updates'] += 1

    def get_message(self, message_id: int) -> Optional[MessageData]:
        """
        Get message from cache (O(1) operation).

        Args:
            message_id: Message ID

        Returns:
            MessageData or None
        """
        msg_data = self._cache.get(message_id)

        if msg_data:
            self._stats['hits'] += 1
            # Move to end (mark as recently used)
            self._cache.move_to_end(message_id)
        else:
            self._stats['misses'] += 1

        return msg_data

    def get_latest_message(self) -> Optional[MessageData]:
        """
        Get most recently updated message (O(1) operation).

        Returns:
            MessageData or None
        """
        if not self._cache:
            return None

        # Get last item (most recent)
        message_id = next(reversed(self._cache))
        return self._cache[message_id]

    def has_message(self, message_id: int) -> bool:
        """
        Check if message exists in cache (O(1) operation).

        Args:
            message_id: Message ID

        Returns:
            True if message is cached
        """
        return message_id in self._cache

    def clear(self) -> None:
        """Clear the cache."""
        self._cache.clear()
        self._stats = {'hits': 0, 'misses': 0, 'updates': 0}

    def get_statistics(self) -> dict:
        """Get cache statistics."""
        total_requests = self._stats['hits'] + self._stats['misses']
        hit_rate = (self._stats['hits'] / total_requests * 100) if total_requests > 0 else 0

        return {
            'size': len(self._cache),
            'max_size': self.max_size,
            'hits': self._stats['hits'],
            'misses': self._stats['misses'],
            'updates': self._stats['updates'],
            'hit_rate': f"{hit_rate:.1f}%"
        }
