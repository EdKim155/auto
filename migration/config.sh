#!/bin/bash

###############################################################################
# Конфигурация миграции Telegram-бота
###############################################################################

# Цвета для вывода
export RED='\033[0;31m'
export GREEN='\033[0;32m'
export YELLOW='\033[1;33m'
export BLUE='\033[0;34m'
export NC='\033[0m' # No Color

# Исходный сервер
export SOURCE_HOST="72.56.76.248"
export SOURCE_USER="root"
export SOURCE_SSH_KEY="$HOME/.ssh/id_ed25519_aprel"
export SOURCE_ALIAS="aprel-server"
export SOURCE_APP_DIR="/root/auto"

# Целевой сервер
export TARGET_HOST="193.108.115.170"
export TARGET_USER="root"
export TARGET_ALIAS="auto-server"
export TARGET_APP_DIR="/root/auto"
export TARGET_SSH_KEY=""  # Пустой, если используется SSH config

# Директории
export MIGRATION_DIR="/Users/edgark/auto/migration"
export BACKUP_DIR="$MIGRATION_DIR/backups"
export LOG_DIR="$MIGRATION_DIR/logs"
export TEMP_DIR="$MIGRATION_DIR/temp"

# Имя systemd-сервиса
export SERVICE_NAME="telegram-bot.service"

# Файлы для переноса
export CRITICAL_FILES=(
    ".env"
    ".env.2nd"
    ".env.control_bot"
    "*.session"
    "control_panel.db"
)

# Директории для переноса
export CRITICAL_DIRS=(
    "sessions"
    "modules"
)

# Файлы для исключения из резервной копии
export EXCLUDE_PATTERNS=(
    "__pycache__"
    "*.pyc"
    "*.pyo"
    "venv"
    "*.log"
    ".git"
)

# Таймауты
export SSH_TIMEOUT=30
export RSYNC_TIMEOUT=3600

# Checksums
export CHECKSUM_FILE="$BACKUP_DIR/checksums.sha256"

# Timestamp для резервных копий
export TIMESTAMP=$(date +%Y%m%d_%H%M%S)
export BACKUP_NAME="auto_backup_${TIMESTAMP}.tar.gz"

# Python
export PYTHON_VERSION="3.10"  # Минимальная версия
export VENV_NAME="venv"

# Логирование
export LOG_FILE="$LOG_DIR/migration_${TIMESTAMP}.log"
export ERROR_LOG="$LOG_DIR/migration_errors_${TIMESTAMP}.log"

# Опции
export VERBOSE=1
export DRY_RUN=0
export SKIP_BACKUP=0
export FORCE=0
export USE_SSH_ALIAS=1  # Использовать алиасы вместо прямого подключения

# Проверка доступности серверов (timeout в секундах)
export HEALTH_CHECK_TIMEOUT=10

# Ротация логов
export LOG_RETENTION_DAYS=30

# Email для уведомлений (опционально)
export NOTIFY_EMAIL=""

# Webhook для уведомлений (опционально)
export NOTIFY_WEBHOOK=""
