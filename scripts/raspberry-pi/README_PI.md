# Автозапуск ассистента на Raspberry Pi

Этот каталог содержит файлы для настройки автоматического запуска вашего голосового ассистента при включении Raspberry Pi с использованием `systemd`.

## 📦 Файлы
- `voice-assistant.service`: Шаблон системного сервиса.
- `install_autostart.sh`: Скрипт для автоматической установки.

## 🚀 Инструкция по установке

1.  Скопируйте проект на Raspberry Pi (например, через Git или SFTP).
2.  Перейдите в каталог `scripts/raspberry-pi/`:
    ```bash
    cd /home/pi/graduation-project/scripts/raspberry-pi/
    ```
3.  Разрешите выполнение скрипта:
    ```bash
    chmod +x install_autostart.sh
    ```
4.  Запустите установку:
    ```bash
    ./install_autostart.sh
    ```

## 🛠️ Основные команды после установки

### Проверка статуса
```bash
sudo systemctl status voice-assistant
```

### Просмотр логов в реальном времени
```bash
journalctl -u voice-assistant -f
```

### Перезапуск сервиса
```bash
sudo systemctl restart voice-assistant
```

### Остановка сервиса
```bash
sudo systemctl stop voice-assistant
```

### Отключение автозапуска
```bash
sudo systemctl disable voice-assistant
```

---

**Важно:** Убедитесь, что ваш виртуальный уровень (`.venv`) в каталоге `core` уже создан и в нем установлены все зависимости.
Если вы используете другой путь к проекту (не `/home/pi/graduation-project`), скрипт `install_autostart.sh` должен автоматически подхватить текущий путь при запуске в папке скриптов.
