"""
Скрипт для тестирования взаимодействия с ботом @ACarriers_bot
Позволяет понять, как бот реагирует на команды и нажатия кнопок
"""

import asyncio
import logging
from datetime import datetime
from telethon import TelegramClient, events
from telethon.tl.types import KeyboardButtonCallback, KeyboardButtonUrl
from dotenv import load_dotenv
import os

# Загрузка переменных окружения
load_dotenv()

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('test_acarriers_bot.log', encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


class BotTester:
    """Класс для тестирования бота @ACarriers_bot"""

    def __init__(self, api_id: str, api_hash: str, phone: str):
        """
        Инициализация тестера бота

        Args:
            api_id: Telegram API ID
            api_hash: Telegram API Hash
            phone: Номер телефона
        """
        self.api_id = int(api_id)
        self.api_hash = api_hash
        self.phone = phone
        self.client = None
        self.bot_username = '@ACarriers_bot'
        self.bot_entity = None

        # Хранилище информации о взаимодействиях
        self.interactions = []
        self.last_message = None
        self.visited_buttons = set()

        # Ключевые слова для кнопок, которые нельзя нажимать
        self.forbidden_keywords = ['подтвердить', 'подтверд', 'забронировать', 'взять', 'беру']

    async def start(self):
        """Запуск клиента и подключение к Telegram"""
        logger.info("Запуск Telegram клиента...")
        self.client = TelegramClient('test_session', self.api_id, self.api_hash)
        await self.client.start(phone=self.phone)
        logger.info("Клиент успешно запущен")

        # Получение информации о боте
        self.bot_entity = await self.client.get_entity(self.bot_username)
        logger.info(f"Подключение к боту: {self.bot_username}")

        # Регистрация обработчика сообщений
        @self.client.on(events.NewMessage(from_users=self.bot_entity))
        async def message_handler(event):
            await self._handle_message(event)

        @self.client.on(events.MessageEdited(from_users=self.bot_entity))
        async def edit_handler(event):
            await self._handle_message(event, is_edit=True)

    async def _handle_message(self, event, is_edit=False):
        """
        Обработка входящего сообщения от бота

        Args:
            event: Событие сообщения
            is_edit: Флаг редактирования сообщения
        """
        message = event.message
        msg_type = "EDIT" if is_edit else "NEW"

        logger.info(f"\n{'='*60}")
        logger.info(f"{msg_type} MESSAGE from bot (ID: {message.id})")
        logger.info(f"Time: {datetime.now().strftime('%H:%M:%S.%f')[:-3]}")
        logger.info(f"{'='*60}")

        # Текст сообщения
        if message.text:
            logger.info(f"TEXT:\n{message.text}")

        # Кнопки
        buttons = self._extract_buttons(message)
        if buttons:
            logger.info(f"\nBUTTONS ({len(buttons)} total):")
            for idx, btn in enumerate(buttons, 1):
                button_type = "CALLBACK" if isinstance(btn['original'], KeyboardButtonCallback) else "URL"
                logger.info(f"  [{idx}] '{btn['text']}' (Row: {btn['row']}, Col: {btn['col']}, Type: {button_type})")
        else:
            logger.info("\nNo buttons in this message")

        # Сохранение информации о взаимодействии
        interaction = {
            'timestamp': datetime.now(),
            'message_id': message.id,
            'text': message.text,
            'buttons': buttons,
            'is_edit': is_edit
        }
        self.interactions.append(interaction)
        self.last_message = message

        logger.info(f"{'='*60}\n")

    def _extract_buttons(self, message):
        """
        Извлечение кнопок из сообщения

        Args:
            message: Объект сообщения

        Returns:
            Список словарей с информацией о кнопках
        """
        if not message.reply_markup or not message.reply_markup.rows:
            return []

        buttons = []
        for row_idx, row in enumerate(message.reply_markup.rows):
            for col_idx, button in enumerate(row.buttons):
                btn_info = {
                    'text': button.text,
                    'row': row_idx,
                    'col': col_idx,
                    'original': button
                }
                buttons.append(btn_info)

        return buttons

    def _is_forbidden_button(self, button_text: str) -> bool:
        """
        Проверка, является ли кнопка запрещенной для нажатия

        Args:
            button_text: Текст кнопки

        Returns:
            True если кнопка запрещена, иначе False
        """
        text_lower = button_text.lower()
        return any(keyword in text_lower for keyword in self.forbidden_keywords)

    async def send_command(self, command: str):
        """
        Отправка команды боту

        Args:
            command: Команда для отправки (например, '/start')
        """
        logger.info(f"\n>>> Sending command: {command}")
        await self.client.send_message(self.bot_entity, command)
        await asyncio.sleep(2)  # Ждем ответа бота

    async def click_button(self, button_index: int = 0):
        """
        Нажатие кнопки по индексу

        Args:
            button_index: Индекс кнопки (0-based)
        """
        if not self.last_message:
            logger.warning("No message to click button on")
            return False

        buttons = self._extract_buttons(self.last_message)

        if not buttons:
            logger.warning("No buttons available to click")
            return False

        if button_index >= len(buttons):
            logger.warning(f"Button index {button_index} out of range (max: {len(buttons)-1})")
            return False

        button = buttons[button_index]

        # Проверка на запрещенную кнопку
        if self._is_forbidden_button(button['text']):
            logger.warning(f"!!! FORBIDDEN BUTTON: '{button['text']}' - SKIPPING !!!")
            return False

        logger.info(f"\n>>> Clicking button: '{button['text']}' (index: {button_index})")

        try:
            await self.last_message.click(button['row'], button['col'])
            self.visited_buttons.add(button['text'])
            await asyncio.sleep(2)  # Ждем ответа после клика
            return True
        except Exception as e:
            logger.error(f"Error clicking button: {e}")
            return False

    async def explore_menu(self, max_depth: int = 3):
        """
        Автоматическое исследование меню бота

        Args:
            max_depth: Максимальная глубина исследования
        """
        logger.info(f"\n{'='*60}")
        logger.info("STARTING MENU EXPLORATION")
        logger.info(f"Max depth: {max_depth}")
        logger.info(f"{'='*60}\n")

        for depth in range(max_depth):
            logger.info(f"\n--- DEPTH {depth + 1} ---")

            if not self.last_message:
                logger.info("No message available")
                break

            buttons = self._extract_buttons(self.last_message)

            if not buttons:
                logger.info("No buttons to explore")
                break

            # Фильтруем кнопки: исключаем запрещенные и уже посещенные
            available_buttons = []
            for idx, btn in enumerate(buttons):
                if not self._is_forbidden_button(btn['text']):
                    available_buttons.append((idx, btn))

            if not available_buttons:
                logger.info("No available buttons to click (all are forbidden or visited)")
                break

            # Нажимаем первую доступную кнопку
            button_idx, button_info = available_buttons[0]
            logger.info(f"Exploring button: '{button_info['text']}'")

            success = await self.click_button(button_idx)

            if not success:
                logger.info("Failed to click button, stopping exploration")
                break

            # Небольшая пауза между действиями
            await asyncio.sleep(1)

    async def test_basic_flow(self):
        """Базовый тест потока взаимодействия с ботом"""
        logger.info("\n" + "="*60)
        logger.info("STARTING BASIC FLOW TEST")
        logger.info("="*60 + "\n")

        # Шаг 1: Отправка /start
        await self.send_command('/start')
        await asyncio.sleep(2)

        # Шаг 2: Исследование доступных кнопок
        buttons = self._extract_buttons(self.last_message)
        if buttons:
            logger.info(f"\nFound {len(buttons)} buttons after /start")

            # Пробуем нажать на первую не-запрещенную кнопку
            for idx, btn in enumerate(buttons):
                if not self._is_forbidden_button(btn['text']):
                    logger.info(f"\nTesting button: '{btn['text']}'")
                    await self.click_button(idx)
                    await asyncio.sleep(2)

                    # Проверяем, что получили в ответ
                    new_buttons = self._extract_buttons(self.last_message)
                    if new_buttons:
                        logger.info(f"Response has {len(new_buttons)} buttons")

                    # Возвращаемся назад или в главное меню (если есть такая кнопка)
                    for back_idx, back_btn in enumerate(new_buttons):
                        if any(keyword in back_btn['text'].lower() for keyword in ['назад', 'меню', 'главн']):
                            logger.info(f"\nReturning to menu via: '{back_btn['text']}'")
                            await self.click_button(back_idx)
                            await asyncio.sleep(2)
                            break

                    break

    async def print_summary(self):
        """Вывод итоговой информации о тестировании"""
        logger.info("\n" + "="*60)
        logger.info("TEST SUMMARY")
        logger.info("="*60)
        logger.info(f"\nTotal interactions: {len(self.interactions)}")
        logger.info(f"Visited buttons: {len(self.visited_buttons)}")

        if self.visited_buttons:
            logger.info("\nClicked buttons:")
            for btn in self.visited_buttons:
                logger.info(f"  - {btn}")

        logger.info("\nAll interactions timeline:")
        for idx, interaction in enumerate(self.interactions, 1):
            time_str = interaction['timestamp'].strftime('%H:%M:%S.%f')[:-3]
            edit_flag = "[EDIT]" if interaction['is_edit'] else "[NEW]"
            logger.info(f"\n{idx}. {time_str} {edit_flag} Message ID: {interaction['message_id']}")
            if interaction['text']:
                logger.info(f"   Text: {interaction['text'][:100]}...")
            if interaction['buttons']:
                logger.info(f"   Buttons: {len(interaction['buttons'])}")
                for btn in interaction['buttons']:
                    forbidden = " [FORBIDDEN]" if self._is_forbidden_button(btn['text']) else ""
                    logger.info(f"     - {btn['text']}{forbidden}")

        logger.info("\n" + "="*60 + "\n")

    async def run_interactive_test(self):
        """Запуск интерактивного тестирования"""
        await self.start()

        logger.info("\n" + "="*60)
        logger.info("INTERACTIVE BOT TESTING MODE")
        logger.info("="*60 + "\n")

        # Отправляем /start
        await self.send_command('/start')

        while True:
            await asyncio.sleep(1)

            logger.info("\nOptions:")
            logger.info("1. Click button by index")
            logger.info("2. Send /start")
            logger.info("3. Explore menu automatically")
            logger.info("4. Show summary")
            logger.info("5. Exit")

            try:
                # В автоматическом режиме просто делаем базовый тест и выходим
                await self.test_basic_flow()
                await self.print_summary()
                break

            except KeyboardInterrupt:
                logger.info("\nTest interrupted by user")
                break

    async def stop(self):
        """Остановка клиента"""
        if self.client:
            await self.client.disconnect()
            logger.info("Client disconnected")


async def main():
    """Главная функция"""
    # Получение учетных данных из .env
    api_id = os.getenv('API_ID')
    api_hash = os.getenv('API_HASH')
    phone = os.getenv('PHONE')

    if not all([api_id, api_hash, phone]):
        logger.error("Missing credentials in .env file!")
        logger.error("Required: API_ID, API_HASH, PHONE")
        return

    logger.info(f"Starting test with phone: {phone}")

    tester = BotTester(api_id, api_hash, phone)

    try:
        await tester.run_interactive_test()
    except Exception as e:
        logger.error(f"Error during testing: {e}", exc_info=True)
    finally:
        await tester.stop()


if __name__ == '__main__':
    asyncio.run(main())
