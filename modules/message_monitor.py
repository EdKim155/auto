"""
Message Monitor Module (FR-1.x)
Monitors incoming messages and edits from target bot.
"""

import logging
from typing import Optional, Callable, Any
from datetime import datetime
from telethon import events, TelegramClient
from telethon.tl.types import Message

from .button_cache import ButtonCache, ButtonInfo
from .button_analyzer import ButtonAnalyzer


logger = logging.getLogger(__name__)


class MessageMonitor:
    """
    Monitors messages and message edits from target bot.
    Implements FR-1.x requirements.
    """

    def __init__(self, client: TelegramClient, bot_entity: Any,
                 button_cache: ButtonCache, trigger_text: str):
        """
        Initialize message monitor.

        Args:
            client: Telethon client
            bot_entity: Target bot entity
            button_cache: Button cache instance
            trigger_text: Text to trigger automation
        """
        self.client = client
        self.bot_entity = bot_entity
        self.bot_id = bot_entity.id
        self.button_cache = button_cache
        self.trigger_text = trigger_text
        self.button_analyzer = ButtonAnalyzer()

        # Callbacks
        self.on_trigger_callback: Optional[Callable[[Message], None]] = None
        self.on_message_callback: Optional[Callable[[Message, bool], None]] = None

        # Statistics
        self.total_messages = 0
        self.total_edits = 0
        self.triggers_detected = 0

    def set_on_trigger(self, callback: Callable[[Message], None]) -> None:
        """
        Set callback for trigger detection.

        Args:
            callback: Function to call when trigger is detected
        """
        self.on_trigger_callback = callback

    def set_on_message(self, callback: Callable[[Message, bool], None]) -> None:
        """
        Set callback for any message/edit.

        Args:
            callback: Function to call on message (message, is_edit)
        """
        self.on_message_callback = callback

    def register_handlers(self) -> None:
        """Register event handlers for messages and edits."""
        # Handler for new messages (FR-1.1)
        @self.client.on(events.NewMessage(chats=[self.bot_entity]))
        async def handle_new_message(event):
            await self._handle_message(event.message, is_edit=False)

        # Handler for message edits (FR-1.2)
        @self.client.on(events.MessageEdited(chats=[self.bot_entity]))
        async def handle_message_edit(event):
            await self._handle_message(event.message, is_edit=True)

        logger.info(f"Registered message handlers for bot ID: {self.bot_id}")

    async def _handle_message(self, message: Message, is_edit: bool) -> None:
        """
        Handle incoming message or edit.

        Args:
            message: Telegram message
            is_edit: True if this is an edit, False if new message
        """
        try:
            # Update statistics
            if is_edit:
                self.total_edits += 1
            else:
                self.total_messages += 1

            # Extract message data
            message_id = message.id
            chat_id = message.chat_id
            text = message.text or ""

            # DEBUG: Log reply_markup details
            has_markup = hasattr(message, 'reply_markup') and message.reply_markup is not None
            logger.debug(
                f"{'Edit' if is_edit else 'New'} msg {message_id}: "
                f"has_markup={has_markup}, "
                f"markup_type={type(message.reply_markup).__name__ if has_markup else 'None'}"
            )

            # Extract buttons (FR-1.4)
            buttons = self.button_analyzer.extract_buttons(message)

            # DEBUG: Log extraction result
            logger.debug(f"Extracted {len(buttons)} buttons from message {message_id}")

            # Update cache
            if buttons:
                self.button_cache.update_message(message_id, chat_id, text, buttons)
                button_texts = [f"'{b.text}'" for b in buttons]
                logger.info(
                    f"📩 {'Edit' if is_edit else 'New'} message {message_id}: "
                    f"{len(buttons)} buttons → {button_texts}"
                )
                if text:
                    logger.info(f"📝 Message text: '{text[:100]}'")
            else:
                if text:
                    logger.info(
                        f"📩 {'Edit' if is_edit else 'New'} message {message_id}: "
                        f"no buttons, text: '{text[:100]}'"
                    )

            # Check for trigger (FR-1.3)
            if self._is_trigger_message(text):
                logger.info(f"🎯 Trigger detected in message {message_id}")
                self.triggers_detected += 1

                if self.on_trigger_callback:
                    self.on_trigger_callback(message)

            # Call general message callback
            if self.on_message_callback:
                self.on_message_callback(message, is_edit)

        except Exception as e:
            logger.error(f"Error handling message: {e}", exc_info=True)

    def _is_trigger_message(self, text: str) -> bool:
        """
        Check if message text contains trigger.

        Args:
            text: Message text

        Returns:
            True if trigger detected
        """
        if not text:
            return False

        return self.trigger_text.lower() in text.lower()

    def get_statistics(self) -> dict:
        """
        Get monitoring statistics.

        Returns:
            Dictionary with statistics
        """
        return {
            'total_messages': self.total_messages,
            'total_edits': self.total_edits,
            'triggers_detected': self.triggers_detected,
            'cached_messages': len(self.button_cache.messages_cache),
        }

    def reset_statistics(self) -> None:
        """Reset all statistics counters."""
        self.total_messages = 0
        self.total_edits = 0
        self.triggers_detected = 0
        logger.info("Statistics reset")
