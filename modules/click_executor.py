"""
Click Executor Module (FR-4.x)
Executes button clicks with error handling and retry logic.
"""

import logging
import asyncio
from typing import Optional, Any
from datetime import datetime
from telethon import TelegramClient
from telethon.tl.functions.messages import GetBotCallbackAnswerRequest
from telethon.errors import (
    MessageNotModifiedError,
    QueryIdInvalidError,
    FloodWaitError,
    TimeoutError as TelethonTimeoutError
)

from .button_cache import ButtonInfo


logger = logging.getLogger(__name__)


class ClickResult:
    """Result of a button click operation."""

    def __init__(self, success: bool, message: str = "",
                 error: Optional[Exception] = None,
                 execution_time: float = 0.0):
        self.success = success
        self.message = message
        self.error = error
        self.execution_time = execution_time

    def __repr__(self) -> str:
        status = "SUCCESS" if self.success else "FAILED"
        return f"ClickResult({status}, {self.execution_time*1000:.1f}ms, '{self.message}')"


class ClickExecutor:
    """
    Executes inline button clicks with retry logic.
    Implements FR-4.x requirements.
    """

    def __init__(self, client: TelegramClient, bot_entity: Any,
                 max_retries: int = 3, retry_delay: float = 0.1):
        """
        Initialize click executor.

        Args:
            client: Telethon client
            bot_entity: Target bot entity
            max_retries: Maximum retry attempts
            retry_delay: Delay between retries in seconds
        """
        self.client = client
        self.bot_entity = bot_entity
        self.max_retries = max_retries
        self.retry_delay = retry_delay

        # Statistics
        self.total_clicks = 0
        self.successful_clicks = 0
        self.failed_clicks = 0

    async def click_button(self, message_id: int, callback_data: bytes,
                          button_text: str = "") -> ClickResult:
        """
        Click an inline button with retry logic (FR-4.x).

        Args:
            message_id: Message ID containing the button
            callback_data: Button's callback_data
            button_text: Button text for logging

        Returns:
            ClickResult with operation status
        """
        start_time = datetime.now()
        self.total_clicks += 1

        for attempt in range(self.max_retries):
            try:
                logger.debug(
                    f"Clicking button '{button_text}' (msg: {message_id}, "
                    f"attempt {attempt + 1}/{self.max_retries})"
                )

                # Execute callback query (FR-4.1)
                result = await self.client(GetBotCallbackAnswerRequest(
                    peer=self.bot_entity,
                    msg_id=message_id,
                    data=callback_data
                ))

                execution_time = (datetime.now() - start_time).total_seconds()

                logger.info(
                    f"✓ Button '{button_text}' clicked successfully "
                    f"({execution_time*1000:.1f}ms)"
                )

                self.successful_clicks += 1

                return ClickResult(
                    success=True,
                    message=f"Clicked '{button_text}'",
                    execution_time=execution_time
                )

            except MessageNotModifiedError:
                # Message was edited, need to get updated callback_data (FR-4.2)
                logger.warning(
                    f"Message {message_id} was modified during click, "
                    f"attempt {attempt + 1}/{self.max_retries}"
                )

                if attempt < self.max_retries - 1:
                    await asyncio.sleep(self.retry_delay)
                    continue
                else:
                    execution_time = (datetime.now() - start_time).total_seconds()
                    self.failed_clicks += 1
                    return ClickResult(
                        success=False,
                        message="Message was modified, max retries reached",
                        error=MessageNotModifiedError("Message modified"),
                        execution_time=execution_time
                    )

            except QueryIdInvalidError:
                # Callback query is invalid/outdated (FR-4.3)
                logger.warning(
                    f"Callback query invalid for message {message_id}, "
                    f"attempt {attempt + 1}/{self.max_retries}"
                )

                if attempt < self.max_retries - 1:
                    await asyncio.sleep(self.retry_delay * 2)
                    continue
                else:
                    execution_time = (datetime.now() - start_time).total_seconds()
                    self.failed_clicks += 1
                    return ClickResult(
                        success=False,
                        message="Query ID invalid, button may have changed",
                        error=QueryIdInvalidError("Invalid query"),
                        execution_time=execution_time
                    )

            except FloodWaitError as e:
                # Hit rate limit, must wait (FR-4.4)
                wait_time = e.seconds
                logger.warning(f"FLOOD_WAIT: must wait {wait_time}s")

                if wait_time > 60:
                    # Wait time too long, abort
                    execution_time = (datetime.now() - start_time).total_seconds()
                    self.failed_clicks += 1
                    return ClickResult(
                        success=False,
                        message=f"Flood wait too long: {wait_time}s",
                        error=e,
                        execution_time=execution_time
                    )

                await asyncio.sleep(wait_time)
                continue

            except TelethonTimeoutError as e:
                # Request timeout (FR-4.5)
                logger.warning(
                    f"Timeout clicking button, attempt {attempt + 1}/{self.max_retries}"
                )

                if attempt < self.max_retries - 1:
                    await asyncio.sleep(self.retry_delay)
                    continue
                else:
                    execution_time = (datetime.now() - start_time).total_seconds()
                    self.failed_clicks += 1
                    return ClickResult(
                        success=False,
                        message="Timeout after max retries",
                        error=e,
                        execution_time=execution_time
                    )

            except Exception as e:
                # Unexpected error
                logger.error(f"Unexpected error clicking button: {e}", exc_info=True)

                if attempt < self.max_retries - 1:
                    await asyncio.sleep(self.retry_delay)
                    continue
                else:
                    execution_time = (datetime.now() - start_time).total_seconds()
                    self.failed_clicks += 1
                    return ClickResult(
                        success=False,
                        message=f"Unexpected error: {str(e)}",
                        error=e,
                        execution_time=execution_time
                    )

        # Should not reach here, but just in case
        execution_time = (datetime.now() - start_time).total_seconds()
        self.failed_clicks += 1
        return ClickResult(
            success=False,
            message="Max retries exceeded",
            execution_time=execution_time
        )

    async def click_button_info(self, message_id: int,
                               button: ButtonInfo) -> ClickResult:
        """
        Click a button using ButtonInfo object.

        Args:
            message_id: Message ID
            button: ButtonInfo object

        Returns:
            ClickResult
        """
        return await self.click_button(
            message_id=message_id,
            callback_data=button.callback_data,
            button_text=button.text
        )

    async def click_with_delay(self, message_id: int, callback_data: bytes,
                              button_text: str = "", delay: float = 0.0) -> ClickResult:
        """
        Click button after a delay.

        Args:
            message_id: Message ID
            callback_data: Callback data
            button_text: Button text for logging
            delay: Delay before clicking in seconds

        Returns:
            ClickResult
        """
        if delay > 0:
            logger.debug(f"Waiting {delay*1000:.1f}ms before clicking '{button_text}'")
            await asyncio.sleep(delay)

        return await self.click_button(message_id, callback_data, button_text)

    def get_statistics(self) -> dict:
        """
        Get click executor statistics.

        Returns:
            Dictionary with statistics
        """
        success_rate = (
            (self.successful_clicks / self.total_clicks * 100)
            if self.total_clicks > 0 else 0.0
        )

        return {
            'total_clicks': self.total_clicks,
            'successful_clicks': self.successful_clicks,
            'failed_clicks': self.failed_clicks,
            'success_rate': round(success_rate, 2),
        }

    def reset_statistics(self) -> None:
        """Reset statistics counters."""
        self.total_clicks = 0
        self.successful_clicks = 0
        self.failed_clicks = 0
