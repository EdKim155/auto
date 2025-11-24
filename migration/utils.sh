#!/bin/bash

###############################################################################
# Вспомогательные функции для миграции
###############################################################################

# Загрузка конфигурации
source "$(dirname "$0")/config.sh"

###############################################################################
# Функции логирования
###############################################################################

log_info() {
    local message="$1"
    echo -e "${GREEN}[INFO]${NC} $(date '+%Y-%m-%d %H:%M:%S') - $message" | tee -a "$LOG_FILE"
}

log_warn() {
    local message="$1"
    echo -e "${YELLOW}[WARN]${NC} $(date '+%Y-%m-%d %H:%M:%S') - $message" | tee -a "$LOG_FILE"
}

log_error() {
    local message="$1"
    echo -e "${RED}[ERROR]${NC} $(date '+%Y-%m-%d %H:%M:%S') - $message" | tee -a "$LOG_FILE" "$ERROR_LOG"
}

log_success() {
    local message="$1"
    echo -e "${GREEN}[SUCCESS]${NC} $(date '+%Y-%m-%d %H:%M:%S') - $message" | tee -a "$LOG_FILE"
}

log_step() {
    local step="$1"
    echo -e "\n${BLUE}═══════════════════════════════════════════════════════════════${NC}" | tee -a "$LOG_FILE"
    echo -e "${BLUE}[STEP]${NC} $step" | tee -a "$LOG_FILE"
    echo -e "${BLUE}═══════════════════════════════════════════════════════════════${NC}\n" | tee -a "$LOG_FILE"
}

###############################################################################
# Функции проверки
###############################################################################

get_ssh_target() {
    local host="$1"
    local user="$2"
    local alias="${3:-}"

    if [ -n "$alias" ] && [ "${USE_SSH_ALIAS:-0}" -eq 1 ]; then
        echo "$alias"
    else
        echo "$user@$host"
    fi
}

check_command() {
    local cmd="$1"
    if ! command -v "$cmd" &> /dev/null; then
        log_error "Команда '$cmd' не найдена. Установите её перед продолжением."
        return 1
    fi
    return 0
}

check_ssh_connection() {
    local host="$1"
    local user="$2"
    local key="$3"
    local alias="${4:-}"

    # Использовать алиас, если передан и включена опция USE_SSH_ALIAS
    local ssh_target
    if [ -n "$alias" ] && [ "${USE_SSH_ALIAS:-0}" -eq 1 ]; then
        ssh_target="$alias"
        log_info "Проверка SSH-соединения через алиас $alias..."
    else
        ssh_target="$user@$host"
        log_info "Проверка SSH-соединения с $user@$host..."
    fi

    if [ -n "$key" ] && [ "${USE_SSH_ALIAS:-0}" -eq 0 ]; then
        ssh -i "$key" -o ConnectTimeout=$SSH_TIMEOUT -o BatchMode=yes "$ssh_target" "echo 'SSH OK'" &> /dev/null
    else
        ssh -o ConnectTimeout=$SSH_TIMEOUT -o BatchMode=yes "$ssh_target" "echo 'SSH OK'" &> /dev/null
    fi

    if [ $? -eq 0 ]; then
        log_success "SSH-соединение установлено"
        return 0
    else
        log_error "Не удалось установить SSH-соединение"
        return 1
    fi
}

check_disk_space() {
    local host="$1"
    local user="$2"
    local key="$3"
    local required_mb="$4"
    local alias="${5:-}"

    log_info "Проверка свободного места на $host..."

    local ssh_target=$(get_ssh_target "$host" "$user" "$alias")
    local ssh_cmd="ssh"
    [ -n "$key" ] && [ "${USE_SSH_ALIAS:-0}" -eq 0 ] && ssh_cmd="ssh -i $key"

    local available_mb=$($ssh_cmd "$ssh_target" "df -m / | tail -1 | awk '{print \$4}'" 2>/dev/null || echo "0")

    if [ "$available_mb" -gt "$required_mb" ]; then
        log_success "Доступно ${available_mb}MB (требуется ${required_mb}MB)"
        return 0
    else
        log_error "Недостаточно места: доступно ${available_mb}MB, требуется ${required_mb}MB"
        return 1
    fi
}

###############################################################################
# Функции создания директорий
###############################################################################

ensure_directory() {
    local dir="$1"
    if [ ! -d "$dir" ]; then
        log_info "Создание директории: $dir"
        mkdir -p "$dir"
        if [ $? -eq 0 ]; then
            log_success "Директория создана: $dir"
        else
            log_error "Не удалось создать директорию: $dir"
            return 1
        fi
    fi
    return 0
}

ensure_remote_directory() {
    local host="$1"
    local user="$2"
    local key="$3"
    local dir="$4"
    local alias="${5:-}"

    log_info "Создание директории на удаленном сервере: $dir"

    local ssh_target=$(get_ssh_target "$host" "$user" "$alias")
    local ssh_cmd="ssh"
    [ -n "$key" ] && [ "${USE_SSH_ALIAS:-0}" -eq 0 ] && ssh_cmd="ssh -i $key"

    $ssh_cmd "$ssh_target" "mkdir -p '$dir'" 2>&1 | tee -a "$LOG_FILE"

    if [ ${PIPESTATUS[0]} -eq 0 ]; then
        log_success "Директория создана на удаленном сервере: $dir"
        return 0
    else
        log_error "Не удалось создать директорию на удаленном сервере: $dir"
        return 1
    fi
}

###############################################################################
# Функции работы с файлами
###############################################################################

create_checksum() {
    local file="$1"
    local checksum_file="$2"

    if [ -f "$file" ]; then
        log_info "Создание контрольной суммы для: $(basename $file)"
        shasum -a 256 "$file" >> "$checksum_file"
        log_success "Контрольная сумма создана"
    else
        log_warn "Файл не найден для создания контрольной суммы: $file"
    fi
}

verify_checksum() {
    local checksum_file="$1"

    log_info "Проверка контрольных сумм..."

    if [ -f "$checksum_file" ]; then
        shasum -a 256 -c "$checksum_file" 2>&1 | tee -a "$LOG_FILE"
        if [ ${PIPESTATUS[0]} -eq 0 ]; then
            log_success "Все контрольные суммы совпадают"
            return 0
        else
            log_error "Обнаружены несоответствия контрольных сумм"
            return 1
        fi
    else
        log_warn "Файл контрольных сумм не найден: $checksum_file"
        return 1
    fi
}

###############################################################################
# Функции выполнения команд
###############################################################################

# Wrapper функции для упрощения вызовов
run_target_command() {
    run_remote_command "$TARGET_HOST" "$TARGET_USER" "$TARGET_SSH_KEY" "$1" "$TARGET_ALIAS"
}

run_source_command() {
    run_remote_command "$SOURCE_HOST" "$SOURCE_USER" "$SOURCE_SSH_KEY" "$1" "$SOURCE_ALIAS"
}

run_remote_command() {
    local host="$1"
    local user="$2"
    local key="$3"
    local command="$4"
    local alias="${5:-}"

    log_info "Выполнение команды на $host: $command"

    local ssh_target=$(get_ssh_target "$host" "$user" "$alias")
    local ssh_cmd="ssh"
    [ -n "$key" ] && [ "${USE_SSH_ALIAS:-0}" -eq 0 ] && ssh_cmd="ssh -i $key"

    $ssh_cmd "$ssh_target" "$command" 2>&1 | tee -a "$LOG_FILE"

    local exit_code=${PIPESTATUS[0]}
    if [ $exit_code -eq 0 ]; then
        log_success "Команда выполнена успешно"
    else
        log_error "Команда завершилась с ошибкой (код: $exit_code)"
    fi

    return $exit_code
}

###############################################################################
# Функции уведомлений
###############################################################################

send_notification() {
    local subject="$1"
    local message="$2"

    # Email уведомление
    if [ -n "$NOTIFY_EMAIL" ]; then
        echo "$message" | mail -s "$subject" "$NOTIFY_EMAIL" 2>&1 | tee -a "$LOG_FILE"
    fi

    # Webhook уведомление
    if [ -n "$NOTIFY_WEBHOOK" ]; then
        curl -X POST "$NOTIFY_WEBHOOK" \
            -H "Content-Type: application/json" \
            -d "{\"subject\": \"$subject\", \"message\": \"$message\"}" \
            2>&1 | tee -a "$LOG_FILE"
    fi
}

###############################################################################
# Функции инициализации
###############################################################################

init_migration() {
    log_step "Инициализация миграции"

    # Создание необходимых директорий
    ensure_directory "$BACKUP_DIR"
    ensure_directory "$LOG_DIR"
    ensure_directory "$TEMP_DIR"

    # Проверка необходимых команд
    local required_commands=("ssh" "scp" "rsync" "tar" "shasum")
    for cmd in "${required_commands[@]}"; do
        check_command "$cmd" || exit 1
    done

    log_success "Инициализация завершена"
}

###############################################################################
# Функции очистки
###############################################################################

cleanup() {
    log_info "Очистка временных файлов..."
    rm -rf "$TEMP_DIR"/*
    log_success "Очистка завершена"
}

###############################################################################
# Функции завершения
###############################################################################

finish_migration() {
    local status="$1"

    if [ "$status" = "success" ]; then
        log_success "Миграция завершена успешно!"
        send_notification "Миграция завершена" "Миграция Telegram-бота завершена успешно"
    else
        log_error "Миграция завершена с ошибками"
        send_notification "Миграция завершена с ошибками" "Проверьте логи: $LOG_FILE"
    fi

    cleanup
}

# Обработчик прерывания
trap 'log_error "Миграция прервана пользователем"; cleanup; exit 1' INT TERM
