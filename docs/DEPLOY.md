# Инструкция по деплою бота на сервер

## Быстрый деплой

### 1. Первая настройка (один раз)

#### Скопируйте файл `.env` на сервер:
```bash
scp -i ~/.ssh/id_ed25519_aprel .env root@72.56.76.248:/root/auto/
```

#### Проверьте подключение к серверу:
```bash
ssh -i ~/.ssh/id_ed25519_aprel root@72.56.76.248
```

### 2. Запуск деплоя

```bash
cd /Users/edgark/auto
./deploy.sh
```

## Ручной деплой

Если скрипт не работает, выполните команды вручную:

### 1. Подключение к серверу
```bash
ssh -i ~/.ssh/id_ed25519_aprel root@72.56.76.248
```

### 2. Остановка текущей версии
```bash
pkill -f "python.*main.py"
```

### 3. Создание директории
```bash
mkdir -p /root/auto
cd /root/auto
```

### 4. Копирование файлов (с локальной машины)
```bash
# С локальной машины:
rsync -avz --progress \
  -e "ssh -i ~/.ssh/id_ed25519_aprel" \
  --exclude='.env' \
  --exclude='*.session' \
  --exclude='venv/' \
  --exclude='__pycache__/' \
  --exclude='*.log' \
  --exclude='.git/' \
  ./ root@72.56.76.248:/root/auto/
```

### 5. Создание виртуального окружения
```bash
# На сервере:
cd /root/auto
python3 -m venv venv
source venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
```

### 6. Копирование .env файла (если еще не скопирован)
```bash
# С локальной машины:
scp -i ~/.ssh/id_ed25519_aprel .env root@72.56.76.248:/root/auto/
```

### 7. Запуск бота в screen
```bash
# На сервере:
cd /root/auto
source venv/bin/activate
screen -S bot-automation
python main.py
# Нажмите Ctrl+A, затем D для отключения от screen сессии
```

## Управление ботом на сервере

### Просмотр логов
```bash
ssh -i ~/.ssh/id_ed25519_aprel root@72.56.76.248 "tail -f /root/auto/bot_automation.log"
```

### Подключение к screen сессии
```bash
ssh -i ~/.ssh/id_ed25519_aprel root@72.56.76.248
screen -r bot-automation
```

### Остановка бота
```bash
ssh -i ~/.ssh/id_ed25519_aprel root@72.56.76.248 "pkill -f main.py"
```

### Перезапуск бота
```bash
ssh -i ~/.ssh/id_ed25519_aprel root@72.56.76.248 "cd /root/auto && source venv/bin/activate && screen -dmS bot-automation bash -c 'python main.py'"
```

### Проверка статуса бота
```bash
ssh -i ~/.ssh/id_ed25519_aprel root@72.56.76.248 "ps aux | grep main.py"
```

## Troubleshooting

### Бот не запускается
1. Проверьте наличие .env файла на сервере
2. Проверьте логи: `tail -f /root/auto/bot_automation.log`
3. Проверьте виртуальное окружение: `source venv/bin/activate && python --version`

### Ошибки при установке зависимостей
```bash
# На сервере:
cd /root/auto
source venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt --no-cache-dir
```

### Проблемы с сессией Telegram
```bash
# На сервере:
cd /root/auto
python fix_session.py
```

### Бот работает, но не реагирует
1. Проверьте логи на ошибки
2. Проверьте, что бот запущен: `ps aux | grep main.py`
3. Перезапустите бота

