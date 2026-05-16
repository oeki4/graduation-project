import os
import sys
import re
import requests
import pymorphy3

sys.path.append(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
import logger

# Лемматизатор инициализируем один раз — это тяжёлый объект (~50 МБ словарей)
_morph = pymorphy3.MorphAnalyzer()

# Стоп-слова: команды, служебные части речи, всё что точно НЕ город
_STOP_WORDS = {
    # сама команда
    "погода", "погоду", "погоды", "погодка", "погодку", "прогноз", "прогнозу", "прогноза",
    # вопросительные/командные глаголы
    "какая", "какой", "какое", "какие", "будет", "будут",
    "была", "был", "было", "были",
    "узнать", "узнай", "скажи", "расскажи", "хочу", "знать",
    # «городе/город» — часто вставляют «погода в городе москва»
    "город", "городе", "города", "городу",
    # предлоги/частицы
    "в", "во", "на", "о", "об", "про", "за", "под",
    # вежливость
    "пожалуйста", "плиз", "плз",
}

# Временные маркеры → (смещение дня, час дня или None для текущей)
# Поддерживаются: сегодня (0), завтра (1), послезавтра (2).
# Вчера/прошлое не поддерживается (wttr.in исторических данных не отдаёт).
_TIME_MAP = {
    "сейчас":      (0, None),
    "сегодня":     (0, None),
    "завтра":      (1, 12),   # полдень завтра
    "послезавтра": (2, 12),
    "вчера":       (-1, None),
    "утром":       (0, 6),
    "днём":        (0, 12),
    "днем":        (0, 12),
    "вечером":     (0, 18),
    "ночью":       (0, 0),
}

_TIME_KEYWORDS = set(_TIME_MAP.keys())


def setup(router):
    """Регистрация интента прогноза погоды."""
    router.register_route("узнать_погоду", _module_weather)


# ------------------------------------------------------------------
# Главный обработчик
# ------------------------------------------------------------------

def _module_weather(parsed_data, assistant):
    text = parsed_data.get("original_text", "").lower().strip()

    logger.step("🌤️ ", "Навык", "weather.py")
    target_time = _extract_time(text)
    target_city = _extract_city(text)

    logger.detail(f"извлечено время: {target_time}")
    logger.detail(f"извлечён город: {target_city or '(не указан)'}")

    if not target_city:
        assistant.speak("Не понял, для какого города узнать погоду. Уточните, пожалуйста.")
        return

    logger.step("🌐", "HTTP-запрос к wttr.in", target_city)
    with logger.Timer("ответ wttr.in"):
        weather = _fetch_weather(target_city, target_time)

    if not weather:
        logger.err("Не удалось получить погоду")
        assistant.speak(f"Не удалось получить погоду для города {target_city}.")
        return

    logger.ok(f"получено: {weather}")
    spoken = f"Погода в городе {target_city} {target_time}: {weather}"
    assistant.speak(spoken)


# ------------------------------------------------------------------
# Извлечение времени
# ------------------------------------------------------------------

def _extract_time(text: str) -> str:
    """Ищет временной маркер в тексте, по умолчанию — «сегодня»."""
    for keyword in _TIME_KEYWORDS:
        if re.search(rf"\b{keyword}\b", text):
            return keyword
    return "сегодня"


# ------------------------------------------------------------------
# Извлечение города
# ------------------------------------------------------------------

def _extract_city(text: str) -> str | None:
    """
    Извлекает название города (поддерживает многословные: «нижний новгород»,
    «санкт-петербург», «ростов на дону»).

    Стратегия:
      1. Паттерн «в|во|на <слово1> [<слово2> [<слово3>]]» — берём до 3 слов.
      2. Иначе — все «значимые» слова (не из стоп-листа), сохраняя порядок.
      3. Каждое слово лемматизируем через pymorphy3:
         «нижнем новгороде» → «нижний новгород»,
         «санкт-петербурге» → «санкт-петербург».
    """
    excluded = _STOP_WORDS | _TIME_KEYWORDS

    # 1. Паттерн «в|во|на <город из 1–3 слов>»
    m = re.search(
        r"\b(?:в|во|на)\s+"
        r"([а-яё][а-яё-]+(?:\s+[а-яё][а-яё-]+){0,2})",
        text,
    )
    if m:
        words = [w for w in m.group(1).split() if w not in excluded]
        if words:
            return " ".join(_normalize(w) for w in words)

    # 2. Все слова (кроме стоп-листа) — собираем многословный город
    words = re.findall(r"[а-яё][а-яё-]+", text)
    candidates = [w for w in words if w not in excluded]
    if candidates:
        return " ".join(_normalize(w) for w in candidates)

    return None


def _normalize(word: str) -> str:
    """Приводит слово к именительному падежу через pymorphy3."""
    try:
        parsed = _morph.parse(word)
        if parsed:
            return parsed[0].normal_form
    except Exception:
        pass
    return word


# ------------------------------------------------------------------
# Запрос погоды через wttr.in (без API-ключа)
# ------------------------------------------------------------------

# Числительные для конвертации температуры в слова (TTS не читает цифры)
_UNITS = ["", "один", "два", "три", "четыре",
          "пять", "шесть", "семь", "восемь", "девять"]
_TEENS = ["десять", "одиннадцать", "двенадцать", "тринадцать", "четырнадцать",
          "пятнадцать", "шестнадцать", "семнадцать", "восемнадцать", "девятнадцать"]
_TENS = ["", "", "двадцать", "тридцать", "сорок",
         "пятьдесят", "шестьдесят", "семьдесят", "восемьдесят", "девяносто"]


def _number_to_words(n: int) -> str:
    """Переводит число 0–99 в слова на русском."""
    n = abs(n)
    if n == 0:
        return "ноль"
    if n < 10:
        return _UNITS[n]
    if 10 <= n < 20:
        return _TEENS[n - 10]
    tens, units = divmod(n, 10)
    if units == 0:
        return _TENS[tens]
    return f"{_TENS[tens]} {_UNITS[units]}"


def _degrees_form(n: int) -> str:
    """Правильная форма слова «градус» для числа: 1 градус, 2 градуса, 5 градусов."""
    n = abs(n)
    # 11–14 — всегда «градусов»
    if 11 <= n % 100 <= 14:
        return "градусов"
    last = n % 10
    if last == 1:
        return "градус"
    if 2 <= last <= 4:
        return "градуса"
    return "градусов"


def _fetch_weather(city: str, time_key: str = "сегодня") -> str | None:
    """
    Возвращает описание погоды для города на русском, удобное для TTS.
    Использует JSON API wttr.in (format=j1):
      - current_condition  — текущая погода
      - weather[0..2]      — прогноз на сегодня/завтра/послезавтра
                              с почасовой разбивкой (8 точек по 3 часа)

    Возвращает строку вида «плюс 11 градусов, облачно».
    """
    day_offset, hour = _TIME_MAP.get(time_key, (0, None))

    # wttr.in не отдаёт исторических данных — на «вчера» отвечаем явно
    if day_offset < 0:
        print("⚠️  [ПОГОДА] wttr.in не предоставляет данные за прошлое.")
        return "к сожалению, данные о погоде в прошлом недоступны"

    try:
        response = requests.get(
            f"https://wttr.in/{city}",
            params={"format": "j1", "lang": "ru"},
            timeout=6,
            headers={"User-Agent": "VoiceAssistant/1.0"},
        )
        response.raise_for_status()
        data = response.json()

        # Выбираем источник: текущая погода или почасовой прогноз
        if day_offset == 0 and hour is None:
            condition = data.get("current_condition", [{}])[0]
        else:
            forecast_days = data.get("weather", [])
            if day_offset >= len(forecast_days):
                return None
            day_data = forecast_days[day_offset]
            hourly = day_data.get("hourly", [])
            if not hourly:
                return None
            # Почасовка идёт шагом 3 часа: hourly[0]=00:00, [4]=12:00, [6]=18:00
            target_hour = 12 if hour is None else hour
            idx = max(0, min(len(hourly) - 1, target_hour // 3))
            condition = hourly[idx]

        # Температура: в current_condition поле «temp_C», в hourly — «tempC»
        temp_str = condition.get("temp_C") or condition.get("tempC")
        if not temp_str:
            return None
        temp = int(temp_str)

        # Описание на русском (lang_ru заполняется при ?lang=ru)
        desc = ""
        if condition.get("lang_ru"):
            desc = condition["lang_ru"][0].get("value", "")
        if not desc:
            # Фоллбэк на английский, если перевода вдруг нет
            desc = condition.get("weatherDesc", [{}])[0].get("value", "")

        # Преобразуем в форму, удобную для TTS (число прописью + правильное окончание):
        # «+11°C, Облачно» → «плюс одиннадцать градусов, облачно»
        # «+1°C» → «плюс один градус»
        # «-22°C» → «минус двадцать два градуса»
        temp_words = _number_to_words(temp)
        degrees = _degrees_form(temp)

        if temp > 0:
            temp_spoken = f"плюс {temp_words} {degrees}"
        elif temp < 0:
            temp_spoken = f"минус {temp_words} {degrees}"
        else:
            temp_spoken = "ноль градусов"

        return f"{temp_spoken}, {desc.lower()}"

    except requests.RequestException as e:
        print(f"❌ [ПОГОДА] Ошибка запроса к wttr.in: {e}")
        return None
    except (ValueError, KeyError, IndexError) as e:
        print(f"❌ [ПОГОДА] Не удалось разобрать ответ: {e}")
        return None
