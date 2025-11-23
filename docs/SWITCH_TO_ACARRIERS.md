# Переключение автоматизации на @ACarriers_bot

## Что было изменено

✅ В файле `.env` изменен `BOT_USERNAME` на `@ACarriers_bot`

## Текущие настройки для @ACarriers_bot

### Триггер
```
TRIGGER_TEXT = 'Появились новые перевозки'
```

### Кнопка 1 (Step 1) - Список перевозок
Ключевые слова:
- 'список прямых перевозок'
- 'список перевозок'
- 'прямые перевозки'
- 'список свободных перевозок'

### Кнопка 2 (Step 2) - Первый транспорт
Используется **первая кнопка** в списке (по индексу 0)

### Кнопка 3 (Step 3) - Подтверждение
Ключевые слова:
- 'подтвердить'
- 'забронировать'
- 'взять'
- 'беру'
- 'подтверждаю'

### Задержки
```
DELAY_AFTER_TRIGGER = 0.5 сек       # После обнаружения триггера
DELAY_BETWEEN_CLICKS = 2.0 сек      # Между нажатиями кнопок
STABILIZATION_THRESHOLD = 0.5 сек   # Порог стабилизации сообщений
```

### Таймауты
```
STEP_1_TIMEOUT = 15.0 сек   # Ожидание ответа на Step 1
STEP_2_TIMEOUT = 15.0 сек   # Ожидание ответа на Step 2
STEP_3_TIMEOUT = 20.0 сек   # Ожидание ответа на Step 3
```

---

## Инструкция для перезапуска на сервере

### 1. Подключитесь к серверу
```bash
ssh root@5934165-yc246618
```

### 2. Перейдите в директорию проекта
```bash
cd /root/auto
```

### 3. Остановите текущую автоматизацию
```bash
# Найдите процесс
ps aux | grep -E "(main\.py|main_2nd\.py)" | grep -v grep

# Остановите процесс (замените <PID> на номер процесса)
kill <PID>

# Или используйте pkill для автоматической остановки всех процессов
pkill -f "main.py"
pkill -f "main_2nd.py"
```

### 4. Обновите .env файл
```bash
# Откройте .env для редактирования
nano .env

# Измените строку:
BOT_USERNAME=@ACarriers_bot

# Сохраните (Ctrl+O, Enter, Ctrl+X)
```

Или используйте команду sed:
```bash
sed -i 's/BOT_USERNAME=.*/BOT_USERNAME=@ACarriers_bot/' /root/auto/.env
```

### 5. Проверьте изменения
```bash
cat /root/auto/.env | grep BOT_USERNAME
```

Вывод должен быть:
```
BOT_USERNAME=@ACarriers_bot
```

### 6. Запустите автоматизацию
```bash
# В фоновом режиме с логированием
nohup python3 main.py > automation_output.log 2>&1 &

# Или используйте screen/tmux для управления сессией
screen -S bot_automation
python3 main.py
# Нажмите Ctrl+A, затем D для отсоединения
```

### 7. Проверьте что автоматизация запущена
```bash
# Проверьте процесс
ps aux | grep main.py | grep -v grep

# Следите за логами
tail -f /root/auto/bot_automation.log
```

Вы должны увидеть:
```
=== Configuration ===
Bot: @ACarriers_bot
...
```

---

## Альтернатива: Использование systemd (рекомендуется для продакшена)

### Создайте systemd service файл

```bash
sudo nano /etc/systemd/system/bot-automation.service
```

Содержимое:
```ini
[Unit]
Description=Telegram Bot Automation for @ACarriers_bot
After=network.target

[Service]
Type=simple
User=root
WorkingDirectory=/root/auto
Environment="PYTHONUNBUFFERED=1"
ExecStart=/usr/bin/python3 /root/auto/main.py
Restart=always
RestartSec=10

# Логирование
StandardOutput=append:/root/auto/bot_automation.log
StandardError=append:/root/auto/bot_automation_error.log

[Install]
WantedBy=multi-user.target
```

### Управление службой

```bash
# Перезагрузить конфигурацию systemd
sudo systemctl daemon-reload

# Запустить службу
sudo systemctl start bot-automation

# Проверить статус
sudo systemctl status bot-automation

# Включить автозапуск при загрузке системы
sudo systemctl enable bot-automation

# Остановить службу
sudo systemctl stop bot-automation

# Перезапустить службу
sudo systemctl restart bot-automation

# Просмотр логов
sudo journalctl -u bot-automation -f
```

---

## Проверка работы

### 1. Проверьте логи
```bash
tail -f /root/auto/bot_automation.log
```

Должно быть видно:
```
=== Configuration ===
Bot: @ACarriers_bot
Trigger: 'Появились новые перевозки'
...
✓ Bot automation started. Waiting for triggers...
```

### 2. Проверьте статистику
Логи должны показывать регулярные обновления статуса:
```
--- Status Update ---
State: IDLE
Messages: X, Edits: Y, Triggers: Z
Clicks: N (Success: M, Failed: 0)
```

### 3. Отправьте тестовое сообщение
Если у вас есть доступ к боту, отправьте сообщение "Появились новые перевозки" от имени бота, чтобы проверить срабатывание триггера.

---

## Использование инструментов тестирования

Перед запуском автоматизации **рекомендуется** протестировать бота:

```bash
# На локальной машине
python test_acarriers_bot_interactive.py
```

Это позволит:
1. Убедиться что бот отвечает
2. Проверить структуру меню и кнопки
3. Убедиться что ключевые слова кнопок совпадают
4. Понять время отклика бота

---

## Мониторинг

### Постоянный мониторинг логов
```bash
# В отдельном терминале/screen сессии
tail -f /root/auto/bot_automation.log
```

### Проверка работоспособности раз в час
Добавьте в crontab:
```bash
crontab -e
```

Добавьте:
```
*/5 * * * * pgrep -f "main.py" > /dev/null || /usr/bin/python3 /root/auto/main.py >> /root/auto/automation_output.log 2>&1 &
```

Это будет перезапускать автоматизацию каждые 5 минут, если процесс упал.

---

## Возможные проблемы

### Бот не обнаруживается
**Решение:** Убедитесь что @ACarriers_bot написан правильно (с большой буквы A и C)

### Триггер не срабатывает
**Решение:** Проверьте что текст триггера точно совпадает: `'Появились новые перевозки'`

### Кнопки не находятся
**Решение:** Запустите тестер и проверьте точные названия кнопок:
```bash
python test_acarriers_bot_interactive.py
```

### Сессия не найдена
**Решение:** Возможно нужно пересоздать сессию:
```bash
rm /root/auto/telegram_session.session*
python3 main.py  # Введите код подтверждения при запросе
```

---

## Откат на старого бота

Если нужно вернуться к @apri1l_test_bot:

```bash
sed -i 's/BOT_USERNAME=.*/BOT_USERNAME=@apri1l_test_bot/' /root/auto/.env
# Перезапустите автоматизацию
```

---

## Дополнительная информация

- Полная документация тестера: `TEST_BOT_README.md`
- Быстрый старт тестирования: `QUICKSTART_BOT_TESTING.md`
- Конфигурация автоматизации: `config.py`
