# Telegram Bot Automation - 2nd Button Version

Это модифицированная версия скрипта автоматизации, которая на **шаге 2 нажимает ВТОРУЮ кнопку** вместо первой.

## Отличия от основной версии

### Основная версия (main.py)
- **Шаг 1**: Нажимает "Список прямых перевозок"
- **Шаг 2**: Нажимает **ПЕРВУЮ** кнопку в списке перевозок
- **Шаг 3**: Нажимает кнопку подтверждения

### Версия 2nd Button (main_2nd.py)
- **Шаг 1**: Нажимает "Список прямых перевозок"
- **Шаг 2**: Нажимает **ВТОРУЮ** кнопку в списке перевозок ⬅️ Изменение здесь
- **Шаг 3**: Нажимает кнопку подтверждения

## Установка

### 1. Создайте конфигурационный файл

Скопируйте пример конфигурации:
```bash
cp .env.2nd.example .env.2nd
```

### 2. Настройте .env.2nd

Отредактируйте `.env.2nd` и укажите:
- `API_ID` и `API_HASH` - получите на https://my.telegram.org/apps
- `PHONE` - ваш номер телефона в международном формате
- `BOT_USERNAME` - имя бота (например, @apri1l_test_bot)
- `SESSION_NAME` - уникальное имя сессии (по умолчанию: telegram_session_2nd.session)

Пример:
```env
API_ID=12345678
API_HASH=abcdef1234567890abcdef1234567890
PHONE=+79501234567
BOT_USERNAME=@apri1l_test_bot
SESSION_NAME=telegram_session_2nd.session
LOG_LEVEL=DEBUG
```

### 3. Модифицируйте config.py для загрузки .env.2nd

Создайте файл `config_2nd.py` или модифицируйте запуск:

```python
# В main_2nd.py можно загрузить другой .env файл
from dotenv import load_dotenv
load_dotenv('.env.2nd')  # Загрузить .env.2nd вместо .env
```

## Запуск

### Локальный запуск
```bash
python3 main_2nd.py
```

### Запуск на сервере

#### Остановить основной бот (если нужно)
```bash
ssh -i ~/.ssh/id_ed25519_aprel root@72.56.76.248 "systemctl stop telegram-bot.service"
```

#### Загрузить новые файлы на сервер
```bash
scp -i ~/.ssh/id_ed25519_aprel bot_automation_2nd.py main_2nd.py .env.2nd root@72.56.76.248:/root/auto/
```

#### Создать новый systemd сервис для 2nd версии
```bash
ssh -i ~/.ssh/id_ed25519_aprel root@72.56.76.248
```

Создайте файл `/etc/systemd/system/telegram-bot-2nd.service`:
```ini
[Unit]
Description=Telegram Bot Automation (2nd Button)
After=network.target

[Service]
Type=simple
User=root
WorkingDirectory=/root/auto
Environment="DOTENV_PATH=/root/auto/.env.2nd"
ExecStart=/root/auto/venv/bin/python3 /root/auto/main_2nd.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

#### Запустить новый сервис
```bash
systemctl daemon-reload
systemctl enable telegram-bot-2nd.service
systemctl start telegram-bot-2nd.service
systemctl status telegram-bot-2nd.service
```

## Проверка логов

### Локальные логи
```bash
tail -f bot_automation_2nd.log
```

### Логи на сервере
```bash
ssh -i ~/.ssh/id_ed25519_aprel root@72.56.76.248 "journalctl -u telegram-bot-2nd.service -f"
```

## Переключение между версиями

Вы можете запускать обе версии одновременно на разных аккаунтах или ботах, или переключаться между ними:

### Остановить основную версию и запустить 2nd
```bash
systemctl stop telegram-bot.service
systemctl start telegram-bot-2nd.service
```

### Остановить 2nd версию и запустить основную
```bash
systemctl stop telegram-bot-2nd.service
systemctl start telegram-bot.service
```

## Отличия в коде

### bot_automation_2nd.py (строки 259-278)

**Основная версия**:
```python
# Get first button (first transport in list)
button = self.button_analyzer.get_first_button(msg_data.buttons)
```

**2nd версия**:
```python
# Get SECOND button (second transport in list)
button = self.button_analyzer.get_button_at_position(msg_data.buttons, row=1, column=0)

# Fallback: if position-based search fails, try getting second button from list
if not button and len(msg_data.buttons) >= 2:
    sorted_buttons = sorted(msg_data.buttons, key=lambda b: (b.row, b.column))
    button = sorted_buttons[1]
```

## Требования

- В списке перевозок должно быть **минимум 2 кнопки**
- Если в списке только 1 кнопка, скрипт выдаст ошибку: "Second button not available (need at least 2 buttons)"

## Troubleshooting

### Ошибка: "Second button not available"
Это означает, что в списке перевозок меньше 2 кнопок. Скрипт требует минимум 2 перевозки в списке.

### Скрипт нажимает не ту кнопку
Проверьте расположение кнопок в боте. Скрипт ищет кнопку на позиции `[1, 0]` (вторая строка, первый столбец) или берет второй элемент из отсортированного списка кнопок.
