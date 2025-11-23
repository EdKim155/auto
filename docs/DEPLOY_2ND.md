# Развертывание 2nd автоматизации на сервере

## Данные для развертывания:
- **API_ID**: 24101164
- **API_HASH**: 80cc2adcd452008ae630d0ee778b5122
- **PHONE**: +79512586335
- **BOT**: @apri1l_test_bot
- **Сервер**: 72.56.76.248

## Шаг 1: Создание сессии на сервере

Подключитесь к серверу и создайте сессию для нового аккаунта:

```bash
# Подключиться к серверу
ssh -i ~/.ssh/id_ed25519_aprel root@72.56.76.248

# Перейти в директорию
cd /root/auto

# Запустить скрипт создания сессии
/root/auto/venv/bin/python3 create_session_2nd.py
```

**Вам придет код в Telegram на номер +79512586335** - введите его когда скрипт попросит.

## Шаг 2: Создание systemd сервиса

На сервере создайте файл сервиса:

```bash
cat > /etc/systemd/system/telegram-bot-2nd.service <<'EOF'
[Unit]
Description=Telegram Bot Automation (2nd Button Version)
After=network.target

[Service]
Type=simple
User=root
WorkingDirectory=/root/auto
ExecStart=/root/auto/venv/bin/python3 /root/auto/main_2nd.py
Restart=always
RestartSec=10
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
EOF
```

## Шаг 3: Запуск сервиса

```bash
# Перезагрузить конфигурацию systemd
systemctl daemon-reload

# Включить автозапуск
systemctl enable telegram-bot-2nd.service

# Запустить сервис
systemctl start telegram-bot-2nd.service

# Проверить статус
systemctl status telegram-bot-2nd.service
```

## Шаг 4: Проверка логов

```bash
# Смотреть логи в реальном времени
journalctl -u telegram-bot-2nd.service -f

# Или посмотреть последние 100 строк
journalctl -u telegram-bot-2nd.service -n 100
```

## Полная последовательность команд (одной строкой)

Скопируйте и выполните на сервере:

```bash
ssh -i ~/.ssh/id_ed25519_aprel root@72.56.76.248 << 'ENDSSH'
cd /root/auto
echo "=== Создание сессии ==="
/root/auto/venv/bin/python3 create_session_2nd.py
ENDSSH
```

После создания сессии:

```bash
ssh -i ~/.ssh/id_ed25519_aprel root@72.56.76.248 << 'ENDSSH'
# Создать systemd сервис
cat > /etc/systemd/system/telegram-bot-2nd.service <<'EOF'
[Unit]
Description=Telegram Bot Automation (2nd Button Version)
After=network.target

[Service]
Type=simple
User=root
WorkingDirectory=/root/auto
ExecStart=/root/auto/venv/bin/python3 /root/auto/main_2nd.py
Restart=always
RestartSec=10
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
EOF

# Запустить сервис
systemctl daemon-reload
systemctl enable telegram-bot-2nd.service
systemctl start telegram-bot-2nd.service
systemctl status telegram-bot-2nd.service
ENDSSH
```

## Управление сервисами

### Запустить обе автоматизации одновременно
```bash
ssh -i ~/.ssh/id_ed25519_aprel root@72.56.76.248 "systemctl start telegram-bot.service telegram-bot-2nd.service"
```

### Остановить обе
```bash
ssh -i ~/.ssh/id_ed25519_aprel root@72.56.76.248 "systemctl stop telegram-bot.service telegram-bot-2nd.service"
```

### Переключиться на только 2nd версию
```bash
ssh -i ~/.ssh/id_ed25519_aprel root@72.56.76.248 "systemctl stop telegram-bot.service && systemctl start telegram-bot-2nd.service"
```

### Переключиться на только основную версию
```bash
ssh -i ~/.ssh/id_ed25519_aprel root@72.56.76.248 "systemctl stop telegram-bot-2nd.service && systemctl start telegram-bot.service"
```

## Проверка работы

После запуска проверьте логи:

```bash
ssh -i ~/.ssh/id_ed25519_aprel root@72.56.76.248 "journalctl -u telegram-bot-2nd.service -f"
```

Вы должны увидеть:
```
✓ Connected to Telegram
✓ Bot found: ...
✓ Bot automation started (2nd button version). Waiting for triggers...
```

## Troubleshooting

### Ошибка "User not authorized"
Нужно заново создать сессию:
```bash
ssh -i ~/.ssh/id_ed25519_aprel root@72.56.76.248 "cd /root/auto && /root/auto/venv/bin/python3 create_session_2nd.py"
```

### Сервис не запускается
Проверьте логи:
```bash
ssh -i ~/.ssh/id_ed25519_aprel root@72.56.76.248 "journalctl -u telegram-bot-2nd.service -n 50"
```

### Проверить какие сервисы запущены
```bash
ssh -i ~/.ssh/id_ed25519_aprel root@72.56.76.248 "systemctl status telegram-bot.service telegram-bot-2nd.service"
```
