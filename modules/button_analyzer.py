"""
Button Analyzer Module (FR-2.x)
Analyzes and extracts inline buttons from messages.
"""

import logging
from typing import List, Optional
from telethon.tl.types import Message, ReplyInlineMarkup, KeyboardButtonCallback

from .button_cache import ButtonInfo


logger = logging.getLogger(__name__)


class ButtonAnalyzer:
    """
    Analyzes inline keyboards and extracts button information.
    Implements FR-2.x requirements.
    """

    def extract_buttons(self, message: Message) -> List[ButtonInfo]:
        """
        Extract all inline buttons from a message (FR-2.1).

        Args:
            message: Telegram message

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

        # Extract buttons from each row
        for row_idx, row in enumerate(reply_markup.rows):
            for col_idx, button in enumerate(row.buttons):
                # Extract button data
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
        Get the first button in the keyboard (FR-2.2).

        Args:
            buttons: List of ButtonInfo objects

        Returns:
            First button or None
        """
        if not buttons:
            return None

        # Find button at position [0,0]
        for button in buttons:
            if button.row == 0 and button.column == 0:
                return button

        # Fallback: return first in list
        return buttons[0] if buttons else None

    def find_button_by_text(self, buttons: List[ButtonInfo],
                           search_text: str, exact: bool = False) -> Optional[ButtonInfo]:
        """
        Find button by text (FR-2.3).

        Args:
            buttons: List of ButtonInfo objects
            search_text: Text to search for
            exact: If True, require exact match; if False, search as substring

        Returns:
            Matching button or None
        """
        search_text_lower = search_text.lower()

        for button in buttons:
            button_text_lower = button.text.lower()

            if exact:
                if button_text_lower == search_text_lower:
                    return button
            else:
                if search_text_lower in button_text_lower:
                    return button

        return None

    def find_button_by_keywords(self, buttons: List[ButtonInfo],
                               keywords: List[str]) -> Optional[ButtonInfo]:
        """
        Find button by any matching keyword (FR-2.4).

        Args:
            buttons: List of ButtonInfo objects
            keywords: List of keywords to search for

        Returns:
            First matching button or None
        """
        if not keywords:
            return None

        for button in buttons:
            button_text_lower = button.text.lower()

            for keyword in keywords:
                if keyword.lower() in button_text_lower:
                    logger.debug(f"Button '{button.text}' matched keyword '{keyword}'")
                    return button

        return None

    def find_confirmation_button(self, buttons: List[ButtonInfo],
                                keywords: List[str]) -> Optional[ButtonInfo]:
        """
        Find confirmation button by keywords (FR-2.4).

        Args:
            buttons: List of ButtonInfo objects
            keywords: List of confirmation keywords

        Returns:
            Confirmation button or None
        """
        return self.find_button_by_keywords(buttons, keywords)

    def get_button_at_position(self, buttons: List[ButtonInfo],
                              row: int, column: int) -> Optional[ButtonInfo]:
        """
        Get button at specific position.

        Args:
            buttons: List of ButtonInfo objects
            row: Row index (0-based)
            column: Column index (0-based)

        Returns:
            Button at position or None
        """
        for button in buttons:
            if button.row == row and button.column == column:
                return button

        return None

    def compare_button_structures(self, buttons1: List[ButtonInfo],
                                 buttons2: List[ButtonInfo]) -> bool:
        """
        Compare two button structures for equality (FR-2.5).

        Args:
            buttons1: First list of buttons
            buttons2: Second list of buttons

        Returns:
            True if structures are identical
        """
        if len(buttons1) != len(buttons2):
            return False

        # Sort buttons by position for comparison
        sorted1 = sorted(buttons1, key=lambda b: (b.row, b.column))
        sorted2 = sorted(buttons2, key=lambda b: (b.row, b.column))

        for b1, b2 in zip(sorted1, sorted2):
            if (b1.text != b2.text or
                b1.row != b2.row or
                b1.column != b2.column):
                return False

        return True

    def get_button_layout(self, buttons: List[ButtonInfo]) -> str:
        """
        Get a string representation of button layout.

        Args:
            buttons: List of ButtonInfo objects

        Returns:
            String representation of layout
        """
        if not buttons:
            return "No buttons"

        # Group buttons by row
        rows = {}
        for button in buttons:
            if button.row not in rows:
                rows[button.row] = []
            rows[button.row].append(button)

        # Sort each row by column
        for row in rows.values():
            row.sort(key=lambda b: b.column)

        # Build layout string
        layout_lines = []
        for row_idx in sorted(rows.keys()):
            row_buttons = rows[row_idx]
            row_text = " | ".join([f"'{b.text}'" for b in row_buttons])
            layout_lines.append(f"Row {row_idx}: {row_text}")

        return "\n".join(layout_lines)

    def log_buttons(self, buttons: List[ButtonInfo], prefix: str = "") -> None:
        """
        Log all buttons for debugging.

        Args:
            buttons: List of ButtonInfo objects
            prefix: Optional prefix for log message
        """
        if not buttons:
            logger.debug(f"{prefix}No buttons found")
            return

        layout = self.get_button_layout(buttons)
        logger.debug(f"{prefix}Buttons layout:\n{layout}")
