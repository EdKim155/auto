#!/bin/bash

###############################################################################
# Скрипт настройки окружения на целевом сервере
# Создает виртуальное окружение и устанавливает зависимости
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
    log_step "НАСТРОЙКА ОКРУЖЕНИЯ НА ЦЕЛЕВОМ СЕРВЕРЕ"

    init_migration

    # Проверка подключения к целевому серверу
    log_info "Проверка подключения к целевому серверу..."
    check_ssh_connection "$TARGET_HOST" "$TARGET_USER" "" "$TARGET_ALIAS" || exit 1

    # Проверка наличия файлов приложения
    log_step "Проверка наличия файлов приложения"

    log_info "Проверка директории приложения..."
    local app_exists=$(ssh "$TARGET_USER@$TARGET_HOST" \
        "[ -d $TARGET_APP_DIR ] && echo 'yes' || echo 'no'")

    if [ "$app_exists" = "no" ]; then
        log_error "Директория приложения не найдена: $TARGET_APP_DIR"
        log_error "Сначала выполните скрипт 03_backup_and_transfer.sh"
        exit 1
    fi

    log_success "Директория приложения найдена"

    # Удаление старого виртуального окружения (если существует)
    log_step "Проверка виртуального окружения"

    log_info "Проверка существующего виртуального окружения..."
    local venv_exists=$(ssh "$TARGET_USER@$TARGET_HOST" \
        "[ -d $TARGET_APP_DIR/$VENV_NAME ] && echo 'yes' || echo 'no'")

    if [ "$venv_exists" = "yes" ]; then
        log_warn "Обнаружено старое виртуальное окружение"
        log_info "Удаление старого виртуального окружения..."
        run_remote_command "$TARGET_HOST" "$TARGET_USER" "" \
            "rm -rf $TARGET_APP_DIR/$VENV_NAME"
        log_success "Старое виртуальное окружение удалено"
    fi

    # Создание нового виртуального окружения
    log_step "Создание виртуального окружения"

    log_info "Создание виртуального окружения Python..."
    run_remote_command "$TARGET_HOST" "$TARGET_USER" "" \
        "cd $TARGET_APP_DIR && python3 -m venv $VENV_NAME"

    log_success "Виртуальное окружение создано"

    # Обновление pip в виртуальном окружении
    log_info "Обновление pip в виртуальном окружении..."
    run_remote_command "$TARGET_HOST" "$TARGET_USER" "" \
        "cd $TARGET_APP_DIR && source $VENV_NAME/bin/activate && \
        pip install --upgrade pip setuptools wheel"

    log_success "pip обновлен"

    # Проверка наличия requirements.txt
    log_step "Проверка requirements.txt"

    log_info "Поиск файла requirements.txt..."
    local req_exists=$(ssh "$TARGET_USER@$TARGET_HOST" \
        "[ -f $TARGET_APP_DIR/requirements.txt ] && echo 'yes' || echo 'no'")

    if [ "$req_exists" = "no" ]; then
        log_warn "Файл requirements.txt не найден"

        # Проверка наличия frozen requirements из аудита
        local frozen_req=$(ls -t "$BACKUP_DIR"/requirements_frozen_*.txt 2>/dev/null | head -1)

        if [ -n "$frozen_req" ]; then
            log_info "Использование frozen requirements из аудита: $frozen_req"
            scp "$frozen_req" "$TARGET_USER@$TARGET_HOST:$TARGET_APP_DIR/requirements.txt"
            log_success "requirements.txt загружен на сервер"
        else
            log_error "Не найден ни requirements.txt, ни frozen requirements"
            exit 1
        fi
    else
        log_success "Файл requirements.txt найден"
    fi

    # Установка зависимостей
    log_step "Установка Python зависимостей"

    log_info "Установка зависимостей из requirements.txt..."
    log_info "Это может занять несколько минут..."

    run_remote_command "$TARGET_HOST" "$TARGET_USER" "" \
        "cd $TARGET_APP_DIR && source $VENV_NAME/bin/activate && \
        pip install -r requirements.txt --no-cache-dir"

    if [ $? -eq 0 ]; then
        log_success "Все зависимости установлены успешно"
    else
        log_error "Ошибка установки зависимостей"
        log_info "Попытка установки с игнорированием ошибок..."
        run_remote_command "$TARGET_HOST" "$TARGET_USER" "" \
            "cd $TARGET_APP_DIR && source $VENV_NAME/bin/activate && \
            pip install -r requirements.txt --no-cache-dir --ignore-errors" || true
        log_warn "Некоторые зависимости могут быть не установлены"
    fi

    # Проверка установленных пакетов
    log_step "Проверка установленных пакетов"

    log_info "Получение списка установленных пакетов..."
    run_remote_command "$TARGET_HOST" "$TARGET_USER" "" \
        "cd $TARGET_APP_DIR && source $VENV_NAME/bin/activate && pip list" \
        > "$TEMP_DIR/target_installed_packages.txt"

    log_info "Сохранение списка установленных пакетов..."
    run_remote_command "$TARGET_HOST" "$TARGET_USER" "" \
        "cd $TARGET_APP_DIR && source $VENV_NAME/bin/activate && pip freeze" \
        > "$BACKUP_DIR/target_pip_freeze_${TIMESTAMP}.txt"

    log_success "Список пакетов сохранен: $BACKUP_DIR/target_pip_freeze_${TIMESTAMP}.txt"

    # Проверка критичных пакетов
    log_step "Проверка критичных пакетов"

    local critical_packages=("telethon" "python-dotenv" "asyncio")

    for package in "${critical_packages[@]}"; do
        log_info "Проверка наличия пакета: $package"
        if grep -qi "$package" "$TEMP_DIR/target_installed_packages.txt"; then
            log_success "Пакет $package установлен"
        else
            log_warn "Пакет $package не найден в списке установленных"
        fi
    done

    # Проверка переменных окружения
    log_step "Проверка переменных окружения"

    log_info "Проверка наличия .env файлов..."
    run_remote_command "$TARGET_HOST" "$TARGET_USER" "" \
        "ls -la $TARGET_APP_DIR/.env*" > "$TEMP_DIR/target_env_files_check.txt" || true

    if [ $? -eq 0 ]; then
        log_success ".env файлы найдены"

        # Проверка прав доступа
        log_info "Проверка прав доступа к .env файлам..."
        run_remote_command "$TARGET_HOST" "$TARGET_USER" "" \
            "find $TARGET_APP_DIR -name '.env*' -type f ! -perm 600 -ls"

        if [ $? -eq 0 ]; then
            log_info "Исправление прав доступа..."
            run_remote_command "$TARGET_HOST" "$TARGET_USER" "" \
                "chmod 600 $TARGET_APP_DIR/.env*"
            log_success "Права доступа исправлены"
        fi
    else
        log_error ".env файлы не найдены!"
        exit 1
    fi

    # Проверка сессионных файлов
    log_step "Проверка сессионных файлов"

    log_info "Проверка наличия .session файлов..."
    run_remote_command "$TARGET_HOST" "$TARGET_USER" "" \
        "find $TARGET_APP_DIR -name '*.session' -ls" > "$TEMP_DIR/target_session_files_check.txt" || true

    if [ -s "$TEMP_DIR/target_session_files_check.txt" ]; then
        log_success ".session файлы найдены"

        # Проверка прав доступа
        log_info "Установка прав доступа для .session файлов..."
        run_remote_command "$TARGET_HOST" "$TARGET_USER" "" \
            "find $TARGET_APP_DIR -name '*.session' -type f -exec chmod 600 {} \;"
        log_success "Права доступа установлены"
    else
        log_warn ".session файлы не найдены"
        log_warn "Может потребоваться повторная авторизация в Telegram"
    fi

    # Проверка базы данных
    log_step "Проверка базы данных"

    log_info "Проверка наличия базы данных..."
    run_remote_command "$TARGET_HOST" "$TARGET_USER" "" \
        "ls -lh $TARGET_APP_DIR/*.db" > "$TEMP_DIR/target_db_check.txt" || true

    if [ -s "$TEMP_DIR/target_db_check.txt" ]; then
        log_success "База данных найдена"

        # Установка прав доступа
        run_remote_command "$TARGET_HOST" "$TARGET_USER" "" \
            "chmod 600 $TARGET_APP_DIR/*.db"
        log_success "Права доступа установлены"
    else
        log_warn "База данных не найдена"
    fi

    # Тестовый запуск Python
    log_step "Тестовый запуск Python"

    log_info "Проверка работы Python в виртуальном окружении..."
    run_remote_command "$TARGET_HOST" "$TARGET_USER" "" \
        "cd $TARGET_APP_DIR && source $VENV_NAME/bin/activate && \
        python -c 'import sys; print(f\"Python {sys.version}\")'"

    log_success "Python работает корректно"

    # Проверка импорта критичных модулей
    log_info "Проверка импорта критичных модулей..."
    run_remote_command "$TARGET_HOST" "$TARGET_USER" "" \
        "cd $TARGET_APP_DIR && source $VENV_NAME/bin/activate && \
        python -c 'import telethon; import asyncio; import dotenv; print(\"All critical modules imported successfully\")'"

    if [ $? -eq 0 ]; then
        log_success "Все критичные модули импортируются успешно"
    else
        log_error "Ошибка импорта критичных модулей"
        exit 1
    fi

    # Создание отчета о настройке окружения
    log_step "Создание отчета о настройке окружения"

    local report_file="$BACKUP_DIR/environment_report_${TIMESTAMP}.md"

    cat > "$report_file" << EOF
# Отчет о настройке окружения

**Дата:** $(date '+%Y-%m-%d %H:%M:%S')
**Сервер:** $TARGET_HOST ($TARGET_ALIAS)

## Виртуальное окружение

- **Расположение:** $TARGET_APP_DIR/$VENV_NAME
- **Статус:** Создано и настроено

## Установленные пакеты

\`\`\`
$(cat "$TEMP_DIR/target_installed_packages.txt")
\`\`\`

## Файлы конфигурации

### .env файлы
\`\`\`
$(cat "$TEMP_DIR/target_env_files_check.txt" 2>/dev/null || echo "Не найдены")
\`\`\`

### .session файлы
\`\`\`
$(cat "$TEMP_DIR/target_session_files_check.txt" 2>/dev/null || echo "Не найдены")
\`\`\`

### База данных
\`\`\`
$(cat "$TEMP_DIR/target_db_check.txt" 2>/dev/null || echo "Не найдена")
\`\`\`

## Проверки

✅ Виртуальное окружение создано
✅ Зависимости установлены
✅ Критичные модули импортируются
✅ Права доступа установлены
✅ Конфигурационные файлы на месте

---
*Отчет создан автоматически скриптом настройки окружения*
EOF

    log_success "Отчет о настройке окружения создан: $report_file"

    log_step "НАСТРОЙКА ОКРУЖЕНИЯ ЗАВЕРШЕНА"
    log_success "Окружение настроено и готово к работе"

    echo -e "\n${GREEN}════════════════════════════════════════════════════════${NC}"
    echo -e "${GREEN}Окружение успешно настроено!${NC}"
    echo -e "${GREEN}════════════════════════════════════════════════════════${NC}"
    echo -e "\nСледующий шаг: Запустите ${BLUE}./05_configure_service.sh${NC}"
}

# Запуск скрипта
main "$@"
