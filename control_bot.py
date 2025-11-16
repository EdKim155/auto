"""
Telegram Control Bot for managing automation sessions.
"""
import os
import logging
import asyncio
from datetime import datetime
from typing import Optional
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application,
    CommandHandler,
    CallbackQueryHandler,
    ContextTypes,
    MessageHandler,
    filters,
    ConversationHandler
)

from database import db
from session_manager import session_manager


# Setup logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)


# Conversation states
(
    ADDING_SESSION_PHONE,
    ADDING_SESSION_API_ID,
    ADDING_SESSION_API_HASH,
    ADDING_SESSION_CODE,
    ADDING_SESSION_PASSWORD,
    ADDING_BOT_USERNAME,
    ADDING_BOT_MODE
) = range(7)


class ControlBot:
    """Main control bot class"""

    def __init__(self, token: str, authorized_user_ids: list):
        """
        Initialize control bot.

        Args:
            token: Bot token from @BotFather
            authorized_user_ids: List of authorized Telegram user IDs
        """
        self.token = token
        self.authorized_user_ids = authorized_user_ids
        self.application = None

        # Temporary storage for session creation
        self.temp_session_data = {}

    def is_authorized(self, user_id: int) -> bool:
        """Check if user is authorized"""
        return user_id in self.authorized_user_ids or db.is_user_authorized(user_id)

    async def auth_required(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> bool:
        """Check authorization and send error if not authorized"""
        user_id = update.effective_user.id
        if not self.is_authorized(user_id):
            await update.message.reply_text(
                "⛔ You are not authorized to use this bot.\n"
                f"Your Telegram ID: {user_id}"
            )
            return False
        return True

    # ==================== Command Handlers ====================

    async def cmd_start(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /start command"""
        if not await self.auth_required(update, context):
            return

        keyboard = [
            [InlineKeyboardButton("📊 Status", callback_data="main_status")],
            [InlineKeyboardButton("📱 Sessions", callback_data="main_sessions")],
            [InlineKeyboardButton("🤖 Bots", callback_data="main_bots")],
            [InlineKeyboardButton("💚 Health Check", callback_data="main_health")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)

        await update.message.reply_text(
            "🎮 *Control Panel*\n\n"
            "Welcome to the bot automation control panel.\n"
            "Choose an option below:",
            parse_mode='Markdown',
            reply_markup=reply_markup
        )

    async def cmd_status(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /status command"""
        if not await self.auth_required(update, context):
            return

        status = session_manager.get_all_status()

        text = "📊 *Overall Status*\n\n"
        text += f"Total Sessions: {status['total_sessions']}\n"
        text += f"Connected Sessions: {status['connected_sessions']}\n"
        text += f"Total Automations: {status['total_automations']}\n"
        text += f"Active Automations: {status['active_automations']}\n\n"

        for session_status in status['sessions']:
            text += f"━━━━━━━━━━━━━━━━\n"
            text += f"📱 *Session:* {session_status['phone']}\n"
            text += f"Status: {'🟢 Connected' if session_status['is_connected'] else '🔴 Disconnected'}\n"

            if session_status['bots']:
                text += f"\n*Bots:*\n"
                for bot in session_status['bots']:
                    status_emoji = "🟢" if bot['running'] else "⚫"
                    mode_emoji = "🔄" if bot['mode'] == 'full_cycle' else "📋"
                    text += f"{status_emoji} {bot['username']} {mode_emoji}\n"
                    text += f"   Mode: {bot['mode']}\n"
                    text += f"   Success Rate: {bot['statistics']['success_rate']:.1f}%\n"
                    text += f"   Total Runs: {bot['statistics']['total_runs']}\n"

        await update.message.reply_text(text, parse_mode='Markdown')

    # ==================== Main Menu Callbacks ====================

    async def callback_main_status(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Show overall status"""
        query = update.callback_query
        await query.answer()

        status = session_manager.get_all_status()

        text = "📊 *Overall Status*\n\n"
        text += f"Total Sessions: {status['total_sessions']}\n"
        text += f"Connected Sessions: {status['connected_sessions']}\n"
        text += f"Total Automations: {status['total_automations']}\n"
        text += f"Active Automations: {status['active_automations']}\n"

        keyboard = [[InlineKeyboardButton("« Back", callback_data="back_to_main")]]
        reply_markup = InlineKeyboardMarkup(keyboard)

        await query.edit_message_text(text, parse_mode='Markdown', reply_markup=reply_markup)

    async def callback_main_sessions(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Show sessions menu"""
        query = update.callback_query
        await query.answer()

        sessions = db.get_all_sessions()

        text = "📱 *Sessions*\n\n"

        keyboard = []
        for session in sessions:
            status_emoji = "🟢" if session.is_active else "🔴"
            keyboard.append([
                InlineKeyboardButton(
                    f"{status_emoji} {session.phone}",
                    callback_data=f"session_{session.id}"
                )
            ])

        keyboard.append([InlineKeyboardButton("➕ Add Session", callback_data="add_session")])
        keyboard.append([InlineKeyboardButton("« Back", callback_data="back_to_main")])

        reply_markup = InlineKeyboardMarkup(keyboard)

        if not sessions:
            text += "No sessions configured yet.\n"

        await query.edit_message_text(text, parse_mode='Markdown', reply_markup=reply_markup)

    async def callback_main_bots(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Show bots menu"""
        query = update.callback_query
        await query.answer()

        sessions = db.get_all_sessions()

        text = "🤖 *Select Session to Manage Bots*\n\n"

        keyboard = []
        for session in sessions:
            bot_count = len(db.get_bots_by_session(session.id))
            keyboard.append([
                InlineKeyboardButton(
                    f"{session.phone} ({bot_count} bots)",
                    callback_data=f"session_bots_{session.id}"
                )
            ])

        keyboard.append([InlineKeyboardButton("« Back", callback_data="back_to_main")])

        reply_markup = InlineKeyboardMarkup(keyboard)

        await query.edit_message_text(text, parse_mode='Markdown', reply_markup=reply_markup)

    async def callback_main_health(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Show health check"""
        query = update.callback_query
        await query.answer()

        status = session_manager.get_all_status()

        text = "💚 *Health Check*\n\n"

        all_healthy = True

        for session_status in status['sessions']:
            if not session_status['is_connected']:
                all_healthy = False
                text += f"🔴 Session {session_status['phone']} disconnected\n"

            for bot in session_status['bots']:
                if bot['enabled'] and not bot['running']:
                    all_healthy = False
                    text += f"⚠️ Bot {bot['username']} should be running but isn't\n"

                if bot['statistics']['success_rate'] < 50 and bot['statistics']['total_runs'] > 10:
                    all_healthy = False
                    text += f"⚠️ Bot {bot['username']} has low success rate ({bot['statistics']['success_rate']:.1f}%)\n"

        if all_healthy:
            text += "✅ All systems operational\n"

        keyboard = [[InlineKeyboardButton("« Back", callback_data="back_to_main")]]
        reply_markup = InlineKeyboardMarkup(keyboard)

        await query.edit_message_text(text, parse_mode='Markdown', reply_markup=reply_markup)

    async def callback_back_to_main(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Back to main menu"""
        query = update.callback_query
        await query.answer()

        keyboard = [
            [InlineKeyboardButton("📊 Status", callback_data="main_status")],
            [InlineKeyboardButton("📱 Sessions", callback_data="main_sessions")],
            [InlineKeyboardButton("🤖 Bots", callback_data="main_bots")],
            [InlineKeyboardButton("💚 Health Check", callback_data="main_health")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)

        await query.edit_message_text(
            "🎮 *Control Panel*\n\nChoose an option:",
            parse_mode='Markdown',
            reply_markup=reply_markup
        )

    # ==================== Session Management ====================

    async def callback_session_detail(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Show session detail"""
        query = update.callback_query
        await query.answer()

        session_id = int(query.data.split('_')[1])
        session_status = session_manager.get_session_status(session_id)

        text = f"📱 *Session: {session_status['phone']}*\n\n"
        text += f"Status: {'🟢 Connected' if session_status['is_connected'] else '🔴 Disconnected'}\n"

        if session_status['last_connected']:
            text += f"Last Connected: {session_status['last_connected']}\n"

        text += f"\n*Bots ({len(session_status['bots'])}):*\n"

        for bot in session_status['bots']:
            status_emoji = "🟢" if bot['running'] else "⚫"
            text += f"{status_emoji} {bot['username']}\n"

        keyboard = []

        if session_status['is_connected']:
            keyboard.append([InlineKeyboardButton("🔌 Disconnect", callback_data=f"session_disconnect_{session_id}")])
        else:
            keyboard.append([InlineKeyboardButton("🔌 Connect", callback_data=f"session_connect_{session_id}")])

        keyboard.append([InlineKeyboardButton("🤖 Manage Bots", callback_data=f"session_bots_{session_id}")])
        keyboard.append([InlineKeyboardButton("🗑️ Delete Session", callback_data=f"session_delete_{session_id}")])
        keyboard.append([InlineKeyboardButton("« Back", callback_data="main_sessions")])

        reply_markup = InlineKeyboardMarkup(keyboard)

        await query.edit_message_text(text, parse_mode='Markdown', reply_markup=reply_markup)

    async def callback_session_connect(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Connect a session"""
        query = update.callback_query
        await query.answer("Connecting session...")

        session_id = int(query.data.split('_')[2])

        try:
            success = await session_manager.connect_session(session_id)
            if success:
                await query.edit_message_text(
                    "✅ Session connected successfully",
                    reply_markup=InlineKeyboardMarkup([[
                        InlineKeyboardButton("« Back", callback_data=f"session_{session_id}")
                    ]])
                )
            else:
                await query.edit_message_text(
                    "⚠️ Session needs authorization. Use /addsession to authorize.",
                    reply_markup=InlineKeyboardMarkup([[
                        InlineKeyboardButton("« Back", callback_data=f"session_{session_id}")
                    ]])
                )
        except Exception as e:
            await query.edit_message_text(
                f"❌ Error: {str(e)}",
                reply_markup=InlineKeyboardMarkup([[
                    InlineKeyboardButton("« Back", callback_data=f"session_{session_id}")
                ]])
            )

    async def callback_session_disconnect(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Disconnect a session"""
        query = update.callback_query
        await query.answer("Disconnecting session...")

        session_id = int(query.data.split('_')[2])

        try:
            await session_manager.disconnect_session(session_id)
            await query.edit_message_text(
                "✅ Session disconnected",
                reply_markup=InlineKeyboardMarkup([[
                    InlineKeyboardButton("« Back", callback_data=f"session_{session_id}")
                ]])
            )
        except Exception as e:
            await query.edit_message_text(f"❌ Error: {str(e)}")

    # ==================== Bot Management ====================

    async def callback_session_bots(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Show bots for a session"""
        query = update.callback_query
        await query.answer()

        session_id = int(query.data.split('_')[2])
        session = db.get_session_by_id(session_id)
        bots = db.get_bots_by_session(session_id)

        text = f"🤖 *Bots for {session.phone}*\n\n"

        keyboard = []
        for bot in bots:
            status_emoji = "🟢" if bot.automation_enabled else "⚫"
            mode_emoji = "🔄" if bot.automation_mode == 'full_cycle' else "📋"
            keyboard.append([
                InlineKeyboardButton(
                    f"{status_emoji} {bot.bot_username} {mode_emoji}",
                    callback_data=f"bot_{bot.id}"
                )
            ])

        keyboard.append([InlineKeyboardButton("➕ Add Bot", callback_data=f"add_bot_{session_id}")])
        keyboard.append([InlineKeyboardButton("« Back", callback_data="main_bots")])

        reply_markup = InlineKeyboardMarkup(keyboard)

        if not bots:
            text += "No bots configured for this session.\n"

        await query.edit_message_text(text, parse_mode='Markdown', reply_markup=reply_markup)

    async def callback_bot_detail(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Show bot detail and controls"""
        query = update.callback_query
        await query.answer()

        bot_id = int(query.data.split('_')[1])
        bot = db.get_bot_by_id(bot_id)
        stats = db.get_statistics(bot_id)

        is_running = bot_id in session_manager.automations

        text = f"🤖 *{bot.bot_username}*\n\n"
        text += f"Status: {'🟢 Running' if is_running else '⚫ Stopped'}\n"
        text += f"Mode: {bot.automation_mode}\n\n"

        if stats:
            text += f"*Statistics:*\n"
            text += f"Total Runs: {stats.total_runs}\n"
            text += f"Success Rate: {stats.success_rate:.1f}%\n"
            text += f"Total Clicks: {stats.total_clicks}\n"
            text += f"Click Success: {stats.click_success_rate:.1f}%\n"

            if stats.last_activity_at:
                text += f"Last Activity: {stats.last_activity_at.strftime('%Y-%m-%d %H:%M:%S')}\n"

            if stats.last_error:
                text += f"\n⚠️ Last Error: {stats.last_error}\n"

        keyboard = []

        # Start/Stop button
        if is_running:
            keyboard.append([InlineKeyboardButton("⏹️ Stop", callback_data=f"bot_stop_{bot_id}")])
        else:
            keyboard.append([InlineKeyboardButton("▶️ Start", callback_data=f"bot_start_{bot_id}")])

        # Mode selection
        if bot.automation_mode == 'full_cycle':
            keyboard.append([InlineKeyboardButton("📋 Switch to List Only", callback_data=f"bot_mode_list_{bot_id}")])
        else:
            keyboard.append([InlineKeyboardButton("🔄 Switch to Full Cycle", callback_data=f"bot_mode_full_{bot_id}")])

        keyboard.append([InlineKeyboardButton("🗑️ Delete Bot", callback_data=f"bot_delete_{bot_id}")])
        keyboard.append([InlineKeyboardButton("« Back", callback_data=f"session_bots_{bot.session_id}")])

        reply_markup = InlineKeyboardMarkup(keyboard)

        await query.edit_message_text(text, parse_mode='Markdown', reply_markup=reply_markup)

    async def callback_bot_start(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Start bot automation"""
        query = update.callback_query
        await query.answer("Starting automation...")

        bot_id = int(query.data.split('_')[2])

        try:
            await session_manager.start_automation(bot_id)
            await query.edit_message_text(
                "✅ Automation started",
                reply_markup=InlineKeyboardMarkup([[
                    InlineKeyboardButton("« Back", callback_data=f"bot_{bot_id}")
                ]])
            )
        except Exception as e:
            await query.edit_message_text(
                f"❌ Error: {str(e)}",
                reply_markup=InlineKeyboardMarkup([[
                    InlineKeyboardButton("« Back", callback_data=f"bot_{bot_id}")
                ]])
            )

    async def callback_bot_stop(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Stop bot automation"""
        query = update.callback_query
        await query.answer("Stopping automation...")

        bot_id = int(query.data.split('_')[2])

        try:
            await session_manager.stop_automation(bot_id)
            await query.edit_message_text(
                "✅ Automation stopped",
                reply_markup=InlineKeyboardMarkup([[
                    InlineKeyboardButton("« Back", callback_data=f"bot_{bot_id}")
                ]])
            )
        except Exception as e:
            await query.edit_message_text(f"❌ Error: {str(e)}")

    async def callback_bot_mode_change(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Change bot mode"""
        query = update.callback_query
        await query.answer("Changing mode...")

        parts = query.data.split('_')
        mode_type = parts[2]  # 'list' or 'full'
        bot_id = int(parts[3])

        mode = 'list_only' if mode_type == 'list' else 'full_cycle'

        try:
            await session_manager.set_automation_mode(bot_id, mode)
            await query.edit_message_text(
                f"✅ Mode changed to {mode}",
                reply_markup=InlineKeyboardMarkup([[
                    InlineKeyboardButton("« Back", callback_data=f"bot_{bot_id}")
                ]])
            )
        except Exception as e:
            await query.edit_message_text(f"❌ Error: {str(e)}")

    # ==================== Callback Router ====================

    async def callback_handler(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Route callbacks to appropriate handlers"""
        query = update.callback_query
        data = query.data

        # Main menu
        if data == "main_status":
            await self.callback_main_status(update, context)
        elif data == "main_sessions":
            await self.callback_main_sessions(update, context)
        elif data == "main_bots":
            await self.callback_main_bots(update, context)
        elif data == "main_health":
            await self.callback_main_health(update, context)
        elif data == "back_to_main":
            await self.callback_back_to_main(update, context)

        # Session management
        elif data.startswith("session_") and not data.startswith("session_bots_") and not data.startswith("session_connect_") and not data.startswith("session_disconnect_"):
            await self.callback_session_detail(update, context)
        elif data.startswith("session_connect_"):
            await self.callback_session_connect(update, context)
        elif data.startswith("session_disconnect_"):
            await self.callback_session_disconnect(update, context)
        elif data.startswith("session_bots_"):
            await self.callback_session_bots(update, context)

        # Bot management
        elif data.startswith("bot_start_"):
            await self.callback_bot_start(update, context)
        elif data.startswith("bot_stop_"):
            await self.callback_bot_stop(update, context)
        elif data.startswith("bot_mode_"):
            await self.callback_bot_mode_change(update, context)
        elif data.startswith("bot_"):
            await self.callback_bot_detail(update, context)

    # ==================== Run Bot ====================

    async def post_init(self, application: Application):
        """Post-initialization callback"""
        # Initialize session manager
        await session_manager.initialize()
        logger.info("Control bot initialized and ready")

    async def post_shutdown(self, application: Application):
        """Post-shutdown callback"""
        # Shutdown session manager
        await session_manager.shutdown()
        logger.info("Control bot shut down")

    def run(self):
        """Run the bot"""
        logger.info("Starting control bot...")

        # Create application
        self.application = Application.builder().token(self.token).post_init(self.post_init).post_shutdown(self.post_shutdown).build()

        # Add handlers
        self.application.add_handler(CommandHandler("start", self.cmd_start))
        self.application.add_handler(CommandHandler("status", self.cmd_status))
        self.application.add_handler(CallbackQueryHandler(self.callback_handler))

        # Start bot
        self.application.run_polling(allowed_updates=Update.ALL_TYPES)


def main():
    """Main entry point"""
    # Load configuration
    from dotenv import load_dotenv
    load_dotenv('.env.control_bot')

    BOT_TOKEN = os.getenv('CONTROL_BOT_TOKEN')
    AUTHORIZED_IDS = os.getenv('AUTHORIZED_USER_IDS', '').split(',')
    AUTHORIZED_IDS = [int(id.strip()) for id in AUTHORIZED_IDS if id.strip()]

    if not BOT_TOKEN:
        raise ValueError("CONTROL_BOT_TOKEN not set in .env.control_bot")

    if not AUTHORIZED_IDS:
        raise ValueError("AUTHORIZED_USER_IDS not set in .env.control_bot")

    # Initialize database
    db.init_db()

    # Add authorized users to database
    for user_id in AUTHORIZED_IDS:
        if not db.is_user_authorized(user_id):
            db.add_authorized_user(user_id)
            logger.info(f"Added authorized user: {user_id}")

    # Create and run bot
    bot = ControlBot(BOT_TOKEN, AUTHORIZED_IDS)
    bot.run()


if __name__ == '__main__':
    main()
