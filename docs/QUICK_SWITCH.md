# Быстрое переключение на @ACarriers_bot

## Вариант 1: Автоматический (РЕКОМЕНДУЕТСЯ)

На сервере выполните:

```bash
cd /root/auto
./switch_bot.sh @ACarriers_bot
```

Скрипт автоматически:
- ✓ Остановит текущую автоматизацию
- ✓ Создаст резервную копию .env
- ✓ Изменит BOT_USERNAME на @ACarriers_bot
- ✓ Предложит запустить автоматизацию
- ✓ Покажет статус запуска

---

## Вариант 2: Вручную

### 1. Подключитесь к серверу
```bash
ssh root@5934165-yc246618
```

### 2. Остановите автоматизацию
```bash
pkill -f main.py
```

### 3. Измените .env
```bash
cd /root/auto
sed -i 's/BOT_USERNAME=.*/BOT_USERNAME=@ACarriers_bot/' .env
```

### 4. Проверьте изменения
```bash
cat .env | grep BOT_USERNAME
```

Должно вывести:
```
BOT_USERNAME=@ACarriers_bot
```

### 5. Запустите автоматизацию
```bash
nohup python3 main.py > automation_output.log 2>&1 &
```

### 6. Проверьте логи
```bash
tail -f /root/auto/bot_automation.log
```

Вы должны увидеть:
```
=== Configuration ===
Bot: @ACarriers_bot
Trigger: 'Появились новые перевозки'
```

---

## Проверка работы

```bash
# Проверить что процесс запущен
ps aux | grep main.py | grep -v grep

# Следить за логами
tail -f /root/auto/bot_automation.log

# Проверить статистику (должна обновляться каждую минуту)
# Вывод должен содержать:
# State: IDLE
# Messages: X, Edits: Y, Triggers: Z
```

---

## Быстрый откат

Если нужно вернуться к предыдущему боту:

### Вариант 1 (автоматически):
```bash
./switch_bot.sh @apri1l_test_bot
```

### Вариант 2 (вручную):
```bash
pkill -f main.py
sed -i 's/BOT_USERNAME=.*/BOT_USERNAME=@apri1l_test_bot/' .env
nohup python3 main.py > automation_output.log 2>&1 &
```

---

## Возможные проблемы

### Скрипт switch_bot.sh не найден
```bash
# Сделайте файл исполняемым
chmod +x /root/auto/switch_bot.sh
```

### Permission denied
```bash
# Выполните от root
sudo ./switch_bot.sh @ACarriers_bot
```

### Процесс не запускается
```bash
# Проверьте логи ошибок
tail -50 /root/auto/automation_output.log

# Проверьте что Python доступен
which python3

# Попробуйте запустить в интерактивном режиме для диагностики
python3 main.py
```

---

## Детальная документация

Для подробной информации см. `SWITCH_TO_ACARRIERS.md`
