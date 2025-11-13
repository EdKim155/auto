"""
Stabilization Detector Module (FR-3.x)
Detects when a message has stopped being edited.
"""

import logging
import asyncio
from datetime import datetime, timedelta
from typing import Dict, Optional, List
from dataclasses import dataclass, field


logger = logging.getLogger(__name__)


@dataclass
class EditHistory:
    """History of message edits for pattern analysis."""
    message_id: int
    edit_times: List[datetime] = field(default_factory=list)
    last_edit: Optional[datetime] = None

    def add_edit(self, timestamp: Optional[datetime] = None) -> None:
        """Add an edit timestamp."""
        if timestamp is None:
            timestamp = datetime.now()

        self.edit_times.append(timestamp)
        self.last_edit = timestamp

        # Keep only recent history (last 20 edits)
        if len(self.edit_times) > 20:
            self.edit_times = self.edit_times[-20:]

    def get_edit_frequency(self, time_window: float = 1.0) -> float:
        """
        Calculate edit frequency over time window.

        Args:
            time_window: Time window in seconds

        Returns:
            Edits per second
        """
        if not self.edit_times:
            return 0.0

        now = datetime.now()
        cutoff = now - timedelta(seconds=time_window)

        recent_edits = [t for t in self.edit_times if t >= cutoff]
        return len(recent_edits) / time_window

    def get_average_interval(self) -> float:
        """
        Get average time between edits.

        Returns:
            Average interval in seconds
        """
        if len(self.edit_times) < 2:
            return 0.0

        intervals = []
        for i in range(1, len(self.edit_times)):
            delta = (self.edit_times[i] - self.edit_times[i-1]).total_seconds()
            intervals.append(delta)

        return sum(intervals) / len(intervals) if intervals else 0.0


class StabilizationDetector:
    """
    Detects when messages have stabilized (stopped being edited).
    Implements FR-3.x requirements.
    """

    def __init__(self, threshold: float = 0.15, strategy: str = 'wait'):
        """
        Initialize stabilization detector.

        Args:
            threshold: Stabilization threshold in seconds (default 150ms)
            strategy: Detection strategy ('wait', 'predict', 'aggressive')
        """
        self.threshold = threshold
        self.strategy = strategy
        self.edit_histories: Dict[int, EditHistory] = {}

    def record_edit(self, message_id: int, timestamp: Optional[datetime] = None) -> None:
        """
        Record a message edit (FR-3.1).

        Args:
            message_id: Message ID
            timestamp: Edit timestamp (default: now)
        """
        if message_id not in self.edit_histories:
            self.edit_histories[message_id] = EditHistory(message_id=message_id)

        self.edit_histories[message_id].add_edit(timestamp)

    def is_stabilized(self, message_id: int) -> bool:
        """
        Check if message has stabilized (FR-3.1).

        Args:
            message_id: Message ID to check

        Returns:
            True if stabilized, False otherwise
        """
        history = self.edit_histories.get(message_id)
        if not history or not history.last_edit:
            return False

        time_since_last_edit = (datetime.now() - history.last_edit).total_seconds()

        if self.strategy == 'wait':
            # Simple time-based strategy (FR-3.2)
            return time_since_last_edit >= self.threshold

        elif self.strategy == 'predict':
            # Pattern-based prediction
            return self._predict_stabilization(history)

        elif self.strategy == 'aggressive':
            # Very short threshold for aggressive clicking
            return time_since_last_edit >= (self.threshold * 0.5)

        return False

    def get_stabilization_probability(self, message_id: int) -> float:
        """
        Get probability that message has stabilized (0-1).

        Args:
            message_id: Message ID

        Returns:
            Probability of stabilization
        """
        history = self.edit_histories.get(message_id)
        if not history or not history.last_edit:
            return 0.0

        time_since_last_edit = (datetime.now() - history.last_edit).total_seconds()

        # Simple linear probability based on time
        if time_since_last_edit >= self.threshold:
            return 1.0

        return min(1.0, time_since_last_edit / self.threshold)

    async def wait_for_stabilization(self, message_id: int,
                                     max_wait: float = 5.0,
                                     check_interval: float = 0.01) -> bool:
        """
        Wait for message to stabilize (FR-3.2).

        Args:
            message_id: Message ID to wait for
            max_wait: Maximum wait time in seconds
            check_interval: Check interval in seconds (default 10ms)

        Returns:
            True if stabilized within max_wait, False if timeout
        """
        start_time = datetime.now()

        while (datetime.now() - start_time).total_seconds() < max_wait:
            if self.is_stabilized(message_id):
                wait_time = (datetime.now() - start_time).total_seconds()
                logger.debug(f"Message {message_id} stabilized after {wait_time*1000:.1f}ms")
                return True

            await asyncio.sleep(check_interval)

        logger.warning(f"Message {message_id} did not stabilize within {max_wait}s")
        return False

    def get_time_since_last_edit(self, message_id: int) -> Optional[float]:
        """
        Get time since last edit in seconds.

        Args:
            message_id: Message ID

        Returns:
            Time in seconds or None if no edits recorded
        """
        history = self.edit_histories.get(message_id)
        if not history or not history.last_edit:
            return None

        return (datetime.now() - history.last_edit).total_seconds()

    def get_edit_frequency(self, message_id: int, time_window: float = 1.0) -> float:
        """
        Get edit frequency for message.

        Args:
            message_id: Message ID
            time_window: Time window in seconds

        Returns:
            Edits per second
        """
        history = self.edit_histories.get(message_id)
        if not history:
            return 0.0

        return history.get_edit_frequency(time_window)

    def clear_history(self, message_id: Optional[int] = None) -> None:
        """
        Clear edit history.

        Args:
            message_id: Specific message ID to clear, or None for all
        """
        if message_id is not None:
            if message_id in self.edit_histories:
                del self.edit_histories[message_id]
        else:
            self.edit_histories.clear()

    def _predict_stabilization(self, history: EditHistory) -> bool:
        """
        Predict stabilization based on edit patterns.

        Args:
            history: Edit history for message

        Returns:
            True if predicted to be stabilized
        """
        if not history.last_edit:
            return False

        time_since_last = (datetime.now() - history.last_edit).total_seconds()

        # Must have at least threshold time passed
        if time_since_last < self.threshold:
            return False

        # Check edit frequency - if slowing down, likely stabilized
        recent_frequency = history.get_edit_frequency(time_window=1.0)

        # If frequency dropped to near zero, likely stabilized
        if recent_frequency < 0.5:  # Less than 0.5 edits/second
            return True

        # Check average interval - if current gap is much longer, likely stabilized
        avg_interval = history.get_average_interval()
        if avg_interval > 0 and time_since_last > (avg_interval * 2):
            return True

        return False

    def get_statistics(self) -> dict:
        """
        Get detector statistics.

        Returns:
            Dictionary with statistics
        """
        total_messages = len(self.edit_histories)
        total_edits = sum(len(h.edit_times) for h in self.edit_histories.values())

        stabilized_count = sum(
            1 for msg_id in self.edit_histories.keys()
            if self.is_stabilized(msg_id)
        )

        return {
            'tracked_messages': total_messages,
            'total_edits': total_edits,
            'stabilized_messages': stabilized_count,
            'strategy': self.strategy,
            'threshold_ms': self.threshold * 1000,
        }
