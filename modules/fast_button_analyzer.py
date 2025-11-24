"""
Fast Button Analyzer - Optimized for speed with caching
Pre-compiles search patterns and uses efficient string matching
"""

import logging
from typing import List, Optional, Set
from functools import lru_cache
from telethon.tl.types import Message, ReplyInlineMarkup

logger = logging.getLogger(__name__)


class ButtonInfo:
    """Lightweight button information."""
    __slots__ = ('text', 'callback_data', 'row', 'column', '_text_lower')

    def __init__(self, text: str, callback_data: bytes, row: int, column: int):
        self.text = text
        self.callback_data = callback_data
        self.row = row
        self.column = column
        self._text_lower = text.lower()  # Pre-compute lowercase for fast matching

    def matches_keyword(self, keyword_lower: str) -> bool:
        """Fast keyword matching using pre-computed lowercase."""
        return keyword_lower in self._text_lower


class FastButtonAnalyzer:
    """
    Ultra-fast button analyzer with caching and optimizations.
    """

    def __init__(self):
        """Initialize the analyzer."""
        # Pre-compile keyword sets for O(1) lookups
        self._keyword_cache: dict = {}

    def extract_buttons(self, message: Message) -> List[ButtonInfo]:
        """
        Extract buttons from Telethon message (optimized).

        Args:
            message: Telethon Message object

        Returns:
            List of ButtonInfo objects
        """
        buttons = []

        # Check if message has inline keyboard
        if not hasattr(message, 'reply_markup') or not message.reply_markup:
            return buttons

        reply_markup = message.reply_markup

        # Only process inline keyboards
        if not isinstance(reply_markup, ReplyInlineMarkup):
            return buttons

        # Fast extraction - iterate through rows and buttons
        for row_idx, row in enumerate(reply_markup.rows):
            for col_idx, button in enumerate(row.buttons):
                # Extract button data efficiently
                button_text = getattr(button, 'text', '')
                callback_data = getattr(button, 'data', b'')

                if button_text:
                    button_info = ButtonInfo(
                        text=button_text,
                        callback_data=callback_data,
                        row=row_idx,
                        column=col_idx
                    )
                    buttons.append(button_info)

        return buttons

    def get_first_button(self, buttons: List[ButtonInfo]) -> Optional[ButtonInfo]:
        """
        Get first button (fast version).

        Args:
            buttons: List of ButtonInfo objects

        Returns:
            First button or None
        """
        if not buttons:
            return None

        # Try to find [0,0] button
        for button in buttons:
            if button.row == 0 and button.column == 0:
                return button

        # Fallback to first in list
        return buttons[0]

    def find_button_by_keywords(
        self,
        buttons: List[ButtonInfo],
        keywords: List[str]
    ) -> Optional[ButtonInfo]:
        """
        Find button by keywords (optimized with pre-computed lowercase).

        Args:
            buttons: List of ButtonInfo objects
            keywords: List of keywords to search for

        Returns:
            First matching button or None
        """
        if not keywords or not buttons:
            return None

        # Pre-compute lowercase keywords once
        keywords_lower = [kw.lower() for kw in keywords]

        # Fast matching using pre-computed lowercase
        for button in buttons:
            for keyword_lower in keywords_lower:
                if button.matches_keyword(keyword_lower):
                    logger.debug(f"Button '{button.text}' matched keyword '{keyword_lower}'")
                    return button

        return None

    def find_confirmation_button(
        self,
        buttons: List[ButtonInfo],
        keywords: List[str]
    ) -> Optional[ButtonInfo]:
        """
        Find confirmation button (wrapper for consistency).

        Args:
            buttons: List of ButtonInfo objects
            keywords: List of confirmation keywords

        Returns:
            Confirmation button or None
        """
        return self.find_button_by_keywords(buttons, keywords)

    def get_button_at_position(
        self,
        buttons: List[ButtonInfo],
        row: int,
        column: int
    ) -> Optional[ButtonInfo]:
        """
        Get button at specific position (fast version).

        Args:
            buttons: List of ButtonInfo objects
            row: Row index
            column: Column index

        Returns:
            Button at position or None
        """
        # Direct iteration is faster than building a dict for small lists
        for button in buttons:
            if button.row == row and button.column == column:
                return button
        return None

    @staticmethod
    @lru_cache(maxsize=128)
    def _normalize_text(text: str) -> str:
        """Cached text normalization."""
        return text.lower().strip()

    def compare_button_structures(
        self,
        buttons1: List[ButtonInfo],
        buttons2: List[ButtonInfo]
    ) -> bool:
        """
        Fast button structure comparison.

        Args:
            buttons1: First list of buttons
            buttons2: Second list of buttons

        Returns:
            True if structures are identical
        """
        if len(buttons1) != len(buttons2):
            return False

        # Quick comparison: just check texts in order
        # (assumes buttons maintain order, which is typical)
        for b1, b2 in zip(buttons1, buttons2):
            if b1.text != b2.text or b1.row != b2.row or b1.column != b2.column:
                return False

        return True

    def get_button_texts(self, buttons: List[ButtonInfo]) -> List[str]:
        """
        Extract button texts efficiently.

        Args:
            buttons: List of ButtonInfo objects

        Returns:
            List of button texts
        """
        return [b.text for b in buttons]

    def log_buttons(self, buttons: List[ButtonInfo], prefix: str = "") -> None:
        """
        Log buttons for debugging (optimized).

        Args:
            buttons: List of ButtonInfo objects
            prefix: Optional prefix for log message
        """
        if not buttons:
            logger.debug(f"{prefix}No buttons found")
            return

        # Build layout string efficiently
        button_texts = ', '.join([f"'{b.text}'" for b in buttons])
        logger.debug(f"{prefix}Buttons ({len(buttons)}): {button_texts}")
