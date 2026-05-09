# Полная настройка голосового ассистента на Raspberry Pi OS

Пошаговая инструкция по развёртыванию голосового ассистента на «чистой»
Raspberry Pi (рекомендуется Pi 4 / Pi 5, 4 ГБ RAM или больше).

Ассистент состоит из четырёх частей:
- **Vosk** — распознавание речи (offline)
- **spaCy + кастомный классификатор интентов** — определение команды
- **Silero TTS** — синтез русской речи
- **Навыки (skills)** — погода, радио, сказки, базовые команды

---

## 1. Подготовка системы

Обновите систему и установите системные зависимости. Они нужны для звука
(ALSA/PulseAudio), микрофона, потокового аудио (VLC/ffmpeg) и сборки
Python-пакетов.

```bash
sudo apt update && sudo apt upgrade -y

sudo apt install -y \
    python3-venv python3-pip python3-dev \
    libportaudio2 libatlas-base-dev libsndfile1 libatomic1 \
    vlc mpg123 ffmpeg \
    alsa-utils pulseaudio \
    git wget unzip
```

| Пакет | Зачем нужен |
|---|---|
| `python3-venv`, `python3-pip` | Виртуальное окружение и установка Python-пакетов |
| `libportaudio2` | Для `sounddevice` (запись/воспроизведение через PortAudio) |
| `libatlas-base-dev` | Численные операции для NumPy |
| `libsndfile1` | Чтение/запись аудиофайлов |
| `vlc`, `ffmpeg`, `mpg123` | Резервные плееры для стриминга |
| `alsa-utils`, `pulseaudio` | Управление звуком и микрофоном |

---

## 2. Получение проекта

```bash
cd /home/pi
git clone https://github.com/oeki4/graduation-project.git
cd graduation-project/core
```

Если проект скопирован вручную (через SCP/USB), просто перейдите
в директорию `core`.

---

## 3. Установка Python-зависимостей

```bash
cd /home/pi/graduation-project/core

# Создаём виртуальное окружение в core/.venv
python3 -m venv .venv
source .venv/bin/activate

pip install --upgrade pip wheel

# Установка зависимостей (5–15 минут на Pi 4 — будут собираться
# numpy, torch, spacy и др.)
pip install -r requirements.txt
```

> **Замечание:** `pycaw` и `comtypes` помечены как `platform_system == "Windows"`,
> на Raspberry Pi они автоматически пропускаются. Громкость на Pi управляется
> через `amixer`.

> **Совет:** На Raspberry Pi 4/5 `torch` установится готовым колесом;
> на Pi 3 (32-bit) сборка может занять до часа и потребовать swap-файла.

---

## 4. Установка моделей

### А. Модель распознавания речи (Vosk)

```bash
cd /home/pi/graduation-project/core
wget https://alphacephei.com/vosk/models/vosk-model-small-ru-0.22.zip
unzip vosk-model-small-ru-0.22.zip
mv vosk-model-small-ru-0.22 vosk-model
rm vosk-model-small-ru-0.22.zip
```

После этого внутри `core/vosk-model/` должны быть подкаталоги
`am`, `conf`, `graph`, `ivector`.

### Б. Языковая модель spaCy

Скачивается автоматически вместе с `requirements.txt` (через ссылку
в файле). Если по какой-то причине пропущена:

```bash
python -m spacy download ru_core_news_md
```

### В. Классификатор интентов (обучается локально)

```bash
cd /home/pi/graduation-project/core/nlp
python train_intent_classifier.py
```

Скрипт прочитает `fairytale.txt`, `weather.txt`, `radio.txt`, `other.txt`,
обучит модель и сохранит её в `core/nlp/models/intent_model/`.

Параметры обучения (внутри `train_intent_classifier.py`):
- `n_iter=40` — максимум эпох
- `patience=10` — ранняя остановка при отсутствии улучшения
- 80/20 train/validation split

Обучение на Pi 4 занимает ~5–10 минут.

После завершения вы увидите финальные метрики (точность по каждому
из четырёх интентов: `включить_сказку`, `узнать_погоду`,
`включить_радио`, `другой_интент`).

---

## 5. Настройка звука

### Проверьте устройства

```bash
# Список входов (микрофоны)
arecord -l

# Список выходов (динамики)
aplay -l
```

### Регулировка громкости

```bash
alsamixer
```

В `alsamixer` нажмите **F6** для выбора звуковой карты, затем стрелками
поднимите уровни **Master**, **Speaker** и **Capture** (микрофон).
Сохраните: `sudo alsactl store`.

### Проверка микрофона

```bash
arecord -d 5 -f cd test.wav && aplay test.wav
```

Должна записаться 5-секундная фраза и воспроизвестись.

---

## 6. Первый запуск

```bash
cd /home/pi/graduation-project/core
source .venv/bin/activate
python3 main.py
```

Если всё хорошо — услышите: «Системы активированы. Я готов к работе.»

В консоли так же доступен **режим разработки** — можно вводить команды
текстом. Голосовой ввод требует обращения по имени:
**«Ассистент, какая погода в Москве»**.

Прерывание: `Ctrl+C`.

---

## 7. Команды ассистента

### Голосовые/текстовые интенты (через NLP-модель)

| Интент | Примеры |
|---|---|
| **Сказка** | «включи сказку колобок», «расскажи про репку», «поставь аудиокнигу про животных» |
| **Погода** | «какая погода в Воронеже», «погода завтра в Москве», «прогноз на послезавтра» |
| **Радио** | «включи радио маяк», «поставь европу плюс», «давай радио» |
| **Таймер** | «таймер на 5 минут», «засеки 30 секунд», «разбуди через час», «отмени таймер» |
| **Прочее** | Любое другое — ассистент скажет, что не понял |

### Системные команды (точное совпадение, минуют NLP)

| Команда | Действие |
|---|---|
| `стоп`, `стой`, `остановись`, `замолчи`, `хватит` | Остановить текущее воспроизведение |
| `громче`, `прибавь`, `погромче` | Увеличить громкость на один шаг |
| `тише`, `убавь`, `потише` | Уменьшить громкость на один шаг |
| `громкость 50` / `громкость пятьдесят` | Установить точный уровень громкости 0–100 |
| `выключи радио`, `выключи сказку` | Остановить воспроизведение |
| `перезагрузи`, `ребут` | Перезагрузить Pi |
| `выключи`, `отключи питание` | Выключить Pi |

Громкость во время воспроизведения **не прерывает аудио** — управляется
через `amixer` параллельно.

---

## 8. Автозапуск через systemd

```bash
cd /home/pi/graduation-project/scripts/raspberry-pi
chmod +x install_autostart.sh
./install_autostart.sh
```

Скрипт пропишет правильные пути и зарегистрирует сервис
`voice-assistant.service`.

### Управление сервисом

```bash
# Просмотр логов в реальном времени
journalctl -u voice-assistant -f

# Перезапуск
sudo systemctl restart voice-assistant

# Остановка
sudo systemctl stop voice-assistant

# Отключение автозапуска
sudo systemctl disable voice-assistant

# Статус
sudo systemctl status voice-assistant
```

---

## 9. Структура проекта

```
graduation-project/
├── core/                         # Основной код ассистента
│   ├── main.py                   # Точка входа
│   ├── assistant.py              # Главный класс VoiceAssistant
│   ├── speech_recognizer.py      # Vosk-обёртка (микрофон → текст)
│   ├── intent_parser.py          # spaCy-обёртка (текст → интент)
│   ├── command_router.py         # Динамическая загрузка навыков
│   ├── tts_engine.py             # Silero TTS (текст → речь)
│   ├── requirements.txt          # Python-зависимости
│   ├── vosk-model/               # Модель распознавания (после п.4А)
│   ├── nlp/
│   │   ├── train_intent_classifier.py  # Обучение классификатора
│   │   ├── fairytale.txt         # Обучающие фразы (5 интентов × ~125 фраз)
│   │   ├── weather.txt
│   │   ├── radio.txt
│   │   ├── timer.txt
│   │   ├── other.txt
│   │   └── models/intent_model/  # Обученная модель (после п.4В)
│   └── skills/                   # Навыки-плагины
│       ├── audio_streamer.py     # HTTP-стриминг аудио
│       ├── radio.py              # Поиск радио через radio-browser.info
│       ├── fairytale.py          # Скрейпер mp3tales.info
│       ├── weather.py            # Запросы к wttr.in
│       ├── timer.py              # Таймер с обратным отсчётом
│       ├── mp3tales_scraper.py   # Парсер сайта со сказками
│       └── other.py              # Заглушка для другой_интент
└── scripts/raspberry-pi/         # systemd-сервис и установщик
    ├── voice-assistant.service
    └── install_autostart.sh
```

---

## 10. Решение проблем

### Микрофон не слышит
- `alsamixer` → поднимите уровень **Capture** (нажав «Space» включите запись)
- Проверьте `arecord -l` — там должно быть устройство
- Иногда USB-микрофон требует перезагрузки: `sudo reboot`

### Нет звука
- `alsamixer` → поднимите **Master** и **Speaker**, снимите Mute (клавиша «M»)
- Проверьте, что выход правильный: `sudo raspi-config` → Advanced → Audio

### `ModuleNotFoundError`
- Убедитесь, что активировано виртуальное окружение: `source .venv/bin/activate`
- Переустановите зависимости: `pip install -r requirements.txt`

### Радио не запускается / ошибки декодирования
- Проверьте интернет: `ping radio-browser.info`
- Установите системные кодеки: `sudo apt install -y libavcodec-extra`

### Модель интентов не найдена
- Запустите обучение: `cd core/nlp && python train_intent_classifier.py`
- Папка `core/nlp/models/intent_model/` должна появиться

### Логи systemd-сервиса
```bash
journalctl -u voice-assistant -n 100 --no-pager
```

---

## 11. Дополнительно

### Обновление кода

```bash
cd /home/pi/graduation-project
git pull
sudo systemctl restart voice-assistant
```

### Переобучение модели после правки `*.txt`

```bash
cd /home/pi/graduation-project/core/nlp
source ../.venv/bin/activate
python train_intent_classifier.py
sudo systemctl restart voice-assistant
```

### Имя ассистента

По умолчанию — **«Ассистент»**. Изменить можно в `core/main.py`,
параметр конструктора `VoiceAssistant(name="...")`.
