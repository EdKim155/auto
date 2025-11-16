"""
Session Manager for handling multiple Telegram sessions and bot automations.
"""
import os
import logging
import asyncio
from typing import Dict, Optional, List
from datetime import datetime
from telethon import TelegramClient
from telethon.errors import SessionPasswordNeededError

from bot_automation import BotAutomation
from database import db
from models import Session, TargetBot


logger = logging.getLogger(__name__)


class AutomationInstance:
    """Represents a running automation instance for a bot"""

    def __init__(
        self,
        bot_id: int,
        session_id: int,
        client: TelegramClient,
        automation: BotAutomation,
        bot_username: str,
        mode: str
    ):
        self.bot_id = bot_id
        self.session_id = session_id
        self.client = client
        self.automation = automation
        self.bot_username = bot_username
        self.mode = mode
        self.is_active = False
        self.created_at = datetime.utcnow()


class SessionManager:
    """
    Manages multiple Telegram sessions and their automations.
    """

    def __init__(self):
        self.sessions: Dict[int, TelegramClient] = {}  # session_id -> TelegramClient
        self.automations: Dict[int, AutomationInstance] = {}  # bot_id -> AutomationInstance
        self.running = False
        self._health_check_task: Optional[asyncio.Task] = None

    async def initialize(self):
        """Initialize the session manager"""
        logger.info("Initializing SessionManager...")

        # Load all active sessions from database
        active_sessions = db.get_all_sessions(active_only=True)

        for session in active_sessions:
            try:
                await self.connect_session(session.id)
                logger.info(f"Loaded session {session.id} ({session.phone})")
            except Exception as e:
                logger.error(f"Failed to load session {session.id}: {e}")

        # Load enabled automations
        enabled_bots = db.get_all_bots(enabled_only=True)

        for bot in enabled_bots:
            try:
                await self.start_automation(bot.id)
                logger.info(f"Started automation for bot {bot.id} ({bot.bot_username})")
            except Exception as e:
                logger.error(f"Failed to start automation for bot {bot.id}: {e}")

        self.running = True

        # Start health check
        self._health_check_task = asyncio.create_task(self._health_check_loop())

        logger.info("SessionManager initialized")

    async def shutdown(self):
        """Shutdown the session manager"""
        logger.info("Shutting down SessionManager...")
        self.running = False

        # Stop health check
        if self._health_check_task:
            self._health_check_task.cancel()
            try:
                await self._health_check_task
            except asyncio.CancelledError:
                pass

        # Stop all automations
        for bot_id in list(self.automations.keys()):
            await self.stop_automation(bot_id)

        # Disconnect all sessions
        for session_id in list(self.sessions.keys()):
            await self.disconnect_session(session_id)

        logger.info("SessionManager shut down")

    # ==================== Session Management ====================

    async def add_session(
        self,
        phone: str,
        api_id: int,
        api_hash: str
    ) -> Session:
        """
        Add a new Telegram session.

        Args:
            phone: Phone number
            api_id: Telegram API ID
            api_hash: Telegram API hash

        Returns:
            Created Session object
        """
        # Create session file path
        sessions_dir = 'sessions'
        os.makedirs(sessions_dir, exist_ok=True)
        session_file = os.path.join(sessions_dir, f"session_{phone}.session")

        # Add to database
        session = db.add_session(phone, api_id, api_hash, session_file)

        logger.info(f"Added new session {session.id} for {phone}")

        return session

    async def connect_session(self, session_id: int) -> bool:
        """
        Connect a Telegram session.

        Args:
            session_id: Session ID

        Returns:
            True if connected successfully
        """
        # Check if already connected
        if session_id in self.sessions:
            logger.warning(f"Session {session_id} already connected")
            return True

        # Get session from database
        session = db.get_session_by_id(session_id)
        if not session:
            raise ValueError(f"Session {session_id} not found")

        # Create client
        client = TelegramClient(
            session.session_file,
            session.api_id,
            session.api_hash
        )

        try:
            await client.connect()

            # Check if authorized
            if not await client.is_user_authorized():
                logger.warning(f"Session {session_id} not authorized - requires phone verification")
                await client.disconnect()
                return False

            self.sessions[session_id] = client
            db.update_session_status(session_id, True)

            logger.info(f"Session {session_id} ({session.phone}) connected")
            return True

        except Exception as e:
            logger.error(f"Failed to connect session {session_id}: {e}")
            if client.is_connected():
                await client.disconnect()
            raise

    async def disconnect_session(self, session_id: int):
        """Disconnect a session"""
        if session_id not in self.sessions:
            return

        # Stop all automations for this session
        bots = db.get_bots_by_session(session_id)
        for bot in bots:
            if bot.id in self.automations:
                await self.stop_automation(bot.id)

        # Disconnect client
        client = self.sessions[session_id]
        await client.disconnect()

        del self.sessions[session_id]
        db.update_session_status(session_id, False)

        logger.info(f"Session {session_id} disconnected")

    async def authorize_session(
        self,
        session_id: int,
        phone: str,
        code: Optional[str] = None,
        password: Optional[str] = None
    ) -> dict:
        """
        Authorize a session (for new sessions).

        Args:
            session_id: Session ID
            phone: Phone number
            code: Verification code (if sent)
            password: 2FA password (if needed)

        Returns:
            Status dict with next steps
        """
        session = db.get_session_by_id(session_id)
        if not session:
            raise ValueError(f"Session {session_id} not found")

        # Create client if not exists
        if session_id not in self.sessions:
            client = TelegramClient(
                session.session_file,
                session.api_id,
                session.api_hash
            )
            await client.connect()
            self.sessions[session_id] = client
        else:
            client = self.sessions[session_id]

        try:
            # If not authorized, start sign in process
            if not await client.is_user_authorized():
                if code:
                    # Sign in with code
                    try:
                        await client.sign_in(phone, code)
                        logger.info(f"Session {session_id} authorized with code")
                        db.update_session_status(session_id, True)
                        return {'status': 'authorized', 'message': 'Session authorized successfully'}
                    except SessionPasswordNeededError:
                        return {'status': 'need_password', 'message': '2FA password required'}
                elif password:
                    # Sign in with 2FA password
                    await client.sign_in(password=password)
                    logger.info(f"Session {session_id} authorized with 2FA")
                    db.update_session_status(session_id, True)
                    return {'status': 'authorized', 'message': 'Session authorized successfully'}
                else:
                    # Send code
                    await client.send_code_request(phone)
                    return {'status': 'code_sent', 'message': 'Verification code sent to Telegram'}
            else:
                return {'status': 'authorized', 'message': 'Session already authorized'}

        except Exception as e:
            logger.error(f"Authorization error for session {session_id}: {e}")
            return {'status': 'error', 'message': str(e)}

    def remove_session(self, session_id: int):
        """Remove a session"""
        # Note: This should disconnect the session first
        if session_id in self.sessions:
            logger.warning(f"Cannot remove active session {session_id} - disconnect first")
            return False

        db.delete_session(session_id)
        logger.info(f"Session {session_id} removed")
        return True

    # ==================== Bot Management ====================

    async def add_bot(
        self,
        session_id: int,
        bot_username: str,
        automation_mode: str = 'full_cycle'
    ) -> TargetBot:
        """
        Add a new target bot.

        Args:
            session_id: Session ID
            bot_username: Bot username (e.g., @apri1l_test_bot)
            automation_mode: 'full_cycle' or 'list_only'

        Returns:
            Created TargetBot object
        """
        # Verify session exists and is connected
        if session_id not in self.sessions:
            raise ValueError(f"Session {session_id} not connected")

        # Add to database
        bot = db.add_target_bot(session_id, bot_username, automation_mode)

        logger.info(f"Added bot {bot.id} ({bot_username}) to session {session_id}")

        return bot

    async def start_automation(self, bot_id: int) -> bool:
        """
        Start automation for a bot.

        Args:
            bot_id: Bot ID

        Returns:
            True if started successfully
        """
        # Check if already running
        if bot_id in self.automations:
            logger.warning(f"Automation for bot {bot_id} already running")
            return True

        # Get bot from database
        bot = db.get_bot_by_id(bot_id)
        if not bot:
            raise ValueError(f"Bot {bot_id} not found")

        # Check if session is connected
        if bot.session_id not in self.sessions:
            raise ValueError(f"Session {bot.session_id} not connected")

        client = self.sessions[bot.session_id]

        try:
            # Get bot entity
            bot_entity = await client.get_entity(bot.bot_username)

            # Create automation instance
            automation = BotAutomation(client, bot_entity, mode=bot.automation_mode)

            # Start automation
            await automation.start()

            # Store instance
            instance = AutomationInstance(
                bot_id=bot.id,
                session_id=bot.session_id,
                client=client,
                automation=automation,
                bot_username=bot.bot_username,
                mode=bot.automation_mode
            )
            instance.is_active = True
            self.automations[bot_id] = instance

            # Update database
            db.update_bot_status(bot_id, True)

            logger.info(f"Started automation for bot {bot_id} ({bot.bot_username}) in {bot.automation_mode} mode")

            return True

        except Exception as e:
            logger.error(f"Failed to start automation for bot {bot_id}: {e}")
            raise

    async def stop_automation(self, bot_id: int):
        """Stop automation for a bot"""
        if bot_id not in self.automations:
            logger.warning(f"Automation for bot {bot_id} not running")
            return

        instance = self.automations[bot_id]

        # Stop automation
        await instance.automation.stop()

        instance.is_active = False
        del self.automations[bot_id]

        # Update database
        db.update_bot_status(bot_id, False)

        logger.info(f"Stopped automation for bot {bot_id}")

    async def set_automation_mode(self, bot_id: int, mode: str):
        """
        Change automation mode for a bot.

        Args:
            bot_id: Bot ID
            mode: 'full_cycle' or 'list_only'
        """
        # Update database
        db.update_bot_mode(bot_id, mode)

        # If automation is running, update it
        if bot_id in self.automations:
            instance = self.automations[bot_id]
            instance.automation.set_mode(mode)
            instance.mode = mode
            logger.info(f"Updated mode for bot {bot_id} to {mode}")

    def remove_bot(self, bot_id: int):
        """Remove a bot"""
        # Stop automation if running
        if bot_id in self.automations:
            logger.warning(f"Cannot remove active bot {bot_id} - stop automation first")
            return False

        db.delete_bot(bot_id)
        logger.info(f"Bot {bot_id} removed")
        return True

    # ==================== Status & Health Check ====================

    def get_session_status(self, session_id: int) -> dict:
        """Get status for a session"""
        session = db.get_session_by_id(session_id)
        if not session:
            return {'error': 'Session not found'}

        is_connected = session_id in self.sessions

        bots = db.get_bots_by_session(session_id)
        bot_statuses = []

        for bot in bots:
            is_running = bot.id in self.automations
            stats = db.get_statistics(bot.id)

            bot_statuses.append({
                'bot_id': bot.id,
                'username': bot.bot_username,
                'mode': bot.automation_mode,
                'enabled': bot.automation_enabled,
                'running': is_running,
                'statistics': {
                    'success_rate': stats.success_rate if stats else 0,
                    'total_runs': stats.total_runs if stats else 0,
                    'last_activity': stats.last_activity_at if stats else None
                }
            })

        return {
            'session_id': session.id,
            'phone': session.phone,
            'is_active': session.is_active,
            'is_connected': is_connected,
            'last_connected': session.last_connected_at,
            'bots': bot_statuses
        }

    def get_all_status(self) -> dict:
        """Get status for all sessions"""
        sessions = db.get_all_sessions()

        session_statuses = []
        for session in sessions:
            session_statuses.append(self.get_session_status(session.id))

        return {
            'total_sessions': len(sessions),
            'connected_sessions': len(self.sessions),
            'total_automations': len(self.automations),
            'active_automations': sum(1 for inst in self.automations.values() if inst.is_active),
            'sessions': session_statuses
        }

    async def _health_check_loop(self):
        """Periodic health check for all sessions and automations"""
        while self.running:
            try:
                await asyncio.sleep(30)  # Check every 30 seconds

                # Check session connections
                for session_id, client in list(self.sessions.items()):
                    if not client.is_connected():
                        logger.warning(f"Session {session_id} disconnected - attempting reconnect")
                        try:
                            await client.connect()
                            db.update_session_status(session_id, True)
                        except Exception as e:
                            logger.error(f"Failed to reconnect session {session_id}: {e}")
                            db.update_session_status(session_id, False)

                # Update statistics from running automations
                for bot_id, instance in self.automations.items():
                    try:
                        status = instance.automation.get_status()

                        # Update statistics in database
                        db.update_statistics(
                            bot_id,
                            total_runs=status['state_machine']['total_runs'],
                            successful_runs=status['state_machine']['successful_runs'],
                            failed_runs=status['state_machine']['failed_runs'],
                            total_clicks=status['click_executor']['total_clicks'],
                            successful_clicks=status['click_executor']['successful_clicks'],
                            failed_clicks=status['click_executor']['failed_clicks'],
                            triggers_detected=status['message_monitor']['triggers_detected']
                        )
                    except Exception as e:
                        logger.error(f"Failed to update statistics for bot {bot_id}: {e}")

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in health check loop: {e}")


# Global session manager instance
session_manager = SessionManager()
