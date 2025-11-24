"""
Fast Stabilization Detector - Optimized for maximum speed
Uses monotonic clock and minimal overhead for ultra-fast detection
"""

import logging
import asyncio
from time import monotonic
from typing import Dict, Optional
from collections import deque

logger = logging.getLogger(__name__)


class EditRecord:
    """Lightweight edit record using monotonic time."""
    __slots__ = ('timestamp', 'message_id')

    def __init__(self, message_id: int):
        self.message_id = message_id
        self.timestamp = monotonic()


class FastStabilizationDetector:
    """
    Ultra-fast stabilization detector using monotonic clock.
    Optimized for minimal overhead and maximum speed.
    """

    __slots__ = ('threshold', 'strategy', '_edit_times', '_last_edits', 'max_history')

    def __init__(self, threshold: float = 0.15, strategy: str = 'wait', max_history: int = 20):
        """
        Initialize fast stabilization detector.

        Args:
            threshold: Stabilization threshold in seconds (default 150ms)
            strategy: Detection strategy ('wait', 'predict', 'aggressive')
            max_history: Maximum edit history to keep per message
        """
        self.threshold = threshold
        self.strategy = strategy
        self.max_history = max_history

        # Use dict for O(1) lookups, deque for efficient history management
        self._edit_times: Dict[int, deque] = {}
        self._last_edits: Dict[int, float] = {}

    def record_edit(self, message_id: int) -> None:
        """
        Record a message edit with minimal overhead.

        Args:
            message_id: Message ID
        """
        current_time = monotonic()

        # Update last edit time for fast access
        self._last_edits[message_id] = current_time

        # Maintain edit history if needed for prediction
        if self.strategy == 'predict':
            if message_id not in self._edit_times:
                self._edit_times[message_id] = deque(maxlen=self.max_history)
            self._edit_times[message_id].append(current_time)

    def is_stabilized(self, message_id: int) -> bool:
        """
        Check if message has stabilized (optimized version).

        Args:
            message_id: Message ID to check

        Returns:
            True if stabilized, False otherwise
        """
        last_edit = self._last_edits.get(message_id)
        if last_edit is None:
            return False

        time_since_last = monotonic() - last_edit

        if self.strategy == 'aggressive':
            # Ultra-aggressive: 50% of threshold
            return time_since_last >= (self.threshold * 0.5)

        elif self.strategy == 'wait':
            # Standard: full threshold
            return time_since_last >= self.threshold

        elif self.strategy == 'predict':
            # Predictive: analyze patterns
            if time_since_last < self.threshold:
                return False

            history = self._edit_times.get(message_id)
            if not history or len(history) < 2:
                return time_since_last >= self.threshold

            # Calculate average interval
            intervals = [history[i] - history[i-1] for i in range(1, len(history))]
            avg_interval = sum(intervals) / len(intervals)

            # If current gap is 2x average, likely stabilized
            return time_since_last > (avg_interval * 2)

        return False

    async def wait_for_stabilization(
        self,
        message_id: int,
        max_wait: float = 5.0,
        check_interval: float = 0.005  # 5ms check interval for ultra-fast response
    ) -> bool:
        """
        Wait for message to stabilize with minimal latency.

        Args:
            message_id: Message ID to wait for
            max_wait: Maximum wait time in seconds
            check_interval: Check interval in seconds (default 5ms)

        Returns:
            True if stabilized within max_wait, False if timeout
        """
        start_time = monotonic()

        while (monotonic() - start_time) < max_wait:
            if self.is_stabilized(message_id):
                wait_time = monotonic() - start_time
                logger.debug(f"Message {message_id} stabilized after {wait_time*1000:.2f}ms")
                return True

            await asyncio.sleep(check_interval)

        logger.warning(f"Message {message_id} timeout after {max_wait}s")
        return False

    def get_time_since_last_edit(self, message_id: int) -> Optional[float]:
        """
        Get time since last edit in seconds (fast version).

        Args:
            message_id: Message ID

        Returns:
            Time in seconds or None
        """
        last_edit = self._last_edits.get(message_id)
        return (monotonic() - last_edit) if last_edit is not None else None

    def clear_history(self, message_id: Optional[int] = None) -> None:
        """
        Clear edit history to free memory.

        Args:
            message_id: Specific message ID or None for all
        """
        if message_id is not None:
            self._last_edits.pop(message_id, None)
            self._edit_times.pop(message_id, None)
        else:
            self._last_edits.clear()
            self._edit_times.clear()

    def get_statistics(self) -> dict:
        """Get detector statistics."""
        stabilized_count = sum(1 for msg_id in self._last_edits if self.is_stabilized(msg_id))

        return {
            'tracked_messages': len(self._last_edits),
            'total_edits': sum(len(h) for h in self._edit_times.values()),
            'stabilized_messages': stabilized_count,
            'strategy': self.strategy,
            'threshold_ms': self.threshold * 1000,
        }
