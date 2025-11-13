"""
Modules package for Telegram bot automation system.
"""

from .button_cache import ButtonCache, ButtonInfo, MessageData
from .message_monitor import MessageMonitor
from .button_analyzer import ButtonAnalyzer
from .stabilization_detector import StabilizationDetector
from .click_executor import ClickExecutor
from .state_machine import StateMachine, AutomationState

__all__ = [
    'ButtonCache',
    'ButtonInfo',
    'MessageData',
    'MessageMonitor',
    'ButtonAnalyzer',
    'StabilizationDetector',
    'ClickExecutor',
    'StateMachine',
    'AutomationState',
]
