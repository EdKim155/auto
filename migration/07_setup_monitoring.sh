#!/bin/bash

###############################################################################
# Скрипт настройки мониторинга и ротации логов
# Настраивает logrotate, создает скрипты мониторинга
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
    log_step "НАСТРОЙКА МОНИТОРИНГА И РОТАЦИИ ЛОГОВ"

    init_migration

    # Проверка подключения к целевому серверу
    log_info "Проверка подключения к целевому серверу..."
    check_ssh_connection "$TARGET_HOST" "$TARGET_USER" "" "$TARGET_ALIAS" || exit 1

    # Настройка logrotate
    log_step "Настройка logrotate"

    log_info "Создание конфигурации logrotate..."

    local temp_logrotate="$TEMP_DIR/telegram-bot-logrotate"

    cat > "$temp_logrotate" << 'EOF'
/var/log/telegram-bot.log {
    daily
    rotate 30
    compress
    delaycompress
    missingok
    notifempty
    create 0644 root root
    sharedscripts
    postrotate
        systemctl reload telegram-bot.service >/dev/null 2>&1 || true
    endscript
}

/root/auto/*.log {
    daily
    rotate 7
    compress
    delaycompress
    missingok
    notifempty
    create 0644 root root
    maxsize 100M
}
EOF

    log_info "Копирование конфигурации logrotate на сервер..."
    scp "$temp_logrotate" "$TARGET_USER@$TARGET_HOST:/tmp/telegram-bot"

    run_remote_command "$TARGET_HOST" "$TARGET_USER" "" \
        "mv /tmp/telegram-bot /etc/logrotate.d/telegram-bot && \
        chmod 644 /etc/logrotate.d/telegram-bot"

    log_success "Конфигурация logrotate установлена"

    # Тестирование logrotate
    log_info "Тестирование конфигурации logrotate..."
    run_remote_command "$TARGET_HOST" "$TARGET_USER" "" \
        "logrotate -d /etc/logrotate.d/telegram-bot" > "$TEMP_DIR/logrotate_test.log" 2>&1 || true

    log_success "Конфигурация logrotate протестирована"

    # Создание скрипта мониторинга
    log_step "Создание скрипта мониторинга"

    log_info "Создание скрипта проверки здоровья сервиса..."

    local temp_healthcheck="$TEMP_DIR/healthcheck.sh"

    cat > "$temp_healthcheck" << 'HEALTHCHECK_EOF'
#!/bin/bash

###############################################################################
# Скрипт мониторинга Telegram-бота
###############################################################################

SERVICE_NAME="telegram-bot.service"
LOG_FILE="/var/log/telegram-bot-healthcheck.log"
MAX_RESTART_ATTEMPTS=3

log_message() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1" | tee -a "$LOG_FILE"
}

# Проверка статуса сервиса
if ! systemctl is-active --quiet "$SERVICE_NAME"; then
    log_message "ERROR: Сервис $SERVICE_NAME не запущен!"

    # Проверка количества недавних перезапусков
    restart_count=$(journalctl -u "$SERVICE_NAME" --since "5 minutes ago" | grep -c "Started" || echo 0)

    if [ "$restart_count" -lt "$MAX_RESTART_ATTEMPTS" ]; then
        log_message "INFO: Попытка перезапуска сервиса..."
        systemctl start "$SERVICE_NAME"

        sleep 5

        if systemctl is-active --quiet "$SERVICE_NAME"; then
            log_message "SUCCESS: Сервис успешно перезапущен"
        else
            log_message "ERROR: Не удалось перезапустить сервис"
            # Отправка уведомления (если настроено)
            # curl -X POST "https://your-webhook-url" -d "Service $SERVICE_NAME failed"
        fi
    else
        log_message "ERROR: Слишком много перезапусков за последние 5 минут ($restart_count)"
        # Отправка критического уведомления
    fi
else
    log_message "INFO: Сервис $SERVICE_NAME работает нормально"

    # Проверка использования памяти
    memory_usage=$(ps aux | grep "python.*main.py" | grep -v grep | awk '{print $4}' | head -1)
    log_message "INFO: Использование памяти: ${memory_usage}%"

    # Проверка CPU
    cpu_usage=$(ps aux | grep "python.*main.py" | grep -v grep | awk '{print $3}' | head -1)
    log_message "INFO: Использование CPU: ${cpu_usage}%"

    # Проверка последних ошибок в логах
    error_count=$(tail -100 /var/log/telegram-bot.log | grep -ci "error" || echo 0)
    if [ "$error_count" -gt 10 ]; then
        log_message "WARN: Обнаружено $error_count ошибок в последних 100 строках лога"
    fi
fi
HEALTHCHECK_EOF

    chmod +x "$temp_healthcheck"

    log_info "Копирование скрипта мониторинга на сервер..."
    scp "$temp_healthcheck" "$TARGET_USER@$TARGET_HOST:$TARGET_APP_DIR/healthcheck.sh"

    run_remote_command "$TARGET_HOST" "$TARGET_USER" "" \
        "chmod +x $TARGET_APP_DIR/healthcheck.sh"

    log_success "Скрипт мониторинга установлен"

    # Настройка cron для мониторинга
    log_step "Настройка cron для автоматического мониторинга"

    log_info "Добавление задачи в cron..."

    run_remote_command "$TARGET_HOST" "$TARGET_USER" "" \
        "(crontab -l 2>/dev/null | grep -v 'healthcheck.sh'; echo '*/5 * * * * $TARGET_APP_DIR/healthcheck.sh') | crontab -"

    log_success "Cron задача добавлена (проверка каждые 5 минут)"

    # Создание скрипта для просмотра статистики
    log_step "Создание скрипта статистики"

    local temp_stats="$TEMP_DIR/bot_stats.sh"

    cat > "$temp_stats" << 'STATS_EOF'
#!/bin/bash

###############################################################################
# Скрипт статистики Telegram-бота
###############################################################################

SERVICE_NAME="telegram-bot.service"

echo "═══════════════════════════════════════════════════════════════"
echo "            Статистика Telegram Bot Automation"
echo "═══════════════════════════════════════════════════════════════"
echo ""

# Статус сервиса
echo "📊 Статус сервиса:"
systemctl status "$SERVICE_NAME" --no-pager | head -10
echo ""

# Время работы
echo "⏱️  Время работы:"
systemctl show "$SERVICE_NAME" --property=ActiveEnterTimestamp --no-pager
echo ""

# Использование ресурсов
echo "💻 Использование ресурсов:"
ps aux | grep "python.*main.py" | grep -v grep | awk '{printf "  CPU: %s%%\n  Memory: %s%%\n  PID: %s\n", $3, $4, $2}'
echo ""

# Последние логи
echo "📝 Последние 10 строк лога:"
tail -10 /var/log/telegram-bot.log
echo ""

# Статистика ошибок
echo "⚠️  Статистика ошибок (последние 1000 строк):"
error_count=$(tail -1000 /var/log/telegram-bot.log | grep -ci "error" || echo 0)
warning_count=$(tail -1000 /var/log/telegram-bot.log | grep -ci "warning" || echo 0)
echo "  Errors: $error_count"
echo "  Warnings: $warning_count"
echo ""

# Размер логов
echo "📂 Размер логов:"
du -h /var/log/telegram-bot.log 2>/dev/null || echo "  Лог файл не найден"
du -sh /root/auto/*.log 2>/dev/null || echo "  Логи приложения не найдены"
echo ""

# Использование диска
echo "💾 Использование диска:"
df -h / | tail -1
echo ""

echo "═══════════════════════════════════════════════════════════════"
STATS_EOF

    chmod +x "$temp_stats"

    log_info "Копирование скрипта статистики на сервер..."
    scp "$temp_stats" "$TARGET_USER@$TARGET_HOST:$TARGET_APP_DIR/bot_stats.sh"

    run_remote_command "$TARGET_HOST" "$TARGET_USER" "" \
        "chmod +x $TARGET_APP_DIR/bot_stats.sh"

    log_success "Скрипт статистики установлен"

    # Создание алиасов для удобства
    log_step "Создание алиасов для удобства"

    log_info "Добавление алиасов в .bashrc..."

    run_remote_command "$TARGET_HOST" "$TARGET_USER" "" \
        "grep -q 'telegram-bot aliases' ~/.bashrc || cat >> ~/.bashrc << 'ALIASES_EOF'

# Telegram-bot aliases
alias bot-status='systemctl status telegram-bot.service'
alias bot-start='systemctl start telegram-bot.service'
alias bot-stop='systemctl stop telegram-bot.service'
alias bot-restart='systemctl restart telegram-bot.service'
alias bot-logs='journalctl -u telegram-bot.service -f'
alias bot-logs-tail='tail -f /var/log/telegram-bot.log'
alias bot-stats='$TARGET_APP_DIR/bot_stats.sh'
alias bot-health='$TARGET_APP_DIR/healthcheck.sh'
ALIASES_EOF
"

    log_success "Алиасы добавлены в .bashrc"

    # Создание отчета о мониторинге
    log_step "Создание отчета о мониторинге"

    local report_file="$BACKUP_DIR/monitoring_report_${TIMESTAMP}.md"

    cat > "$report_file" << EOF
# Отчет о настройке мониторинга

**Дата:** $(date '+%Y-%m-%d %H:%M:%S')
**Сервер:** $TARGET_HOST ($TARGET_ALIAS)

## Ротация логов

### Конфигурация logrotate
- **Расположение:** /etc/logrotate.d/telegram-bot
- **Ротация:** ежедневно
- **Хранение:** 30 дней для systemd логов, 7 дней для логов приложения
- **Сжатие:** включено
- **Максимальный размер:** 100MB для логов приложения

### Логи
- /var/log/telegram-bot.log (основной лог systemd)
- /root/auto/*.log (логи приложения)

## Мониторинг

### Скрипт healthcheck
- **Расположение:** $TARGET_APP_DIR/healthcheck.sh
- **Частота:** каждые 5 минут (cron)
- **Лог:** /var/log/telegram-bot-healthcheck.log
- **Функции:**
  - Проверка статуса сервиса
  - Автоматический перезапуск при сбое
  - Мониторинг использования ресурсов
  - Подсчет ошибок в логах

### Скрипт статистики
- **Расположение:** $TARGET_APP_DIR/bot_stats.sh
- **Вызов:** вручную или через алиас \`bot-stats\`
- **Информация:**
  - Статус сервиса
  - Время работы
  - Использование CPU и памяти
  - Последние логи
  - Статистика ошибок
  - Использование диска

## Алиасы команд

Для удобства управления добавлены следующие алиасы:

\`\`\`bash
bot-status      # Статус сервиса
bot-start       # Запуск сервиса
bot-stop        # Остановка сервиса
bot-restart     # Перезапуск сервиса
bot-logs        # Просмотр логов (journalctl)
bot-logs-tail   # Просмотр логов (tail)
bot-stats       # Статистика работы
bot-health      # Запуск проверки здоровья
\`\`\`

## Использование

### Просмотр статистики
\`\`\`bash
ssh $TARGET_ALIAS 'bot-stats'
\`\`\`

### Просмотр логов в реальном времени
\`\`\`bash
ssh $TARGET_ALIAS 'bot-logs'
\`\`\`

### Ручная проверка здоровья
\`\`\`bash
ssh $TARGET_ALIAS 'bot-health'
\`\`\`

### Просмотр логов healthcheck
\`\`\`bash
ssh $TARGET_ALIAS 'tail -f /var/log/telegram-bot-healthcheck.log'
\`\`\`

## Автоматизация

- ✅ Ротация логов настроена (logrotate)
- ✅ Автоматический мониторинг (cron каждые 5 минут)
- ✅ Автоматический перезапуск при сбое
- ✅ Алиасы для быстрого доступа

---
*Отчет создан автоматически скриптом настройки мониторинга*
EOF

    log_success "Отчет о мониторинге создан: $report_file"

    log_step "НАСТРОЙКА МОНИТОРИНГА ЗАВЕРШЕНА"
    log_success "Мониторинг и ротация логов настроены"

    echo -e "\n${GREEN}════════════════════════════════════════════════════════${NC}"
    echo -e "${GREEN}Мониторинг успешно настроен!${NC}"
    echo -e "${GREEN}════════════════════════════════════════════════════════${NC}"
    echo -e "\n${GREEN}Доступные команды:${NC}"
    echo -e "  ${BLUE}ssh $TARGET_ALIAS 'bot-stats'${NC}      - статистика"
    echo -e "  ${BLUE}ssh $TARGET_ALIAS 'bot-logs'${NC}       - логи"
    echo -e "  ${BLUE}ssh $TARGET_ALIAS 'bot-health'${NC}     - проверка здоровья"
    echo -e "\n${GREEN}Мониторинг запускается автоматически каждые 5 минут${NC}"
}

# Запуск скрипта
main "$@"
