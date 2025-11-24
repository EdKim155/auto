#!/usr/bin/env python3
"""
Telegram Bot Automation - FAST Edition
Telethon + Optimized Modules for maximum performance
"""

import asyncio
import logging
import sys
from pathlib import Path

from telethon import TelegramClient
from telethon.errors import SessionPasswordNeededError

from config import Config
from bot_automation_fast import BotAutomationFast

# Configure logging
logging.basicConfig(
    level=getattr(logging, Config.LOG_LEVEL),
    format=Config.LOG_FORMAT,
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler('bot_automation_fast.log', encoding='utf-8')
    ]
)

logger = logging.getLogger(__name__)


class AutomationApp:
    """Main application class for FAST automation."""

    def __init__(self):
        self.client: TelegramClient = None
        self.automation: BotAutomationFast = None
        self.is_running = False

    async def start(self):
        """Start the application."""
        print("\n" + "="*60)
        print("TELEGRAM BOT AUTOMATION - FAST Edition")
        print("Telethon + Optimized Modules")
        print("="*60 + "\n")

        # Validate configuration
        if not Config.validate():
            print("\nPlease copy .env.example to .env and configure it")
            sys.exit(1)

        try:
            # Initialize Telegram client
            logger.info("Connecting to Telegram...")
            self.client = TelegramClient(
                Config.SESSION_NAME,
                Config.API_ID,
                Config.API_HASH
            )

            await self.client.start(phone=Config.PHONE)
            logger.info("✓ Connected to Telegram")

            # Check authorization
            if not await self.client.is_user_authorized():
                logger.error("User not authorized")
                sys.exit(1)

            # Get bot entity
            logger.info(f"Getting bot entity: {Config.BOT_USERNAME}")
            try:
                bot_entity = await self.client.get_entity(Config.BOT_USERNAME)
                logger.info(f"✓ Bot found: {bot_entity.id}")
            except Exception as e:
                logger.error(f"Failed to get bot entity: {e}")
                print(f"\n❌ Could not find bot: {Config.BOT_USERNAME}")
                print("Please check that the bot username is correct and you have a chat with the bot")
                sys.exit(1)

            # Initialize FAST automation
            self.automation = BotAutomationFast(self.client, bot_entity)
            await self.automation.start()

            self.is_running = True

            # Set up signal handlers
            import signal
            signal.signal(signal.SIGINT, lambda s, f: asyncio.create_task(self.stop()))
            signal.signal(signal.SIGTERM, lambda s, f: asyncio.create_task(self.stop()))

            # Show status every 60 seconds
            asyncio.create_task(self._periodic_status())

            print("\n✓ FAST Automation is running")
            print("Press Ctrl+C to stop\n")

            # Keep running
            while self.is_running:
                await asyncio.sleep(1)

        except SessionPasswordNeededError:
            logger.error("2FA is enabled. Please disable it or implement 2FA handling")
            sys.exit(1)
        except KeyboardInterrupt:
            await self.stop()
        except Exception as e:
            logger.error(f"Unexpected error: {e}", exc_info=True)
            await self.stop()
            sys.exit(1)

    async def stop(self):
        """Stop the application."""
        if not self.is_running:
            return

        logger.info("\nStopping automation...")
        self.is_running = False

        if self.automation:
            await self.automation.stop()

        if self.client:
            await self.client.disconnect()

        print("\n" + "="*60)
        print("Final Statistics:")
        print("="*60)
        if self.automation:
            self.automation.print_status()

        print("✓ Stopped\n")

    async def _periodic_status(self):
        """Periodically print status."""
        while self.is_running:
            await asyncio.sleep(60)
            if self.is_running and self.automation:
                logger.info("--- Status Update ---")
                status = self.automation.get_status()
                logger.info(f"State: {status['state_machine']['current_state']}")
                logger.info(f"Messages: {status['message_monitor']['total_messages']}, "
                          f"Edits: {status['message_monitor']['total_edits']}, "
                          f"Triggers: {status['message_monitor']['triggers_detected']}")
                logger.info(f"Clicks: {status['click_executor']['total_clicks']} "
                          f"(Success: {status['click_executor']['successful_clicks']}, "
                          f"Failed: {status['click_executor']['failed_clicks']})")
                if status['metrics']['avg_cycle_time'] > 0:
                    logger.info(f"Avg cycle time: {status['metrics']['avg_cycle_time']*1000:.1f}ms")


async def main():
    """Main entry point."""
    app = AutomationApp()
    await app.start()


if __name__ == '__main__':
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n\nInterrupted by user")
        sys.exit(0)
