"""
Telegram Control Bot for managing automation sessions.
Enhanced version with full session and bot management.
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


# Conversation states for adding session
(
    ADD_SESSION_PHONE,
    ADD_SESSION_API_ID,
    ADD_SESSION_API_HASH,
    ADD_SESSION_CODE,
    ADD_SESSION_PASSWORD
) = range(5)

# Conversation states for adding bot
(
    ADD_BOT_SESSION_SELECT,
    ADD_BOT_USERNAME,
    ADD_BOT_MODE,
    ADD_BOT_STEP2_METHOD,
    ADD_BOT_STEP2_KEYWORDS,
    ADD_BOT_STEP2_INDEX
) = range(5, 11)

# Conversation states for reauthorization
(
    REAUTH_CODE,
    REAUTH_PASSWORD
) = range(11, 13)

# Conversation states for Step 2 configuration
(
    CONFIG_STEP2_METHOD,
    CONFIG_STEP2_KEYWORDS,
    CONFIG_STEP2_INDEX
) = range(13, 16)


class ControlBot:
    """Main control bot class with full management features"""

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

        # Temporary storage for conversations
        self.temp_data = {}

    def is_authorized(self, user_id: int) -> bool:
        """Check if user is authorized"""
        return user_id in self.authorized_user_ids or db.is_user_authorized(user_id)

    async def auth_required(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> bool:
        """Check authorization and send error if not authorized"""
        user_id = update.effective_user.id
        if not self.is_authorized(user_id):
            if update.message:
                await update.message.reply_text(
                    "⛔ Вы не авторизованы для использования этого бота.\n"
                    f"Ваш Telegram ID: {user_id}"
                )
            elif update.callback_query:
                await update.callback_query.answer("⛔ Доступ запрещен")
            return False
        return True

    # ==================== Command Handlers ====================

    async def cmd_start(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /start command"""
        if not await self.auth_required(update, context):
            return

        keyboard = [
            [InlineKeyboardButton("📊 Статус", callback_data="main_status")],
            [InlineKeyboardButton("📱 Сессии", callback_data="main_sessions")],
            [InlineKeyboardButton("🤖 Боты", callback_data="main_bots")],
            [InlineKeyboardButton("💚 Проверка здоровья", callback_data="main_health")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)

        await update.message.reply_text(
            "🎮 *Панель управления автоматизацией*\n\n"
            "Добро пожаловать! Выберите опцию:",
            parse_mode='Markdown',
            reply_markup=reply_markup
        )

    async def cmd_status(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /status command"""
        if not await self.auth_required(update, context):
            return

        status = session_manager.get_all_status()

        text = "📊 *Общий статус*\n\n"
        text += f"Всего сессий: {status['total_sessions']}\n"
        text += f"Подключено сессий: {status['connected_sessions']}\n"
        text += f"Всего ботов: {status['total_automations']}\n"
        text += f"Активных ботов: {status['active_automations']}\n\n"

        for session_status in status['sessions']:
            text += f"━━━━━━━━━━━━━━━━\n"
            text += f"📱 *Сессия:* {session_status['phone']}\n"
            text += f"Статус: {'🟢 Подключена' if session_status['is_connected'] else '🔴 Отключена'}\n"

            if session_status['bots']:
                text += f"\n*Боты:*\n"
                for bot in session_status['bots']:
                    status_emoji = "🟢" if bot['running'] else "⚫"
                    mode_emoji = "🔄" if bot['mode'] == 'full_cycle' else "📋"
                    mode_text = "Полный цикл" if bot['mode'] == 'full_cycle' else "Только список"
                    text += f"{status_emoji} {bot['username']} {mode_emoji}\n"
                    text += f"   Режим: {mode_text}\n"
                    text += f"   Успешность: {bot['statistics']['success_rate']:.1f}%\n"
                    text += f"   Всего запусков: {bot['statistics']['total_runs']}\n"

        await update.message.reply_text(text, parse_mode='Markdown')

    # ==================== Main Menu Callbacks ====================

    async def callback_main_status(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Show overall status"""
        query = update.callback_query
        await query.answer()

        status = session_manager.get_all_status()

        text = "📊 *Общий статус*\n\n"
        text += f"Всего сессий: {status['total_sessions']}\n"
        text += f"Подключено сессий: {status['connected_sessions']}\n"
        text += f"Всего ботов: {status['total_automations']}\n"
        text += f"Активных ботов: {status['active_automations']}\n"

        keyboard = [[InlineKeyboardButton("« Назад", callback_data="back_to_main")]]
        reply_markup = InlineKeyboardMarkup(keyboard)

        await query.edit_message_text(text, parse_mode='Markdown', reply_markup=reply_markup)

    async def callback_main_sessions(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Show sessions menu"""
        query = update.callback_query
        await query.answer()

        sessions = db.get_all_sessions()

        text = "📱 *Управление сессиями*\n\n"

        keyboard = []
        for session in sessions:
            status_emoji = "🟢" if session.is_active else "🔴"
            keyboard.append([
                InlineKeyboardButton(
                    f"{status_emoji} {session.phone}",
                    callback_data=f"session_{session.id}"
                )
            ])

        keyboard.append([InlineKeyboardButton("➕ Добавить сессию", callback_data="add_session_start")])
        keyboard.append([InlineKeyboardButton("« Назад", callback_data="back_to_main")])

        reply_markup = InlineKeyboardMarkup(keyboard)

        if not sessions:
            text += "Сессий пока нет.\n"

        await query.edit_message_text(text, parse_mode='Markdown', reply_markup=reply_markup)

    async def callback_main_bots(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Show bots menu"""
        query = update.callback_query
        await query.answer()

        sessions = db.get_all_sessions()

        text = "🤖 *Выберите сессию для управления ботами*\n\n"

        keyboard = []
        for session in sessions:
            bot_count = len(db.get_bots_by_session(session.id))
            keyboard.append([
                InlineKeyboardButton(
                    f"{session.phone} ({bot_count} ботов)",
                    callback_data=f"session_bots_{session.id}"
                )
            ])

        keyboard.append([InlineKeyboardButton("« Назад", callback_data="back_to_main")])

        reply_markup = InlineKeyboardMarkup(keyboard)

        await query.edit_message_text(text, parse_mode='Markdown', reply_markup=reply_markup)

    async def callback_main_health(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Show health check"""
        query = update.callback_query
        await query.answer()

        status = session_manager.get_all_status()

        text = "💚 *Проверка здоровья системы*\n\n"

        all_healthy = True

        for session_status in status['sessions']:
            if not session_status['is_connected']:
                all_healthy = False
                text += f"🔴 Сессия {session_status['phone']} отключена\n"

            for bot in session_status['bots']:
                if bot['enabled'] and not bot['running']:
                    all_healthy = False
                    text += f"⚠️ Бот {bot['username']} должен работать, но неактивен\n"

                if bot['statistics']['success_rate'] < 50 and bot['statistics']['total_runs'] > 10:
                    all_healthy = False
                    text += f"⚠️ Бот {bot['username']} имеет низкую успешность ({bot['statistics']['success_rate']:.1f}%)\n"

        if all_healthy:
            text += "✅ Все системы работают нормально\n"

        keyboard = [[InlineKeyboardButton("« Назад", callback_data="back_to_main")]]
        reply_markup = InlineKeyboardMarkup(keyboard)

        await query.edit_message_text(text, parse_mode='Markdown', reply_markup=reply_markup)

    async def callback_back_to_main(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Back to main menu"""
        query = update.callback_query
        await query.answer()

        keyboard = [
            [InlineKeyboardButton("📊 Статус", callback_data="main_status")],
            [InlineKeyboardButton("📱 Сессии", callback_data="main_sessions")],
            [InlineKeyboardButton("🤖 Боты", callback_data="main_bots")],
            [InlineKeyboardButton("💚 Проверка здоровья", callback_data="main_health")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)

        await query.edit_message_text(
            "🎮 *Панель управления*\n\nВыберите опцию:",
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

        text = f"📱 *Сессия: {session_status['phone']}*\n\n"
        text += f"Статус: {'🟢 Подключена' if session_status['is_connected'] else '🔴 Отключена'}\n"

        if session_status['last_connected']:
            text += f"Последнее подключение: {session_status['last_connected']}\n"

        text += f"\n*Боты ({len(session_status['bots'])}):*\n"

        for bot in session_status['bots']:
            status_emoji = "🟢" if bot['running'] else "⚫"
            text += f"{status_emoji} {bot['username']}\n"

        keyboard = []

        if session_status['is_connected']:
            keyboard.append([InlineKeyboardButton("🔌 Отключить", callback_data=f"session_disconnect_{session_id}")])
        else:
            keyboard.append([InlineKeyboardButton("🔌 Подключить", callback_data=f"session_connect_{session_id}")])
            keyboard.append([InlineKeyboardButton("🔐 Переавторизация", callback_data=f"session_reauth_{session_id}")])

        keyboard.append([InlineKeyboardButton("🤖 Управление ботами", callback_data=f"session_bots_{session_id}")])
        keyboard.append([InlineKeyboardButton("🗑️ Удалить сессию", callback_data=f"session_delete_confirm_{session_id}")])
        keyboard.append([InlineKeyboardButton("« Назад", callback_data="main_sessions")])

        reply_markup = InlineKeyboardMarkup(keyboard)

        await query.edit_message_text(text, parse_mode='Markdown', reply_markup=reply_markup)

    async def callback_session_connect(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Connect a session"""
        query = update.callback_query
        await query.answer("Подключаем сессию...")

        session_id = int(query.data.split('_')[2])

        try:
            success = await session_manager.connect_session(session_id)
            if success:
                await query.edit_message_text(
                    "✅ Сессия успешно подключена",
                    reply_markup=InlineKeyboardMarkup([[
                        InlineKeyboardButton("« Назад", callback_data=f"session_{session_id}")
                    ]])
                )
            else:
                await query.edit_message_text(
                    "⚠️ Сессия требует авторизации. Используйте кнопку 'Переавторизация'.",
                    reply_markup=InlineKeyboardMarkup([[
                        InlineKeyboardButton("« Назад", callback_data=f"session_{session_id}")
                    ]])
                )
        except Exception as e:
            await query.edit_message_text(
                f"❌ Ошибка: {str(e)}",
                reply_markup=InlineKeyboardMarkup([[
                    InlineKeyboardButton("« Назад", callback_data=f"session_{session_id}")
                ]])
            )

    async def callback_session_disconnect(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Disconnect a session"""
        query = update.callback_query
        await query.answer("Отключаем сессию...")

        session_id = int(query.data.split('_')[2])

        try:
            await session_manager.disconnect_session(session_id)
            await query.edit_message_text(
                "✅ Сессия отключена",
                reply_markup=InlineKeyboardMarkup([[
                    InlineKeyboardButton("« Назад", callback_data=f"session_{session_id}")
                ]])
            )
        except Exception as e:
            await query.edit_message_text(f"❌ Ошибка: {str(e)}")

    async def callback_session_delete_confirm(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Confirm session deletion"""
        query = update.callback_query
        await query.answer()

        session_id = int(query.data.split('_')[3])
        session = db.get_session_by_id(session_id)

        text = f"⚠️ *Подтверждение удаления*\n\n"
        text += f"Вы уверены, что хотите удалить сессию *{session.phone}*?\n\n"
        text += "Все боты этой сессии также будут удалены!"

        keyboard = [
            [InlineKeyboardButton("❌ Да, удалить", callback_data=f"session_delete_{session_id}")],
            [InlineKeyboardButton("« Отмена", callback_data=f"session_{session_id}")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)

        await query.edit_message_text(text, parse_mode='Markdown', reply_markup=reply_markup)

    async def callback_session_delete(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Delete a session"""
        query = update.callback_query
        await query.answer("Удаляем сессию...")

        session_id = int(query.data.split('_')[2])

        try:
            # First disconnect
            if session_id in session_manager.sessions:
                await session_manager.disconnect_session(session_id)

            # Then delete
            db.delete_session(session_id)

            await query.edit_message_text(
                "✅ Сессия удалена",
                reply_markup=InlineKeyboardMarkup([[
                    InlineKeyboardButton("« Назад", callback_data="main_sessions")
                ]])
            )
        except Exception as e:
            await query.edit_message_text(f"❌ Ошибка: {str(e)}")

    # ==================== Bot Management ====================

    async def callback_session_bots(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Show bots for a session"""
        query = update.callback_query
        await query.answer()

        session_id = int(query.data.split('_')[2])
        session = db.get_session_by_id(session_id)
        bots = db.get_bots_by_session(session_id)

        text = f"🤖 *Боты для {session.phone}*\n\n"

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

        keyboard.append([InlineKeyboardButton("➕ Добавить бота", callback_data=f"add_bot_start_{session_id}")])
        keyboard.append([InlineKeyboardButton("« Назад", callback_data=f"session_{session_id}")])

        reply_markup = InlineKeyboardMarkup(keyboard)

        if not bots:
            text += "Ботов пока нет.\n"

        await query.edit_message_text(text, parse_mode='Markdown', reply_markup=reply_markup)

    async def callback_bot_detail(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Show bot detail and controls"""
        query = update.callback_query
        await query.answer()

        bot_id = int(query.data.split('_')[1])
        bot = db.get_bot_by_id(bot_id)
        stats = db.get_statistics(bot_id)

        is_running = bot_id in session_manager.automations

        mode_text = "Полный цикл" if bot.automation_mode == 'full_cycle' else "Только список"

        text = f"🤖 *{bot.bot_username}*\n\n"
        text += f"Статус: {'🟢 Работает' if is_running else '⚫ Остановлен'}\n"
        text += f"Режим: {mode_text}\n"

        # Step 2 configuration
        if bot.step2_button_keywords:
            text += f"Шаг 2: по ключевым словам ({bot.step2_button_keywords})\n"
        else:
            text += f"Шаг 2: кнопка #{bot.step2_button_index + 1}\n"

        if stats:
            text += f"\n*Статистика:*\n"
            text += f"Всего запусков: {stats.total_runs}\n"
            text += f"Успешность: {stats.success_rate:.1f}%\n"
            text += f"Всего кликов: {stats.total_clicks}\n"
            text += f"Успешность кликов: {stats.click_success_rate:.1f}%\n"

            if stats.last_activity_at:
                text += f"Последняя активность: {stats.last_activity_at.strftime('%Y-%m-%d %H:%M:%S')}\n"

            if stats.last_error:
                text += f"\n⚠️ Последняя ошибка: {stats.last_error}\n"

        keyboard = []

        # Start/Stop button
        if is_running:
            keyboard.append([InlineKeyboardButton("⏹️ Остановить", callback_data=f"bot_stop_{bot_id}")])
        else:
            keyboard.append([InlineKeyboardButton("▶️ Запустить", callback_data=f"bot_start_{bot_id}")])

        # Mode selection
        if bot.automation_mode == 'full_cycle':
            keyboard.append([InlineKeyboardButton("📋 Переключить на режим 'Только список'", callback_data=f"bot_mode_list_{bot_id}")])
        else:
            keyboard.append([InlineKeyboardButton("🔄 Переключить на режим 'Полный цикл'", callback_data=f"bot_mode_full_{bot_id}")])

        # Step 2 configuration
        keyboard.append([InlineKeyboardButton("⚙️ Настроить Шаг 2", callback_data=f"config_step2_start_{bot_id}")])

        keyboard.append([InlineKeyboardButton("🗑️ Удалить бота", callback_data=f"bot_delete_confirm_{bot_id}")])
        keyboard.append([InlineKeyboardButton("« Назад", callback_data=f"session_bots_{bot.session_id}")])

        reply_markup = InlineKeyboardMarkup(keyboard)

        await query.edit_message_text(text, parse_mode='Markdown', reply_markup=reply_markup)

    async def callback_bot_start(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Start bot automation"""
        query = update.callback_query
        await query.answer("Запускаем автоматизацию...")

        bot_id = int(query.data.split('_')[2])

        try:
            await session_manager.start_automation(bot_id)
            await query.edit_message_text(
                "✅ Автоматизация запущена",
                reply_markup=InlineKeyboardMarkup([[
                    InlineKeyboardButton("« Назад", callback_data=f"bot_{bot_id}")
                ]])
            )
        except Exception as e:
            await query.edit_message_text(
                f"❌ Ошибка: {str(e)}",
                reply_markup=InlineKeyboardMarkup([[
                    InlineKeyboardButton("« Назад", callback_data=f"bot_{bot_id}")
                ]])
            )

    async def callback_bot_stop(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Stop bot automation"""
        query = update.callback_query
        await query.answer("Останавливаем автоматизацию...")

        bot_id = int(query.data.split('_')[2])

        try:
            await session_manager.stop_automation(bot_id)
            await query.edit_message_text(
                "✅ Автоматизация остановлена",
                reply_markup=InlineKeyboardMarkup([[
                    InlineKeyboardButton("« Назад", callback_data=f"bot_{bot_id}")
                ]])
            )
        except Exception as e:
            await query.edit_message_text(f"❌ Ошибка: {str(e)}")

    async def callback_bot_mode_change(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Change bot mode"""
        query = update.callback_query
        await query.answer("Меняем режим...")

        parts = query.data.split('_')
        mode_type = parts[2]  # 'list' or 'full'
        bot_id = int(parts[3])

        mode = 'list_only' if mode_type == 'list' else 'full_cycle'

        try:
            await session_manager.set_automation_mode(bot_id, mode)
            await query.edit_message_text(
                f"✅ Режим изменен на {mode}",
                reply_markup=InlineKeyboardMarkup([[
                    InlineKeyboardButton("« Назад", callback_data=f"bot_{bot_id}")
                ]])
            )
        except Exception as e:
            await query.edit_message_text(f"❌ Ошибка: {str(e)}")

    async def callback_bot_delete_confirm(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Confirm bot deletion"""
        query = update.callback_query
        await query.answer()

        bot_id = int(query.data.split('_')[3])
        bot = db.get_bot_by_id(bot_id)

        text = f"⚠️ *Подтверждение удаления*\n\n"
        text += f"Вы уверены, что хотите удалить бота *{bot.bot_username}*?"

        keyboard = [
            [InlineKeyboardButton("❌ Да, удалить", callback_data=f"bot_delete_{bot_id}")],
            [InlineKeyboardButton("« Отмена", callback_data=f"bot_{bot_id}")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)

        await query.edit_message_text(text, parse_mode='Markdown', reply_markup=reply_markup)

    async def callback_bot_delete(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Delete a bot"""
        query = update.callback_query
        await query.answer("Удаляем бота...")

        bot_id = int(query.data.split('_')[2])
        bot = db.get_bot_by_id(bot_id)
        session_id = bot.session_id

        try:
            # First stop if running
            if bot_id in session_manager.automations:
                await session_manager.stop_automation(bot_id)

            # Then delete
            db.delete_bot(bot_id)

            await query.edit_message_text(
                "✅ Бот удален",
                reply_markup=InlineKeyboardMarkup([[
                    InlineKeyboardButton("« Назад", callback_data=f"session_bots_{session_id}")
                ]])
            )
        except Exception as e:
            await query.edit_message_text(f"❌ Ошибка: {str(e)}")

    # ==================== Add Session Conversation ====================

    async def add_session_start(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Start add session conversation"""
        query = update.callback_query
        await query.answer()

        user_id = update.effective_user.id
        self.temp_data[user_id] = {}

        await query.edit_message_text(
            "📱 *Добавление новой сессии*\n\n"
            "Введите номер телефона в международном формате (например, +79991234567):",
            parse_mode='Markdown'
        )

        return ADD_SESSION_PHONE

    async def add_session_phone(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Receive phone number"""
        user_id = update.effective_user.id
        phone = update.message.text.strip()

        # Validate phone
        if not phone.startswith('+') or len(phone) < 10:
            await update.message.reply_text(
                "❌ Неверный формат номера. Используйте международный формат, например: +79991234567\n\n"
                "Введите номер еще раз:"
            )
            return ADD_SESSION_PHONE

        self.temp_data[user_id]['phone'] = phone

        await update.message.reply_text(
            "Отлично! Теперь введите ваш *API ID* от Telegram:\n"
            "(Получить можно на https://my.telegram.org/apps)",
            parse_mode='Markdown'
        )

        return ADD_SESSION_API_ID

    async def add_session_api_id(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Receive API ID"""
        user_id = update.effective_user.id
        api_id_text = update.message.text.strip()

        try:
            api_id = int(api_id_text)
            self.temp_data[user_id]['api_id'] = api_id

            await update.message.reply_text(
                "Отлично! Теперь введите ваш *API Hash* от Telegram:",
                parse_mode='Markdown'
            )

            return ADD_SESSION_API_HASH
        except ValueError:
            await update.message.reply_text(
                "❌ API ID должен быть числом. Введите еще раз:"
            )
            return ADD_SESSION_API_ID

    async def add_session_api_hash(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Receive API Hash and create session"""
        user_id = update.effective_user.id
        api_hash = update.message.text.strip()

        self.temp_data[user_id]['api_hash'] = api_hash

        phone = self.temp_data[user_id]['phone']
        api_id = self.temp_data[user_id]['api_id']

        try:
            # Create session
            session = await session_manager.add_session(phone, api_id, api_hash)
            self.temp_data[user_id]['session_id'] = session.id

            # Request authorization code
            result = await session_manager.authorize_session(session.id, phone)

            if result['status'] == 'code_sent':
                await update.message.reply_text(
                    f"✅ Сессия создана!\n\n"
                    f"📱 Код подтверждения отправлен в Telegram на номер {phone}\n\n"
                    f"Введите код (например: 12345):"
                )
                return ADD_SESSION_CODE
            else:
                await update.message.reply_text(f"❌ Ошибка: {result['message']}")
                return ConversationHandler.END

        except Exception as e:
            await update.message.reply_text(f"❌ Ошибка при создании сессии: {str(e)}")
            return ConversationHandler.END

    async def add_session_code(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Receive verification code"""
        user_id = update.effective_user.id
        code = update.message.text.strip()

        session_id = self.temp_data[user_id]['session_id']
        phone = self.temp_data[user_id]['phone']

        try:
            result = await session_manager.authorize_session(session_id, phone, code=code)

            if result['status'] == 'authorized':
                await update.message.reply_text(
                    "✅ Сессия успешно авторизована!\n\n"
                    "Теперь можете добавить ботов для этой сессии.",
                    reply_markup=InlineKeyboardMarkup([[
                        InlineKeyboardButton("« Вернуться к сессиям", callback_data="main_sessions")
                    ]])
                )
                return ConversationHandler.END

            elif result['status'] == 'need_password':
                await update.message.reply_text(
                    "🔐 Требуется пароль двухфакторной аутентификации.\n\n"
                    "Введите ваш 2FA пароль:"
                )
                return ADD_SESSION_PASSWORD

            else:
                await update.message.reply_text(f"❌ Ошибка: {result['message']}")
                return ConversationHandler.END

        except Exception as e:
            await update.message.reply_text(f"❌ Ошибка при авторизации: {str(e)}")
            return ConversationHandler.END

    async def add_session_password(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Receive 2FA password"""
        user_id = update.effective_user.id
        password = update.message.text.strip()

        session_id = self.temp_data[user_id]['session_id']

        try:
            result = await session_manager.authorize_session(session_id, None, password=password)

            if result['status'] == 'authorized':
                await update.message.reply_text(
                    "✅ Сессия успешно авторизована с 2FA!\n\n"
                    "Теперь можете добавить ботов для этой сессии.",
                    reply_markup=InlineKeyboardMarkup([[
                        InlineKeyboardButton("« Вернуться к сессиям", callback_data="main_sessions")
                    ]])
                )
                return ConversationHandler.END
            else:
                await update.message.reply_text(f"❌ Ошибка: {result['message']}")
                return ConversationHandler.END

        except Exception as e:
            await update.message.reply_text(f"❌ Ошибка при авторизации: {str(e)}")
            return ConversationHandler.END

    async def add_session_cancel(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Cancel add session conversation"""
        user_id = update.effective_user.id
        if user_id in self.temp_data:
            del self.temp_data[user_id]

        if update.message:
            await update.message.reply_text(
                "❌ Добавление сессии отменено.",
                reply_markup=InlineKeyboardMarkup([[
                    InlineKeyboardButton("« Назад", callback_data="main_sessions")
                ]])
            )
        elif update.callback_query:
            await update.callback_query.edit_message_text(
                "❌ Добавление сессии отменено.",
                reply_markup=InlineKeyboardMarkup([[
                    InlineKeyboardButton("« Назад", callback_data="main_sessions")
                ]])
            )

        return ConversationHandler.END

    # ==================== Add Bot Conversation ====================

    async def add_bot_start(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Start add bot conversation"""
        query = update.callback_query
        await query.answer()

        session_id = int(query.data.split('_')[3])
        session = db.get_session_by_id(session_id)

        user_id = update.effective_user.id
        self.temp_data[user_id] = {'session_id': session_id}

        await query.edit_message_text(
            f"🤖 *Добавление бота для {session.phone}*\n\n"
            f"Введите username бота (например: @apri1l_test_bot):",
            parse_mode='Markdown'
        )

        return ADD_BOT_USERNAME

    async def add_bot_username(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Receive bot username"""
        user_id = update.effective_user.id
        username = update.message.text.strip()

        # Add @ if not present
        if not username.startswith('@'):
            username = '@' + username

        self.temp_data[user_id]['bot_username'] = username

        keyboard = [
            [InlineKeyboardButton("🔄 Полный цикл (3 кнопки)", callback_data="addbot_mode_full")],
            [InlineKeyboardButton("📋 Только список (1 кнопка)", callback_data="addbot_mode_list")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)

        await update.message.reply_text(
            f"Отлично! Бот: {username}\n\n"
            "Теперь выберите режим работы:",
            reply_markup=reply_markup
        )

        return ADD_BOT_MODE

    async def add_bot_mode(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Receive automation mode"""
        query = update.callback_query
        await query.answer()

        user_id = update.effective_user.id
        mode_type = query.data.split('_')[2]  # 'full' or 'list'

        mode = 'full_cycle' if mode_type == 'full' else 'list_only'
        self.temp_data[user_id]['mode'] = mode

        # If list_only, skip Step 2 config
        if mode == 'list_only':
            # Create bot immediately
            await self._create_bot(user_id, query)
            return ConversationHandler.END

        # Otherwise ask about Step 2 configuration
        keyboard = [
            [InlineKeyboardButton("🔢 По номеру кнопки (1-я, 2-я, ...)", callback_data="addbot_step2_index")],
            [InlineKeyboardButton("🔤 По ключевым словам", callback_data="addbot_step2_keywords")],
            [InlineKeyboardButton("⏩ Пропустить (1-я кнопка)", callback_data="addbot_step2_skip")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)

        await query.edit_message_text(
            "⚙️ *Настройка Шага 2*\n\n"
            "Как выбирать кнопку на втором шаге?",
            parse_mode='Markdown',
            reply_markup=reply_markup
        )

        return ADD_BOT_STEP2_METHOD

    async def add_bot_step2_method(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Choose Step 2 method"""
        query = update.callback_query
        await query.answer()

        user_id = update.effective_user.id
        method = query.data.split('_')[2]  # 'index', 'keywords', or 'skip'

        if method == 'skip':
            # Use default (first button)
            self.temp_data[user_id]['step2_keywords'] = None
            self.temp_data[user_id]['step2_index'] = 0
            await self._create_bot(user_id, query)
            return ConversationHandler.END

        elif method == 'index':
            await query.edit_message_text(
                "🔢 *Выбор по номеру кнопки*\n\n"
                "Введите номер кнопки (1 = первая, 2 = вторая, и т.д.):",
                parse_mode='Markdown'
            )
            return ADD_BOT_STEP2_INDEX

        elif method == 'keywords':
            await query.edit_message_text(
                "🔤 *Выбор по ключевым словам*\n\n"
                "Введите ключевые слова через запятую (например: Москва,доставка):",
                parse_mode='Markdown'
            )
            return ADD_BOT_STEP2_KEYWORDS

    async def add_bot_step2_index(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Receive button index"""
        user_id = update.effective_user.id
        index_text = update.message.text.strip()

        try:
            index = int(index_text) - 1  # Convert to 0-based
            if index < 0:
                raise ValueError("Index must be >= 1")

            self.temp_data[user_id]['step2_keywords'] = None
            self.temp_data[user_id]['step2_index'] = index

            await self._create_bot_from_message(user_id, update.message)
            return ConversationHandler.END

        except ValueError:
            await update.message.reply_text(
                "❌ Введите корректный номер (целое число >= 1):"
            )
            return ADD_BOT_STEP2_INDEX

    async def add_bot_step2_keywords(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Receive keywords"""
        user_id = update.effective_user.id
        keywords = update.message.text.strip()

        self.temp_data[user_id]['step2_keywords'] = keywords
        self.temp_data[user_id]['step2_index'] = 0

        await self._create_bot_from_message(user_id, update.message)
        return ConversationHandler.END

    async def _create_bot(self, user_id: int, query):
        """Helper to create bot"""
        data = self.temp_data[user_id]

        try:
            bot = await session_manager.add_bot(
                data['session_id'],
                data['bot_username'],
                data['mode']
            )

            # Update Step 2 config if present
            if 'step2_keywords' in data or 'step2_index' in data:
                db.update_bot_step2_config(
                    bot.id,
                    data.get('step2_keywords'),
                    data.get('step2_index', 0)
                )

            mode_text = "Полный цикл" if data['mode'] == 'full_cycle' else "Только список"

            await query.edit_message_text(
                f"✅ Бот {data['bot_username']} успешно добавлен!\n\n"
                f"Режим: {mode_text}",
                reply_markup=InlineKeyboardMarkup([[
                    InlineKeyboardButton("« К ботам", callback_data=f"session_bots_{data['session_id']}")
                ]])
            )

        except Exception as e:
            await query.edit_message_text(f"❌ Ошибка при создании бота: {str(e)}")

    async def _create_bot_from_message(self, user_id: int, message):
        """Helper to create bot from message context"""
        data = self.temp_data[user_id]

        try:
            bot = await session_manager.add_bot(
                data['session_id'],
                data['bot_username'],
                data['mode']
            )

            # Update Step 2 config
            db.update_bot_step2_config(
                bot.id,
                data.get('step2_keywords'),
                data.get('step2_index', 0)
            )

            mode_text = "Полный цикл" if data['mode'] == 'full_cycle' else "Только список"

            await message.reply_text(
                f"✅ Бот {data['bot_username']} успешно добавлен!\n\n"
                f"Режим: {mode_text}",
                reply_markup=InlineKeyboardMarkup([[
                    InlineKeyboardButton("« К ботам", callback_data=f"session_bots_{data['session_id']}")
                ]])
            )

        except Exception as e:
            await message.reply_text(f"❌ Ошибка при создании бота: {str(e)}")

    async def add_bot_cancel(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Cancel add bot conversation"""
        user_id = update.effective_user.id

        session_id = None
        if user_id in self.temp_data:
            session_id = self.temp_data[user_id].get('session_id')
            del self.temp_data[user_id]

        if update.message:
            await update.message.reply_text(
                "❌ Добавление бота отменено.",
                reply_markup=InlineKeyboardMarkup([[
                    InlineKeyboardButton("« Назад", callback_data=f"session_bots_{session_id}" if session_id else "main_bots")
                ]])
            )
        elif update.callback_query:
            await update.callback_query.edit_message_text(
                "❌ Добавление бота отменено.",
                reply_markup=InlineKeyboardMarkup([[
                    InlineKeyboardButton("« Назад", callback_data=f"session_bots_{session_id}" if session_id else "main_bots")
                ]])
            )

        return ConversationHandler.END

    # ==================== Step 2 Configuration ====================

    async def config_step2_start(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Start Step 2 configuration"""
        query = update.callback_query
        await query.answer()

        bot_id = int(query.data.split('_')[3])
        bot = db.get_bot_by_id(bot_id)

        user_id = update.effective_user.id
        self.temp_data[user_id] = {'bot_id': bot_id}

        current_config = ""
        if bot.step2_button_keywords:
            current_config = f"Текущая настройка: по ключевым словам ({bot.step2_button_keywords})"
        else:
            current_config = f"Текущая настройка: кнопка #{bot.step2_button_index + 1}"

        keyboard = [
            [InlineKeyboardButton("🔢 По номеру кнопки", callback_data="config_step2_index")],
            [InlineKeyboardButton("🔤 По ключевым словам", callback_data="config_step2_keywords")],
            [InlineKeyboardButton("« Отмена", callback_data=f"bot_{bot_id}")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)

        await query.edit_message_text(
            f"⚙️ *Настройка Шага 2 для {bot.bot_username}*\n\n"
            f"{current_config}\n\n"
            "Как выбирать кнопку на втором шаге?",
            parse_mode='Markdown',
            reply_markup=reply_markup
        )

        return CONFIG_STEP2_METHOD

    async def config_step2_method(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Choose Step 2 configuration method"""
        query = update.callback_query
        await query.answer()

        user_id = update.effective_user.id
        method = query.data.split('_')[2]  # 'index' or 'keywords'

        if method == 'index':
            await query.edit_message_text(
                "🔢 *Выбор по номеру кнопки*\n\n"
                "Введите номер кнопки (1 = первая, 2 = вторая, и т.д.):",
                parse_mode='Markdown'
            )
            return CONFIG_STEP2_INDEX

        elif method == 'keywords':
            await query.edit_message_text(
                "🔤 *Выбор по ключевым словам*\n\n"
                "Введите ключевые слова через запятую (например: Москва,доставка):",
                parse_mode='Markdown'
            )
            return CONFIG_STEP2_KEYWORDS

    async def config_step2_index(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Receive button index"""
        user_id = update.effective_user.id
        index_text = update.message.text.strip()

        try:
            index = int(index_text) - 1  # Convert to 0-based
            if index < 0:
                raise ValueError("Index must be >= 1")

            bot_id = self.temp_data[user_id]['bot_id']

            db.update_bot_step2_config(bot_id, keywords=None, button_index=index)

            # If bot is running, restart it
            if bot_id in session_manager.automations:
                await session_manager.stop_automation(bot_id)
                await session_manager.start_automation(bot_id)

            await update.message.reply_text(
                f"✅ Шаг 2 настроен: кнопка #{index + 1}",
                reply_markup=InlineKeyboardMarkup([[
                    InlineKeyboardButton("« Назад к боту", callback_data=f"bot_{bot_id}")
                ]])
            )

            return ConversationHandler.END

        except ValueError:
            await update.message.reply_text(
                "❌ Введите корректный номер (целое число >= 1):"
            )
            return CONFIG_STEP2_INDEX

    async def config_step2_keywords(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Receive keywords"""
        user_id = update.effective_user.id
        keywords = update.message.text.strip()

        bot_id = self.temp_data[user_id]['bot_id']

        db.update_bot_step2_config(bot_id, keywords=keywords, button_index=0)

        # If bot is running, restart it
        if bot_id in session_manager.automations:
            await session_manager.stop_automation(bot_id)
            await session_manager.start_automation(bot_id)

        await update.message.reply_text(
            f"✅ Шаг 2 настроен: по ключевым словам ({keywords})",
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("« Назад к боту", callback_data=f"bot_{bot_id}")
            ]])
        )

        return ConversationHandler.END

    async def config_step2_cancel(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Cancel Step 2 configuration"""
        user_id = update.effective_user.id

        bot_id = None
        if user_id in self.temp_data:
            bot_id = self.temp_data[user_id].get('bot_id')
            del self.temp_data[user_id]

        if update.message:
            await update.message.reply_text(
                "❌ Настройка отменена.",
                reply_markup=InlineKeyboardMarkup([[
                    InlineKeyboardButton("« Назад", callback_data=f"bot_{bot_id}" if bot_id else "main_bots")
                ]])
            )
        elif update.callback_query:
            await update.callback_query.edit_message_text(
                "❌ Настройка отменена.",
                reply_markup=InlineKeyboardMarkup([[
                    InlineKeyboardButton("« Назад", callback_data=f"bot_{bot_id}" if bot_id else "main_bots")
                ]])
            )

        return ConversationHandler.END

    # ==================== Reauthorization ====================

    async def reauth_start(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Start reauthorization"""
        query = update.callback_query
        await query.answer()

        session_id = int(query.data.split('_')[2])
        session = db.get_session_by_id(session_id)

        user_id = update.effective_user.id
        self.temp_data[user_id] = {'session_id': session_id}

        try:
            # Request new code
            result = await session_manager.authorize_session(session_id, session.phone)

            if result['status'] == 'code_sent':
                await query.edit_message_text(
                    f"🔐 *Переавторизация {session.phone}*\n\n"
                    f"Код подтверждения отправлен в Telegram.\n\n"
                    f"Введите код:",
                    parse_mode='Markdown'
                )
                return REAUTH_CODE
            else:
                await query.edit_message_text(
                    f"❌ Ошибка: {result['message']}",
                    reply_markup=InlineKeyboardMarkup([[
                        InlineKeyboardButton("« Назад", callback_data=f"session_{session_id}")
                    ]])
                )
                return ConversationHandler.END

        except Exception as e:
            await query.edit_message_text(
                f"❌ Ошибка: {str(e)}",
                reply_markup=InlineKeyboardMarkup([[
                    InlineKeyboardButton("« Назад", callback_data=f"session_{session_id}")
                ]])
            )
            return ConversationHandler.END

    async def reauth_code(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Receive reauth code"""
        user_id = update.effective_user.id
        code = update.message.text.strip()

        session_id = self.temp_data[user_id]['session_id']
        session = db.get_session_by_id(session_id)

        try:
            result = await session_manager.authorize_session(session_id, session.phone, code=code)

            if result['status'] == 'authorized':
                await update.message.reply_text(
                    "✅ Сессия успешно переавторизована!",
                    reply_markup=InlineKeyboardMarkup([[
                        InlineKeyboardButton("« К сессии", callback_data=f"session_{session_id}")
                    ]])
                )
                return ConversationHandler.END

            elif result['status'] == 'need_password':
                await update.message.reply_text(
                    "🔐 Требуется пароль 2FA.\n\n"
                    "Введите ваш пароль:"
                )
                return REAUTH_PASSWORD

            else:
                await update.message.reply_text(
                    f"❌ Ошибка: {result['message']}",
                    reply_markup=InlineKeyboardMarkup([[
                        InlineKeyboardButton("« К сессии", callback_data=f"session_{session_id}")
                    ]])
                )
                return ConversationHandler.END

        except Exception as e:
            await update.message.reply_text(
                f"❌ Ошибка: {str(e)}",
                reply_markup=InlineKeyboardMarkup([[
                    InlineKeyboardButton("« К сессии", callback_data=f"session_{session_id}")
                ]])
            )
            return ConversationHandler.END

    async def reauth_password(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Receive reauth password"""
        user_id = update.effective_user.id
        password = update.message.text.strip()

        session_id = self.temp_data[user_id]['session_id']

        try:
            result = await session_manager.authorize_session(session_id, None, password=password)

            if result['status'] == 'authorized':
                await update.message.reply_text(
                    "✅ Сессия успешно переавторизована с 2FA!",
                    reply_markup=InlineKeyboardMarkup([[
                        InlineKeyboardButton("« К сессии", callback_data=f"session_{session_id}")
                    ]])
                )
                return ConversationHandler.END
            else:
                await update.message.reply_text(
                    f"❌ Ошибка: {result['message']}",
                    reply_markup=InlineKeyboardMarkup([[
                        InlineKeyboardButton("« К сессии", callback_data=f"session_{session_id}")
                    ]])
                )
                return ConversationHandler.END

        except Exception as e:
            await update.message.reply_text(
                f"❌ Ошибка: {str(e)}",
                reply_markup=InlineKeyboardMarkup([[
                    InlineKeyboardButton("« К сессии", callback_data=f"session_{session_id}")
                ]])
            )
            return ConversationHandler.END

    async def reauth_cancel(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Cancel reauthorization"""
        user_id = update.effective_user.id

        session_id = None
        if user_id in self.temp_data:
            session_id = self.temp_data[user_id].get('session_id')
            del self.temp_data[user_id]

        if update.message:
            await update.message.reply_text(
                "❌ Переавторизация отменена.",
                reply_markup=InlineKeyboardMarkup([[
                    InlineKeyboardButton("« Назад", callback_data=f"session_{session_id}" if session_id else "main_sessions")
                ]])
            )
        elif update.callback_query:
            await update.callback_query.edit_message_text(
                "❌ Переавторизация отменена.",
                reply_markup=InlineKeyboardMarkup([[
                    InlineKeyboardButton("« Назад", callback_data=f"session_{session_id}" if session_id else "main_sessions")
                ]])
            )

        return ConversationHandler.END

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
        elif data.startswith("session_") and not any([
            data.startswith("session_bots_"),
            data.startswith("session_connect_"),
            data.startswith("session_disconnect_"),
            data.startswith("session_delete_confirm_"),
            data.startswith("session_delete_"),
            data.startswith("session_reauth_")
        ]):
            await self.callback_session_detail(update, context)
        elif data.startswith("session_connect_"):
            await self.callback_session_connect(update, context)
        elif data.startswith("session_disconnect_"):
            await self.callback_session_disconnect(update, context)
        elif data.startswith("session_delete_confirm_"):
            await self.callback_session_delete_confirm(update, context)
        elif data.startswith("session_delete_") and not data.startswith("session_delete_confirm_"):
            await self.callback_session_delete(update, context)
        elif data.startswith("session_bots_"):
            await self.callback_session_bots(update, context)

        # Bot management
        elif data.startswith("bot_start_"):
            await self.callback_bot_start(update, context)
        elif data.startswith("bot_stop_"):
            await self.callback_bot_stop(update, context)
        elif data.startswith("bot_mode_"):
            await self.callback_bot_mode_change(update, context)
        elif data.startswith("bot_delete_confirm_"):
            await self.callback_bot_delete_confirm(update, context)
        elif data.startswith("bot_delete_") and not data.startswith("bot_delete_confirm_"):
            await self.callback_bot_delete(update, context)
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
        self.application = (
            Application.builder()
            .token(self.token)
            .post_init(self.post_init)
            .post_shutdown(self.post_shutdown)
            .build()
        )

        # Add basic handlers
        self.application.add_handler(CommandHandler("start", self.cmd_start))
        self.application.add_handler(CommandHandler("status", self.cmd_status))

        # Add session conversation
        add_session_conv = ConversationHandler(
            entry_points=[
                CallbackQueryHandler(self.add_session_start, pattern="^add_session_start$")
            ],
            states={
                ADD_SESSION_PHONE: [MessageHandler(filters.TEXT & ~filters.COMMAND, self.add_session_phone)],
                ADD_SESSION_API_ID: [MessageHandler(filters.TEXT & ~filters.COMMAND, self.add_session_api_id)],
                ADD_SESSION_API_HASH: [MessageHandler(filters.TEXT & ~filters.COMMAND, self.add_session_api_hash)],
                ADD_SESSION_CODE: [MessageHandler(filters.TEXT & ~filters.COMMAND, self.add_session_code)],
                ADD_SESSION_PASSWORD: [MessageHandler(filters.TEXT & ~filters.COMMAND, self.add_session_password)],
            },
            fallbacks=[CommandHandler("cancel", self.add_session_cancel)],
            name="add_session",
            persistent=False
        )
        self.application.add_handler(add_session_conv)

        # Add bot conversation
        add_bot_conv = ConversationHandler(
            entry_points=[
                CallbackQueryHandler(self.add_bot_start, pattern="^add_bot_start_\d+$")
            ],
            states={
                ADD_BOT_USERNAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, self.add_bot_username)],
                ADD_BOT_MODE: [
                    CallbackQueryHandler(self.add_bot_mode, pattern="^addbot_mode_(full|list)$")
                ],
                ADD_BOT_STEP2_METHOD: [
                    CallbackQueryHandler(self.add_bot_step2_method, pattern="^addbot_step2_(index|keywords|skip)$")
                ],
                ADD_BOT_STEP2_INDEX: [MessageHandler(filters.TEXT & ~filters.COMMAND, self.add_bot_step2_index)],
                ADD_BOT_STEP2_KEYWORDS: [MessageHandler(filters.TEXT & ~filters.COMMAND, self.add_bot_step2_keywords)],
            },
            fallbacks=[CommandHandler("cancel", self.add_bot_cancel)],
            name="add_bot",
            persistent=False
        )
        self.application.add_handler(add_bot_conv)

        # Step 2 configuration conversation
        config_step2_conv = ConversationHandler(
            entry_points=[
                CallbackQueryHandler(self.config_step2_start, pattern="^config_step2_start_\d+$")
            ],
            states={
                CONFIG_STEP2_METHOD: [
                    CallbackQueryHandler(self.config_step2_method, pattern="^config_step2_(index|keywords)$")
                ],
                CONFIG_STEP2_INDEX: [MessageHandler(filters.TEXT & ~filters.COMMAND, self.config_step2_index)],
                CONFIG_STEP2_KEYWORDS: [MessageHandler(filters.TEXT & ~filters.COMMAND, self.config_step2_keywords)],
            },
            fallbacks=[CommandHandler("cancel", self.config_step2_cancel)],
            name="config_step2",
            persistent=False
        )
        self.application.add_handler(config_step2_conv)

        # Reauthorization conversation
        reauth_conv = ConversationHandler(
            entry_points=[
                CallbackQueryHandler(self.reauth_start, pattern="^session_reauth_\d+$")
            ],
            states={
                REAUTH_CODE: [MessageHandler(filters.TEXT & ~filters.COMMAND, self.reauth_code)],
                REAUTH_PASSWORD: [MessageHandler(filters.TEXT & ~filters.COMMAND, self.reauth_password)],
            },
            fallbacks=[CommandHandler("cancel", self.reauth_cancel)],
            name="reauth",
            persistent=False
        )
        self.application.add_handler(reauth_conv)

        # Add callback handler (must be last)
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
