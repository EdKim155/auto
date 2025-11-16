"""
Database manager for the control panel.
"""
import os
from datetime import datetime
from typing import List, Optional
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session as DBSession
from models import Base, Session, TargetBot, Statistics, AuthorizedUser


class Database:
    """Database manager for SQLite operations"""

    def __init__(self, db_path: str = 'control_panel.db'):
        """
        Initialize database connection.

        Args:
            db_path: Path to SQLite database file
        """
        self.db_path = db_path
        self.engine = create_engine(f'sqlite:///{db_path}', echo=False)
        self.SessionLocal = sessionmaker(bind=self.engine)

    def init_db(self):
        """Create all tables if they don't exist"""
        Base.metadata.create_all(self.engine)
        print(f"Database initialized at: {self.db_path}")

    def get_session(self) -> DBSession:
        """Get a new database session"""
        return self.SessionLocal()

    # ==================== Session CRUD ====================

    def add_session(self, phone: str, api_id: int, api_hash: str, session_file: str) -> Session:
        """
        Add a new Telegram session.

        Args:
            phone: Phone number
            api_id: Telegram API ID
            api_hash: Telegram API hash
            session_file: Path to session file

        Returns:
            Created Session object
        """
        db = self.get_session()
        try:
            session = Session(
                phone=phone,
                api_id=api_id,
                api_hash=api_hash,
                session_file=session_file
            )
            db.add(session)
            db.commit()
            db.refresh(session)
            return session
        finally:
            db.close()

    def get_session_by_id(self, session_id: int) -> Optional[Session]:
        """Get session by ID"""
        db = self.get_session()
        try:
            return db.query(Session).filter(Session.id == session_id).first()
        finally:
            db.close()

    def get_session_by_phone(self, phone: str) -> Optional[Session]:
        """Get session by phone number"""
        db = self.get_session()
        try:
            return db.query(Session).filter(Session.phone == phone).first()
        finally:
            db.close()

    def get_all_sessions(self, active_only: bool = False) -> List[Session]:
        """Get all sessions"""
        db = self.get_session()
        try:
            query = db.query(Session)
            if active_only:
                query = query.filter(Session.is_active == True)
            return query.all()
        finally:
            db.close()

    def update_session_status(self, session_id: int, is_active: bool):
        """Update session active status"""
        db = self.get_session()
        try:
            session = db.query(Session).filter(Session.id == session_id).first()
            if session:
                session.is_active = is_active
                if is_active:
                    session.last_connected_at = datetime.utcnow()
                db.commit()
        finally:
            db.close()

    def delete_session(self, session_id: int):
        """Delete a session and all related data"""
        db = self.get_session()
        try:
            session = db.query(Session).filter(Session.id == session_id).first()
            if session:
                db.delete(session)
                db.commit()
        finally:
            db.close()

    # ==================== TargetBot CRUD ====================

    def add_target_bot(self, session_id: int, bot_username: str, automation_mode: str = 'full_cycle') -> TargetBot:
        """
        Add a new target bot.

        Args:
            session_id: ID of the session
            bot_username: Bot username (e.g., @apri1l_test_bot)
            automation_mode: 'full_cycle' or 'list_only'

        Returns:
            Created TargetBot object
        """
        db = self.get_session()
        try:
            bot = TargetBot(
                session_id=session_id,
                bot_username=bot_username,
                automation_mode=automation_mode
            )
            db.add(bot)
            db.commit()
            db.refresh(bot)

            # Create statistics entry
            stats = Statistics(bot_id=bot.id)
            db.add(stats)
            db.commit()

            return bot
        finally:
            db.close()

    def get_bot_by_id(self, bot_id: int) -> Optional[TargetBot]:
        """Get target bot by ID"""
        db = self.get_session()
        try:
            return db.query(TargetBot).filter(TargetBot.id == bot_id).first()
        finally:
            db.close()

    def get_bots_by_session(self, session_id: int) -> List[TargetBot]:
        """Get all bots for a session"""
        db = self.get_session()
        try:
            return db.query(TargetBot).filter(TargetBot.session_id == session_id).all()
        finally:
            db.close()

    def get_all_bots(self, enabled_only: bool = False) -> List[TargetBot]:
        """Get all target bots"""
        db = self.get_session()
        try:
            query = db.query(TargetBot)
            if enabled_only:
                query = query.filter(TargetBot.automation_enabled == True)
            return query.all()
        finally:
            db.close()

    def update_bot_status(self, bot_id: int, enabled: bool):
        """Update bot automation enabled status"""
        db = self.get_session()
        try:
            bot = db.query(TargetBot).filter(TargetBot.id == bot_id).first()
            if bot:
                bot.automation_enabled = enabled
                bot.updated_at = datetime.utcnow()
                db.commit()
        finally:
            db.close()

    def update_bot_mode(self, bot_id: int, mode: str):
        """Update bot automation mode"""
        db = self.get_session()
        try:
            bot = db.query(TargetBot).filter(TargetBot.id == bot_id).first()
            if bot:
                bot.automation_mode = mode
                bot.updated_at = datetime.utcnow()
                db.commit()
        finally:
            db.close()

    def update_bot_step2_config(self, bot_id: int, keywords: str = None, button_index: int = 0):
        """
        Update Step 2 button configuration for a bot.

        Args:
            bot_id: Bot ID
            keywords: Comma-separated keywords or None for index-based selection
            button_index: Button index (0 = first button)
        """
        db = self.get_session()
        try:
            bot = db.query(TargetBot).filter(TargetBot.id == bot_id).first()
            if bot:
                bot.step2_button_keywords = keywords
                bot.step2_button_index = button_index
                bot.updated_at = datetime.utcnow()
                db.commit()
        finally:
            db.close()

    def delete_bot(self, bot_id: int):
        """Delete a target bot"""
        db = self.get_session()
        try:
            bot = db.query(TargetBot).filter(TargetBot.id == bot_id).first()
            if bot:
                db.delete(bot)
                db.commit()
        finally:
            db.close()

    # ==================== Statistics CRUD ====================

    def get_statistics(self, bot_id: int) -> Optional[Statistics]:
        """Get statistics for a bot"""
        db = self.get_session()
        try:
            return db.query(Statistics).filter(Statistics.bot_id == bot_id).first()
        finally:
            db.close()

    def update_statistics(self, bot_id: int, **kwargs):
        """
        Update statistics for a bot.

        Accepted kwargs: total_runs, successful_runs, failed_runs,
                        total_clicks, successful_clicks, failed_clicks,
                        triggers_detected, last_error
        """
        db = self.get_session()
        try:
            stats = db.query(Statistics).filter(Statistics.bot_id == bot_id).first()
            if stats:
                for key, value in kwargs.items():
                    if hasattr(stats, key):
                        setattr(stats, key, value)

                stats.last_activity_at = datetime.utcnow()

                if 'last_error' in kwargs:
                    stats.last_error_at = datetime.utcnow()

                db.commit()
        finally:
            db.close()

    def increment_statistics(self, bot_id: int, field: str, amount: int = 1):
        """Increment a statistics field"""
        db = self.get_session()
        try:
            stats = db.query(Statistics).filter(Statistics.bot_id == bot_id).first()
            if stats and hasattr(stats, field):
                current_value = getattr(stats, field) or 0
                setattr(stats, field, current_value + amount)
                stats.last_activity_at = datetime.utcnow()
                db.commit()
        finally:
            db.close()

    # ==================== AuthorizedUser CRUD ====================

    def add_authorized_user(self, telegram_id: int, username: str = None, first_name: str = None) -> AuthorizedUser:
        """Add an authorized user"""
        db = self.get_session()
        try:
            user = AuthorizedUser(
                telegram_id=telegram_id,
                username=username,
                first_name=first_name
            )
            db.add(user)
            db.commit()
            db.refresh(user)
            return user
        finally:
            db.close()

    def is_user_authorized(self, telegram_id: int) -> bool:
        """Check if user is authorized"""
        db = self.get_session()
        try:
            user = db.query(AuthorizedUser).filter(
                AuthorizedUser.telegram_id == telegram_id,
                AuthorizedUser.is_active == True
            ).first()
            return user is not None
        finally:
            db.close()

    def get_all_authorized_users(self) -> List[AuthorizedUser]:
        """Get all authorized users"""
        db = self.get_session()
        try:
            return db.query(AuthorizedUser).filter(AuthorizedUser.is_active == True).all()
        finally:
            db.close()

    def remove_authorized_user(self, telegram_id: int):
        """Remove an authorized user"""
        db = self.get_session()
        try:
            user = db.query(AuthorizedUser).filter(AuthorizedUser.telegram_id == telegram_id).first()
            if user:
                user.is_active = False
                db.commit()
        finally:
            db.close()


# Global database instance
db = Database()
