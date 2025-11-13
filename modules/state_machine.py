"""
State Machine Module
Manages the automation workflow through different states.
"""

import logging
from enum import Enum, auto
from datetime import datetime
from typing import Optional, Dict, Any


logger = logging.getLogger(__name__)


class AutomationState(Enum):
    """States of the automation process."""
    IDLE = auto()           # Waiting for trigger
    STEP_1 = auto()        # Clicking "Список прямых перевозок"
    STEP_2 = auto()        # Clicking first transport in list
    STEP_3 = auto()        # Clicking confirmation button
    COMPLETED = auto()     # Successfully completed
    ERROR = auto()         # Error occurred


class StateMachine:
    """
    Manages state transitions for the automation workflow.
    Implements the main automation algorithm from TZ.
    """

    def __init__(self, step_1_timeout: float = 5.0,
                 step_2_timeout: float = 5.0,
                 step_3_timeout: float = 5.0):
        """
        Initialize state machine.

        Args:
            step_1_timeout: Timeout for step 1 in seconds
            step_2_timeout: Timeout for step 2 in seconds
            step_3_timeout: Timeout for step 3 in seconds
        """
        self.current_state = AutomationState.IDLE
        self.previous_state: Optional[AutomationState] = None

        # Timeouts
        self.step_1_timeout = step_1_timeout
        self.step_2_timeout = step_2_timeout
        self.step_3_timeout = step_3_timeout

        # State tracking
        self.state_entered_at: Optional[datetime] = None
        self.trigger_message_id: Optional[int] = None
        self.step_1_message_id: Optional[int] = None
        self.step_2_message_id: Optional[int] = None

        # Statistics
        self.total_runs = 0
        self.successful_runs = 0
        self.failed_runs = 0
        self.state_history: list = []

    def transition_to(self, new_state: AutomationState,
                     reason: str = "", **context) -> None:
        """
        Transition to a new state.

        Args:
            new_state: State to transition to
            reason: Reason for transition
            **context: Additional context data
        """
        old_state = self.current_state
        self.previous_state = old_state
        self.current_state = new_state
        self.state_entered_at = datetime.now()

        # Update context
        for key, value in context.items():
            setattr(self, key, value)

        # Log transition
        logger.info(f"State: {old_state.name} -> {new_state.name} ({reason})")

        # Track history
        self.state_history.append({
            'from': old_state,
            'to': new_state,
            'timestamp': self.state_entered_at,
            'reason': reason,
            'context': context
        })

        # Handle special transitions
        if new_state == AutomationState.IDLE:
            self._reset_context()
        elif new_state == AutomationState.COMPLETED:
            self.successful_runs += 1
            self._log_completion()
        elif new_state == AutomationState.ERROR:
            self.failed_runs += 1

    def reset(self) -> None:
        """Reset state machine to IDLE."""
        self.transition_to(AutomationState.IDLE, "Manual reset")

    def is_idle(self) -> bool:
        """Check if state machine is idle."""
        return self.current_state == AutomationState.IDLE

    def is_active(self) -> bool:
        """Check if automation is actively running."""
        return self.current_state in [
            AutomationState.STEP_1,
            AutomationState.STEP_2,
            AutomationState.STEP_3
        ]

    def is_completed(self) -> bool:
        """Check if automation completed successfully."""
        return self.current_state == AutomationState.COMPLETED

    def is_error(self) -> bool:
        """Check if automation is in error state."""
        return self.current_state == AutomationState.ERROR

    def get_current_timeout(self) -> float:
        """
        Get timeout for current state.

        Returns:
            Timeout in seconds
        """
        timeout_map = {
            AutomationState.STEP_1: self.step_1_timeout,
            AutomationState.STEP_2: self.step_2_timeout,
            AutomationState.STEP_3: self.step_3_timeout,
        }
        return timeout_map.get(self.current_state, 0.0)

    def is_timeout_exceeded(self) -> bool:
        """
        Check if current state has exceeded its timeout.

        Returns:
            True if timeout exceeded
        """
        if not self.state_entered_at or not self.is_active():
            return False

        elapsed = (datetime.now() - self.state_entered_at).total_seconds()
        timeout = self.get_current_timeout()

        return elapsed > timeout

    def get_elapsed_time(self) -> float:
        """
        Get elapsed time in current state.

        Returns:
            Elapsed time in seconds
        """
        if not self.state_entered_at:
            return 0.0

        return (datetime.now() - self.state_entered_at).total_seconds()

    def start_automation(self, trigger_message_id: int) -> None:
        """
        Start automation from trigger.

        Args:
            trigger_message_id: ID of trigger message
        """
        self.total_runs += 1
        self.transition_to(
            AutomationState.STEP_1,
            "Trigger detected",
            trigger_message_id=trigger_message_id
        )

    def complete_step_1(self, step_1_message_id: int) -> None:
        """
        Complete step 1 and move to step 2.

        Args:
            step_1_message_id: Message ID for step 1 response
        """
        self.transition_to(
            AutomationState.STEP_2,
            "Step 1 completed",
            step_1_message_id=step_1_message_id
        )

    def complete_step_2(self, step_2_message_id: int) -> None:
        """
        Complete step 2 and move to step 3.

        Args:
            step_2_message_id: Message ID for step 2 response
        """
        self.transition_to(
            AutomationState.STEP_3,
            "Step 2 completed",
            step_2_message_id=step_2_message_id
        )

    def complete_automation(self) -> None:
        """Mark automation as completed."""
        self.transition_to(AutomationState.COMPLETED, "All steps completed")

    def error(self, reason: str) -> None:
        """
        Transition to error state.

        Args:
            reason: Error reason
        """
        self.transition_to(AutomationState.ERROR, f"Error: {reason}")

    def get_statistics(self) -> Dict[str, Any]:
        """
        Get state machine statistics.

        Returns:
            Dictionary with statistics
        """
        success_rate = (
            (self.successful_runs / self.total_runs * 100)
            if self.total_runs > 0 else 0.0
        )

        return {
            'current_state': self.current_state.name,
            'total_runs': self.total_runs,
            'successful_runs': self.successful_runs,
            'failed_runs': self.failed_runs,
            'success_rate': round(success_rate, 2),
            'elapsed_time_current_state': round(self.get_elapsed_time(), 3),
        }

    def get_state_history(self, limit: int = 10) -> list:
        """
        Get recent state transition history.

        Args:
            limit: Maximum number of entries to return

        Returns:
            List of state transitions
        """
        return self.state_history[-limit:]

    def _reset_context(self) -> None:
        """Reset context variables."""
        self.trigger_message_id = None
        self.step_1_message_id = None
        self.step_2_message_id = None

    def _log_completion(self) -> None:
        """Log successful completion details."""
        if not self.state_history:
            return

        # Calculate total time from STEP_1 to COMPLETED
        step_1_entry = None
        completed_entry = None

        for entry in reversed(self.state_history):
            if entry['to'] == AutomationState.COMPLETED and not completed_entry:
                completed_entry = entry
            if entry['to'] == AutomationState.STEP_1 and not step_1_entry:
                step_1_entry = entry

        if step_1_entry and completed_entry:
            total_time = (
                completed_entry['timestamp'] - step_1_entry['timestamp']
            ).total_seconds()

            logger.info(
                f"✓ Automation completed successfully in {total_time*1000:.1f}ms "
                f"(Success rate: {self.successful_runs}/{self.total_runs})"
            )

    def __repr__(self) -> str:
        return f"StateMachine({self.current_state.name})"
