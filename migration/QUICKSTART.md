# Быстрый старт миграции

## Предварительные требования

1. SSH-доступ к обоим серверам
2. Установленные утилиты: `ssh`, `scp`, `rsync`, `tar`, `shasum`
3. Права root на обоих серверах

## Проверка перед началом

```bash
# Проверьте подключение к исходному серверу
ssh -i ~/.ssh/id_ed25519_aprel root@72.56.76.248 "echo OK"

# Проверьте подключение к целевому серверу
ssh auto-server "echo OK"
```

## Вариант 1: Автоматическая миграция (рекомендуется)

Запустите полный цикл миграции одной командой:

```bash
cd /Users/edgark/auto/migration
./migrate.sh
```

### С интерактивным режимом (с подтверждениями)

```bash
./migrate.sh --interactive
```

### Тестовый запуск (без изменений)

```bash
./migrate.sh --dry-run
```

## Вариант 2: Пошаговая миграция

Выполните скрипты последовательно:

```bash
cd /Users/edgark/auto/migration

# Шаг 1: Аудит исходного сервера
./01_audit_source.sh

# Шаг 2: Подготовка целевого сервера
./02_prepare_target.sh

# Шаг 3: Резервное копирование и перенос
./03_backup_and_transfer.sh

# Шаг 4: Настройка окружения
./04_setup_environment.sh

# Шаг 5: Настройка systemd-сервиса
./05_configure_service.sh

# Шаг 6: Валидация
./06_validate_migration.sh

# Шаг 7: Настройка мониторинга
./07_setup_monitoring.sh
```

## Вариант 3: Запуск конкретного шага

```bash
# Запустить только шаг 3
./migrate.sh --step 3

# Запустить только валидацию
./migrate.sh --step 6
```

## После успешной миграции

1. **Остановите сервис на старом сервере:**
   ```bash
   ssh aprel-server 'systemctl stop telegram-bot.service'
   ssh aprel-server 'systemctl disable telegram-bot.service'
   ```

2. **Запустите сервис на новом сервере:**
   ```bash
   ssh auto-server 'systemctl start telegram-bot.service'
   ```

3. **Проверьте статус:**
   ```bash
   ssh auto-server 'systemctl status telegram-bot.service'
   ```

4. **Мониторьте логи:**
   ```bash
   ssh auto-server 'journalctl -u telegram-bot.service -f'
   ```

5. **Проверьте работу бота в Telegram**

## В случае проблем

### Откат на исходный сервер

```bash
./rollback.sh
```

### Просмотр логов миграции

```bash
# Последний лог миграции
tail -f migration/logs/migration_*.log

# Лог ошибок
tail -f migration/logs/migration_errors_*.log
```

### Повторный запуск валидации

```bash
./06_validate_migration.sh
```

## Полезные команды после миграции

```bash
# На новом сервере доступны алиасы:
ssh auto-server

bot-status      # Статус сервиса
bot-start       # Запуск
bot-stop        # Остановка
bot-restart     # Перезапуск
bot-logs        # Логи (journalctl)
bot-stats       # Статистика
bot-health      # Проверка здоровья
```

## Расположение файлов

- Резервные копии: `migration/backups/`
- Логи миграции: `migration/logs/`
- Отчеты: `migration/backups/*_report_*.md`
- Конфигурация: `migration/config.sh`

## Поддержка

В случае проблем проверьте:
1. Логи миграции в `migration/logs/`
2. Отчеты в `migration/backups/`
3. Статус сервиса: `systemctl status telegram-bot.service`
4. Доступность Telegram API

## Примечания

- Все скрипты идемпотентны (можно запускать несколько раз)
- Создаются автоматические резервные копии
- Логируется каждое действие
- Проверяется целостность данных (checksums)
- План отката включен

## Безопасность

- Файлы .env защищены (chmod 600)
- Файлы .session защищены (chmod 600)
- SSH-ключи используются для безопасной передачи
- Все пароли и токены остаются конфиденциальными
