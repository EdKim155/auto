#!/bin/bash
# Скрипт для переключения бота автоматизации
# Использование: ./switch_bot.sh @ACarriers_bot

set -e  # Остановить при ошибке

# Цвета для вывода
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Функция для вывода с цветом
print_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Проверка аргументов
if [ $# -eq 0 ]; then
    print_error "Не указан бот для переключения"
    echo "Использование: $0 <BOT_USERNAME>"
    echo "Пример: $0 @ACarriers_bot"
    exit 1
fi

NEW_BOT="$1"

# Проверка формата имени бота
if [[ ! "$NEW_BOT" =~ ^@[a-zA-Z0-9_]+$ ]]; then
    print_warning "Имя бота должно начинаться с @ и содержать только буквы, цифры и _"
    echo "Вы указали: $NEW_BOT"
    read -p "Продолжить? (y/n) " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        exit 1
    fi
fi

print_info "Переключение автоматизации на бота: $NEW_BOT"
echo

# 1. Определение директории проекта
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd "$SCRIPT_DIR"
print_info "Директория проекта: $SCRIPT_DIR"

# 2. Проверка существования .env файла
if [ ! -f ".env" ]; then
    print_error "Файл .env не найден!"
    exit 1
fi

# 3. Сохранение текущего бота
CURRENT_BOT=$(grep "^BOT_USERNAME=" .env | cut -d'=' -f2)
print_info "Текущий бот: $CURRENT_BOT"
print_info "Новый бот: $NEW_BOT"
echo

# 4. Подтверждение
read -p "Переключить с $CURRENT_BOT на $NEW_BOT? (y/n) " -n 1 -r
echo
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    print_warning "Отменено пользователем"
    exit 0
fi

# 5. Остановка текущей автоматизации
print_info "Остановка текущих процессов автоматизации..."
pkill -f "main.py" 2>/dev/null && print_info "Процесс main.py остановлен" || print_warning "Процесс main.py не найден"
pkill -f "main_2nd.py" 2>/dev/null && print_info "Процесс main_2nd.py остановлен" || print_warning "Процесс main_2nd.py не найден"
sleep 2

# 6. Создание резервной копии .env
BACKUP_FILE=".env.backup.$(date +%Y%m%d_%H%M%S)"
cp .env "$BACKUP_FILE"
print_info "Резервная копия создана: $BACKUP_FILE"

# 7. Обновление .env файла
sed -i.tmp "s|^BOT_USERNAME=.*|BOT_USERNAME=$NEW_BOT|" .env
rm -f .env.tmp
print_info "Файл .env обновлен"

# 8. Проверка изменений
NEW_VALUE=$(grep "^BOT_USERNAME=" .env | cut -d'=' -f2)
if [ "$NEW_VALUE" = "$NEW_BOT" ]; then
    print_info "✓ Проверка: BOT_USERNAME = $NEW_VALUE"
else
    print_error "✗ Проверка не прошла: BOT_USERNAME = $NEW_VALUE (ожидалось: $NEW_BOT)"
    print_error "Восстановление из резервной копии..."
    cp "$BACKUP_FILE" .env
    exit 1
fi

# 9. Вывод текущей конфигурации
echo
print_info "=== Текущая конфигурация ==="
grep -E "^(API_ID|API_HASH|PHONE|BOT_USERNAME|SESSION_NAME)" .env | while IFS= read -r line; do
    KEY=$(echo "$line" | cut -d'=' -f1)
    VALUE=$(echo "$line" | cut -d'=' -f2)

    # Скрыть чувствительные данные
    if [[ "$KEY" == "API_HASH" ]]; then
        VALUE="${VALUE:0:10}..."
    elif [[ "$KEY" == "PHONE" ]]; then
        VALUE="${VALUE:0:8}..."
    fi

    echo "  $KEY = $VALUE"
done
echo

# 10. Предложение запустить автоматизацию
print_info "Переключение завершено успешно!"
echo
read -p "Запустить автоматизацию сейчас? (y/n) " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    print_info "Запуск автоматизации..."

    # Проверка наличия screen
    if command -v screen &> /dev/null; then
        print_info "Используется screen для запуска..."
        screen -dmS bot_automation bash -c "cd $SCRIPT_DIR && python3 main.py"
        print_info "✓ Автоматизация запущена в screen сессии 'bot_automation'"
        print_info "Для подключения: screen -r bot_automation"
    else
        print_info "Запуск в фоновом режиме..."
        nohup python3 main.py > automation_output.log 2>&1 &
        PID=$!
        print_info "✓ Автоматизация запущена с PID: $PID"
    fi

    sleep 3

    # Проверка что процесс запущен
    if pgrep -f "main.py" > /dev/null; then
        print_info "✓ Процесс автоматизации работает"
        echo
        print_info "Просмотр логов: tail -f bot_automation.log"
    else
        print_error "✗ Процесс не найден. Проверьте логи для деталей."
        if [ -f "automation_output.log" ]; then
            print_info "Последние строки из лога:"
            tail -20 automation_output.log
        fi
    fi
else
    print_info "Автоматизация не запущена"
    echo
    print_info "Для запуска вручную выполните:"
    echo "  nohup python3 main.py > automation_output.log 2>&1 &"
    echo "или"
    echo "  screen -S bot_automation"
    echo "  python3 main.py"
fi

echo
print_info "=== Полезные команды ==="
echo "  Просмотр логов:     tail -f bot_automation.log"
echo "  Остановка:          pkill -f main.py"
echo "  Проверка процесса:  ps aux | grep main.py"
echo "  Откат к $CURRENT_BOT: ./switch_bot.sh $CURRENT_BOT"
echo
