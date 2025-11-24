"""
Optimized Bot Automation - Telethon + Fast Modules
Оптимизированная версия с быстрыми модулями без полного переписывания на TDLib
"""

import asyncio
import logging
from typing import Optional, List
from time import monotonic

from telethon import TelegramClient
from telethon.tl.types import Message

from config import Config
from modules.fast_stabilization_detector import FastStabilizationDetector
from modules.fast_button_analyzer import FastButtonAnalyzer, ButtonInfo
from modules.fast_button_cache import FastButtonCache
from modules.state_machine import StateMachine, AutomationState

logger = logging.getLogger(__name__)


class BotAutomationFast:
    """
    Optimized bot automation using Telethon + fast modules.
    Drop-in replacement for original BotAutomation with performance improvements.
    """

    def __init__(
        self,
        client: TelegramClient,
        bot_entity,
        mode: str = 'full_cycle',
        step2_button_keywords: Optional[str] = None,
        step2_button_index: int = 0
    ):
        """Initialize optimized automation."""
        self.client = client
        self.bot_entity = bot_entity
        self.mode = mode

        # Step 2 configuration
        self.step2_button_keywords = step2_button_keywords
        self.step2_button_index = step2_button_index

        # Initialize FAST modules
        self.button_cache = FastButtonCache(max_size=Config.MAX_CACHED_MESSAGES)
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

        # Message monitor
        from modules.message_monitor import MessageMonitor
        self.message_monitor = MessageMonitor(
            client=client,
            bot_entity=bot_entity,
            button_cache=self.button_cache,
            trigger_text=Config.TRIGGER_TEXT
        )

        # CRITICAL: Replace MessageMonitor's button_analyzer with FastButtonAnalyzer
        # to ensure it uses FastButtonInfo with matches_keyword method
        self.message_monitor.button_analyzer = self.button_analyzer

        # Set up callbacks
        self.message_monitor.set_on_trigger(self._handle_trigger)
        self.message_monitor.set_on_message(self._handle_message)

        # Control flags
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

        # Click executor
        from modules.click_executor import ClickExecutor
        self.click_executor = ClickExecutor(
            client=client,
            bot_entity=bot_entity,
            max_retries=Config.MAX_RETRIES,
            retry_delay=Config.RETRY_DELAY
        )

    async def start(self) -> None:
        """Start the automation system."""
        logger.info("Starting FAST bot automation...")
        Config.display()

        # Register message handlers
        self.message_monitor.register_handlers()

        # Initialize cache with recent messages
        await self._initialize_cache()

        self.is_running = True
        logger.info("✓ FAST automation started. Waiting for triggers...")

        # Start timeout checker
        asyncio.create_task(self._timeout_checker())

    async def _initialize_cache(self) -> None:
        """Initialize cache by fetching recent messages from bot."""
        try:
            logger.info("Initializing cache with recent messages...")

            # Clear any old cache to avoid ButtonInfo conflicts
            self.button_cache.clear()

            # Fetch last 10 messages from bot
            messages = await self.client.get_messages(
                self.bot_entity,
                limit=10
            )

            if not messages:
                logger.warning("No messages found in chat history")
                return

            # Process messages in reverse order (oldest first)
            processed = 0
            for message in reversed(messages):
                if message.reply_markup and message.reply_markup.rows:
                    # Extract buttons using FAST analyzer (FastButtonInfo)
                    buttons = self._extract_buttons_from_telethon(message)
                    if buttons:
                        self.button_cache.update_message(
                            message.id,
                            message.chat_id,
                            message.text or "",
                            buttons
                        )
                        processed += 1

            logger.info(f"✓ Cache initialized with {processed} messages")

        except Exception as e:
            logger.error(f"Error initializing cache: {e}", exc_info=True)

    def _extract_buttons_from_telethon(self, message: Message) -> List[ButtonInfo]:
        """Extract buttons from Telethon message using fast analyzer."""
        buttons = []

        if not hasattr(message, 'reply_markup') or not message.reply_markup:
            return buttons

        reply_markup = message.reply_markup

        # Extract buttons from each row - using FastButtonInfo!
        for row_idx, row in enumerate(reply_markup.rows):
            for col_idx, button in enumerate(row.buttons):
                # Extract button data
                button_text = getattr(button, 'text', '')
                callback_data = getattr(button, 'data', b'')

                if button_text:
                    # Use FastButtonInfo with pre-computed lowercase
                    from modules.fast_button_analyzer import ButtonInfo as FastButtonInfo
                    button_info = FastButtonInfo(
                        text=button_text,
                        callback_data=callback_data,
                        row=row_idx,
                        column=col_idx
                    )
                    buttons.append(button_info)

        return buttons

    def _handle_trigger(self, message: Message) -> None:
        """Handle trigger message detection."""
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

        # Record edit for stabilization tracking
        self.stabilization_detector.record_edit(message.id)

        # Schedule step 1 execution
        asyncio.create_task(self._execute_step_1(message.id, cycle_start))

    def _handle_message(self, message: Message, is_edit: bool) -> None:
        """Handle any message or edit."""
        # Record edit for stabilization tracking
        if is_edit:
            self.stabilization_detector.record_edit(message.id)
            logger.debug(f"Message edit detected: {message.id}")

            # If we're waiting on this message, check if we should proceed
            if self.state_machine.is_active():
                asyncio.create_task(self._check_stabilization(message.id))

    async def _execute_step_1(self, message_id: int, cycle_start: float) -> None:
        """Execute Step 1: Click "Список прямых перевозок"."""
        try:
            logger.info("=== STEP 1: Clicking 'Список прямых перевозок' ===")

            # Wait for trigger delay
            if Config.DELAY_AFTER_TRIGGER > 0:
                await asyncio.sleep(Config.DELAY_AFTER_TRIGGER)

            # Wait for stabilization using FAST detector
            logger.debug("Waiting for message stabilization...")
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

            # If trigger message has no buttons, find the latest menu with buttons
            if not msg_data or not msg_data.buttons:
                logger.info("Trigger message has no buttons, searching for latest menu in chat history...")

                # Get recent messages to find the latest menu
                try:
                    recent_messages = await self.client.get_messages(
                        self.bot_entity,
                        limit=20  # Look at last 20 messages
                    )

                    # Find the most recent message with the target button
                    menu_message = None
                    for msg in recent_messages:
                        if msg.reply_markup and msg.reply_markup.rows:
                            buttons = self._extract_buttons_from_telethon(msg)
                            if buttons:
                                # Check if this message has the button we need
                                target_button = self.button_analyzer.find_button_by_keywords(
                                    buttons,
                                    Config.BUTTON_1_KEYWORDS
                                )
                                if target_button:
                                    menu_message = msg
                                    msg_data = self.button_cache.get_message(msg.id)
                                    if not msg_data:
                                        # Add to cache if not there
                                        self.button_cache.update_message(
                                            msg.id,
                                            msg.chat_id,
                                            msg.text or "",
                                            buttons
                                        )
                                        msg_data = self.button_cache.get_message(msg.id)
                                    break

                    if menu_message and msg_data:
                        logger.info(f"✓ Found menu in message {menu_message.id} with {len(msg_data.buttons)} buttons")
                        message_id = menu_message.id
                        self.last_button_texts = self.button_analyzer.get_button_texts(msg_data.buttons)
                    else:
                        self.state_machine.error("Step 1: No menu with target button found in history")
                        self._metrics['failed_cycles'] += 1
                        return

                except Exception as e:
                    logger.error(f"Error searching for menu: {e}", exc_info=True)
                    self.state_machine.error(f"Step 1: Error finding menu - {e}")
                    self._metrics['failed_cycles'] += 1
                    return

            # Find target button using FAST analyzer
            logger.info(f"🔍 Step 1: Searching for button with keywords: {Config.BUTTON_1_KEYWORDS}")
            button = self.button_analyzer.find_button_by_keywords(
                msg_data.buttons,
                Config.BUTTON_1_KEYWORDS
            )

            # Fallback to first button
            if not button:
                logger.warning("⚠️ Button 1 not found by keywords, using first button")
                button = self.button_analyzer.get_first_button(msg_data.buttons)

            if not button:
                self.state_machine.error("Step 1: No button available")
                self._metrics['failed_cycles'] += 1
                return

            logger.info(f"🎯 Target button: '{button.text}' at [{button.row},{button.column}]")

            # Click button
            result = await self.click_executor.click_button_info(message_id, button)

            if result.success:
                self._metrics['total_clicks'] += 1
                logger.info(f"✓ Step 1 completed in {result.execution_time*1000:.1f}ms")
                await asyncio.sleep(Config.DELAY_BETWEEN_CLICKS)
            else:
                self.state_machine.error(f"Step 1 click failed: {result.message}")
                self._metrics['failed_cycles'] += 1

        except Exception as e:
            logger.error(f"Error in step 1: {e}", exc_info=True)
            self.state_machine.error(f"Step 1 exception: {str(e)}")
            self._metrics['failed_cycles'] += 1

    async def _execute_step_2(self, message_id: int) -> None:
        """Execute Step 2: Click first transport in list."""
        try:
            logger.info("=== STEP 2: Clicking first transport ===")

            # Get message data (already called after buttons detected, no need to wait)
            msg_data = self.button_cache.get_message(message_id)
            if not msg_data or not msg_data.buttons:
                self.state_machine.error("Step 2: No buttons found")
                self._metrics['failed_cycles'] += 1
                return

            # Find button using configured method
            button = None

            # Try keywords first if configured
            if self.step2_button_keywords:
                keywords = [k.strip() for k in self.step2_button_keywords.split(',') if k.strip()]
                if keywords:
                    button = self.button_analyzer.find_button_by_keywords(msg_data.buttons, keywords)

            # Fallback to index-based selection
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
            result = await self.click_executor.click_button_info(message_id, button)

            if result.success:
                self._metrics['total_clicks'] += 1
                logger.info(f"✓ Step 2 completed in {result.execution_time*1000:.1f}ms")
                await asyncio.sleep(Config.DELAY_BETWEEN_CLICKS)
            else:
                self.state_machine.error(f"Step 2 click failed: {result.message}")
                self._metrics['failed_cycles'] += 1

        except Exception as e:
            logger.error(f"Error in step 2: {e}", exc_info=True)
            self.state_machine.error(f"Step 2 exception: {str(e)}")
            self._metrics['failed_cycles'] += 1

    async def _execute_step_3(self, message_id: int, cycle_start: float) -> None:
        """Execute Step 3: Click confirmation button."""
        try:
            logger.info("=== STEP 3: Clicking confirmation ===")

            # Get message data (already called after buttons detected, no need to wait)
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
            result = await self.click_executor.click_button_info(message_id, button)

            if result.success:
                self._metrics['total_clicks'] += 1
                cycle_time = monotonic() - cycle_start
                logger.info(f"✓ Step 3 completed - Total cycle time: {cycle_time*1000:.1f}ms")

                # Update metrics
                self._metrics['successful_cycles'] += 1
                self._metrics['total_cycles'] += 1
                self._update_avg_cycle_time(cycle_time)

                await asyncio.sleep(Config.DELAY_BETWEEN_CLICKS)
            else:
                self.state_machine.error(f"Step 3 click failed: {result.message}")
                self._metrics['failed_cycles'] += 1

        except Exception as e:
            logger.error(f"Error in step 3: {e}", exc_info=True)
            self.state_machine.error(f"Step 3 exception: {str(e)}")
            self._metrics['failed_cycles'] += 1

    async def _check_stabilization(self, message_id: int) -> None:
        """Check if message has stabilized and proceed to next step."""
        # Only proceed if we're in an active state
        if not self.state_machine.is_active():
            return

        # Get message data
        msg_data = self.button_cache.get_message(message_id)

        # Check if this message has buttons (response to our click)
        if msg_data and msg_data.buttons:
            # For STEP_1: Accept message with buttons (list response)
            if self.state_machine.current_state == AutomationState.STEP_1:
                await asyncio.sleep(0.02)  # 20ms debounce

                if self.state_machine.current_state != AutomationState.STEP_1:
                    return

                msg_data = self.button_cache.get_message(message_id)
                if msg_data and msg_data.buttons:
                    current_button_texts = self.button_analyzer.get_button_texts(msg_data.buttons)

                    if self.last_button_texts and current_button_texts == self.last_button_texts:
                        return

                    logger.info(f"Step 1 response detected in message {message_id} with {len(msg_data.buttons)} buttons")
                    self.current_message_id = message_id
                    self.last_button_texts = current_button_texts
                    self.state_machine.complete_step_1(message_id)

                    if self.mode == 'list_only':
                        logger.info("Mode is 'list_only' - completing automation after Step 1")
                        self.state_machine.complete_automation()
                        await asyncio.sleep(0.05)
                        self.state_machine.reset()
                    else:
                        await self._execute_step_2(message_id)

            # For STEP_2: Accept same message with confirmation buttons
            elif self.state_machine.current_state == AutomationState.STEP_2:
                await asyncio.sleep(0.02)  # 20ms debounce

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
                        logger.info(f"Step 2 response detected in message {message_id} with confirmation buttons")
                        self.current_message_id = message_id
                        self.last_button_texts = current_button_texts
                        self.state_machine.complete_step_2(message_id)
                        await self._execute_step_3(message_id, 0)

            # For STEP_3: Check for reservation success message
            elif self.state_machine.current_state == AutomationState.STEP_3:
                await asyncio.sleep(0.02)  # 20ms debounce

                if self.state_machine.current_state != AutomationState.STEP_3:
                    return

                msg_data = self.button_cache.get_message(message_id)
                if msg_data:
                    text_lower = msg_data.text.lower() if msg_data.text else ""

                    if 'успешно зарезервирована' in text_lower or 'перевозка успешно' in text_lower:
                        logger.info(f"✅ Step 3 SUCCESS: Reservation confirmed in message {message_id}")
                        self.state_machine.complete_automation()
                        await asyncio.sleep(0.1)
                        self.state_machine.reset()
                        logger.info("🏁 Automation completed successfully - returned to IDLE")

    async def _timeout_checker(self) -> None:
        """Periodically check for state timeouts."""
        while self.is_running:
            await asyncio.sleep(1.0)

            if self.state_machine.is_active() and self.state_machine.is_timeout_exceeded():
                timeout = self.state_machine.get_current_timeout()
                logger.error(
                    f"Timeout exceeded in state {self.state_machine.current_state.name} "
                    f"(limit: {timeout}s)"
                )
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

    def get_status(self) -> dict:
        """Get current automation status."""
        return {
            'running': self.is_running,
            'state_machine': self.state_machine.get_statistics(),
            'message_monitor': self.message_monitor.get_statistics(),
            'click_executor': self.click_executor.get_statistics(),
            'stabilization_detector': self.stabilization_detector.get_statistics(),
            'metrics': self._metrics,
            'cache': self.button_cache.get_statistics()
        }

    def print_status(self) -> None:
        """Print current status to console."""
        status = self.get_status()

        print("\n" + "="*60)
        print("FAST AUTOMATION STATUS")
        print("="*60)

        print(f"\nRunning: {'Yes' if status['running'] else 'No'}")
        print(f"State: {status['state_machine']['current_state']}")

        print(f"\nPerformance Metrics:")
        for key, value in status['metrics'].items():
            print(f"  {key}: {value}")

        print(f"\nCache Statistics:")
        for key, value in status['cache'].items():
            print(f"  {key}: {value}")

        print("="*60 + "\n")

    async def stop(self) -> None:
        """Stop the automation system."""
        logger.info("Stopping FAST automation...")
        self.is_running = False
        self.state_machine.reset()
