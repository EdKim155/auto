#!/bin/bash

###############################################################################
# Скрипт аудита исходного сервера
# Проверяет текущее состояние, версии ПО, создает резервные копии
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
    log_step "АУДИТ ИСХОДНОГО СЕРВЕРА"

    init_migration

    # Проверка подключения к исходному серверу
    log_info "Проверка подключения к исходному серверу..."
    check_ssh_connection "$SOURCE_HOST" "$SOURCE_USER" "$SOURCE_SSH_KEY" "$SOURCE_ALIAS" || {
        log_error "Не удалось подключиться к исходному серверу"
        exit 1
    }

    # Сбор информации о системе
    log_step "Сбор информации о системе"

    log_info "Получение информации об ОС..."
    run_remote_command "$SOURCE_HOST" "$SOURCE_USER" "$SOURCE_SSH_KEY" \
        "cat /etc/os-release" > "$TEMP_DIR/source_os_info.txt"

    log_info "Получение информации о ядре..."
    run_remote_command "$SOURCE_HOST" "$SOURCE_USER" "$SOURCE_SSH_KEY" \
        "uname -a" > "$TEMP_DIR/source_kernel_info.txt"

    # Проверка версий Python
    log_step "Проверка версий Python"

    log_info "Проверка версии Python..."
    run_remote_command "$SOURCE_HOST" "$SOURCE_USER" "$SOURCE_SSH_KEY" \
        "python3 --version" > "$TEMP_DIR/source_python_version.txt"

    log_info "Проверка версии pip..."
    run_remote_command "$SOURCE_HOST" "$SOURCE_USER" "$SOURCE_SSH_KEY" \
        "pip3 --version" > "$TEMP_DIR/source_pip_version.txt"

    # Экспорт установленных пакетов
    log_step "Экспорт Python-зависимостей"

    log_info "Экспорт pip freeze..."
    run_remote_command "$SOURCE_HOST" "$SOURCE_USER" "$SOURCE_SSH_KEY" \
        "cd $SOURCE_APP_DIR && source venv/bin/activate && pip freeze" > "$TEMP_DIR/requirements_frozen.txt"

    # Проверка структуры приложения
    log_step "Проверка структуры приложения"

    log_info "Получение списка файлов приложения..."
    run_remote_command "$SOURCE_HOST" "$SOURCE_USER" "$SOURCE_SSH_KEY" \
        "ls -lAh $SOURCE_APP_DIR" > "$TEMP_DIR/source_app_structure.txt"

    log_info "Получение размера директории..."
    run_remote_command "$SOURCE_HOST" "$SOURCE_USER" "$SOURCE_SSH_KEY" \
        "du -sh $SOURCE_APP_DIR" > "$TEMP_DIR/source_app_size.txt"

    # Проверка статуса systemd-сервиса
    log_step "Проверка статуса systemd-сервиса"

    log_info "Получение статуса сервиса..."
    run_remote_command "$SOURCE_HOST" "$SOURCE_USER" "$SOURCE_SSH_KEY" \
        "systemctl status $SERVICE_NAME --no-pager" > "$TEMP_DIR/source_service_status.txt" || true

    log_info "Получение конфигурации сервиса..."
    run_remote_command "$SOURCE_HOST" "$SOURCE_USER" "$SOURCE_SSH_KEY" \
        "cat /etc/systemd/system/$SERVICE_NAME" > "$TEMP_DIR/source_service_config.txt" || true

    # Проверка логов
    log_step "Проверка логов"

    log_info "Получение последних 100 строк лога сервиса..."
    run_remote_command "$SOURCE_HOST" "$SOURCE_USER" "$SOURCE_SSH_KEY" \
        "journalctl -u $SERVICE_NAME -n 100 --no-pager" > "$TEMP_DIR/source_service_logs.txt" || true

    # Проверка переменных окружения
    log_step "Проверка переменных окружения"

    log_info "Проверка наличия .env файлов..."
    run_remote_command "$SOURCE_HOST" "$SOURCE_USER" "$SOURCE_SSH_KEY" \
        "ls -lh $SOURCE_APP_DIR/.env*" > "$TEMP_DIR/source_env_files.txt" || true

    # Проверка сессионных файлов
    log_step "Проверка сессионных файлов"

    log_info "Проверка наличия .session файлов..."
    run_remote_command "$SOURCE_HOST" "$SOURCE_USER" "$SOURCE_SSH_KEY" \
        "find $SOURCE_APP_DIR -name '*.session' -ls" > "$TEMP_DIR/source_session_files.txt" || true

    # Проверка базы данных
    log_step "Проверка базы данных"

    log_info "Проверка наличия базы данных..."
    run_remote_command "$SOURCE_HOST" "$SOURCE_USER" "$SOURCE_SSH_KEY" \
        "ls -lh $SOURCE_APP_DIR/*.db" > "$TEMP_DIR/source_database_files.txt" || true

    # Проверка использования ресурсов
    log_step "Проверка использования ресурсов"

    log_info "Проверка использования памяти..."
    run_remote_command "$SOURCE_HOST" "$SOURCE_USER" "$SOURCE_SSH_KEY" \
        "free -h" > "$TEMP_DIR/source_memory_usage.txt"

    log_info "Проверка использования диска..."
    run_remote_command "$SOURCE_HOST" "$SOURCE_USER" "$SOURCE_SSH_KEY" \
        "df -h" > "$TEMP_DIR/source_disk_usage.txt"

    log_info "Проверка использования CPU..."
    run_remote_command "$SOURCE_HOST" "$SOURCE_USER" "$SOURCE_SSH_KEY" \
        "top -bn1 | head -20" > "$TEMP_DIR/source_cpu_usage.txt"

    # Проверка сетевых подключений
    log_step "Проверка сетевых подключений"

    log_info "Проверка активных подключений..."
    run_remote_command "$SOURCE_HOST" "$SOURCE_USER" "$SOURCE_SSH_KEY" \
        "ss -tuln | grep -E 'LISTEN|ESTAB' | head -20" > "$TEMP_DIR/source_network_connections.txt" || true

    # Создание отчета об аудите
    log_step "Создание отчета об аудите"

    local report_file="$BACKUP_DIR/audit_report_${TIMESTAMP}.md"

    cat > "$report_file" << EOF
# Отчет об аудите исходного сервера

**Дата:** $(date '+%Y-%m-%d %H:%M:%S')
**Сервер:** $SOURCE_HOST ($SOURCE_ALIAS)

## Информация о системе

### ОС
\`\`\`
$(cat "$TEMP_DIR/source_os_info.txt")
\`\`\`

### Ядро
\`\`\`
$(cat "$TEMP_DIR/source_kernel_info.txt")
\`\`\`

## Python окружение

### Версия Python
\`\`\`
$(cat "$TEMP_DIR/source_python_version.txt")
\`\`\`

### Версия pip
\`\`\`
$(cat "$TEMP_DIR/source_pip_version.txt")
\`\`\`

## Структура приложения

### Список файлов
\`\`\`
$(cat "$TEMP_DIR/source_app_structure.txt")
\`\`\`

### Размер директории
\`\`\`
$(cat "$TEMP_DIR/source_app_size.txt")
\`\`\`

## Systemd сервис

### Статус
\`\`\`
$(cat "$TEMP_DIR/source_service_status.txt" 2>/dev/null || echo "Не удалось получить статус")
\`\`\`

### Конфигурация
\`\`\`
$(cat "$TEMP_DIR/source_service_config.txt" 2>/dev/null || echo "Не удалось получить конфигурацию")
\`\`\`

## Использование ресурсов

### Память
\`\`\`
$(cat "$TEMP_DIR/source_memory_usage.txt")
\`\`\`

### Диск
\`\`\`
$(cat "$TEMP_DIR/source_disk_usage.txt")
\`\`\`

## Критичные файлы

### .env файлы
\`\`\`
$(cat "$TEMP_DIR/source_env_files.txt" 2>/dev/null || echo "Не найдены")
\`\`\`

### .session файлы
\`\`\`
$(cat "$TEMP_DIR/source_session_files.txt" 2>/dev/null || echo "Не найдены")
\`\`\`

### База данных
\`\`\`
$(cat "$TEMP_DIR/source_database_files.txt" 2>/dev/null || echo "Не найдена")
\`\`\`

---
*Отчет создан автоматически скриптом аудита*
EOF

    log_success "Отчет об аудите создан: $report_file"

    # Копирование requirements_frozen.txt для использования на целевом сервере
    cp "$TEMP_DIR/requirements_frozen.txt" "$BACKUP_DIR/requirements_frozen_${TIMESTAMP}.txt"
    log_success "Зависимости сохранены: $BACKUP_DIR/requirements_frozen_${TIMESTAMP}.txt"

    log_step "АУДИТ ЗАВЕРШЕН"
    log_success "Все проверки выполнены успешно"
    log_info "Результаты аудита сохранены в: $BACKUP_DIR"

    echo -e "\n${GREEN}════════════════════════════════════════════════════════${NC}"
    echo -e "${GREEN}Аудит исходного сервера завершен успешно!${NC}"
    echo -e "${GREEN}════════════════════════════════════════════════════════${NC}"
    echo -e "\nСледующий шаг: Запустите ${BLUE}./02_prepare_target.sh${NC}"
}

# Запуск скрипта
main "$@"
