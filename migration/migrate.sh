#!/bin/bash

###############################################################################
# Главный скрипт миграции Telegram-бота
# Выполняет полный цикл миграции от начала до конца
###############################################################################

set -euo pipefail

# Загрузка конфигурации и утилит
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$SCRIPT_DIR/config.sh"
source "$SCRIPT_DIR/utils.sh"

###############################################################################
# Функция отображения использования
###############################################################################

usage() {
    cat << EOF
Использование: $0 [ОПЦИИ]

Главный скрипт миграции Telegram-бота с исходного сервера на целевой.

ОПЦИИ:
    -h, --help              Показать эту справку
    -s, --step STEP         Запустить конкретный шаг (1-7)
    -f, --force             Принудительный режим (перезапись существующих файлов)
    -v, --verbose           Подробный вывод
    -d, --dry-run           Тестовый режим (без изменений)
    --skip-backup           Пропустить создание резервной копии (НЕ РЕКОМЕНДУЕТСЯ)
    --interactive           Интерактивный режим с подтверждениями

ШАГИ:
    1. Аудит исходного сервера
    2. Подготовка целевого сервера
    3. Резервное копирование и перенос
    4. Настройка окружения
    5. Настройка systemd-сервиса
    6. Валидация миграции
    7. Настройка мониторинга

ПРИМЕРЫ:
    $0                      # Выполнить полную миграцию
    $0 --step 3             # Выполнить только шаг 3
    $0 --interactive        # Интерактивный режим
    $0 --dry-run            # Тестовый запуск

ИСХОДНЫЙ СЕРВЕР: $SOURCE_HOST ($SOURCE_ALIAS)
ЦЕЛЕВОЙ СЕРВЕР: $TARGET_HOST ($TARGET_ALIAS)

EOF
}

###############################################################################
# Функция запуска отдельного шага
###############################################################################

run_step() {
    local step_num="$1"
    local step_script="$2"
    local step_name="$3"

    log_step "ШАГ $step_num: $step_name"

    if [ "$DRY_RUN" -eq 1 ]; then
        log_info "[DRY RUN] Пропуск выполнения: $step_script"
        return 0
    fi

    if [ ! -f "$SCRIPT_DIR/$step_script" ]; then
        log_error "Скрипт не найден: $step_script"
        return 1
    fi

    bash "$SCRIPT_DIR/$step_script"
    local exit_code=$?

    if [ $exit_code -eq 0 ]; then
        log_success "Шаг $step_num завершен успешно"
        return 0
    else
        log_error "Шаг $step_num завершился с ошибкой (код: $exit_code)"
        return 1
    fi
}

###############################################################################
# Функция интерактивного подтверждения
###############################################################################

confirm_step() {
    local step_name="$1"

    if [ "$INTERACTIVE" -eq 1 ]; then
        echo -e "\n${YELLOW}═══════════════════════════════════════════════════════════════${NC}"
        echo -e "${YELLOW}Следующий шаг: $step_name${NC}"
        echo -e "${YELLOW}═══════════════════════════════════════════════════════════════${NC}"
        read -p "Продолжить? (y/n): " response
        if [[ ! "$response" =~ ^[Yy]$ ]]; then
            log_info "Шаг пропущен пользователем"
            return 1
        fi
    fi
    return 0
}

###############################################################################
# Главная функция
###############################################################################

main() {
    log_step "НАЧАЛО МИГРАЦИИ TELEGRAM-БОТА"

    cat << "EOF"
╔═══════════════════════════════════════════════════════════════╗
║                                                               ║
║          МИГРАЦИЯ СИСТЕМЫ TELEGRAM-БОТА                       ║
║                                                               ║
╚═══════════════════════════════════════════════════════════════╝
EOF

    echo -e "\n${BLUE}Исходный сервер:${NC} $SOURCE_HOST ($SOURCE_ALIAS)"
    echo -e "${BLUE}Целевой сервер:${NC} $TARGET_HOST ($TARGET_ALIAS)"
    echo -e "${BLUE}Дата начала:${NC} $(date '+%Y-%m-%d %H:%M:%S')"
    echo -e ""

    # Проверка предварительных условий
    log_step "ПРЕДВАРИТЕЛЬНЫЕ ПРОВЕРКИ"

    log_info "Проверка SSH-подключений..."
    check_ssh_connection "$SOURCE_HOST" "$SOURCE_USER" "$SOURCE_SSH_KEY" "$SOURCE_ALIAS" || {
        log_error "Не удалось подключиться к исходному серверу"
        exit 1
    }

    check_ssh_connection "$TARGET_HOST" "$TARGET_USER" "$TARGET_SSH_KEY" "$TARGET_ALIAS" || {
        log_error "Не удалось подключиться к целевому серверу"
        exit 1
    }

    log_success "Все предварительные проверки пройдены"

    # Создание резервной копии для отката
    log_info "Создание точки восстановления..."
    echo "$(date '+%Y-%m-%d %H:%M:%S') - Migration started" > "$BACKUP_DIR/migration_checkpoint_${TIMESTAMP}.txt"

    # Выполнение шагов миграции
    local total_steps=7
    local completed_steps=0

    # Шаг 1: Аудит исходного сервера
    if confirm_step "Аудит исходного сервера"; then
        if run_step 1 "01_audit_source.sh" "Аудит исходного сервера"; then
            ((completed_steps++))
        else
            log_error "Критическая ошибка на шаге 1"
            finish_migration "failure"
            exit 1
        fi
    fi

    # Шаг 2: Подготовка целевого сервера
    if confirm_step "Подготовка целевого сервера"; then
        if run_step 2 "02_prepare_target.sh" "Подготовка целевого сервера"; then
            ((completed_steps++))
        else
            log_error "Критическая ошибка на шаге 2"
            finish_migration "failure"
            exit 1
        fi
    fi

    # Шаг 3: Резервное копирование и перенос
    if confirm_step "Резервное копирование и перенос данных"; then
        if run_step 3 "03_backup_and_transfer.sh" "Резервное копирование и перенос"; then
            ((completed_steps++))
        else
            log_error "Критическая ошибка на шаге 3"
            log_warn "Рекомендуется выполнить откат: ./rollback.sh"
            finish_migration "failure"
            exit 1
        fi
    fi

    # Шаг 4: Настройка окружения
    if confirm_step "Настройка окружения"; then
        if run_step 4 "04_setup_environment.sh" "Настройка окружения"; then
            ((completed_steps++))
        else
            log_error "Критическая ошибка на шаге 4"
            log_warn "Рекомендуется выполнить откат: ./rollback.sh"
            finish_migration "failure"
            exit 1
        fi
    fi

    # Шаг 5: Настройка systemd-сервиса
    if confirm_step "Настройка systemd-сервиса"; then
        if run_step 5 "05_configure_service.sh" "Настройка systemd-сервиса"; then
            ((completed_steps++))
        else
            log_error "Ошибка на шаге 5"
            log_warn "Вы можете попробовать исправить и продолжить"
        fi
    fi

    # Шаг 6: Валидация миграции
    if confirm_step "Валидация миграции"; then
        if run_step 6 "06_validate_migration.sh" "Валидация миграции"; then
            ((completed_steps++))
        else
            log_error "Валидация не пройдена"
            log_warn "Проверьте ошибки и исправьте их перед запуском сервиса"
            log_info "Вы можете запустить валидацию повторно: ./06_validate_migration.sh"
        fi
    fi

    # Шаг 7: Настройка мониторинга
    if confirm_step "Настройка мониторинга"; then
        if run_step 7 "07_setup_monitoring.sh" "Настройка мониторинга"; then
            ((completed_steps++))
        else
            log_warn "Мониторинг не настроен, но это не критично"
            log_info "Вы можете настроить его позже: ./07_setup_monitoring.sh"
        fi
    fi

    # Итоги миграции
    log_step "ИТОГИ МИГРАЦИИ"

    echo -e "\n${BLUE}════════════════════════════════════════════════════════${NC}"
    echo -e "${BLUE}Выполнено шагов: $completed_steps из $total_steps${NC}"
    echo -e "${BLUE}════════════════════════════════════════════════════════${NC}\n"

    if [ $completed_steps -eq $total_steps ]; then
        log_success "ВСЕ ШАГИ МИГРАЦИИ ЗАВЕРШЕНЫ УСПЕШНО!"

        echo -e "\n${GREEN}╔═══════════════════════════════════════════════════════════════╗${NC}"
        echo -e "${GREEN}║                                                               ║${NC}"
        echo -e "${GREEN}║              МИГРАЦИЯ ЗАВЕРШЕНА УСПЕШНО!                      ║${NC}"
        echo -e "${GREEN}║                                                               ║${NC}"
        echo -e "${GREEN}╚═══════════════════════════════════════════════════════════════╝${NC}\n"

        echo -e "${GREEN}Следующие шаги:${NC}\n"
        echo -e "1. ${YELLOW}ВАЖНО:${NC} Остановите сервис на старом сервере:"
        echo -e "   ${BLUE}ssh $SOURCE_ALIAS 'systemctl stop $SERVICE_NAME && systemctl disable $SERVICE_NAME'${NC}\n"

        echo -e "2. Запустите сервис на новом сервере:"
        echo -e "   ${BLUE}ssh $TARGET_ALIAS 'systemctl start $SERVICE_NAME'${NC}\n"

        echo -e "3. Проверьте статус сервиса:"
        echo -e "   ${BLUE}ssh $TARGET_ALIAS 'systemctl status $SERVICE_NAME'${NC}\n"

        echo -e "4. Мониторьте логи в реальном времени:"
        echo -e "   ${BLUE}ssh $TARGET_ALIAS 'journalctl -u $SERVICE_NAME -f'${NC}\n"

        echo -e "5. Проверьте работу бота в Telegram\n"

        echo -e "6. Если все работает, архивируйте данные на старом сервере\n"

        echo -e "${YELLOW}В случае проблем выполните откат:${NC}"
        echo -e "${BLUE}./rollback.sh${NC}\n"

        finish_migration "success"
        exit 0
    else
        log_warn "Миграция завершена с предупреждениями"
        log_info "Завершено шагов: $completed_steps из $total_steps"

        echo -e "\n${YELLOW}╔═══════════════════════════════════════════════════════════════╗${NC}"
        echo -e "${YELLOW}║                                                               ║${NC}"
        echo -e "${YELLOW}║          МИГРАЦИЯ ЗАВЕРШЕНА С ПРЕДУПРЕЖДЕНИЯМИ                ║${NC}"
        echo -e "${YELLOW}║                                                               ║${NC}"
        echo -e "${YELLOW}╚═══════════════════════════════════════════════════════════════╝${NC}\n"

        echo -e "${YELLOW}Рекомендации:${NC}"
        echo -e "1. Проверьте логи миграции: ${BLUE}$LOG_FILE${NC}"
        echo -e "2. Исправьте обнаруженные проблемы"
        echo -e "3. Запустите пропущенные шаги вручную"
        echo -e "4. Проведите валидацию: ${BLUE}./06_validate_migration.sh${NC}\n"

        finish_migration "partial"
        exit 1
    fi
}

###############################################################################
# Парсинг аргументов командной строки
###############################################################################

SPECIFIC_STEP=""
INTERACTIVE=0

while [[ $# -gt 0 ]]; do
    case $1 in
        -h|--help)
            usage
            exit 0
            ;;
        -s|--step)
            SPECIFIC_STEP="$2"
            shift 2
            ;;
        -f|--force)
            export FORCE=1
            shift
            ;;
        -v|--verbose)
            export VERBOSE=1
            shift
            ;;
        -d|--dry-run)
            export DRY_RUN=1
            shift
            ;;
        --skip-backup)
            export SKIP_BACKUP=1
            shift
            ;;
        --interactive)
            INTERACTIVE=1
            shift
            ;;
        *)
            echo "Неизвестная опция: $1"
            usage
            exit 1
            ;;
    esac
done

# Выполнение конкретного шага
if [ -n "$SPECIFIC_STEP" ]; then
    case $SPECIFIC_STEP in
        1)
            run_step 1 "01_audit_source.sh" "Аудит исходного сервера"
            ;;
        2)
            run_step 2 "02_prepare_target.sh" "Подготовка целевого сервера"
            ;;
        3)
            run_step 3 "03_backup_and_transfer.sh" "Резервное копирование и перенос"
            ;;
        4)
            run_step 4 "04_setup_environment.sh" "Настройка окружения"
            ;;
        5)
            run_step 5 "05_configure_service.sh" "Настройка systemd-сервиса"
            ;;
        6)
            run_step 6 "06_validate_migration.sh" "Валидация миграции"
            ;;
        7)
            run_step 7 "07_setup_monitoring.sh" "Настройка мониторинга"
            ;;
        *)
            echo "Неверный номер шага: $SPECIFIC_STEP (допустимо: 1-7)"
            exit 1
            ;;
    esac
else
    # Выполнение полной миграции
    main "$@"
fi
