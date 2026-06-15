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


# ------------------------------------------------------------------
# Источники погоды
# ------------------------------------------------------------------
# Основной: OpenWeatherMap (надёжный, работает из РФ, описание на русском).
#   Требует бесплатный API-ключ. Задаётся через переменную окружения
#   OWM_API_KEY или прямо в _OWM_API_KEY ниже.
# Резервный: Open-Meteo (бесплатный, без ключа) — если OWM не настроен
#   или недоступен.
# ------------------------------------------------------------------

# Ключ OpenWeatherMap. Получить бесплатно: https://openweathermap.org/api
# Рекомендуется задавать через переменную окружения, а не хранить в коде:
#   export OWM_API_KEY="ваш_ключ"   (Linux)
#   $env:OWM_API_KEY="ваш_ключ"     (Windows PowerShell)
_OWM_API_KEY = os.environ.get("OWM_API_KEY", "")

_OWM_CURRENT_URL  = "https://api.openweathermap.org/data/2.5/weather"
_OWM_FORECAST_URL = "https://api.openweathermap.org/data/2.5/forecast"

# Резервный Open-Meteo
# Геокодинг: имя города → координаты
_GEOCODE_URL = "https://geocoding-api.open-meteo.com/v1/search"
# Прогноз: координаты → погода
_FORECAST_URL = "https://api.open-meteo.com/v1/forecast"

# WMO weather codes → русские описания
# https://open-meteo.com/en/docs (раздел Weather codes)
_WMO_CODES = {
    0:  "ясно",
    1:  "преимущественно ясно",
    2:  "переменная облачность",
    3:  "пасмурно",
    45: "туман",
    48: "изморозь",
    51: "слабая морось",
    53: "морось",
    55: "сильная морось",
    56: "слабая ледяная морось",
    57: "ледяная морось",
    61: "слабый дождь",
    63: "дождь",
    65: "сильный дождь",
    66: "слабый ледяной дождь",
    67: "ледяной дождь",
    71: "слабый снег",
    73: "снег",
    75: "сильный снег",
    77: "снежные зёрна",
    80: "слабый ливень",
    81: "ливень",
    82: "сильный ливень",
    85: "слабый снегопад",
    86: "сильный снегопад",
    95: "гроза",
    96: "гроза с градом",
    99: "сильная гроза с градом",
}


def _get_json(url: str, params: dict, attempts: int = 3, timeout: int = 8):
    """
    GET-запрос с несколькими попытками. Сетевые таймауты к Open-Meteo
    бывают перемежающимися (особенно на медленных каналах и при работе
    через Wi-Fi на Pi), поэтому одна неудача — не повод сдаваться.
    Возвращает разобранный JSON или пробрасывает последнее исключение.
    """
    last_exc = None
    for attempt in range(1, attempts + 1):
        try:
            resp = requests.get(
                url, params=params, timeout=timeout,
                headers={"User-Agent": "VoiceAssistant/1.0"},
            )
            resp.raise_for_status()
            return resp.json()
        except (requests.RequestException, ValueError) as e:
            last_exc = e
            if attempt < attempts:
                print(f"⚠️  [ПОГОДА] Попытка {attempt}/{attempts} не удалась: {e}")
    raise last_exc


def _fetch_weather(city: str, time_key: str = "сегодня") -> str | None:
    """
    Возвращает описание погоды для города на русском, удобное для TTS.

    Цепочка источников:
      1. OpenWeatherMap (если задан ключ) — основной, надёжный.
      2. Open-Meteo — резервный, бесключевой.
      3. wttr.in — последний фолбэк (только текущая погода).

    Возвращает строку вида «плюс 11 градусов, облачно».
    """
    day_offset, hour = _TIME_MAP.get(time_key, (0, None))

    if day_offset < 0:
        print("⚠️  [ПОГОДА] Данные о погоде в прошлом недоступны.")
        return "к сожалению, данные о погоде в прошлом недоступны"

    # ── Основной источник: OpenWeatherMap ─────────────────────────
    if _OWM_API_KEY:
        result = _fetch_weather_owm(city, day_offset, hour)
        if result:
            return result
        print("⚠️  [ПОГОДА] OpenWeatherMap не ответил — перехожу на Open-Meteo.")
    else:
        print("ℹ️  [ПОГОДА] Ключ OWM_API_KEY не задан — использую Open-Meteo.")

    # ── Резервный источник: Open-Meteo ────────────────────────────
    return _fetch_weather_open_meteo(city, day_offset, hour)


def _fetch_weather_owm(city: str, day_offset: int, hour) -> str | None:
    """
    Основной источник — OpenWeatherMap.

    Для текущей погоды используется endpoint /weather, для прогноза на
    завтра/послезавтра — /forecast (даёт точки с шагом 3 часа на 5 дней).
    OWM сразу отдаёт описание погоды на русском (lang=ru), поэтому
    словарь WMO-кодов здесь не нужен.
    """
    try:
        if day_offset == 0 and hour is None:
            # Текущая погода
            data = _get_json(_OWM_CURRENT_URL, {
                "q": city, "appid": _OWM_API_KEY,
                "units": "metric", "lang": "ru",
            })
            temp = data["main"]["temp"]
            desc = data["weather"][0]["description"]
        else:
            # Прогноз: список 3-часовых точек на 5 дней
            data = _get_json(_OWM_FORECAST_URL, {
                "q": city, "appid": _OWM_API_KEY,
                "units": "metric", "lang": "ru",
            })
            entries = data.get("list", [])
            if not entries:
                return None
            # Подбираем точку, ближайшую к нужному дню и часу.
            # Точки идут с шагом 3 часа; индекс ≈ день*8 + час/3.
            target_hour = 12 if hour is None else hour
            idx = day_offset * 8 + target_hour // 3
            idx = max(0, min(len(entries) - 1, idx))
            entry = entries[idx]
            temp = entry["main"]["temp"]
            desc = entry["weather"][0]["description"]

        temp = int(round(temp))
        return _format_weather(temp, desc)

    except (requests.RequestException, ValueError, KeyError, IndexError) as e:
        print(f"❌ [ПОГОДА] OpenWeatherMap: {e}")
        return None


def _fetch_weather_open_meteo(city: str, day_offset: int, hour) -> str | None:
    """Резервный источник погоды — Open-Meteo (без ключа)."""
    # ── 1. Геокодинг (с ретраями) ─────────────────────────────────
    try:
        geo_data = _get_json(
            _GEOCODE_URL,
            {"name": city, "count": 1, "language": "ru", "format": "json"},
        )
        results = geo_data.get("results")
        if not results:
            print(f"⚠️  [ПОГОДА] Город «{city}» не найден.")
            return None
        lat = results[0]["latitude"]
        lon = results[0]["longitude"]
        timezone = results[0].get("timezone", "auto")
    except (requests.RequestException, ValueError, KeyError) as e:
        print(f"❌ [ПОГОДА] Ошибка геокодинга: {e}")
        return None

    # ── 2. Прогноз (с ретраями) ───────────────────────────────────
    try:
        fc_data = _get_json(
            _FORECAST_URL,
            {
                "latitude":  lat,
                "longitude": lon,
                "timezone":  timezone,
                "current":   "temperature_2m,weather_code",
                "hourly":    "temperature_2m,weather_code",
                "forecast_days": 3,
            },
        )
    except (requests.RequestException, ValueError) as e:
        print(f"❌ [ПОГОДА] Ошибка прогноза: {e}")
        # Резервный источник — wttr.in (иногда доступен, когда Open-Meteo нет)
        fallback = _fetch_weather_wttr(city)
        if fallback:
            print("✅ [ПОГОДА] Получено через резервный источник wttr.in")
        return fallback

    # ── 3. Выбираем точку прогноза согласно time_key ──────────────
    try:
        if day_offset == 0 and hour is None:
            # Текущая погода
            cur = fc_data["current"]
            temp = cur["temperature_2m"]
            code = cur["weather_code"]
        else:
            # Почасовой прогноз: hourly[0] = час 0 первого дня,
            # hourly[24] = час 0 второго дня, и т. д.
            target_hour = 12 if hour is None else hour
            idx = day_offset * 24 + target_hour
            hourly = fc_data["hourly"]
            if idx >= len(hourly["time"]):
                return None
            temp = hourly["temperature_2m"][idx]
            code = hourly["weather_code"][idx]

        temp = int(round(temp))
        desc = _WMO_CODES.get(int(code), "неизвестная погода")

    except (KeyError, IndexError, TypeError) as e:
        print(f"❌ [ПОГОДА] Не удалось разобрать ответ: {e}")
        return None

    return _format_weather(temp, desc)


# ------------------------------------------------------------------
# Форматирование температуры и описания для TTS
# ------------------------------------------------------------------

def _format_weather(temp: int, desc: str) -> str:
    """
    Собирает озвучиваемую фразу из температуры и описания.
      (+11, «пасмурно») → «плюс одиннадцать градусов, пасмурно»
      (+1,  «ясно»)     → «плюс один градус, ясно»
      (-22, «снег»)     → «минус двадцать два градуса, снег»
    """
    temp_words = _number_to_words(temp)
    degrees = _degrees_form(temp)

    if temp > 0:
        temp_spoken = f"плюс {temp_words} {degrees}"
    elif temp < 0:
        temp_spoken = f"минус {temp_words} {degrees}"
    else:
        temp_spoken = "ноль градусов"

    desc = (desc or "").strip().lower()
    return f"{temp_spoken}, {desc}" if desc else temp_spoken


# ------------------------------------------------------------------
# Резервный источник: wttr.in (только текущая погода)
# ------------------------------------------------------------------

def _fetch_weather_wttr(city: str) -> str | None:
    """
    Запасной источник погоды на случай, если Open-Meteo недоступен.
    wttr.in отдаёт текущую погоду в компактном формате. Прогноз на
    будущие дни здесь не поддерживается — возвращаем только «сейчас».

    Формат j1 даёт JSON с current_condition: температура и код погоды.
    """
    try:
        data = _get_json(f"https://wttr.in/{city}", {"format": "j1"},
                         attempts=2, timeout=7)
        current = data.get("current_condition", [{}])[0]
        temp_str = current.get("temp_C")
        if temp_str is None:
            return None
        temp = int(round(float(temp_str)))

        # wttr.in отдаёт код погоды в weatherCode (WWO, не WMO) —
        # его описание есть прямо в ответе на русском при lang=ru,
        # но в j1 без lang оно на английском. Берём температуру и
        # обобщённое описание по облачности.
        desc = ""
        cloud = current.get("cloudcover")
        if cloud is not None:
            c = int(cloud)
            if c < 25:
                desc = "ясно"
            elif c < 60:
                desc = "переменная облачность"
            else:
                desc = "облачно"

        temp_words = _number_to_words(temp)
        degrees = _degrees_form(temp)
        if temp > 0:
            temp_spoken = f"плюс {temp_words} {degrees}"
        elif temp < 0:
            temp_spoken = f"минус {temp_words} {degrees}"
        else:
            temp_spoken = "ноль градусов"

        return f"{temp_spoken}, {desc}" if desc else temp_spoken

    except (requests.RequestException, ValueError, KeyError, IndexError) as e:
        print(f"❌ [ПОГОДА] Резервный источник wttr.in тоже недоступен: {e}")
        return None
