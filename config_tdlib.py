"""
Optimized Configuration for TDLib-based automation
Aggressive timings for maximum speed
"""

import os
from typing import List
from dotenv import load_dotenv

# Load environment variables
load_dotenv()


class Config:
    """Optimized configuration for TDLib automation."""

    # Telegram API credentials
    API_ID = os.getenv('API_ID')
    API_HASH = os.getenv('API_HASH')
    PHONE = os.getenv('PHONE')
    SESSION_NAME = os.getenv('SESSION_NAME', 'fast_automation')

    # Target bot
    BOT_USERNAME = os.getenv('BOT_USERNAME')

    # Trigger message configuration
    TRIGGER_TEXT = 'Появились новые перевозки'

    # OPTIMIZED DELAYS (агрессивные настройки для максимальной скорости)
    DELAY_AFTER_TRIGGER = 0.1  # 100ms - быстрая реакция
    DELAY_BETWEEN_CLICKS = 0.2  # 200ms - минимальная задержка между кликами
    STABILIZATION_THRESHOLD = 0.15  # 150ms - быстрая детекция стабилизации

    # Stabilization strategy: 'wait', 'predict', 'aggressive'
    # 'aggressive' - самый быстрый, но может быть нестабильным
    # 'wait' - надежный, умеренная скорость
    # 'predict' - баланс между скоростью и надежностью
    STABILIZATION_STRATEGY = 'predict'  # Предиктивная стратегия для баланса

    # Retry configuration
    MAX_RETRIES = 2  # Меньше retry для скорости
    RETRY_DELAY = 0.5  # Быстрые retry

    # Monitoring configuration
    MAX_CACHED_MESSAGES = 15  # Больше кэша для быстрого доступа
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

    # OPTIMIZED TIMEOUTS (короткие тайм-ауты для быстрой работы)
    STEP_1_TIMEOUT = 10.0  # Оптимизировано
    STEP_2_TIMEOUT = 10.0  # Оптимизировано
    STEP_3_TIMEOUT = 15.0  # Оптимизировано

    # Logging configuration
    LOG_LEVEL = os.getenv('LOG_LEVEL', 'INFO')
    LOG_FORMAT = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'

    # Performance optimizations
    USE_UVLOOP = True  # Использовать uvloop для ускорения asyncio

    @classmethod
    def validate(cls) -> bool:
        """Validate configuration."""
        required_fields = ['API_ID', 'API_HASH', 'PHONE', 'BOT_USERNAME']
        missing = []

        for field in required_fields:
            if not getattr(cls, field):
                missing.append(field)

        if missing:
            print(f"❌ Missing configuration: {', '.join(missing)}")
            print("Please set these in your .env file")
            return False

        return True

    @classmethod
    def display(cls) -> None:
        """Display configuration."""
        print("\n=== TDLib Automation Configuration ===")
        print(f"Bot: {cls.BOT_USERNAME}")
        print(f"Session: {cls.SESSION_NAME}")
        print(f"Trigger: '{cls.TRIGGER_TEXT}'")
        print(f"Strategy: {cls.STABILIZATION_STRATEGY}")
        print(f"Stabilization: {cls.STABILIZATION_THRESHOLD * 1000}ms")
        print(f"Delay after trigger: {cls.DELAY_AFTER_TRIGGER * 1000}ms")
        print(f"Delay between clicks: {cls.DELAY_BETWEEN_CLICKS * 1000}ms")
        print(f"Use uvloop: {cls.USE_UVLOOP}")
        print("======================================\n")
