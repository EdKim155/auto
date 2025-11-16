"""
SQLAlchemy models for the control panel database.
"""
from datetime import datetime
from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey, Float
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship

Base = declarative_base()


class Session(Base):
    """Telegram session configuration"""
    __tablename__ = 'sessions'

    id = Column(Integer, primary_key=True)
    phone = Column(String, unique=True, nullable=False)
    api_id = Column(Integer, nullable=False)
    api_hash = Column(String, nullable=False)
    session_file = Column(String, unique=True, nullable=False)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    last_connected_at = Column(DateTime, nullable=True)

    # Relationships
    target_bots = relationship('TargetBot', back_populates='session', cascade='all, delete-orphan')

    def __repr__(self):
        return f"<Session(id={self.id}, phone={self.phone}, active={self.is_active})>"


class TargetBot(Base):
    """Configuration for target bots to automate"""
    __tablename__ = 'target_bots'

    id = Column(Integer, primary_key=True)
    session_id = Column(Integer, ForeignKey('sessions.id'), nullable=False)
    bot_username = Column(String, nullable=False)
    automation_enabled = Column(Boolean, default=False)
    automation_mode = Column(String, default='full_cycle')  # 'full_cycle' or 'list_only'

    # Step 2 button configuration
    step2_button_keywords = Column(String, nullable=True)  # Comma-separated keywords or None for first button
    step2_button_index = Column(Integer, default=0)  # Button index (0 = first button, 1 = second, etc.)

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    session = relationship('Session', back_populates='target_bots')
    statistics = relationship('Statistics', back_populates='bot', uselist=False, cascade='all, delete-orphan')

    def __repr__(self):
        return f"<TargetBot(id={self.id}, bot={self.bot_username}, mode={self.automation_mode}, enabled={self.automation_enabled})>"


class Statistics(Base):
    """Statistics for bot automation runs"""
    __tablename__ = 'statistics'

    id = Column(Integer, primary_key=True)
    bot_id = Column(Integer, ForeignKey('target_bots.id'), unique=True, nullable=False)
    total_runs = Column(Integer, default=0)
    successful_runs = Column(Integer, default=0)
    failed_runs = Column(Integer, default=0)
    total_clicks = Column(Integer, default=0)
    successful_clicks = Column(Integer, default=0)
    failed_clicks = Column(Integer, default=0)
    triggers_detected = Column(Integer, default=0)
    last_activity_at = Column(DateTime, nullable=True)
    last_error = Column(String, nullable=True)
    last_error_at = Column(DateTime, nullable=True)

    # Relationships
    bot = relationship('TargetBot', back_populates='statistics')

    @property
    def success_rate(self):
        if self.total_runs == 0:
            return 0.0
        return (self.successful_runs / self.total_runs) * 100

    @property
    def click_success_rate(self):
        if self.total_clicks == 0:
            return 0.0
        return (self.successful_clicks / self.total_clicks) * 100

    def __repr__(self):
        return f"<Statistics(bot_id={self.bot_id}, success_rate={self.success_rate:.1f}%)>"


class AuthorizedUser(Base):
    """Authorized users for the control bot"""
    __tablename__ = 'authorized_users'

    id = Column(Integer, primary_key=True)
    telegram_id = Column(Integer, unique=True, nullable=False)
    username = Column(String, nullable=True)
    first_name = Column(String, nullable=True)
    added_at = Column(DateTime, default=datetime.utcnow)
    is_active = Column(Boolean, default=True)

    def __repr__(self):
        return f"<AuthorizedUser(telegram_id={self.telegram_id}, username={self.username})>"
