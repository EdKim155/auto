"""
TDLib-based Bot Automation - High-performance version
Uses pytdbot for native TDLib speed with optimized modules
"""

import asyncio
import logging
from typing import Optional, List
from time import monotonic

from pytdbot import Client, types, filters

from config import Config
from modules.fast_stabilization_detector import FastStabilizationDetector
from modules.fast_button_analyzer import FastButtonAnalyzer, ButtonInfo
from modules.fast_button_cache import FastButtonCache
from modules.state_machine import StateMachine, AutomationState

logger = logging.getLogger(__name__)


class BotAutomationTDLib:
    """
    High-performance bot automation using TDLib.
    Optimized for maximum speed and reliability.
    """

    def __init__(
        self,
        client: Client,
        bot_username: str,
        mode: str = 'full_cycle',
        step2_button_keywords: Optional[str] = None,
        step2_button_index: int = 0
    ):
        """
        Initialize TDLib-based automation.

        Args:
            client: pytdbot Client instance
            bot_username: Target bot username
            mode: 'full_cycle' or 'list_only'
            step2_button_keywords: Keywords for Step 2 button
            step2_button_index: Index for Step 2 button
        """
        self.client = client
        self.bot_username = bot_username
        self.mode = mode
        self.bot_chat_id: Optional[int] = None

        # Step 2 configuration
        self.step2_button_keywords = step2_button_keywords
        self.step2_button_index = step2_button_index

        # Initialize optimized modules
        self.button_cache = FastButtonCache(max_messages=Config.MAX_CACHED_MESSAGES)
        self.button_analyzer = FastButtonAnalyzer()
        self.stabilization_detector = FastStabilizationDetector(
            threshold=Config.STABILIZATION_THRESHOLD,
            strategy=Config.STABILIZATION_STRATEGY
        )
        self.state_machine = StateMachine(
            step_1_timeout=Config.STEP_1_TIMEOUT,
            step_2_timeout=Config.STEP_2_TIMEOUT,
            step_3_timeout=Config.STEP_3_TIMEOUT
        )

        # State tracking
        self.is_running = False
        self.current_message_id: Optional[int] = None
        self.last_button_texts: Optional[List[str]] = None

        # Performance metrics
        self._metrics = {
            'total_cycles': 0,
            'successful_cycles': 0,
            'failed_cycles': 0,
            'total_clicks': 0,
            'avg_cycle_time': 0.0
        }

    async def start(self) -> None:
        """Start the automation system."""
        logger.info("Starting TDLib-based bot automation...")
        Config.display()

        # Get bot chat
        self.bot_chat_id = await self._get_bot_chat_id()
        if not self.bot_chat_id:
            raise RuntimeError(f"Could not find chat with bot: {self.bot_username}")

        logger.info(f"✓ Bot chat ID: {self.bot_chat_id}")

        # Initialize cache with recent messages
        await self._initialize_cache()

        self.is_running = True
        logger.info("✓ TDLib automation started. Waiting for triggers...")

        # Start timeout checker
        asyncio.create_task(self._timeout_checker())

    async def _get_bot_chat_id(self) -> Optional[int]:
        """Get bot chat ID by username."""
        try:
            # Search for the bot
            result = await self.client.searchPublicChat(self.bot_username)
            if result and hasattr(result, 'id'):
                return result.id

            logger.error(f"Bot not found: {self.bot_username}")
            return None

        except Exception as e:
            logger.error(f"Error getting bot chat: {e}", exc_info=True)
            return None

    async def _initialize_cache(self) -> None:
        """Initialize cache with recent messages."""
        try:
            logger.info("Initializing cache with recent messages...")

            # Get chat history
            result = await self.client.getChatHistory(
                chat_id=self.bot_chat_id,
                limit=10
            )

            if not result or not hasattr(result, 'messages'):
                logger.warning("No messages found in chat history")
                return

            # Process messages
            processed = 0
            for message in result.messages:
                if hasattr(message, 'reply_markup') and message.reply_markup:
                    buttons = self.button_analyzer.extract_buttons(message.reply_markup)
                    if buttons:
                        self.button_cache.update_message(
                            message.id,
                            message.chat_id,
                            getattr(message.content, 'text', {}).get('text', '') if hasattr(message.content, 'text') else '',
                            buttons
                        )
                        processed += 1

            logger.info(f"✓ Cache initialized with {processed} messages")

        except Exception as e:
            logger.error(f"Error initializing cache: {e}", exc_info=True)

    async def handle_new_message(self, message: types.Message) -> None:
        """
        Handle new message from bot.

        Args:
            message: New message
        """
        # Only process messages from our bot
        if message.chat_id != self.bot_chat_id:
            return

        # Extract message text
        message_text = ''
        if hasattr(message.content, 'text'):
            message_text = message.content.text.get('text', '')

        # Extract buttons
        buttons = []
        if hasattr(message, 'reply_markup') and message.reply_markup:
            buttons = self.button_analyzer.extract_buttons(message.reply_markup)

        # Update cache
        self.button_cache.update_message(
            message.id,
            message.chat_id,
            message_text,
            buttons
        )

        # Check for trigger
        if Config.TRIGGER_TEXT in message_text:
            await self._handle_trigger(message)

    async def handle_message_edit(self, message: types.Message) -> None:
        """
        Handle message edit from bot.

        Args:
            message: Edited message
        """
        # Only process messages from our bot
        if message.chat_id != self.bot_chat_id:
            return

        # Record edit for stabilization
        self.stabilization_detector.record_edit(message.id)

        # Extract message text
        message_text = ''
        if hasattr(message.content, 'text'):
            message_text = message.content.text.get('text', '')

        # Extract buttons
        buttons = []
        if hasattr(message, 'reply_markup') and message.reply_markup:
            buttons = self.button_analyzer.extract_buttons(message.reply_markup)

        # Update cache
        self.button_cache.update_message(
            message.id,
            message.chat_id,
            message_text,
            buttons
        )

        # If we're active, check for state progression
        if self.state_machine.is_active():
            asyncio.create_task(self._check_stabilization(message.id))

    async def _handle_trigger(self, message: types.Message) -> None:
        """
        Handle trigger message detection.

        Args:
            message: Trigger message
        """
        # Only process if idle
        if not self.state_machine.is_idle():
            logger.warning(
                f"Trigger ignored - already running in state {self.state_machine.current_state.name}"
            )
            return

        logger.info(f"🎯 Trigger detected! Starting automation for message {message.id}")

        # Start performance tracking
        cycle_start = monotonic()

        # Start automation
        self.state_machine.start_automation(message.id)
        self.current_message_id = message.id
        self.last_button_texts = None

        # Record edit for stabilization
        self.stabilization_detector.record_edit(message.id)

        # Execute step 1
        asyncio.create_task(self._execute_step_1(message.id, cycle_start))

    async def _execute_step_1(self, message_id: int, cycle_start: float) -> None:
        """Execute Step 1: Click 'Список прямых перевозок'."""
        try:
            logger.info("=== STEP 1: Clicking 'Список прямых перевозок' ===")

            # Wait for trigger delay
            if Config.DELAY_AFTER_TRIGGER > 0:
                await asyncio.sleep(Config.DELAY_AFTER_TRIGGER)

            # Wait for stabilization
            stabilized = await self.stabilization_detector.wait_for_stabilization(
                message_id,
                max_wait=Config.STEP_1_TIMEOUT
            )

            if not stabilized:
                self.state_machine.error("Step 1: Message did not stabilize")
                self._metrics['failed_cycles'] += 1
                return

            # Get message data
            msg_data = self.button_cache.get_message(message_id)

            # If no buttons, use latest cached message
            if not msg_data or not msg_data.buttons:
                logger.info("Trigger message has no buttons, using cached menu...")
                msg_data = self.button_cache.get_latest_message()

                if msg_data and msg_data.buttons:
                    logger.info(f"Using cached message {msg_data.message_id}")
                    message_id = msg_data.message_id
                    self.last_button_texts = self.button_analyzer.get_button_texts(msg_data.buttons)
                else:
                    self.state_machine.error("Step 1: No buttons found")
                    self._metrics['failed_cycles'] += 1
                    return

            # Find target button
            logger.info(f"🔍 Searching for button with keywords: {Config.BUTTON_1_KEYWORDS}")
            button = self.button_analyzer.find_button_by_keywords(
                msg_data.buttons,
                Config.BUTTON_1_KEYWORDS
            )

            # Fallback to first button
            if not button:
                logger.warning("⚠️ Button 1 not found, using first button")
                button = self.button_analyzer.get_first_button(msg_data.buttons)

            if not button:
                self.state_machine.error("Step 1: No button available")
                self._metrics['failed_cycles'] += 1
                return

            logger.info(f"🎯 Target button: '{button.text}' at [{button.row},{button.column}]")

            # Click button
            success = await self._click_button(message_id, button)

            if success:
                self._metrics['total_clicks'] += 1
                logger.info("✓ Step 1 completed")
                await asyncio.sleep(Config.DELAY_BETWEEN_CLICKS)
            else:
                self.state_machine.error("Step 1 click failed")
                self._metrics['failed_cycles'] += 1

        except Exception as e:
            logger.error(f"Error in step 1: {e}", exc_info=True)
            self.state_machine.error(f"Step 1 exception: {str(e)}")
            self._metrics['failed_cycles'] += 1

    async def _execute_step_2(self, message_id: int) -> None:
        """Execute Step 2: Click first transport."""
        try:
            logger.info("=== STEP 2: Clicking transport ===")

            # Wait for stabilization
            stabilized = await self.stabilization_detector.wait_for_stabilization(
                message_id,
                max_wait=Config.STEP_2_TIMEOUT
            )

            if not stabilized:
                self.state_machine.error("Step 2: Message did not stabilize")
                self._metrics['failed_cycles'] += 1
                return

            # Get message data
            msg_data = self.button_cache.get_message(message_id)
            if not msg_data or not msg_data.buttons:
                self.state_machine.error("Step 2: No buttons found")
                self._metrics['failed_cycles'] += 1
                return

            # Find button
            button = None

            # Try keywords first
            if self.step2_button_keywords:
                keywords = [k.strip() for k in self.step2_button_keywords.split(',') if k.strip()]
                if keywords:
                    button = self.button_analyzer.find_button_by_keywords(msg_data.buttons, keywords)

            # Fallback to index
            if not button:
                if self.step2_button_index < len(msg_data.buttons):
                    button = msg_data.buttons[self.step2_button_index]
                else:
                    button = self.button_analyzer.get_first_button(msg_data.buttons)

            if not button:
                self.state_machine.error("Step 2: No button available")
                self._metrics['failed_cycles'] += 1
                return

            logger.info(f"🎯 Target button: '{button.text}'")

            # Click button
            success = await self._click_button(message_id, button)

            if success:
                self._metrics['total_clicks'] += 1
                logger.info("✓ Step 2 completed")
                await asyncio.sleep(Config.DELAY_BETWEEN_CLICKS)
            else:
                self.state_machine.error("Step 2 click failed")
                self._metrics['failed_cycles'] += 1

        except Exception as e:
            logger.error(f"Error in step 2: {e}", exc_info=True)
            self.state_machine.error(f"Step 2 exception: {str(e)}")
            self._metrics['failed_cycles'] += 1

    async def _execute_step_3(self, message_id: int, cycle_start: float) -> None:
        """Execute Step 3: Click confirmation."""
        try:
            logger.info("=== STEP 3: Clicking confirmation ===")

            # Wait for stabilization
            stabilized = await self.stabilization_detector.wait_for_stabilization(
                message_id,
                max_wait=Config.STEP_3_TIMEOUT
            )

            if not stabilized:
                self.state_machine.error("Step 3: Message did not stabilize")
                self._metrics['failed_cycles'] += 1
                return

            # Get message data
            msg_data = self.button_cache.get_message(message_id)
            if not msg_data or not msg_data.buttons:
                self.state_machine.error("Step 3: No buttons found")
                self._metrics['failed_cycles'] += 1
                return

            # Find confirmation button
            button = self.button_analyzer.find_confirmation_button(
                msg_data.buttons,
                Config.BUTTON_3_KEYWORDS
            )

            # Fallback to first button
            if not button:
                logger.warning("⚠️ Confirmation button not found, using first button")
                button = self.button_analyzer.get_first_button(msg_data.buttons)

            if not button:
                self.state_machine.error("Step 3: No button available")
                self._metrics['failed_cycles'] += 1
                return

            logger.info(f"🎯 Target button: '{button.text}'")

            # Click button
            success = await self._click_button(message_id, button)

            if success:
                self._metrics['total_clicks'] += 1
                cycle_time = monotonic() - cycle_start
                logger.info(f"✓ Step 3 completed - Total cycle time: {cycle_time*1000:.1f}ms")

                # Update metrics
                self._metrics['successful_cycles'] += 1
                self._metrics['total_cycles'] += 1
                self._update_avg_cycle_time(cycle_time)

                await asyncio.sleep(Config.DELAY_BETWEEN_CLICKS)
            else:
                self.state_machine.error("Step 3 click failed")
                self._metrics['failed_cycles'] += 1

        except Exception as e:
            logger.error(f"Error in step 3: {e}", exc_info=True)
            self.state_machine.error(f"Step 3 exception: {str(e)}")
            self._metrics['failed_cycles'] += 1

    async def _click_button(self, message_id: int, button: ButtonInfo) -> bool:
        """
        Click button using TDLib.

        Args:
            message_id: Message ID
            button: Button to click

        Returns:
            True if successful
        """
        try:
            # Get callback data
            callback_data = button.callback_data

            # Send callback query
            result = await self.client.getCallbackQueryAnswer(
                chat_id=self.bot_chat_id,
                message_id=message_id,
                payload=types.CallbackQueryPayloadData(data=callback_data)
            )

            return result is not None

        except Exception as e:
            logger.error(f"Error clicking button: {e}", exc_info=True)
            return False

    async def _check_stabilization(self, message_id: int) -> None:
        """Check stabilization and progress to next step."""
        if not self.state_machine.is_active():
            return

        msg_data = self.button_cache.get_message(message_id)

        if msg_data and msg_data.buttons:
            current_button_texts = self.button_analyzer.get_button_texts(msg_data.buttons)

            # Check state transitions
            if self.state_machine.current_state == AutomationState.STEP_1:
                await asyncio.sleep(0.1)

                if self.state_machine.current_state != AutomationState.STEP_1:
                    return

                msg_data = self.button_cache.get_message(message_id)
                if msg_data and msg_data.buttons:
                    current_button_texts = self.button_analyzer.get_button_texts(msg_data.buttons)

                    if self.last_button_texts and current_button_texts == self.last_button_texts:
                        return

                    logger.info(f"Step 1 response detected with {len(msg_data.buttons)} buttons")
                    self.current_message_id = message_id
                    self.last_button_texts = current_button_texts
                    self.state_machine.complete_step_1(message_id)

                    if self.mode == 'list_only':
                        logger.info("Mode is 'list_only' - completing automation")
                        self.state_machine.complete_automation()
                        await asyncio.sleep(0.05)
                        self.state_machine.reset()
                    else:
                        await self._execute_step_2(message_id)

            elif self.state_machine.current_state == AutomationState.STEP_2:
                await asyncio.sleep(0.1)

                if self.state_machine.current_state != AutomationState.STEP_2:
                    return

                msg_data = self.button_cache.get_message(message_id)
                if msg_data and msg_data.buttons:
                    current_button_texts = self.button_analyzer.get_button_texts(msg_data.buttons)

                    if self.last_button_texts and current_button_texts == self.last_button_texts:
                        return

                    button_texts_lower = [text.lower() for text in current_button_texts]
                    has_confirm = any('подтверд' in text for text in button_texts_lower)

                    if has_confirm:
                        logger.info("Step 2 response detected with confirmation buttons")
                        self.current_message_id = message_id
                        self.last_button_texts = current_button_texts
                        self.state_machine.complete_step_2(message_id)
                        await self._execute_step_3(message_id, 0)  # cycle_start passed separately

            elif self.state_machine.current_state == AutomationState.STEP_3:
                await asyncio.sleep(0.1)

                if self.state_machine.current_state != AutomationState.STEP_3:
                    return

                msg_data = self.button_cache.get_message(message_id)
                if msg_data:
                    text_lower = msg_data.text.lower() if msg_data.text else ""

                    if 'успешно зарезервирована' in text_lower or 'перевозка успешно' in text_lower:
                        logger.info(f"✅ Step 3 SUCCESS: Reservation confirmed")
                        self.state_machine.complete_automation()
                        await asyncio.sleep(0.1)
                        self.state_machine.reset()
                        logger.info("🏁 Automation completed - returned to IDLE")

    async def _timeout_checker(self) -> None:
        """Check for timeouts."""
        while self.is_running:
            await asyncio.sleep(1.0)

            if self.state_machine.is_active() and self.state_machine.is_timeout_exceeded():
                timeout = self.state_machine.get_current_timeout()
                logger.error(f"Timeout in state {self.state_machine.current_state.name} (limit: {timeout}s)")
                self.state_machine.error("Timeout exceeded")
                self._metrics['failed_cycles'] += 1
                await asyncio.sleep(2.0)
                self.state_machine.reset()

    def _update_avg_cycle_time(self, cycle_time: float) -> None:
        """Update average cycle time."""
        n = self._metrics['successful_cycles']
        if n == 1:
            self._metrics['avg_cycle_time'] = cycle_time
        else:
            # Running average
            self._metrics['avg_cycle_time'] = (
                self._metrics['avg_cycle_time'] * (n - 1) + cycle_time
            ) / n

    def get_statistics(self) -> dict:
        """Get automation statistics."""
        return {
            'running': self.is_running,
            'state': self.state_machine.current_state.name,
            'metrics': self._metrics,
            'cache': self.button_cache.get_statistics(),
            'stabilization': self.stabilization_detector.get_statistics()
        }

    async def stop(self) -> None:
        """Stop the automation."""
        logger.info("Stopping TDLib automation...")
        self.is_running = False
        self.state_machine.reset()
