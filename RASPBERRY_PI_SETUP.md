# 🍓 Полная настройка ассистента на Raspberry Pi OS

Следуйте этим шагам по порядку, чтобы запустить ассистента на «чистой» системе.

---

## 1. Обновление системы и установка библиотек
Откройте терминал и выполните установку необходимых системных компонентов для работы звука (ALSA), микрофона и математических вычислений (OpenBLAS):

```bash
sudo apt update && sudo apt upgrade -y
# Системные библиотеки для звука, микрофона и дополнительных инструментов
sudo apt install -y python3-venv python3-pip libportaudio2 libatlas-base-dev libsndfile1 vlc libatomic1 mpg123 wget unzip
```

## 2. Подготовка проекта
Склонируйте проект или скопируйте его в `/home/pi/graduation-project`:

```bash
cd /home/pi/graduation-project/core
# Создаем виртуальное окружение
python3 -m venv .venv
# Активируем его
source .venv/bin/activate
# Устанавливаем все Python-зависимости (может занять 5-10 минут)
pip install --upgrade pip
pip install -r requirements.txt
```

---

## 3. Установка моделей (Критически важно!)
Ассистент требует наличия двух обученных моделей.

### А. Модель распознавания голоса (Vosk)
Выполните эти команды, чтобы скачать и подготовить небольшую русскую модель:
```bash
cd /home/pi/graduation-project/core
wget https://alphacephei.com/vosk/models/vosk-model-small-ru-0.22.zip
unzip vosk-model-small-ru-0.22.zip
mv vosk-model-small-ru-0.22 vosk-model
rm vosk-model-small-ru-0.22.zip
```
*Убедитесь, что внутри `core/vosk-model/` теперь лежат файлы `am`, `conf` и другие.*

### Б. Модель интентов (NLP)
Перед запуском нужно обучить классификатор (или положить готовую модель):
```bash
# Перейдите в папку nlp
cd /home/pi/graduation-project/core/nlp
# Запустите скрипт обучения (он создаст папку models/intent_model)
python train-model.py
```

---

## 4. Первый запуск и тест
Проверьте, всё ли работает вручную из папки `core`:
```bash
cd /home/pi/graduation-project/core
python3 main.py
```
*Если ассистент сказал «Я готов к работе», значит база настроена верно.*

---

## 5. Настройка автозапуска
Чтобы ассистент запускался сам при включении Raspberry Pi:

```bash
cd /home/pi/graduation-project/scripts/raspberry-pi
chmod +x install_autostart.sh
./install_autostart.sh
```

## 6. Полезные команды для управления
* **Просмотр логов (что слышит ассистент):** `journalctl -u voice-assistant -f`
* **Перезапуск:** `sudo systemctl restart voice-assistant`
* **Остановка:** `sudo systemctl stop voice-assistant`

---
**Совет по звуку:** Если звук не идет или микрофон не слышит, проверьте настройки в `alsamixer`:
`alsamixer` -> (нажать F6 для выбора аудиокарты) -> поднять уровни громкости Space/Стрелками.
