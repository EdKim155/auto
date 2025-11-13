"""
Main Bot Automation Class
Orchestrates all modules to implement the complete automation workflow.
"""

import logging
import asyncio
from typing import Optional
from telethon import TelegramClient
from telethon.tl.types import Message

from config import Config
from modules import (
    ButtonCache,
    MessageMonitor,
    ButtonAnalyzer,
    StabilizationDetector,
    ClickExecutor,
    StateMachine,
    AutomationState
)


logger = logging.getLogger(__name__)


class BotAutomation:
    """
    Main automation orchestrator.
    Implements the complete automation workflow from TZ Section 5.
    """

    def __init__(self, client: TelegramClient, bot_entity):
        """
        Initialize bot automation.

        Args:
            client: Telethon client
            bot_entity: Target bot entity
        """
        self.client = client
        self.bot_entity = bot_entity

        # Initialize all modules
        self.button_cache = ButtonCache(max_messages=Config.MAX_CACHED_MESSAGES)
        self.button_analyzer = ButtonAnalyzer()
        self.stabilization_detector = StabilizationDetector(
            threshold=Config.STABILIZATION_THRESHOLD,
            strategy=Config.STABILIZATION_STRATEGY
        )
        self.click_executor = ClickExecutor(
            client=client,
            bot_entity=bot_entity,
            max_retries=Config.MAX_RETRIES,
            retry_delay=Config.RETRY_DELAY
        )
        self.state_machine = StateMachine(
            step_1_timeout=Config.STEP_1_TIMEOUT,
            step_2_timeout=Config.STEP_2_TIMEOUT,
            step_3_timeout=Config.STEP_3_TIMEOUT
        )
        self.message_monitor = MessageMonitor(
            client=client,
            bot_entity=bot_entity,
            button_cache=self.button_cache,
            trigger_text=Config.TRIGGER_TEXT
        )

        # Set up callbacks
        self.message_monitor.set_on_trigger(self._handle_trigger)
        self.message_monitor.set_on_message(self._handle_message)

        # Control flags
        self.is_running = False
        self.current_message_id: Optional[int] = None

    async def start(self) -> None:
        """Start the automation system."""
        logger.info("Starting bot automation...")
        Config.display()

        # Register message handlers
        self.message_monitor.register_handlers()

        self.is_running = True
        logger.info("✓ Bot automation started. Waiting for triggers...")

        # Start timeout checker
        asyncio.create_task(self._timeout_checker())

    async def stop(self) -> None:
        """Stop the automation system."""
        logger.info("Stopping bot automation...")
        self.is_running = False
        self.state_machine.reset()

    def _handle_trigger(self, message: Message) -> None:
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

        # Start automation
        self.state_machine.start_automation(message.id)
        self.current_message_id = message.id

        # Record edit for stabilization tracking
        self.stabilization_detector.record_edit(message.id)

        # Schedule step 1 execution
        asyncio.create_task(self._execute_step_1(message.id))

    def _handle_message(self, message: Message, is_edit: bool) -> None:
        """
        Handle any message or edit.

        Args:
            message: Message object
            is_edit: True if this is an edit
        """
        # Record edit for stabilization tracking
        if is_edit:
            self.stabilization_detector.record_edit(message.id)

            # If we're waiting on this message, check if we should proceed
            if self.state_machine.is_active() and message.id == self.current_message_id:
                asyncio.create_task(self._check_stabilization(message.id))

    async def _execute_step_1(self, message_id: int) -> None:
        """
        Execute Step 1: Click "Список прямых перевозок".

        Args:
            message_id: Trigger message ID
        """
        try:
            logger.info("=== STEP 1: Clicking 'Список прямых перевозок' ===")

            # Wait for trigger delay
            if Config.DELAY_AFTER_TRIGGER > 0:
                await asyncio.sleep(Config.DELAY_AFTER_TRIGGER)

            # Wait for stabilization
            logger.debug("Waiting for message stabilization...")
            stabilized = await self.stabilization_detector.wait_for_stabilization(
                message_id,
                max_wait=Config.STEP_1_TIMEOUT
            )

            if not stabilized:
                self.state_machine.error("Step 1: Message did not stabilize")
                return

            # Get message data
            msg_data = self.button_cache.get_message(message_id)
            if not msg_data or not msg_data.buttons:
                self.state_machine.error("Step 1: No buttons found")
                return

            # Find target button
            button = self.button_analyzer.find_button_by_keywords(
                msg_data.buttons,
                Config.BUTTON_1_KEYWORDS
            )

            # Fallback to first button
            if not button:
                logger.warning("Button 1 not found by keywords, using first button")
                button = self.button_analyzer.get_first_button(msg_data.buttons)

            if not button:
                self.state_machine.error("Step 1: No button available")
                return

            logger.info(f"Target button: '{button.text}' at [{button.row},{button.column}]")

            # Click button
            result = await self.click_executor.click_button_info(message_id, button)

            if result.success:
                logger.info(f"✓ Step 1 completed in {result.execution_time*1000:.1f}ms")
                # Wait for response and move to step 2
                await asyncio.sleep(Config.DELAY_BETWEEN_CLICKS)
                # We'll transition to STEP_2 when we detect the new message
            else:
                self.state_machine.error(f"Step 1 click failed: {result.message}")

        except Exception as e:
            logger.error(f"Error in step 1: {e}", exc_info=True)
            self.state_machine.error(f"Step 1 exception: {str(e)}")

    async def _execute_step_2(self, message_id: int) -> None:
        """
        Execute Step 2: Click first transport in list.

        Args:
            message_id: List message ID
        """
        try:
            logger.info("=== STEP 2: Clicking first transport ===")

            # Wait for stabilization
            logger.debug("Waiting for message stabilization...")
            stabilized = await self.stabilization_detector.wait_for_stabilization(
                message_id,
                max_wait=Config.STEP_2_TIMEOUT
            )

            if not stabilized:
                self.state_machine.error("Step 2: Message did not stabilize")
                return

            # Get message data
            msg_data = self.button_cache.get_message(message_id)
            if not msg_data or not msg_data.buttons:
                self.state_machine.error("Step 2: No buttons found")
                return

            # Get first button (first transport in list)
            button = self.button_analyzer.get_first_button(msg_data.buttons)

            if not button:
                self.state_machine.error("Step 2: No button available")
                return

            logger.info(f"Target button: '{button.text}' at [{button.row},{button.column}]")

            # Click button
            result = await self.click_executor.click_button_info(message_id, button)

            if result.success:
                logger.info(f"✓ Step 2 completed in {result.execution_time*1000:.1f}ms")
                # Wait for response and move to step 3
                await asyncio.sleep(Config.DELAY_BETWEEN_CLICKS)
                # We'll transition to STEP_3 when we detect the new message
            else:
                self.state_machine.error(f"Step 2 click failed: {result.message}")

        except Exception as e:
            logger.error(f"Error in step 2: {e}", exc_info=True)
            self.state_machine.error(f"Step 2 exception: {str(e)}")

    async def _execute_step_3(self, message_id: int) -> None:
        """
        Execute Step 3: Click confirmation button.

        Args:
            message_id: Details message ID
        """
        try:
            logger.info("=== STEP 3: Clicking confirmation ===")

            # Wait for stabilization
            logger.debug("Waiting for message stabilization...")
            stabilized = await self.stabilization_detector.wait_for_stabilization(
                message_id,
                max_wait=Config.STEP_3_TIMEOUT
            )

            if not stabilized:
                self.state_machine.error("Step 3: Message did not stabilize")
                return

            # Get message data
            msg_data = self.button_cache.get_message(message_id)
            if not msg_data or not msg_data.buttons:
                self.state_machine.error("Step 3: No buttons found")
                return

            # Find confirmation button
            button = self.button_analyzer.find_confirmation_button(
                msg_data.buttons,
                Config.BUTTON_3_KEYWORDS
            )

            # Fallback to first button
            if not button:
                logger.warning("Confirmation button not found by keywords, using first button")
                button = self.button_analyzer.get_first_button(msg_data.buttons)

            if not button:
                self.state_machine.error("Step 3: No button available")
                return

            logger.info(f"Target button: '{button.text}' at [{button.row},{button.column}]")

            # Click button
            result = await self.click_executor.click_button_info(message_id, button)

            if result.success:
                logger.info(f"✓ Step 3 completed in {result.execution_time*1000:.1f}ms")
                # Complete automation
                self.state_machine.complete_automation()
                await asyncio.sleep(1.0)  # Wait before returning to idle
                self.state_machine.reset()
            else:
                self.state_machine.error(f"Step 3 click failed: {result.message}")

        except Exception as e:
            logger.error(f"Error in step 3: {e}", exc_info=True)
            self.state_machine.error(f"Step 3 exception: {str(e)}")

    async def _check_stabilization(self, message_id: int) -> None:
        """
        Check if message has stabilized and proceed to next step.

        Args:
            message_id: Message ID to check
        """
        # Only proceed if we're in an active state
        if not self.state_machine.is_active():
            return

        # Check if this is a new message (potential next step)
        if message_id != self.current_message_id:
            # New message received - might be response to our click
            msg_data = self.button_cache.get_message(message_id)

            if msg_data and msg_data.buttons:
                # Update current message and proceed to next step
                self.current_message_id = message_id
                self.stabilization_detector.record_edit(message_id)

                # Determine which step to execute based on current state
                if self.state_machine.current_state == AutomationState.STEP_1:
                    self.state_machine.complete_step_1(message_id)
                    await self._execute_step_2(message_id)
                elif self.state_machine.current_state == AutomationState.STEP_2:
                    self.state_machine.complete_step_2(message_id)
                    await self._execute_step_3(message_id)

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
                await asyncio.sleep(2.0)
                self.state_machine.reset()

    def get_status(self) -> dict:
        """
        Get current automation status.

        Returns:
            Dictionary with status information
        """
        return {
            'running': self.is_running,
            'state_machine': self.state_machine.get_statistics(),
            'message_monitor': self.message_monitor.get_statistics(),
            'click_executor': self.click_executor.get_statistics(),
            'stabilization_detector': self.stabilization_detector.get_statistics(),
        }

    def print_status(self) -> None:
        """Print current status to console."""
        status = self.get_status()

        print("\n" + "="*60)
        print("AUTOMATION STATUS")
        print("="*60)

        print(f"\nRunning: {'Yes' if status['running'] else 'No'}")

        print(f"\nState Machine:")
        for key, value in status['state_machine'].items():
            print(f"  {key}: {value}")

        print(f"\nMessage Monitor:")
        for key, value in status['message_monitor'].items():
            print(f"  {key}: {value}")

        print(f"\nClick Executor:")
        for key, value in status['click_executor'].items():
            print(f"  {key}: {value}")

        print(f"\nStabilization Detector:")
        for key, value in status['stabilization_detector'].items():
            print(f"  {key}: {value}")

        print("="*60 + "\n")
