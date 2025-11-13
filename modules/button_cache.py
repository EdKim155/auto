"""
Button Cache Module (FR-MON-x)
Caches recent messages with inline keyboards for fast access.
"""

import logging
from datetime import datetime
from typing import Dict, List, Optional
from dataclasses import dataclass, field


logger = logging.getLogger(__name__)


@dataclass
class ButtonInfo:
    """Information about a single inline button."""
    text: str
    callback_data: bytes
    row: int
    column: int
    first_seen: datetime = field(default_factory=datetime.now)
    last_seen: datetime = field(default_factory=datetime.now)

    def __repr__(self) -> str:
        return f"Button('{self.text}' at [{self.row},{self.column}])"


@dataclass
class MessageData:
    """Cached message data with inline keyboard."""
    message_id: int
    chat_id: int
    text: str
    buttons: List[ButtonInfo]
    last_edit_time: datetime
    edit_count: int = 0

    def __repr__(self) -> str:
        return f"Message({self.message_id}, {len(self.buttons)} buttons, {self.edit_count} edits)"


class ButtonCache:
    """
    Caches recent messages with inline keyboards.
    Implements FR-MON requirements for button monitoring.
    """

    def __init__(self, max_messages: int = 10):
        """
        Initialize button cache.

        Args:
            max_messages: Maximum number of messages to cache
        """
        self.max_messages = max_messages
        self.messages_cache: Dict[int, MessageData] = {}
        self.buttons_history: List[Dict] = []

    def update_message(self, message_id: int, chat_id: int, text: str,
                      buttons: List[ButtonInfo]) -> None:
        """
        Update cached message with new data.

        Args:
            message_id: Telegram message ID
            chat_id: Chat ID
            text: Message text
            buttons: List of buttons in the message
        """
        now = datetime.now()

        if message_id in self.messages_cache:
            # Update existing message
            msg_data = self.messages_cache[message_id]
            msg_data.text = text
            msg_data.buttons = buttons
            msg_data.last_edit_time = now
            msg_data.edit_count += 1

            # Log changes
            self._log_button_changes(message_id, buttons)
        else:
            # Add new message
            msg_data = MessageData(
                message_id=message_id,
                chat_id=chat_id,
                text=text,
                buttons=buttons,
                last_edit_time=now,
                edit_count=0
            )
            self.messages_cache[message_id] = msg_data

            # Clean up old messages if cache is full
            if len(self.messages_cache) > self.max_messages:
                self._cleanup_old_messages()

        logger.debug(f"Updated cache: {msg_data}")

    def get_message(self, message_id: int) -> Optional[MessageData]:
        """
        Get cached message by ID.

        Args:
            message_id: Message ID to retrieve

        Returns:
            MessageData if found, None otherwise
        """
        return self.messages_cache.get(message_id)

    def get_latest_message(self) -> Optional[MessageData]:
        """
        Get the most recently updated message.

        Returns:
            Most recent MessageData or None if cache is empty
        """
        if not self.messages_cache:
            return None

        return max(
            self.messages_cache.values(),
            key=lambda m: m.last_edit_time
        )

    def find_button(self, criteria: str, message_id: Optional[int] = None) -> Optional[ButtonInfo]:
        """
        Find button matching criteria.

        Args:
            criteria: Search criteria:
                - "first" - first button
                - "text:Button Text" - by exact text
                - "contains:keyword" - by text containing keyword
                - "position:row,col" - by position
                - "keywords:word1,word2" - by any keyword match
            message_id: Optional message ID to search in (searches all if None)

        Returns:
            First matching ButtonInfo or None
        """
        messages = [self.messages_cache[message_id]] if message_id and message_id in self.messages_cache \
                   else self.messages_cache.values()

        for message in messages:
            for button in message.buttons:
                if self._matches_criteria(button, criteria):
                    return button

        return None

    def find_all_buttons(self, criteria: str, message_id: Optional[int] = None) -> List[ButtonInfo]:
        """
        Find all buttons matching criteria.

        Args:
            criteria: Search criteria (same as find_button)
            message_id: Optional message ID to search in

        Returns:
            List of matching ButtonInfo objects
        """
        messages = [self.messages_cache[message_id]] if message_id and message_id in self.messages_cache \
                   else self.messages_cache.values()

        results = []
        for message in messages:
            for button in message.buttons:
                if self._matches_criteria(button, criteria):
                    results.append(button)

        return results

    def get_edit_frequency(self, message_id: int, time_window: float = 1.0) -> float:
        """
        Calculate edit frequency for a message.

        Args:
            message_id: Message ID
            time_window: Time window in seconds

        Returns:
            Edits per second
        """
        msg_data = self.messages_cache.get(message_id)
        if not msg_data:
            return 0.0

        # Simple calculation based on total edits
        # In real implementation, would track edit timestamps
        return msg_data.edit_count / max(time_window, 0.1)

    def clear(self) -> None:
        """Clear all cached data."""
        self.messages_cache.clear()
        self.buttons_history.clear()
        logger.info("Cache cleared")

    def _matches_criteria(self, button: ButtonInfo, criteria: str) -> bool:
        """Check if button matches search criteria."""
        if criteria == "first":
            return button.row == 0 and button.column == 0

        if criteria.startswith("text:"):
            search_text = criteria[5:].lower()
            return button.text.lower() == search_text

        if criteria.startswith("contains:"):
            search_text = criteria[9:].lower()
            return search_text in button.text.lower()

        if criteria.startswith("position:"):
            try:
                pos = criteria[9:].split(',')
                row, col = int(pos[0]), int(pos[1])
                return button.row == row and button.column == col
            except (ValueError, IndexError):
                return False

        if criteria.startswith("keywords:"):
            keywords = criteria[9:].split(',')
            button_text_lower = button.text.lower()
            return any(kw.strip().lower() in button_text_lower for kw in keywords)

        return False

    def _log_button_changes(self, message_id: int, new_buttons: List[ButtonInfo]) -> None:
        """Log changes in button structure."""
        old_data = self.messages_cache.get(message_id)
        if not old_data:
            return

        old_texts = [b.text for b in old_data.buttons]
        new_texts = [b.text for b in new_buttons]

        if old_texts != new_texts:
            logger.debug(f"Buttons changed in message {message_id}: {old_texts} -> {new_texts}")

    def _cleanup_old_messages(self) -> None:
        """Remove oldest messages from cache."""
        if len(self.messages_cache) <= self.max_messages:
            return

        # Sort by last edit time and remove oldest
        sorted_messages = sorted(
            self.messages_cache.items(),
            key=lambda x: x[1].last_edit_time
        )

        # Keep only the most recent max_messages
        messages_to_remove = sorted_messages[:len(sorted_messages) - self.max_messages]

        for msg_id, _ in messages_to_remove:
            del self.messages_cache[msg_id]
            logger.debug(f"Removed old message {msg_id} from cache")
