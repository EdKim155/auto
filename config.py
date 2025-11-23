"""
Configuration module for Telegram bot automation system.
Contains all configurable parameters for the automation.
"""

import os
from typing import List
from dotenv import load_dotenv

# Load environment variables
load_dotenv()


class Config:
    """Main configuration class for the automation system."""

    # Telegram API credentials
    API_ID = os.getenv('API_ID')
    API_HASH = os.getenv('API_HASH')
    PHONE = os.getenv('PHONE')
    SESSION_NAME = os.getenv('SESSION_NAME', 'telegram_bot_automation')

    # Target bot
    BOT_USERNAME = os.getenv('BOT_USERNAME')

    # Trigger message configuration
    TRIGGER_TEXT = 'Появились новые перевозки'

    # Delays (in seconds) - BALANCED for reliability + speed
    DELAY_AFTER_TRIGGER = 0.25  # Wait 250ms after trigger detection
    DELAY_BETWEEN_CLICKS = 0.4  # 400ms delay between clicks
    STABILIZATION_THRESHOLD = 0.3  # 300ms threshold (3x bot edit frequency)

    # Stabilization strategy: 'wait', 'predict', 'aggressive'
    STABILIZATION_STRATEGY = 'wait'  # Wait for full stabilization (reliable)

    # Retry configuration
    MAX_RETRIES = 3
    RETRY_DELAY = 1.0  # 1 second delay between retries

    # Monitoring configuration
    MAX_CACHED_MESSAGES = 10
    LOG_BUTTONS = True

    # Button search keywords
    BUTTON_1_KEYWORDS: List[str] = [
        'список прямых перевозок',
        'список перевозок',
        'прямые перевозки',
        'список свободных перевозок'
    ]

    BUTTON_2_KEYWORDS: List[str] = []  # First button in list

    BUTTON_3_KEYWORDS: List[str] = [
        'подтвердить',
        'забронировать',
        'взять',
        'беру',
        'подтверждаю'
    ]

    # Timeouts for each step (in seconds)
    STEP_1_TIMEOUT = 15.0  # Increased for slow bot
    STEP_2_TIMEOUT = 15.0  # Increased for slow bot
    STEP_3_TIMEOUT = 20.0  # Increased for slow bot

    # Logging configuration
    LOG_LEVEL = os.getenv('LOG_LEVEL', 'INFO')
    LOG_FORMAT = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'

    @classmethod
    def validate(cls) -> bool:
        """Validate that all required configuration is present."""
        required_fields = ['API_ID', 'API_HASH', 'PHONE', 'BOT_USERNAME']
        missing = []

        for field in required_fields:
            if not getattr(cls, field):
                missing.append(field)

        if missing:
            print(f"❌ Missing required configuration: {', '.join(missing)}")
            print("Please set these in your .env file")
            return False

        return True

    @classmethod
    def display(cls) -> None:
        """Display current configuration (without sensitive data)."""
        print("\n=== Configuration ===")
        print(f"Bot: {cls.BOT_USERNAME}")
        print(f"Session: {cls.SESSION_NAME}")
        print(f"Trigger: '{cls.TRIGGER_TEXT}'")
        print(f"Strategy: {cls.STABILIZATION_STRATEGY}")
        print(f"Stabilization threshold: {cls.STABILIZATION_THRESHOLD * 1000}ms")
        print(f"Max retries: {cls.MAX_RETRIES}")
        print("====================\n")
