#!/bin/bash
# Скрипт для деплоя бота на сервер

set -e

# Конфигурация
SERVER="root@72.56.76.248"
SSH_KEY="~/.ssh/id_ed25519_aprel"
REMOTE_DIR="/root/auto"
SERVICE_NAME="bot-automation"

# Цвета для вывода
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo -e "${GREEN}=== DEPLOY BOT TO SERVER ===${NC}\n"

# Проверка подключения к серверу
echo -e "${YELLOW}1. Проверка подключения к серверу...${NC}"
ssh -i $SSH_KEY $SERVER "echo '✓ Подключение успешно'"

# Остановка текущей версии
echo -e "\n${YELLOW}2. Остановка текущей версии бота...${NC}"
ssh -i $SSH_KEY $SERVER "pkill -f 'python.*main.py' || echo 'Бот не запущен'"

# Создание директории на сервере
echo -e "\n${YELLOW}3. Создание директории на сервере...${NC}"
ssh -i $SSH_KEY $SERVER "mkdir -p $REMOTE_DIR"

# Копирование файлов (исключая ненужные)
echo -e "\n${YELLOW}4. Копирование файлов на сервер...${NC}"
rsync -avz --progress \
  -e "ssh -i $SSH_KEY" \
  --exclude='.env' \
  --exclude='.env.control_bot' \
  --exclude='*.session' \
  --exclude='*.session-journal' \
  --exclude='venv/' \
  --exclude='__pycache__/' \
  --exclude='*.pyc' \
  --exclude='*.log' \
  --exclude='.git/' \
  --exclude='.DS_Store' \
  --exclude='control_panel.db' \
  --exclude='sessions/' \
  --exclude='logs/' \
  ./ $SERVER:$REMOTE_DIR/

# Создание виртуального окружения на сервере
echo -e "\n${YELLOW}5. Создание виртуального окружения на сервере...${NC}"
ssh -i $SSH_KEY $SERVER "cd $REMOTE_DIR && python3 -m venv venv || python3 -m venv venv"

# Установка зависимостей
echo -e "\n${YELLOW}6. Установка зависимостей...${NC}"
ssh -i $SSH_KEY $SERVER "cd $REMOTE_DIR && source venv/bin/activate && pip install --upgrade pip && pip install -r requirements.txt"

# Проверка наличия .env файла
echo -e "\n${YELLOW}7. Проверка конфигурации...${NC}"
ssh -i $SSH_KEY $SERVER "cd $REMOTE_DIR && if [ ! -f .env ]; then echo -e '${RED}⚠️  Файл .env не найден!${NC}'; echo 'Скопируйте .env файл на сервер вручную:'; echo 'scp -i $SSH_KEY .env $SERVER:$REMOTE_DIR/'; fi"

# Запуск бота в screen
echo -e "\n${YELLOW}8. Запуск бота...${NC}"
echo -e "${GREEN}Бот будет запущен в screen сессии 'bot-automation'${NC}"
echo -e "${YELLOW}Для подключения к сессии используйте:${NC}"
echo -e "ssh -i $SSH_KEY $SERVER"
echo -e "screen -r bot-automation"
echo ""

read -p "Запустить бота сейчас? (y/n): " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
  ssh -i $SSH_KEY $SERVER "cd $REMOTE_DIR && screen -dmS bot-automation bash -c 'source venv/bin/activate && python main.py'"
  echo -e "${GREEN}✓ Бот запущен в screen сессии${NC}"
else
  echo -e "${YELLOW}Бот не запущен. Запустите вручную:${NC}"
  echo -e "ssh -i $SSH_KEY $SERVER"
  echo -e "cd $REMOTE_DIR"
  echo -e "source venv/bin/activate"
  echo -e "screen -S bot-automation"
  echo -e "python main.py"
fi

echo -e "\n${GREEN}=== ДЕПЛОЙ ЗАВЕРШЕН ===${NC}"
echo -e "\n${YELLOW}Полезные команды:${NC}"
echo -e "  Просмотр логов: ssh -i $SSH_KEY $SERVER 'tail -f $REMOTE_DIR/bot_automation.log'"
echo -e "  Подключение к screen: ssh -i $SSH_KEY $SERVER 'screen -r bot-automation'"
echo -e "  Остановка бота: ssh -i $SSH_KEY $SERVER 'pkill -f main.py'"
echo -e "  Перезапуск бота: ssh -i $SSH_KEY $SERVER 'cd $REMOTE_DIR && screen -dmS bot-automation bash -c \"source venv/bin/activate && python main.py\"'"

