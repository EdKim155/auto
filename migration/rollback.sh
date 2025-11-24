#!/bin/bash

###############################################################################
# Скрипт отката миграции
# Восстанавливает работу на исходном сервере в случае проблем
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
    log_step "ОТКАТ МИГРАЦИИ"

    log_warn "═══════════════════════════════════════════════════════════════"
    log_warn "ВНИМАНИЕ! Вы запускаете процедуру отката миграции"
    log_warn "Это остановит сервис на новом сервере и запустит на старом"
    log_warn "═══════════════════════════════════════════════════════════════"

    # Запрос подтверждения
    read -p "Вы уверены, что хотите выполнить откат? (yes/no): " confirmation

    if [ "$confirmation" != "yes" ]; then
        log_info "Откат отменен пользователем"
        exit 0
    fi

    init_migration

    # Шаг 1: Остановка сервиса на целевом сервере
    log_step "Шаг 1: Остановка сервиса на целевом сервере"

    log_info "Проверка подключения к целевому серверу..."
    if check_ssh_connection "$TARGET_HOST" "$TARGET_USER" "" "$TARGET_ALIAS"; then
        log_info "Остановка сервиса на целевом сервере..."

        if run_remote_command "$TARGET_HOST" "$TARGET_USER" "" \
            "systemctl is-active --quiet $SERVICE_NAME" 2>/dev/null; then
            run_remote_command "$TARGET_HOST" "$TARGET_USER" "" \
                "systemctl stop $SERVICE_NAME"
            log_success "Сервис остановлен на целевом сервере"
        else
            log_info "Сервис уже остановлен на целевом сервере"
        fi

        log_info "Отключение автозапуска на целевом сервере..."
        run_remote_command "$TARGET_HOST" "$TARGET_USER" "" \
            "systemctl disable $SERVICE_NAME" || true
        log_success "Автозапуск отключен"
    else
        log_error "Не удалось подключиться к целевому серверу"
        log_warn "Продолжение без остановки сервиса на целевом сервере..."
    fi

    # Шаг 2: Проверка исходного сервера
    log_step "Шаг 2: Проверка исходного сервера"

    log_info "Проверка подключения к исходному серверу..."
    check_ssh_connection "$SOURCE_HOST" "$SOURCE_USER" "$SOURCE_SSH_KEY" "$SOURCE_ALIAS" || {
        log_error "Не удалось подключиться к исходному серверу!"
        exit 1
    }

    log_success "Подключение к исходному серверу установлено"

    # Шаг 3: Проверка наличия файлов на исходном сервере
    log_step "Шаг 3: Проверка наличия файлов на исходном сервере"

    log_info "Проверка директории приложения..."
    if run_remote_command "$SOURCE_HOST" "$SOURCE_USER" "$SOURCE_SSH_KEY" \
        "[ -d $SOURCE_APP_DIR ]"; then
        log_success "Директория приложения найдена"
    else
        log_error "Директория приложения не найдена на исходном сервере!"
        exit 1
    fi

    log_info "Проверка основных файлов..."
    if run_remote_command "$SOURCE_HOST" "$SOURCE_USER" "$SOURCE_SSH_KEY" \
        "[ -f $SOURCE_APP_DIR/main.py ]"; then
        log_success "Основные файлы найдены"
    else
        log_error "Файл main.py не найден на исходном сервере!"
        exit 1
    fi

    # Шаг 4: Проверка конфигурации сервиса на исходном сервере
    log_step "Шаг 4: Проверка конфигурации сервиса"

    log_info "Проверка конфигурации systemd-сервиса..."
    if run_remote_command "$SOURCE_HOST" "$SOURCE_USER" "$SOURCE_SSH_KEY" \
        "[ -f /etc/systemd/system/$SERVICE_NAME ]"; then
        log_success "Конфигурация сервиса найдена"
    else
        log_warn "Конфигурация сервиса не найдена"
        log_info "Восстановление конфигурации из резервной копии..."

        # Поиск последней резервной копии конфигурации
        local service_backup=$(ls -t "$BACKUP_DIR"/${SERVICE_NAME}_* 2>/dev/null | head -1)

        if [ -n "$service_backup" ]; then
            log_info "Найдена резервная копия: $service_backup"
            scp "$service_backup" "$SOURCE_USER@$SOURCE_HOST:/tmp/$SERVICE_NAME"
            run_remote_command "$SOURCE_HOST" "$SOURCE_USER" "$SOURCE_SSH_KEY" \
                "mv /tmp/$SERVICE_NAME /etc/systemd/system/$SERVICE_NAME && \
                chmod 644 /etc/systemd/system/$SERVICE_NAME && \
                systemctl daemon-reload"
            log_success "Конфигурация восстановлена"
        else
            log_error "Резервная копия конфигурации не найдена!"
            log_info "Создание новой конфигурации..."

            # Создание конфигурации
            run_remote_command "$SOURCE_HOST" "$SOURCE_USER" "$SOURCE_SSH_KEY" \
                "cat > /etc/systemd/system/$SERVICE_NAME << 'EOF'
[Unit]
Description=Telegram Bot Automation
After=network.target

[Service]
Type=simple
User=root
WorkingDirectory=$SOURCE_APP_DIR
ExecStart=$SOURCE_APP_DIR/venv/bin/python3 $SOURCE_APP_DIR/main.py
Restart=always
RestartSec=10
StandardOutput=append:/var/log/telegram-bot.log
StandardError=append:/var/log/telegram-bot.log

[Install]
WantedBy=multi-user.target
EOF"

            run_remote_command "$SOURCE_HOST" "$SOURCE_USER" "$SOURCE_SSH_KEY" \
                "systemctl daemon-reload"
            log_success "Новая конфигурация создана"
        fi
    fi

    # Шаг 5: Включение автозапуска на исходном сервере
    log_step "Шаг 5: Включение автозапуска"

    log_info "Включение автозапуска сервиса..."
    run_remote_command "$SOURCE_HOST" "$SOURCE_USER" "$SOURCE_SSH_KEY" \
        "systemctl enable $SERVICE_NAME"
    log_success "Автозапуск включен"

    # Шаг 6: Запуск сервиса на исходном сервере
    log_step "Шаг 6: Запуск сервиса на исходном сервере"

    log_info "Запуск сервиса..."
    run_remote_command "$SOURCE_HOST" "$SOURCE_USER" "$SOURCE_SSH_KEY" \
        "systemctl start $SERVICE_NAME"

    # Ожидание запуска
    log_info "Ожидание запуска сервиса (10 секунд)..."
    sleep 10

    # Проверка статуса
    log_info "Проверка статуса сервиса..."
    if run_remote_command "$SOURCE_HOST" "$SOURCE_USER" "$SOURCE_SSH_KEY" \
        "systemctl is-active --quiet $SERVICE_NAME"; then
        log_success "Сервис успешно запущен на исходном сервере!"
    else
        log_error "Сервис не запустился!"
        log_info "Проверка логов..."
        run_remote_command "$SOURCE_HOST" "$SOURCE_USER" "$SOURCE_SSH_KEY" \
            "journalctl -u $SERVICE_NAME -n 50 --no-pager" | tee "$LOG_DIR/rollback_error_${TIMESTAMP}.log"
        exit 1
    fi

    # Шаг 7: Проверка работы
    log_step "Шаг 7: Финальная проверка"

    log_info "Получение статуса сервиса..."
    run_remote_command "$SOURCE_HOST" "$SOURCE_USER" "$SOURCE_SSH_KEY" \
        "systemctl status $SERVICE_NAME --no-pager" | tee "$TEMP_DIR/rollback_status.txt"

    log_info "Получение последних логов..."
    run_remote_command "$SOURCE_HOST" "$SOURCE_USER" "$SOURCE_SSH_KEY" \
        "journalctl -u $SERVICE_NAME -n 20 --no-pager" | tee "$TEMP_DIR/rollback_logs.txt"

    # Создание отчета об откате
    log_step "Создание отчета об откате"

    local report_file="$BACKUP_DIR/rollback_report_${TIMESTAMP}.md"

    cat > "$report_file" << EOF
# Отчет об откате миграции

**Дата:** $(date '+%Y-%m-%d %H:%M:%S')
**Причина:** Откат на исходный сервер
**Исполнитель:** $(whoami)

## Выполненные действия

1. ✅ Остановка сервиса на целевом сервере ($TARGET_HOST)
2. ✅ Отключение автозапуска на целевом сервере
3. ✅ Проверка исходного сервера ($SOURCE_HOST)
4. ✅ Проверка файлов приложения
5. ✅ Восстановление конфигурации сервиса (если требовалось)
6. ✅ Включение автозапуска на исходном сервере
7. ✅ Запуск сервиса на исходном сервере

## Текущий статус

### Исходный сервер: $SOURCE_HOST
\`\`\`
$(cat "$TEMP_DIR/rollback_status.txt")
\`\`\`

### Последние логи
\`\`\`
$(cat "$TEMP_DIR/rollback_logs.txt")
\`\`\`

## Рекомендации

- Сервис работает на исходном сервере
- Проанализируйте причины проблем на целевом сервере
- После устранения проблем можно повторить миграцию

## Следующие шаги

1. Проверьте работу бота в Telegram
2. Мониторьте логи: \`ssh $SOURCE_ALIAS 'journalctl -u $SERVICE_NAME -f'\`
3. Проанализируйте причину отката
4. Подготовьтесь к повторной миграции

---
*Отчет создан автоматически скриптом отката*
EOF

    log_success "Отчет об откате создан: $report_file"

    # Итоги
    log_step "ОТКАТ ЗАВЕРШЕН"
    log_success "Сервис восстановлен на исходном сервере"

    echo -e "\n${GREEN}════════════════════════════════════════════════════════${NC}"
    echo -e "${GREEN}✅ ОТКАТ ВЫПОЛНЕН УСПЕШНО!${NC}"
    echo -e "${GREEN}════════════════════════════════════════════════════════${NC}"
    echo -e "\n${GREEN}Статус:${NC}"
    echo -e "  • Исходный сервер ($SOURCE_HOST): ${GREEN}РАБОТАЕТ${NC}"
    echo -e "  • Целевой сервер ($TARGET_HOST): ${YELLOW}ОСТАНОВЛЕН${NC}"
    echo -e "\n${GREEN}Следующие шаги:${NC}"
    echo -e "  1. Проверьте работу: ${BLUE}ssh $SOURCE_ALIAS 'systemctl status $SERVICE_NAME'${NC}"
    echo -e "  2. Мониторьте логи: ${BLUE}ssh $SOURCE_ALIAS 'journalctl -u $SERVICE_NAME -f'${NC}"
    echo -e "  3. Проанализируйте проблемы и подготовьтесь к повторной миграции"
    echo -e "\nОтчет: ${BLUE}$report_file${NC}"
}

# Запуск скрипта
main "$@"
