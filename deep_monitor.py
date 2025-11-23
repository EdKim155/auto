#!/usr/bin/env python3
"""
Глубокий мониторинг бота @ACarriers_bot
Только наблюдение - НЕ нажимает кнопки!
Собирает детальную статистику для оптимизации автоматизации
"""

import asyncio
import logging
from datetime import datetime
from typing import Optional, Dict, List
from telethon import TelegramClient, events
from telethon.tl.custom import Message
from telethon.tl.types import KeyboardButtonCallback

# ============================================================================
# КОНФИГУРАЦИЯ
# ============================================================================
API_ID = 27270483
API_HASH = '054487666c6a886114b50b6210e8c051'
PHONE = '+79507380505'
BOT_USERNAME = '@ACarriers_bot'
SESSION_NAME = 'deep_monitor_session'

# Триггеры для отслеживания
TRIGGER_TEXTS = ['Появились новые перевозки', 'новые перевозки', 'перевозки']

# ============================================================================
# ЛОГИРОВАНИЕ
# ============================================================================
logging.basicConfig(
    format='%(asctime)s.%(msecs)03d - %(levelname)s - %(message)s',
    datefmt='%H:%M:%S',
    level=logging.INFO,
    handlers=[
        logging.FileHandler('deep_monitor.log', encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)
logging.getLogger('telethon').setLevel(logging.WARNING)


class DeepMonitor:
    """Глубокий мониторинг бота без вмешательства"""

    def __init__(self):
        self.client = None
        self.bot_entity = None

        # Отслеживание сообщений
        self.last_message_time: Optional[datetime] = None
        self.message_history: Dict[int, List[Dict]] = {}  # message_id -> list of events

        # Статистика
        self.stats = {
            'total_messages': 0,
            'new_messages': 0,
            'edits': 0,
            'triggers_detected': 0,
            'messages_with_buttons': 0,
            'messages_without_buttons': 0,
            'start_time': datetime.now(),

            # Задержки
            'edit_delays': [],  # Задержки между редактированиями
            'response_times': [],  # Время отклика бота

            # Кнопки
            'button_texts_seen': set(),
            'menu_structures': []
        }

    async def start(self):
        """Запуск мониторинга"""
        logger.info('='*70)
        logger.info('🔍 DEEP MONITOR - Запуск глубокого мониторинга')
        logger.info('='*70)
        logger.info(f'Бот: {BOT_USERNAME}')
        logger.info(f'Режим: ТОЛЬКО НАБЛЮДЕНИЕ (не нажимает кнопки)')
        logger.info('='*70)

        # Инициализация клиента
        self.client = TelegramClient(SESSION_NAME, API_ID, PHONE)
        await self.client.start(phone=PHONE)
        logger.info('✓ Подключено к Telegram')

        # Получение бота
        try:
            self.bot_entity = await self.client.get_entity(BOT_USERNAME)
            logger.info(f'✓ Найден бот: {BOT_USERNAME} (ID: {self.bot_entity.id})')
        except Exception as e:
            logger.error(f'❌ Ошибка получения бота: {e}')
            return

        # Регистрация обработчиков
        self.client.add_event_handler(
            self.handle_new_message,
            events.NewMessage(chats=[self.bot_entity])
        )
        self.client.add_event_handler(
            self.handle_edit,
            events.MessageEdited(chats=[self.bot_entity])
        )

        logger.info('✓ Обработчики зарегистрированы')
        logger.info('')
        logger.info('🎯 Ожидание сообщений от бота...')
        logger.info('   Триггеры: ' + ', '.join(f'"{t}"' for t in TRIGGER_TEXTS))
        logger.info('')

        # Запуск периодической статистики
        asyncio.create_task(self.periodic_stats())

        # Запуск клиента
        await self.client.run_until_disconnected()

    async def handle_new_message(self, event):
        """Обработка нового сообщения"""
        message = event.message
        now = datetime.now()

        self.stats['total_messages'] += 1
        self.stats['new_messages'] += 1

        # Время с последнего сообщения
        time_since_last = None
        if self.last_message_time:
            time_since_last = (now - self.last_message_time).total_seconds() * 1000
        self.last_message_time = now

        # Извлечение данных
        buttons = self.extract_buttons(message)
        has_buttons = len(buttons) > 0

        if has_buttons:
            self.stats['messages_with_buttons'] += 1
        else:
            self.stats['messages_without_buttons'] += 1

        # Сохранение в историю
        event_data = {
            'type': 'NEW',
            'time': now,
            'text': message.text,
            'buttons': buttons,
            'has_buttons': has_buttons
        }

        if message.id not in self.message_history:
            self.message_history[message.id] = []
        self.message_history[message.id].append(event_data)

        # Проверка на триггер
        is_trigger = self.check_trigger(message.text)
        if is_trigger:
            self.stats['triggers_detected'] += 1

        # Логирование
        logger.info('')
        logger.info('┌' + '─'*68 + '┐')
        logger.info(f'│ 🆕 НОВОЕ СООБЩЕНИЕ (ID: {message.id})')
        if time_since_last:
            logger.info(f'│ ⏱️  Время с последнего: {time_since_last:.1f} мс')

        if is_trigger:
            logger.info(f'│ 🚨 ОБНАРУЖЕН ТРИГГЕР!')

        if message.text:
            text_preview = message.text[:60] + '...' if len(message.text) > 60 else message.text
            logger.info(f'│ 📝 Текст: {text_preview}')

        logger.info(f'│ 🎛️  Кнопок: {len(buttons)}')

        if buttons:
            logger.info('│ 📋 Кнопки:')
            for idx, btn in enumerate(buttons, 1):
                self.stats['button_texts_seen'].add(btn['text'])
                logger.info(f'│    [{idx}] {btn["text"]}')

        logger.info('└' + '─'*68 + '┘')

    async def handle_edit(self, event):
        """Обработка редактирования сообщения"""
        message = event.message
        now = datetime.now()

        self.stats['total_messages'] += 1
        self.stats['edits'] += 1

        # Извлечение данных
        buttons = self.extract_buttons(message)
        has_buttons = len(buttons) > 0

        if has_buttons:
            self.stats['messages_with_buttons'] += 1
        else:
            self.stats['messages_without_buttons'] += 1

        # Вычисление задержки с предыдущим событием
        delay = None
        if message.id in self.message_history and self.message_history[message.id]:
            last_event = self.message_history[message.id][-1]
            delay = (now - last_event['time']).total_seconds() * 1000
            self.stats['edit_delays'].append(delay)

        # Сохранение в историю
        event_data = {
            'type': 'EDIT',
            'time': now,
            'text': message.text,
            'buttons': buttons,
            'has_buttons': has_buttons,
            'delay_from_previous': delay
        }

        if message.id not in self.message_history:
            self.message_history[message.id] = []
        self.message_history[message.id].append(event_data)

        # Проверка на триггер
        is_trigger = self.check_trigger(message.text)

        # Логирование
        logger.info('')
        logger.info('┌' + '─'*68 + '┐')
        logger.info(f'│ ✏️  РЕДАКТИРОВАНИЕ (ID: {message.id})')

        if delay:
            logger.info(f'│ ⏱️  Задержка с предыдущего: {delay:.1f} мс')

            # Анализ паттерна
            history = self.message_history[message.id]
            if len(history) == 2:
                prev_had_buttons = history[-2]['has_buttons']
                curr_has_buttons = has_buttons

                if not prev_had_buttons and curr_has_buttons:
                    logger.info(f'│ 🔄 ПАТТЕРН: Без кнопок → С кнопками ({delay:.1f} мс)')
                elif prev_had_buttons and not curr_has_buttons:
                    logger.info(f'│ 🔄 ПАТТЕРН: С кнопками → Без кнопок ({delay:.1f} мс)')

        if is_trigger:
            logger.info(f'│ 🚨 ОБНАРУЖЕН ТРИГГЕР!')

        if message.text:
            text_preview = message.text[:60] + '...' if len(message.text) > 60 else message.text
            logger.info(f'│ 📝 Текст: {text_preview}')

        logger.info(f'│ 🎛️  Кнопок: {len(buttons)}')

        if buttons:
            logger.info('│ 📋 Кнопки:')
            for idx, btn in enumerate(buttons, 1):
                self.stats['button_texts_seen'].add(btn['text'])
                logger.info(f'│    [{idx}] {btn["text"]}')

        logger.info('└' + '─'*68 + '┘')

    def extract_buttons(self, message: Message) -> List[Dict]:
        """Извлечение кнопок из сообщения"""
        buttons = []
        if message.reply_markup and message.reply_markup.rows:
            for row_idx, row in enumerate(message.reply_markup.rows):
                for col_idx, button in enumerate(row.buttons):
                    if isinstance(button, KeyboardButtonCallback):
                        buttons.append({
                            'text': button.text,
                            'row': row_idx,
                            'col': col_idx
                        })
        return buttons

    def check_trigger(self, text: Optional[str]) -> bool:
        """Проверка на триггер"""
        if not text:
            return False
        text_lower = text.lower()
        return any(trigger.lower() in text_lower for trigger in TRIGGER_TEXTS)

    async def periodic_stats(self):
        """Периодический вывод статистики"""
        await asyncio.sleep(60)  # Первый вывод через минуту

        while True:
            self.print_stats()
            await asyncio.sleep(300)  # Каждые 5 минут

    def print_stats(self):
        """Вывод статистики"""
        runtime = datetime.now() - self.stats['start_time']

        logger.info('')
        logger.info('╔' + '═'*68 + '╗')
        logger.info('║' + ' '*22 + '📊 СТАТИСТИКА' + ' '*33 + '║')
        logger.info('╠' + '═'*68 + '╣')
        logger.info(f'║ Время работы: {str(runtime).split(".")[0]}' + ' '*(68-len(str(runtime).split(".")[0])-16) + '║')
        logger.info('╠' + '─'*68 + '╣')
        logger.info(f'║ Всего событий: {self.stats["total_messages"]}' + ' '*(68-len(str(self.stats["total_messages"]))-19) + '║')
        logger.info(f'║   • Новые сообщения: {self.stats["new_messages"]}' + ' '*(68-len(str(self.stats["new_messages"]))-23) + '║')
        logger.info(f'║   • Редактирования: {self.stats["edits"]}' + ' '*(68-len(str(self.stats["edits"]))-22) + '║')
        logger.info(f'║ Триггеров: {self.stats["triggers_detected"]}' + ' '*(68-len(str(self.stats["triggers_detected"]))-14) + '║')
        logger.info('╠' + '─'*68 + '╣')
        logger.info(f'║ Сообщений с кнопками: {self.stats["messages_with_buttons"]}' + ' '*(68-len(str(self.stats["messages_with_buttons"]))-26) + '║')
        logger.info(f'║ Сообщений без кнопок: {self.stats["messages_without_buttons"]}' + ' '*(68-len(str(self.stats["messages_without_buttons"]))-26) + '║')

        if self.stats['edit_delays']:
            avg_delay = sum(self.stats['edit_delays']) / len(self.stats['edit_delays'])
            min_delay = min(self.stats['edit_delays'])
            max_delay = max(self.stats['edit_delays'])

            logger.info('╠' + '─'*68 + '╣')
            logger.info(f'║ ⏱️  ЗАДЕРЖКИ РЕДАКТИРОВАНИЯ:' + ' '*38 + '║')
            logger.info(f'║   • Средняя: {avg_delay:.1f} мс' + ' '*(68-len(f"{avg_delay:.1f}")-19) + '║')
            logger.info(f'║   • Минимум: {min_delay:.1f} мс' + ' '*(68-len(f"{min_delay:.1f}")-19) + '║')
            logger.info(f'║   • Максимум: {max_delay:.1f} мс' + ' '*(68-len(f"{max_delay:.1f}")-19) + '║')
            logger.info(f'║   • Замеров: {len(self.stats["edit_delays"])}' + ' '*(68-len(str(len(self.stats["edit_delays"])))-16) + '║')

        if self.stats['button_texts_seen']:
            logger.info('╠' + '─'*68 + '╣')
            logger.info(f'║ 🎛️  УНИКАЛЬНЫХ КНОПОК: {len(self.stats["button_texts_seen"])}' + ' '*(68-len(str(len(self.stats["button_texts_seen"])))-25) + '║')

        logger.info('╚' + '═'*68 + '╝')
        logger.info('')


async def main():
    """Главная функция"""
    monitor = DeepMonitor()

    try:
        await monitor.start()
    except KeyboardInterrupt:
        logger.info('')
        logger.info('⏹️  Остановка мониторинга...')
        monitor.print_stats()
        logger.info('👋 Мониторинг завершен')
    except Exception as e:
        logger.error(f'❌ Критическая ошибка: {e}', exc_info=True)


if __name__ == '__main__':
    asyncio.run(main())
