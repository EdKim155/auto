#!/bin/bash

###############################################################################
# Скрипт резервного копирования и переноса данных
# Создает резервную копию, переносит файлы и проверяет целостность
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
    log_step "РЕЗЕРВНОЕ КОПИРОВАНИЕ И ПЕРЕНОС ДАННЫХ"

    init_migration

    # Проверка подключения к обоим серверам
    log_info "Проверка подключения к серверам..."
    check_ssh_connection "$SOURCE_HOST" "$SOURCE_USER" "$SOURCE_SSH_KEY" "$SOURCE_ALIAS" || exit 1
    check_ssh_connection "$TARGET_HOST" "$TARGET_USER" "" "$TARGET_ALIAS" || exit 1

    # Создание резервной копии на исходном сервере
    log_step "Создание резервной копии на исходном сервере"

    log_info "Создание архива приложения..."

    # Формирование списка исключений для tar
    local exclude_args=""
    for pattern in "${EXCLUDE_PATTERNS[@]}"; do
        exclude_args="$exclude_args --exclude='$pattern'"
    done

    # Создание архива на исходном сервере
    run_remote_command "$SOURCE_HOST" "$SOURCE_USER" "$SOURCE_SSH_KEY" \
        "cd $(dirname $SOURCE_APP_DIR) && \
        tar -czf /tmp/$BACKUP_NAME \
        $exclude_args \
        $(basename $SOURCE_APP_DIR)/"

    log_success "Архив создан: /tmp/$BACKUP_NAME"

    # Проверка размера архива
    log_info "Проверка размера архива..."
    local archive_size=$(ssh -i "$SOURCE_SSH_KEY" "$SOURCE_USER@$SOURCE_HOST" \
        "ls -lh /tmp/$BACKUP_NAME | awk '{print \$5}'")
    log_info "Размер архива: $archive_size"

    # Создание контрольной суммы на исходном сервере
    log_info "Создание контрольной суммы..."
    run_remote_command "$SOURCE_HOST" "$SOURCE_USER" "$SOURCE_SSH_KEY" \
        "cd /tmp && shasum -a 256 $BACKUP_NAME > ${BACKUP_NAME}.sha256"

    log_success "Контрольная сумма создана"

    # Копирование архива на локальную машину (для безопасности)
    log_step "Копирование архива на локальную машину"

    log_info "Скачивание архива..."
    scp -i "$SOURCE_SSH_KEY" \
        "$SOURCE_USER@$SOURCE_HOST:/tmp/$BACKUP_NAME" \
        "$BACKUP_DIR/" | tee -a "$LOG_FILE"

    log_info "Скачивание контрольной суммы..."
    scp -i "$SOURCE_SSH_KEY" \
        "$SOURCE_USER@$SOURCE_HOST:/tmp/${BACKUP_NAME}.sha256" \
        "$BACKUP_DIR/" | tee -a "$LOG_FILE"

    log_success "Архив скачан в: $BACKUP_DIR/$BACKUP_NAME"

    # Проверка контрольной суммы локально
    log_info "Проверка контрольной суммы на локальной машине..."
    cd "$BACKUP_DIR"
    shasum -a 256 -c "${BACKUP_NAME}.sha256" | tee -a "$LOG_FILE"

    if [ ${PIPESTATUS[0]} -eq 0 ]; then
        log_success "Контрольная сумма совпадает"
    else
        log_error "Ошибка проверки контрольной суммы!"
        exit 1
    fi

    cd "$SCRIPT_DIR"

    # Копирование архива на целевой сервер
    log_step "Копирование архива на целевой сервер"

    log_info "Загрузка архива на целевой сервер..."
    scp "$BACKUP_DIR/$BACKUP_NAME" \
        "$TARGET_USER@$TARGET_HOST:/tmp/" | tee -a "$LOG_FILE"

    log_info "Загрузка контрольной суммы на целевой сервер..."
    scp "$BACKUP_DIR/${BACKUP_NAME}.sha256" \
        "$TARGET_USER@$TARGET_HOST:/tmp/" | tee -a "$LOG_FILE"

    log_success "Файлы загружены на целевой сервер"

    # Проверка контрольной суммы на целевом сервере
    log_info "Проверка контрольной суммы на целевом сервере..."
    run_remote_command "$TARGET_HOST" "$TARGET_USER" "" \
        "cd /tmp && shasum -a 256 -c ${BACKUP_NAME}.sha256"

    if [ $? -eq 0 ]; then
        log_success "Контрольная сумма на целевом сервере совпадает"
    else
        log_error "Ошибка проверки контрольной суммы на целевом сервере!"
        exit 1
    fi

    # Распаковка архива на целевом сервере
    log_step "Распаковка архива на целевом сервере"

    log_info "Распаковка архива..."
    run_remote_command "$TARGET_HOST" "$TARGET_USER" "" \
        "cd $(dirname $TARGET_APP_DIR) && \
        tar -xzf /tmp/$BACKUP_NAME"

    log_success "Архив распакован"

    # Проверка структуры файлов
    log_info "Проверка структуры файлов..."
    run_remote_command "$TARGET_HOST" "$TARGET_USER" "" \
        "ls -lAh $TARGET_APP_DIR" > "$TEMP_DIR/target_transferred_structure.txt"

    # Установка правильных прав доступа
    log_step "Установка прав доступа"

    log_info "Установка прав для .env файлов..."
    run_remote_command "$TARGET_HOST" "$TARGET_USER" "" \
        "find $TARGET_APP_DIR -name '.env*' -type f -exec chmod 600 {} \;"

    log_info "Установка прав для .session файлов..."
    run_remote_command "$TARGET_HOST" "$TARGET_USER" "" \
        "find $TARGET_APP_DIR -name '*.session' -type f -exec chmod 600 {} \;"

    log_info "Установка прав для .db файлов..."
    run_remote_command "$TARGET_HOST" "$TARGET_USER" "" \
        "find $TARGET_APP_DIR -name '*.db' -type f -exec chmod 600 {} \;"

    log_success "Права доступа установлены"

    # Очистка временных файлов
    log_step "Очистка временных файлов"

    log_info "Удаление архива на исходном сервере..."
    run_remote_command "$SOURCE_HOST" "$SOURCE_USER" "$SOURCE_SSH_KEY" \
        "rm -f /tmp/$BACKUP_NAME /tmp/${BACKUP_NAME}.sha256"

    log_info "Удаление архива на целевом сервере..."
    run_remote_command "$TARGET_HOST" "$TARGET_USER" "" \
        "rm -f /tmp/$BACKUP_NAME /tmp/${BACKUP_NAME}.sha256"

    log_success "Временные файлы удалены"

    # Создание дополнительной резервной копии критичных файлов
    log_step "Резервное копирование критичных файлов"

    ensure_directory "$BACKUP_DIR/critical_files_${TIMESTAMP}"

    log_info "Копирование .env файлов..."
    run_remote_command "$TARGET_HOST" "$TARGET_USER" "" \
        "cd $TARGET_APP_DIR && tar -czf /tmp/env_files.tar.gz .env*"

    scp "$TARGET_USER@$TARGET_HOST:/tmp/env_files.tar.gz" \
        "$BACKUP_DIR/critical_files_${TIMESTAMP}/" &>/dev/null

    log_info "Копирование .session файлов..."
    run_remote_command "$TARGET_HOST" "$TARGET_USER" "" \
        "cd $TARGET_APP_DIR && tar -czf /tmp/session_files.tar.gz *.session"

    scp "$TARGET_USER@$TARGET_HOST:/tmp/session_files.tar.gz" \
        "$BACKUP_DIR/critical_files_${TIMESTAMP}/" &>/dev/null

    log_info "Копирование базы данных..."
    run_remote_command "$TARGET_HOST" "$TARGET_USER" "" \
        "cd $TARGET_APP_DIR && tar -czf /tmp/database_files.tar.gz *.db"

    scp "$TARGET_USER@$TARGET_HOST:/tmp/database_files.tar.gz" \
        "$BACKUP_DIR/critical_files_${TIMESTAMP}/" &>/dev/null

    # Очистка временных файлов
    run_remote_command "$TARGET_HOST" "$TARGET_USER" "" \
        "rm -f /tmp/env_files.tar.gz /tmp/session_files.tar.gz /tmp/database_files.tar.gz"

    log_success "Критичные файлы сохранены в: $BACKUP_DIR/critical_files_${TIMESTAMP}/"

    # Создание отчета о переносе
    log_step "Создание отчета о переносе"

    local report_file="$BACKUP_DIR/transfer_report_${TIMESTAMP}.md"

    cat > "$report_file" << EOF
# Отчет о переносе данных

**Дата:** $(date '+%Y-%m-%d %H:%M:%S')
**Исходный сервер:** $SOURCE_HOST
**Целевой сервер:** $TARGET_HOST

## Резервная копия

- **Файл:** $BACKUP_NAME
- **Размер:** $archive_size
- **Расположение (локально):** $BACKUP_DIR/$BACKUP_NAME
- **Контрольная сумма:** $(cat "$BACKUP_DIR/${BACKUP_NAME}.sha256")

## Перенесенные файлы

### Структура на целевом сервере
\`\`\`
$(cat "$TEMP_DIR/target_transferred_structure.txt")
\`\`\`

## Проверка целостности

✅ Контрольная сумма на локальной машине: PASSED
✅ Контрольная сумма на целевом сервере: PASSED
✅ Права доступа установлены: PASSED

## Резервные копии

- Полная резервная копия: $BACKUP_DIR/$BACKUP_NAME
- Критичные файлы: $BACKUP_DIR/critical_files_${TIMESTAMP}/

---
*Отчет создан автоматически скриптом переноса*
EOF

    log_success "Отчет о переносе создан: $report_file"

    log_step "ПЕРЕНОС ДАННЫХ ЗАВЕРШЕН"
    log_success "Все файлы успешно перенесены и проверены"

    echo -e "\n${GREEN}════════════════════════════════════════════════════════${NC}"
    echo -e "${GREEN}Перенос данных завершен успешно!${NC}"
    echo -e "${GREEN}════════════════════════════════════════════════════════${NC}"
    echo -e "\nРезервная копия: ${BLUE}$BACKUP_DIR/$BACKUP_NAME${NC}"
    echo -e "Следующий шаг: Запустите ${BLUE}./04_setup_environment.sh${NC}"
}

# Запуск скрипта
main "$@"
