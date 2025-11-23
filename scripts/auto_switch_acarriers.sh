#!/bin/bash
# Автоматическое переключение на @ACarriers_bot
# Выполните этот скрипт на сервере: bash auto_switch_acarriers.sh

set -e

echo "=========================================="
echo "Переключение на @ACarriers_bot"
echo "=========================================="
echo

# Остановка текущей автоматизации
echo "[1/5] Остановка текущих процессов..."
pkill -f "main.py" 2>/dev/null && echo "✓ Процесс остановлен" || echo "⚠ Процесс не найден"
sleep 2

# Переход в директорию проекта
cd /root/auto
echo "✓ Директория: $(pwd)"

# Резервная копия
echo "[2/5] Создание резервной копии..."
cp .env .env.backup.$(date +%Y%m%d_%H%M%S)
echo "✓ Резервная копия создана"

# Изменение BOT_USERNAME
echo "[3/5] Изменение BOT_USERNAME..."
sed -i 's/BOT_USERNAME=.*/BOT_USERNAME=@ACarriers_bot/' .env
echo "✓ BOT_USERNAME изменен"

# Проверка
echo "[4/5] Проверка изменений..."
NEW_BOT=$(grep "^BOT_USERNAME=" .env | cut -d'=' -f2)
if [ "$NEW_BOT" = "@ACarriers_bot" ]; then
    echo "✓ Проверка пройдена: BOT_USERNAME = $NEW_BOT"
else
    echo "✗ ОШИБКА: BOT_USERNAME = $NEW_BOT"
    exit 1
fi

# Запуск автоматизации
echo "[5/5] Запуск автоматизации..."
nohup python3 main.py > automation_output.log 2>&1 &
PID=$!
echo "✓ Автоматизация запущена (PID: $PID)"

sleep 3

# Проверка запуска
if pgrep -f "main.py" > /dev/null; then
    echo
    echo "=========================================="
    echo "✓ УСПЕШНО! Автоматизация переключена"
    echo "=========================================="
    echo
    echo "Бот: @ACarriers_bot"
    echo "Процесс: $(pgrep -f main.py)"
    echo
    echo "Просмотр логов:"
    echo "  tail -f /root/auto/bot_automation.log"
    echo
    echo "Показываю последние 20 строк лога..."
    echo "------------------------------------------"
    tail -20 /root/auto/bot_automation.log
else
    echo
    echo "✗ ОШИБКА: Процесс не запустился"
    echo "Проверьте логи:"
    tail -20 automation_output.log
    exit 1
fi
