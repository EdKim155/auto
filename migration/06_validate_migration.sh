#!/bin/bash

###############################################################################
# Скрипт валидации миграции
# Проверяет корректность миграции и готовность к запуску
###############################################################################

set -euo pipefail

# Загрузка конфигурации и утилит
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$SCRIPT_DIR/config.sh"
source "$SCRIPT_DIR/utils.sh"

###############################################################################
# Функции проверки
###############################################################################

check_file_exists() {
    local file="$1"
    local description="$2"

    if ssh "$TARGET_USER@$TARGET_HOST" "[ -f $file ]" 2>/dev/null; then
        log_success "✓ $description: $file"
        return 0
    else
        log_error "✗ $description не найден: $file"
        return 1
    fi
}

check_directory_exists() {
    local dir="$1"
    local description="$2"

    if ssh "$TARGET_USER@$TARGET_HOST" "[ -d $dir ]" 2>/dev/null; then
        log_success "✓ $description: $dir"
        return 0
    else
        log_error "✗ $description не найдена: $dir"
        return 1
    fi
}

###############################################################################
# Главная функция
###############################################################################

main() {
    log_step "ВАЛИДАЦИЯ МИГРАЦИИ"

    init_migration

    local errors=0

    # Проверка подключения к целевому серверу
    log_info "Проверка подключения к целевому серверу..."
    check_ssh_connection "$TARGET_HOST" "$TARGET_USER" "" "$TARGET_ALIAS" || {
        log_error "Не удалось подключиться к целевому серверу"
        exit 1
    }

    # Проверка структуры директорий
    log_step "Проверка структуры директорий"

    check_directory_exists "$TARGET_APP_DIR" "Директория приложения" || ((errors++))
    check_directory_exists "$TARGET_APP_DIR/$VENV_NAME" "Виртуальное окружение" || ((errors++))
    check_directory_exists "$TARGET_APP_DIR/modules" "Директория modules" || ((errors++))

    # Проверка основных файлов приложения
    log_step "Проверка основных файлов приложения"

    check_file_exists "$TARGET_APP_DIR/main.py" "Главный файл main.py" || ((errors++))
    check_file_exists "$TARGET_APP_DIR/bot_automation.py" "Файл bot_automation.py" || ((errors++))
    check_file_exists "$TARGET_APP_DIR/config.py" "Файл config.py" || ((errors++))
    check_file_exists "$TARGET_APP_DIR/requirements.txt" "Файл requirements.txt" || ((errors++))

    # Проверка конфигурационных файлов
    log_step "Проверка конфигурационных файлов"

    check_file_exists "$TARGET_APP_DIR/.env" "Файл .env" || ((errors++))

    # Проверка прав доступа на .env файлы
    log_info "Проверка прав доступа на .env файлы..."
    local env_perms=$(ssh "$TARGET_USER@$TARGET_HOST" \
        "stat -c '%a' $TARGET_APP_DIR/.env" 2>/dev/null || echo "000")

    if [ "$env_perms" = "600" ]; then
        log_success "✓ Права доступа .env корректны (600)"
    else
        log_warn "✗ Права доступа .env некорректны ($env_perms, ожидается 600)"
        ((errors++))
    fi

    # Проверка сессионных файлов
    log_step "Проверка сессионных файлов"

    local session_count=$(ssh "$TARGET_USER@$TARGET_HOST" \
        "find $TARGET_APP_DIR -name '*.session' | wc -l" 2>/dev/null || echo "0")

    if [ "$session_count" -gt 0 ]; then
        log_success "✓ Найдено $session_count сессионных файлов"

        # Проверка прав доступа
        local bad_perms=$(ssh "$TARGET_USER@$TARGET_HOST" \
            "find $TARGET_APP_DIR -name '*.session' -type f ! -perm 600 | wc -l" 2>/dev/null || echo "0")

        if [ "$bad_perms" -eq 0 ]; then
            log_success "✓ Права доступа на .session файлы корректны"
        else
            log_warn "✗ $bad_perms файлов с некорректными правами доступа"
            ((errors++))
        fi
    else
        log_warn "✗ Сессионные файлы не найдены (может потребоваться авторизация)"
    fi

    # Проверка базы данных
    log_step "Проверка базы данных"

    local db_count=$(ssh "$TARGET_USER@$TARGET_HOST" \
        "find $TARGET_APP_DIR -name '*.db' | wc -l" 2>/dev/null || echo "0")

    if [ "$db_count" -gt 0 ]; then
        log_success "✓ Найдено $db_count файлов базы данных"
    else
        log_warn "⚠ Файлы базы данных не найдены"
    fi

    # Проверка Python и виртуального окружения
    log_step "Проверка Python и виртуального окружения"

    log_info "Проверка активации виртуального окружения..."
    if run_remote_command "$TARGET_HOST" "$TARGET_USER" "" \
        "cd $TARGET_APP_DIR && source $VENV_NAME/bin/activate && which python" >/dev/null; then
        log_success "✓ Виртуальное окружение активируется"
    else
        log_error "✗ Ошибка активации виртуального окружения"
        ((errors++))
    fi

    # Проверка импорта модулей
    log_step "Проверка импорта критичных модулей"

    log_info "Проверка импорта telethon..."
    if run_remote_command "$TARGET_HOST" "$TARGET_USER" "" \
        "cd $TARGET_APP_DIR && source $VENV_NAME/bin/activate && python -c 'import telethon'" 2>/dev/null; then
        log_success "✓ Модуль telethon импортируется"
    else
        log_error "✗ Ошибка импорта модуля telethon"
        ((errors++))
    fi

    log_info "Проверка импорта dotenv..."
    if run_remote_command "$TARGET_HOST" "$TARGET_USER" "" \
        "cd $TARGET_APP_DIR && source $VENV_NAME/bin/activate && python -c 'import dotenv'" 2>/dev/null; then
        log_success "✓ Модуль dotenv импортируется"
    else
        log_error "✗ Ошибка импорта модуля dotenv"
        ((errors++))
    fi

    log_info "Проверка импорта asyncio..."
    if run_remote_command "$TARGET_HOST" "$TARGET_USER" "" \
        "cd $TARGET_APP_DIR && source $VENV_NAME/bin/activate && python -c 'import asyncio'" 2>/dev/null; then
        log_success "✓ Модуль asyncio импортируется"
    else
        log_error "✗ Ошибка импорта модуля asyncio"
        ((errors++))
    fi

    # Проверка синтаксиса основных файлов
    log_step "Проверка синтаксиса Python файлов"

    log_info "Проверка синтаксиса main.py..."
    if run_remote_command "$TARGET_HOST" "$TARGET_USER" "" \
        "cd $TARGET_APP_DIR && source $VENV_NAME/bin/activate && python -m py_compile main.py" 2>/dev/null; then
        log_success "✓ Синтаксис main.py корректен"
    else
        log_error "✗ Ошибка синтаксиса в main.py"
        ((errors++))
    fi

    # Проверка systemd-сервиса
    log_step "Проверка systemd-сервиса"

    check_file_exists "/etc/systemd/system/$SERVICE_NAME" "Файл systemd-сервиса" || ((errors++))

    log_info "Проверка статуса сервиса..."
    if run_remote_command "$TARGET_HOST" "$TARGET_USER" "" \
        "systemctl is-enabled $SERVICE_NAME" 2>/dev/null; then
        log_success "✓ Сервис включен в автозапуск"
    else
        log_warn "✗ Сервис не включен в автозапуск"
        ((errors++))
    fi

    # Проверка файла лога
    log_step "Проверка логирования"

    check_file_exists "/var/log/telegram-bot.log" "Файл лога" || {
        log_warn "Файл лога не существует, будет создан при запуске"
    }

    # Проверка доступности Telegram API
    log_step "Проверка сетевого подключения"

    log_info "Проверка доступности Telegram API..."
    if run_remote_command "$TARGET_HOST" "$TARGET_USER" "" \
        "curl -s -o /dev/null -w '%{http_code}' https://api.telegram.org --max-time 10" 2>/dev/null | grep -q "200\|404"; then
        log_success "✓ Telegram API доступен"
    else
        log_error "✗ Telegram API недоступен"
        ((errors++))
    fi

    # Проверка свободного места
    log_step "Проверка ресурсов"

    log_info "Проверка свободного места..."
    local free_space=$(ssh "$TARGET_USER@$TARGET_HOST" \
        "df -h $TARGET_APP_DIR | tail -1 | awk '{print \$4}'")
    log_info "Свободное место: $free_space"

    log_info "Проверка свободной памяти..."
    local free_memory=$(ssh "$TARGET_USER@$TARGET_HOST" \
        "free -h | grep Mem | awk '{print \$7}'")
    log_info "Доступная память: $free_memory"

    # Тестовый запуск (dry-run)
    log_step "Тестовый запуск приложения"

    log_info "Попытка запуска приложения в тестовом режиме (10 секунд)..."
    log_warn "Это запустит приложение на 10 секунд для проверки..."

    if ssh "$TARGET_USER@$TARGET_HOST" \
        "cd $TARGET_APP_DIR && source $VENV_NAME/bin/activate && timeout 10 python main.py" 2>&1 | tee "$TEMP_DIR/test_run.log"; then
        log_info "Тестовый запуск завершен (проверьте логи)"
    else
        local exit_code=$?
        if [ $exit_code -eq 124 ]; then
            log_success "✓ Приложение запустилось и работало 10 секунд (завершено по timeout)"
        else
            log_error "✗ Ошибка при запуске приложения (код: $exit_code)"
            log_error "Проверьте логи в $TEMP_DIR/test_run.log"
            ((errors++))
        fi
    fi

    # Создание отчета о валидации
    log_step "Создание отчета о валидации"

    local report_file="$BACKUP_DIR/validation_report_${TIMESTAMP}.md"
    local status="PASSED"
    [ $errors -gt 0 ] && status="FAILED"

    cat > "$report_file" << EOF
# Отчет о валидации миграции

**Дата:** $(date '+%Y-%m-%d %H:%M:%S')
**Сервер:** $TARGET_HOST ($TARGET_ALIAS)
**Статус:** $status
**Обнаружено ошибок:** $errors

## Результаты проверок

### Структура директорий
- Директория приложения: $TARGET_APP_DIR
- Виртуальное окружение: $TARGET_APP_DIR/$VENV_NAME
- Модули: $TARGET_APP_DIR/modules

### Файлы
- main.py
- bot_automation.py
- config.py
- requirements.txt
- .env файлы
- .session файлы ($session_count шт.)
- .db файлы ($db_count шт.)

### Python окружение
- Виртуальное окружение активируется
- Критичные модули импортируются
- Синтаксис файлов корректен

### Systemd сервис
- Конфигурация: /etc/systemd/system/$SERVICE_NAME
- Автозапуск: включен

### Ресурсы
- Свободное место: $free_space
- Доступная память: $free_memory

### Сеть
- Telegram API: доступен

## Тестовый запуск

\`\`\`
$(cat "$TEMP_DIR/test_run.log" 2>/dev/null || echo "Логи недоступны")
\`\`\`

## Рекомендации

$(if [ $errors -eq 0 ]; then
    echo "✅ Все проверки пройдены успешно!"
    echo "✅ Миграция готова к финальному запуску"
    echo ""
    echo "Для запуска сервиса выполните:"
    echo "\`\`\`bash"
    echo "ssh $TARGET_ALIAS 'systemctl start $SERVICE_NAME'"
    echo "\`\`\`"
else
    echo "⚠️  Обнаружено $errors ошибок"
    echo "⚠️  Необходимо исправить ошибки перед запуском"
    echo ""
    echo "Проверьте детали в логах миграции"
fi)

---
*Отчет создан автоматически скриптом валидации*
EOF

    log_success "Отчет о валидации создан: $report_file"

    # Вывод итогов
    log_step "ИТОГИ ВАЛИДАЦИИ"

    if [ $errors -eq 0 ]; then
        log_success "Все проверки пройдены успешно!"
        log_success "Миграция готова к финальному запуску"

        echo -e "\n${GREEN}════════════════════════════════════════════════════════${NC}"
        echo -e "${GREEN}✅ ВАЛИДАЦИЯ ПРОЙДЕНА УСПЕШНО!${NC}"
        echo -e "${GREEN}════════════════════════════════════════════════════════${NC}"
        echo -e "\n${GREEN}Следующие шаги:${NC}"
        echo -e "1. Настройте мониторинг: ${BLUE}./07_setup_monitoring.sh${NC}"
        echo -e "2. Запустите сервис: ${BLUE}ssh $TARGET_ALIAS 'systemctl start $SERVICE_NAME'${NC}"
        echo -e "3. Проверьте логи: ${BLUE}ssh $TARGET_ALIAS 'journalctl -u $SERVICE_NAME -f'${NC}"

        return 0
    else
        log_error "Обнаружено ошибок: $errors"
        log_error "Исправьте ошибки перед запуском сервиса"

        echo -e "\n${RED}════════════════════════════════════════════════════════${NC}"
        echo -e "${RED}✗ ВАЛИДАЦИЯ НЕ ПРОЙДЕНА${NC}"
        echo -e "${RED}════════════════════════════════════════════════════════${NC}"
        echo -e "\n${YELLOW}Обнаружено ошибок: $errors${NC}"
        echo -e "Проверьте отчет: ${BLUE}$report_file${NC}"

        return 1
    fi
}

# Запуск скрипта
main "$@"
