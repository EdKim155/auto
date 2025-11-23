# Быстрый старт - 2nd Button Version

## Созданные файлы

1. **bot_automation_2nd.py** - основной модуль автоматизации (нажимает 2-ю кнопку)
2. **main_2nd.py** - точка входа для запуска
3. **.env.2nd** - конфигурация (уже настроен на @apri1l_test_bot)
4. **.env.2nd.example** - пример конфигурации
5. **README_2ND.md** - полная документация

## Быстрый запуск локально

```bash
# Запустить 2nd версию (нажимает 2-ю кнопку)
python3 main_2nd.py
```

## Развертывание на сервере

### 1. Загрузить файлы на сервер
```bash
scp -i ~/.ssh/id_ed25519_aprel bot_automation_2nd.py main_2nd.py .env.2nd root@72.56.76.248:/root/auto/
```

### 2. Создать systemd сервис
```bash
ssh -i ~/.ssh/id_ed25519_aprel root@72.56.76.248

# Создать файл сервиса
cat > /etc/systemd/system/telegram-bot-2nd.service <<EOF
[Unit]
Description=Telegram Bot Automation (2nd Button)
After=network.target

[Service]
Type=simple
User=root
WorkingDirectory=/root/auto
ExecStart=/root/auto/venv/bin/python3 /root/auto/main_2nd.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
EOF
```

### 3. Запустить сервис
```bash
systemctl daemon-reload
systemctl enable telegram-bot-2nd.service
systemctl start telegram-bot-2nd.service
systemctl status telegram-bot-2nd.service
```

### 4. Проверить логи
```bash
journalctl -u telegram-bot-2nd.service -f
```

## Переключение версий на сервере

### Запустить 2nd версию (нажимает 2-ю кнопку)
```bash
ssh -i ~/.ssh/id_ed25519_aprel root@72.56.76.248 "systemctl stop telegram-bot.service && systemctl start telegram-bot-2nd.service"
```

### Вернуться к основной версии (нажимает 1-ю кнопку)
```bash
ssh -i ~/.ssh/id_ed25519_aprel root@72.56.76.248 "systemctl stop telegram-bot-2nd.service && systemctl start telegram-bot.service"
```

## Что изменено?

**Шаг 2** теперь нажимает **ВТОРУЮ** кнопку в списке перевозок вместо первой:

```python
# Было (основная версия):
button = self.button_analyzer.get_first_button(msg_data.buttons)

# Стало (2nd версия):
button = self.button_analyzer.get_button_at_position(msg_data.buttons, row=1, column=0)
```

## Важно

- Для работы 2nd версии нужно **минимум 2 перевозки** в списке
- Если перевозка только одна, скрипт выдаст ошибку
- Можно запускать обе версии одновременно на разных аккаунтах/ботах
