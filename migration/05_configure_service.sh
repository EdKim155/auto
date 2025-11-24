#!/bin/bash

###############################################################################
# Скрипт настройки systemd-сервиса
# Создает и настраивает systemd-сервис для автоматического запуска
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
    log_step "НАСТРОЙКА SYSTEMD-СЕРВИСА"

    init_migration

    # Проверка подключения к целевому серверу
    log_info "Проверка подключения к целевому серверу..."
    check_ssh_connection "$TARGET_HOST" "$TARGET_USER" "" "$TARGET_ALIAS" || exit 1

    # Проверка наличия main.py
    log_step "Проверка основного файла приложения"

    log_info "Проверка наличия main.py..."
    local main_exists=$(ssh "$TARGET_USER@$TARGET_HOST" \
        "[ -f $TARGET_APP_DIR/main.py ] && echo 'yes' || echo 'no'")

    if [ "$main_exists" = "no" ]; then
        log_error "Файл main.py не найден в $TARGET_APP_DIR"
        exit 1
    fi

    log_success "Файл main.py найден"

    # Остановка существующего сервиса (если запущен)
    log_step "Проверка существующего сервиса"

    log_info "Проверка статуса сервиса..."
    if run_remote_command "$TARGET_HOST" "$TARGET_USER" "" \
        "systemctl is-active --quiet $SERVICE_NAME" 2>/dev/null; then
        log_warn "Сервис $SERVICE_NAME уже запущен"
        log_info "Остановка сервиса..."
        run_remote_command "$TARGET_HOST" "$TARGET_USER" "" \
            "systemctl stop $SERVICE_NAME"
        log_success "Сервис остановлен"
    else
        log_info "Сервис не запущен"
    fi

    # Создание конфигурации systemd-сервиса
    log_step "Создание конфигурации systemd-сервиса"

    log_info "Создание файла конфигурации сервиса..."

    # Создание временного файла с конфигурацией
    local temp_service_file="$TEMP_DIR/$SERVICE_NAME"

    cat > "$temp_service_file" << EOF
[Unit]
Description=Telegram Bot Automation
After=network.target network-online.target
Wants=network-online.target

[Service]
Type=simple
User=root
WorkingDirectory=$TARGET_APP_DIR
ExecStart=$TARGET_APP_DIR/$VENV_NAME/bin/python3 $TARGET_APP_DIR/main.py
Restart=always
RestartSec=10
StandardOutput=append:/var/log/telegram-bot.log
StandardError=append:/var/log/telegram-bot.log

# Безопасность
NoNewPrivileges=true
PrivateTmp=true

# Переменные окружения
Environment="PYTHONUNBUFFERED=1"
Environment="PATH=$TARGET_APP_DIR/$VENV_NAME/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin"

# Ограничения ресурсов
LimitNOFILE=65535
TimeoutStartSec=30
TimeoutStopSec=30

[Install]
WantedBy=multi-user.target
EOF

    log_success "Конфигурация создана локально"

    # Копирование конфигурации на целевой сервер
    log_info "Копирование конфигурации на целевой сервер..."
    scp "$temp_service_file" \
        "$TARGET_USER@$TARGET_HOST:/tmp/$SERVICE_NAME"

    # Перемещение конфигурации в /etc/systemd/system/
    log_info "Установка конфигурации сервиса..."
    run_remote_command "$TARGET_HOST" "$TARGET_USER" "" \
        "mv /tmp/$SERVICE_NAME /etc/systemd/system/$SERVICE_NAME && \
        chmod 644 /etc/systemd/system/$SERVICE_NAME"

    log_success "Конфигурация установлена"

    # Создание файла лога
    log_step "Создание файла лога"

    log_info "Создание файла лога..."
    run_remote_command "$TARGET_HOST" "$TARGET_USER" "" \
        "touch /var/log/telegram-bot.log && \
        chown root:root /var/log/telegram-bot.log && \
        chmod 644 /var/log/telegram-bot.log"

    log_success "Файл лога создан"

    # Перезагрузка systemd
    log_step "Перезагрузка systemd"

    log_info "Перезагрузка конфигурации systemd..."
    run_remote_command "$TARGET_HOST" "$TARGET_USER" "" \
        "systemctl daemon-reload"

    log_success "Конфигурация systemd перезагружена"

    # Включение автозапуска
    log_step "Включение автозапуска"

    log_info "Включение автозапуска сервиса..."
    run_remote_command "$TARGET_HOST" "$TARGET_USER" "" \
        "systemctl enable $SERVICE_NAME"

    log_success "Автозапуск включен"

    # Проверка конфигурации сервиса
    log_step "Проверка конфигурации сервиса"

    log_info "Проверка синтаксиса конфигурации..."
    run_remote_command "$TARGET_HOST" "$TARGET_USER" "" \
        "systemd-analyze verify /etc/systemd/system/$SERVICE_NAME" || {
        log_warn "Обнаружены предупреждения в конфигурации (возможно несущественные)"
    }

    # Сохранение конфигурации локально
    log_info "Сохранение конфигурации локально..."
    cp "$temp_service_file" "$BACKUP_DIR/${SERVICE_NAME}_${TIMESTAMP}"
    log_success "Конфигурация сохранена: $BACKUP_DIR/${SERVICE_NAME}_${TIMESTAMP}"

    # Создание отчета о настройке сервиса
    log_step "Создание отчета о настройке сервиса"

    local report_file="$BACKUP_DIR/service_report_${TIMESTAMP}.md"

    cat > "$report_file" << EOF
# Отчет о настройке systemd-сервиса

**Дата:** $(date '+%Y-%m-%d %H:%M:%S')
**Сервер:** $TARGET_HOST ($TARGET_ALIAS)

## Конфигурация сервиса

### Имя сервиса
\`$SERVICE_NAME\`

### Расположение конфигурации
\`/etc/systemd/system/$SERVICE_NAME\`

### Содержимое конфигурации

\`\`\`ini
$(cat "$temp_service_file")
\`\`\`

## Параметры

- **Тип:** simple
- **Пользователь:** root
- **Рабочая директория:** $TARGET_APP_DIR
- **Команда запуска:** $TARGET_APP_DIR/$VENV_NAME/bin/python3 $TARGET_APP_DIR/main.py
- **Перезапуск:** always (каждые 10 секунд)
- **Логи:** /var/log/telegram-bot.log

## Статус

✅ Конфигурация создана
✅ systemd перезагружен
✅ Автозапуск включен
⏸️  Сервис не запущен (требуется ручной запуск после проверки)

## Управление сервисом

### Запуск
\`\`\`bash
systemctl start $SERVICE_NAME
\`\`\`

### Остановка
\`\`\`bash
systemctl stop $SERVICE_NAME
\`\`\`

### Перезапуск
\`\`\`bash
systemctl restart $SERVICE_NAME
\`\`\`

### Статус
\`\`\`bash
systemctl status $SERVICE_NAME
\`\`\`

### Просмотр логов
\`\`\`bash
journalctl -u $SERVICE_NAME -f
\`\`\`

или

\`\`\`bash
tail -f /var/log/telegram-bot.log
\`\`\`

---
*Отчет создан автоматически скриптом настройки сервиса*
EOF

    log_success "Отчет о настройке сервиса создан: $report_file"

    log_step "НАСТРОЙКА СЕРВИСА ЗАВЕРШЕНА"
    log_success "Systemd-сервис настроен и готов к запуску"

    echo -e "\n${GREEN}════════════════════════════════════════════════════════${NC}"
    echo -e "${GREEN}Systemd-сервис успешно настроен!${NC}"
    echo -e "${GREEN}════════════════════════════════════════════════════════${NC}"
    echo -e "\n${YELLOW}ВАЖНО:${NC} Сервис создан, но не запущен."
    echo -e "Сначала выполните валидацию: ${BLUE}./06_validate_migration.sh${NC}"
    echo -e "\nПосле успешной валидации запустите сервис командой:"
    echo -e "${BLUE}ssh $TARGET_ALIAS 'systemctl start $SERVICE_NAME'${NC}"
}

# Запуск скрипта
main "$@"
