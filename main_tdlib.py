#!/usr/bin/env python3
"""
TDLib-based Telegram Bot Automation - Main Entry Point
High-performance version using pytdbot and optimized modules
"""

import asyncio
import logging
import sys
from pathlib import Path

from pytdbot import Client, types

from config import Config
from bot_automation_tdlib import BotAutomationTDLib

# Configure logging
logging.basicConfig(
    level=getattr(logging, Config.LOG_LEVEL),
    format=Config.LOG_FORMAT,
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler('bot_automation_tdlib.log', encoding='utf-8')
    ]
)

logger = logging.getLogger(__name__)


class AutomationApp:
    """Main TDLib automation application."""

    def __init__(self):
        self.client: Client = None
        self.automation: BotAutomationTDLib = None
        self.is_running = False

    async def start(self):
        """Start the application."""
        print("\n" + "="*60)
        print("TELEGRAM BOT AUTOMATION - TDLib Edition")
        print("High-Performance Version")
        print("="*60 + "\n")

        # Validate configuration
        if not Config.validate():
            print("\nPlease configure .env file")
            sys.exit(1)

        try:
            # Initialize TDLib client
            logger.info("Initializing TDLib client...")

            # pytdbot doesn't use phone in constructor, it handles auth automatically
            self.client = Client(
                api_id=int(Config.API_ID),
                api_hash=Config.API_HASH,
                database_encryption_key='automation_key_2024',
                files_directory='./tdlib_files/',
                td_verbosity=1,  # Minimal TDLib logging
                td_log=types.LogStreamFile('tdlib.log', 10485760)  # 10MB log file
            )

            # Register message handlers
            @self.client.on_updateNewMessage()
            async def handle_new_message(c: Client, update: types.UpdateNewMessage):
                if self.automation:
                    await self.automation.handle_new_message(update.message)

            @self.client.on_updateMessageContent()
            async def handle_message_edit(c: Client, update: types.UpdateMessageContent):
                # Get full message
                try:
                    message = await c.getMessage(
                        chat_id=update.chat_id,
                        message_id=update.message_id
                    )
                    if self.automation:
                        await self.automation.handle_message_edit(message)
                except Exception as e:
                    logger.debug(f"Error getting edited message: {e}")

            logger.info("✓ TDLib client initialized")

            # Start client (this will handle login/auth)
            logger.info("Starting TDLib client...")
            await self.client.start()
            logger.info("✓ TDLib client started")

            # Check authorization
            me = await self.client.getMe()
            if me:
                logger.info(f"✓ Authorized as: {me.first_name} (ID: {me.id})")
            else:
                logger.error("Authorization failed")
                sys.exit(1)

            # Initialize automation
            self.automation = BotAutomationTDLib(
                client=self.client,
                bot_username=Config.BOT_USERNAME,
                mode='full_cycle'
            )

            await self.automation.start()

            self.is_running = True

            # Show status periodically
            asyncio.create_task(self._periodic_status())

            print("\n✓ TDLib Automation is running")
            print("Press Ctrl+C to stop\n")

            # Keep running
            while self.is_running:
                await asyncio.sleep(1)

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
            await self.client.stop()

        print("\n" + "="*60)
        print("Final Statistics:")
        print("="*60)
        if self.automation:
            stats = self.automation.get_statistics()
            print(f"\nMetrics:")
            for key, value in stats['metrics'].items():
                print(f"  {key}: {value}")
            print(f"\nCache:")
            for key, value in stats['cache'].items():
                print(f"  {key}: {value}")

        print("\n✓ Stopped\n")

    async def _periodic_status(self):
        """Periodically print status."""
        while self.is_running:
            await asyncio.sleep(60)
            if self.is_running and self.automation:
                logger.info("--- Status Update ---")
                stats = self.automation.get_statistics()
                logger.info(f"State: {stats['state']}")
                logger.info(f"Total cycles: {stats['metrics']['total_cycles']}, "
                          f"Success: {stats['metrics']['successful_cycles']}, "
                          f"Failed: {stats['metrics']['failed_cycles']}")
                logger.info(f"Total clicks: {stats['metrics']['total_clicks']}")
                if stats['metrics']['avg_cycle_time'] > 0:
                    logger.info(f"Avg cycle time: {stats['metrics']['avg_cycle_time']*1000:.1f}ms")


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
