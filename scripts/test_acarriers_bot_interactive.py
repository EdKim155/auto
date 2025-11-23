"""
Интерактивный тестер бота @ACarriers_bot
Позволяет вручную управлять взаимодействием с ботом через консоль
"""

import asyncio
import logging
from datetime import datetime
from telethon import TelegramClient, events
from telethon.tl.types import KeyboardButtonCallback, KeyboardButtonUrl
from dotenv import load_dotenv
import os
import sys

# Загрузка переменных окружения
load_dotenv()

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('test_acarriers_bot_interactive.log', encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


class InteractiveBotTester:
    """Интерактивный тестер бота @ACarriers_bot"""

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
        self.message_history = {}  # message_id -> message_data
        self.visited_buttons = set()

        # Ключевые слова для кнопок, которые нельзя нажимать
        self.forbidden_keywords = ['подтвердить', 'подтверд', 'забронировать', 'взять', 'беру']

        # Флаг для остановки цикла
        self.running = True

    async def start(self):
        """Запуск клиента и подключение к Telegram"""
        logger.info("Запуск Telegram клиента...")
        self.client = TelegramClient('test_interactive_session', self.api_id, self.api_hash)
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

        logger.info(f"\n{'='*70}")
        logger.info(f"{msg_type} MESSAGE from bot (ID: {message.id})")
        logger.info(f"Time: {datetime.now().strftime('%H:%M:%S.%f')[:-3]}")
        logger.info(f"{'='*70}")

        # Текст сообщения
        if message.text:
            logger.info(f"TEXT:\n{message.text}")

        # Кнопки
        buttons = self._extract_buttons(message)
        if buttons:
            logger.info(f"\nBUTTONS ({len(buttons)} total):")
            for idx, btn in enumerate(buttons, 1):
                button_type = "CALLBACK" if isinstance(btn['original'], KeyboardButtonCallback) else "URL"
                forbidden_mark = " [FORBIDDEN]" if self._is_forbidden_button(btn['text']) else ""
                logger.info(f"  [{idx}] '{btn['text']}'{forbidden_mark} (Row: {btn['row']}, Col: {btn['col']}, Type: {button_type})")
        else:
            logger.info("\nNo buttons in this message")

        # Сохранение информации
        interaction = {
            'timestamp': datetime.now(),
            'message_id': message.id,
            'text': message.text,
            'buttons': buttons,
            'is_edit': is_edit
        }
        self.interactions.append(interaction)
        self.last_message = message
        self.message_history[message.id] = message

        logger.info(f"{'='*70}\n")

        # Показываем меню после каждого сообщения от бота
        if not is_edit:  # Показываем только для новых сообщений, не для редактирований
            self._print_quick_menu()

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

    def _print_quick_menu(self):
        """Вывод быстрого меню действий"""
        print("\n" + "─"*70)
        print("QUICK MENU: [1-9] click button | [s] /start | [h] help | [q] quit")
        print("─"*70)

    def _print_main_menu(self):
        """Вывод главного меню"""
        print("\n" + "═"*70)
        print("INTERACTIVE BOT TESTER - MAIN MENU")
        print("═"*70)
        print("\nCommands:")
        print("  1-9    - Click button by number (1-9)")
        print("  b <n>  - Click button by number (any number)")
        print("  s      - Send /start command")
        print("  c <cmd>- Send custom command (e.g., 'c /help')")
        print("  l      - List all buttons from last message")
        print("  h      - Show message history")
        print("  v      - Show visited buttons")
        print("  sum    - Show test summary")
        print("  help   - Show this menu")
        print("  q      - Quit")
        print("═"*70)

    async def send_command(self, command: str):
        """
        Отправка команды боту

        Args:
            command: Команда для отправки
        """
        logger.info(f"\n>>> Sending command: {command}")
        await self.client.send_message(self.bot_entity, command)
        await asyncio.sleep(1)

    async def click_button(self, button_index: int):
        """
        Нажатие кнопки по индексу (1-based для пользователя)

        Args:
            button_index: Индекс кнопки (1-based)
        """
        if not self.last_message:
            print("⚠️  No message to click button on")
            return False

        buttons = self._extract_buttons(self.last_message)

        if not buttons:
            print("⚠️  No buttons available to click")
            return False

        # Конвертируем в 0-based индекс
        idx = button_index - 1

        if idx < 0 or idx >= len(buttons):
            print(f"⚠️  Button number {button_index} out of range (available: 1-{len(buttons)})")
            return False

        button = buttons[idx]

        # Проверка на запрещенную кнопку
        if self._is_forbidden_button(button['text']):
            print(f"\n❌ FORBIDDEN BUTTON: '{button['text']}' - CANNOT CLICK!")
            print("This button is blocked to prevent unwanted actions.")
            confirm = input("Do you really want to click it? (type 'YES' to confirm): ")
            if confirm != 'YES':
                print("Click cancelled.")
                return False

        print(f"\n>>> Clicking button #{button_index}: '{button['text']}'")

        try:
            await self.last_message.click(button['row'], button['col'])
            self.visited_buttons.add(button['text'])
            print(f"✓ Button clicked successfully")
            await asyncio.sleep(1)
            return True
        except Exception as e:
            print(f"❌ Error clicking button: {e}")
            logger.error(f"Error clicking button: {e}", exc_info=True)
            return False

    def list_buttons(self):
        """Вывод списка доступных кнопок"""
        if not self.last_message:
            print("⚠️  No message available")
            return

        buttons = self._extract_buttons(self.last_message)

        if not buttons:
            print("⚠️  No buttons in the last message")
            return

        print(f"\n{'═'*70}")
        print(f"AVAILABLE BUTTONS (Message ID: {self.last_message.id})")
        print(f"{'═'*70}")

        for idx, btn in enumerate(buttons, 1):
            forbidden_mark = " ❌ [FORBIDDEN]" if self._is_forbidden_button(btn['text']) else " ✓"
            print(f"  [{idx}]{forbidden_mark} {btn['text']}")
            print(f"       Position: Row {btn['row']}, Col {btn['col']}")

        print(f"{'═'*70}\n")

    def show_history(self):
        """Вывод истории сообщений"""
        if not self.interactions:
            print("⚠️  No interactions yet")
            return

        print(f"\n{'═'*70}")
        print("MESSAGE HISTORY")
        print(f"{'═'*70}")

        for idx, interaction in enumerate(self.interactions, 1):
            time_str = interaction['timestamp'].strftime('%H:%M:%S.%f')[:-3]
            edit_flag = "[EDIT]" if interaction['is_edit'] else "[NEW]"
            print(f"\n{idx}. {time_str} {edit_flag} Message ID: {interaction['message_id']}")

            if interaction['text']:
                text_preview = interaction['text'][:80] + "..." if len(interaction['text']) > 80 else interaction['text']
                print(f"   Text: {text_preview}")

            if interaction['buttons']:
                print(f"   Buttons ({len(interaction['buttons'])}): ", end="")
                button_names = [b['text'][:20] for b in interaction['buttons'][:3]]
                print(", ".join(button_names), end="")
                if len(interaction['buttons']) > 3:
                    print(f" ... (+{len(interaction['buttons'])-3} more)")
                else:
                    print()

        print(f"{'═'*70}\n")

    def show_visited_buttons(self):
        """Вывод посещенных кнопок"""
        if not self.visited_buttons:
            print("⚠️  No buttons clicked yet")
            return

        print(f"\n{'═'*70}")
        print(f"VISITED BUTTONS ({len(self.visited_buttons)} total)")
        print(f"{'═'*70}")

        for idx, btn in enumerate(self.visited_buttons, 1):
            print(f"  {idx}. {btn}")

        print(f"{'═'*70}\n")

    def show_summary(self):
        """Вывод сводной информации"""
        print(f"\n{'═'*70}")
        print("TEST SUMMARY")
        print(f"{'═'*70}")
        print(f"\nTotal interactions: {len(self.interactions)}")
        print(f"Visited buttons: {len(self.visited_buttons)}")
        print(f"Messages in history: {len(self.message_history)}")

        # Подсчет новых сообщений и редактирований
        new_count = sum(1 for i in self.interactions if not i['is_edit'])
        edit_count = sum(1 for i in self.interactions if i['is_edit'])
        print(f"New messages: {new_count}")
        print(f"Edits: {edit_count}")

        print(f"{'═'*70}\n")

    async def run(self):
        """Запуск интерактивного режима"""
        await self.start()

        self._print_main_menu()

        # Отправляем /start автоматически
        print("\nSending /start to bot...")
        await self.send_command('/start')

        # Основной цикл
        while self.running:
            try:
                # Получаем ввод пользователя
                user_input = await asyncio.get_event_loop().run_in_executor(
                    None, input, "\n> "
                )

                user_input = user_input.strip()

                if not user_input:
                    continue

                # Обработка команд
                if user_input.lower() == 'q':
                    print("Exiting...")
                    self.running = False
                    break

                elif user_input.lower() == 'help':
                    self._print_main_menu()

                elif user_input.lower() == 's':
                    await self.send_command('/start')

                elif user_input.lower().startswith('c '):
                    command = user_input[2:].strip()
                    await self.send_command(command)

                elif user_input.lower() == 'l':
                    self.list_buttons()

                elif user_input.lower() == 'h':
                    self.show_history()

                elif user_input.lower() == 'v':
                    self.show_visited_buttons()

                elif user_input.lower() == 'sum':
                    self.show_summary()

                elif user_input.lower().startswith('b '):
                    try:
                        btn_num = int(user_input[2:].strip())
                        await self.click_button(btn_num)
                    except ValueError:
                        print("⚠️  Invalid button number")

                elif user_input.isdigit():
                    btn_num = int(user_input)
                    if 1 <= btn_num <= 9:
                        await self.click_button(btn_num)
                    else:
                        print(f"⚠️  Use 'b {btn_num}' for buttons > 9")

                else:
                    print("⚠️  Unknown command. Type 'help' for available commands.")

            except KeyboardInterrupt:
                print("\n\nInterrupted by user")
                self.running = False
                break
            except Exception as e:
                logger.error(f"Error in main loop: {e}", exc_info=True)
                print(f"❌ Error: {e}")

    async def stop(self):
        """Остановка клиента"""
        self.show_summary()
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

    print("="*70)
    print("INTERACTIVE BOT TESTER FOR @ACarriers_bot")
    print("="*70)
    print(f"\nConnecting with phone: {phone}")
    print("Loading...")

    tester = InteractiveBotTester(api_id, api_hash, phone)

    try:
        await tester.run()
    except Exception as e:
        logger.error(f"Error during testing: {e}", exc_info=True)
        print(f"\n❌ Fatal error: {e}")
    finally:
        await tester.stop()


if __name__ == '__main__':
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n\nExiting...")
