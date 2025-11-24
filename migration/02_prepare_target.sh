#!/bin/bash

###############################################################################
# Скрипт подготовки целевого сервера
# Устанавливает необходимое ПО и создает структуру директорий
###############################################################################

set -euo pipefail

# Загрузка конфигурации и утилит
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$SCRIPT_DIR/config.sh"
source "$SCRIPT_DIR/utils.sh"

###############################################################################
# Главная функция
###############################################################################

main() {
    log_step "ПОДГОТОВКА ЦЕЛЕВОГО СЕРВЕРА"

    init_migration

    # Проверка подключения к целевому серверу
    log_info "Проверка подключения к целевому серверу..."
    check_ssh_connection "$TARGET_HOST" "$TARGET_USER" "" "$TARGET_ALIAS" || {
        log_error "Не удалось подключиться к целевому серверу"
        exit 1
    }

    # Проверка свободного места
    log_info "Проверка свободного места на целевом сервере..."
    check_disk_space "$TARGET_HOST" "$TARGET_USER" "" 2048 "$TARGET_ALIAS" || {
        log_error "Недостаточно места на целевом сервере"
        exit 1
    }

    # Получение информации о целевом сервере
    log_step "Сбор информации о целевом сервере"

    log_info "Получение информации об ОС..."
    run_remote_command "$TARGET_HOST" "$TARGET_USER" "" \
        "cat /etc/os-release" > "$TEMP_DIR/target_os_info.txt"

    log_info "Получение информации о ядре..."
    run_remote_command "$TARGET_HOST" "$TARGET_USER" "" \
        "uname -a" > "$TEMP_DIR/target_kernel_info.txt"

    # Обновление системы
    log_step "Обновление системы"

    log_info "Обновление списка пакетов..."
    run_remote_command "$TARGET_HOST" "$TARGET_USER" "" \
        "apt-get update -qq"

    # Установка необходимых системных пакетов
    log_step "Установка системных зависимостей"

    log_info "Установка необходимых пакетов..."
    run_remote_command "$TARGET_HOST" "$TARGET_USER" "" \
        "DEBIAN_FRONTEND=noninteractive apt-get install -y -qq \
        python3 \
        python3-pip \
        python3-venv \
        build-essential \
        libssl-dev \
        libffi-dev \
        python3-dev \
        git \
        curl \
        wget \
        rsync \
        htop \
        vim \
        screen"

    # Проверка версии Python
    log_step "Проверка Python"

    log_info "Проверка версии Python..."
    run_remote_command "$TARGET_HOST" "$TARGET_USER" "" \
        "python3 --version" > "$TEMP_DIR/target_python_version.txt"

    local target_python_version=$(cat "$TEMP_DIR/target_python_version.txt" | grep -oP '\d+\.\d+' | head -1)
    log_info "Версия Python на целевом сервере: $target_python_version"

    # Проверка pip
    log_info "Проверка pip..."
    run_remote_command "$TARGET_HOST" "$TARGET_USER" "" \
        "python3 -m pip --version" > "$TEMP_DIR/target_pip_version.txt"

    # Обновление pip
    log_info "Обновление pip..."
    run_remote_command "$TARGET_HOST" "$TARGET_USER" "" \
        "python3 -m pip install --upgrade pip setuptools wheel"

    # Создание структуры директорий
    log_step "Создание структуры директорий"

    log_info "Создание директории приложения..."
    ensure_remote_directory "$TARGET_HOST" "$TARGET_USER" "" "$TARGET_APP_DIR"

    log_info "Создание директории для резервных копий..."
    ensure_remote_directory "$TARGET_HOST" "$TARGET_USER" "" "$TARGET_APP_DIR/backups"

    log_info "Создание директории для логов..."
    ensure_remote_directory "$TARGET_HOST" "$TARGET_USER" "" "/var/log/telegram-bot"

    # Проверка существующих файлов
    log_step "Проверка существующих файлов"

    log_info "Проверка наличия существующих файлов приложения..."
    local existing_files=$(ssh "$TARGET_USER@$TARGET_HOST" "ls -A $TARGET_APP_DIR 2>/dev/null | wc -l" || echo "0")

    if [ "$existing_files" -gt 0 ]; then
        log_warn "На целевом сервере уже существуют файлы в $TARGET_APP_DIR"

        if [ "$FORCE" -eq 1 ]; then
            log_warn "Режим FORCE включен. Создание резервной копии существующих файлов..."
            run_remote_command "$TARGET_HOST" "$TARGET_USER" "" \
                "cd $(dirname $TARGET_APP_DIR) && tar -czf auto_existing_backup_${TIMESTAMP}.tar.gz $(basename $TARGET_APP_DIR)/"
            log_success "Резервная копия создана"
        else
            log_error "Для перезаписи используйте флаг FORCE=1"
            exit 1
        fi
    else
        log_success "Директория приложения пуста"
    fi

    # Настройка firewall (опционально)
    log_step "Проверка firewall"

    log_info "Проверка статуса UFW..."
    if run_remote_command "$TARGET_HOST" "$TARGET_USER" "" "command -v ufw" &>/dev/null; then
        log_info "UFW установлен. Проверка правил..."
        run_remote_command "$TARGET_HOST" "$TARGET_USER" "" \
            "ufw status" > "$TEMP_DIR/target_ufw_status.txt" || true

        log_info "Убедитесь, что порты 80 и 443 открыты для Telegram API"
    else
        log_info "UFW не установлен"
    fi

    # Проверка часового пояса
    log_step "Проверка настроек времени"

    log_info "Проверка часового пояса..."
    run_remote_command "$TARGET_HOST" "$TARGET_USER" "" \
        "timedatectl" > "$TEMP_DIR/target_timezone.txt"

    # Создание отчета о подготовке
    log_step "Создание отчета о подготовке"

    local report_file="$BACKUP_DIR/preparation_report_${TIMESTAMP}.md"

    cat > "$report_file" << EOF
# Отчет о подготовке целевого сервера

**Дата:** $(date '+%Y-%m-%d %H:%M:%S')
**Сервер:** $TARGET_HOST ($TARGET_ALIAS)

## Информация о системе

### ОС
\`\`\`
$(cat "$TEMP_DIR/target_os_info.txt")
\`\`\`

### Ядро
\`\`\`
$(cat "$TEMP_DIR/target_kernel_info.txt")
\`\`\`

## Python окружение

### Версия Python
\`\`\`
$(cat "$TEMP_DIR/target_python_version.txt")
\`\`\`

### Версия pip
\`\`\`
$(cat "$TEMP_DIR/target_pip_version.txt")
\`\`\`

## Установленные пакеты

- Python 3
- pip
- venv
- build-essential
- libssl-dev
- libffi-dev
- git
- curl, wget
- rsync
- htop, vim, screen

## Созданные директории

- $TARGET_APP_DIR
- $TARGET_APP_DIR/backups
- /var/log/telegram-bot

## Firewall

\`\`\`
$(cat "$TEMP_DIR/target_ufw_status.txt" 2>/dev/null || echo "UFW не установлен")
\`\`\`

## Часовой пояс

\`\`\`
$(cat "$TEMP_DIR/target_timezone.txt")
\`\`\`

---
*Отчет создан автоматически скриптом подготовки*
EOF

    log_success "Отчет о подготовке создан: $report_file"

    log_step "ПОДГОТОВКА ЗАВЕРШЕНА"
    log_success "Целевой сервер готов к миграции"

    echo -e "\n${GREEN}════════════════════════════════════════════════════════${NC}"
    echo -e "${GREEN}Целевой сервер успешно подготовлен!${NC}"
    echo -e "${GREEN}════════════════════════════════════════════════════════${NC}"
    echo -e "\nСледующий шаг: Запустите ${BLUE}./03_backup_and_transfer.sh${NC}"
}

# Запуск скрипта
main "$@"
