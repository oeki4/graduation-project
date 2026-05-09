import re
import requests
import pymorphy3

# Лемматизатор инициализируем один раз — это тяжёлый объект (~50 МБ словарей)
_morph = pymorphy3.MorphAnalyzer()

# Стоп-слова: команды, служебные части речи, всё что точно НЕ город
_STOP_WORDS = {
    # сама команда
    "погода", "погоду", "погоды", "погодка", "погодку", "прогноз", "прогнозу", "прогноза",
    # вопросительные/командные глаголы
    "какая", "какой", "какое", "какие", "будет", "будут",
    "узнать", "узнай", "скажи", "расскажи", "хочу", "знать",
    # предлоги/частицы
    "в", "во", "на", "о", "об", "про", "за", "под",
    # вежливость
    "пожалуйста", "плиз", "плз",
}

# Временные маркеры → нормализованное значение
_TIME_KEYWORDS = {
    "сейчас":      "сейчас",
    "сегодня":     "сегодня",
    "завтра":      "завтра",
    "послезавтра": "послезавтра",
    "вечером":     "вечером",
    "утром":       "утром",
    "днём":        "днём",
    "днем":        "днём",
    "ночью":       "ночью",
}


def setup(router):
    """Регистрация интента прогноза погоды."""
    router.register_route("узнать_погоду", _module_weather)


# ------------------------------------------------------------------
# Главный обработчик
# ------------------------------------------------------------------

def _module_weather(parsed_data, assistant):
    text = parsed_data.get("original_text", "").lower().strip()

    target_time = _extract_time(text)
    target_city = _extract_city(text)

    print(f"🌤️  [МОДУЛЬ ПОГОДЫ] Время: {target_time} | Город: {target_city or '(не указан)'}")
    print(f"   [ОРИГИНАЛ]: {text}")

    if not target_city:
        assistant.speak("Не понял, для какого города узнать погоду. Уточните, пожалуйста.")
        return

    weather = _fetch_weather(target_city)
    if not weather:
        assistant.speak(f"Не удалось получить погоду для города {target_city}.")
        return

    spoken = f"Погода в городе {target_city} {target_time}: {weather}"
    print(f"   ✅ {spoken}")
    assistant.speak(spoken)


# ------------------------------------------------------------------
# Извлечение времени
# ------------------------------------------------------------------

def _extract_time(text: str) -> str:
    """Ищет временной маркер в тексте, по умолчанию — «сегодня»."""
    for keyword, normalized in _TIME_KEYWORDS.items():
        if re.search(rf"\b{keyword}\b", text):
            return normalized
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
    excluded = _STOP_WORDS | set(_TIME_KEYWORDS.keys())

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

def _fetch_weather(city: str) -> str | None:
    """
    Возвращает описание погоды для города на русском, удобное для TTS.
    Использует JSON API wttr.in (format=j1) — там есть поле lang_ru
    с переводом погодных условий, в отличие от текстового %C.

    Возвращает строку вида «плюс 11 градусов, облачно».
    """
    try:
        response = requests.get(
            f"https://wttr.in/{city}",
            params={"format": "j1", "lang": "ru"},
            timeout=6,
            headers={"User-Agent": "VoiceAssistant/1.0"},
        )
        response.raise_for_status()
        data = response.json()
        current = data.get("current_condition", [{}])[0]

        # Температура в Цельсиях
        temp_str = current.get("temp_C", "")
        if not temp_str:
            return None
        temp = int(temp_str)

        # Описание на русском (lang_ru заполняется при ?lang=ru)
        desc = ""
        if current.get("lang_ru"):
            desc = current["lang_ru"][0].get("value", "")
        if not desc:
            # Фоллбэк на английский, если перевода вдруг нет
            desc = current.get("weatherDesc", [{}])[0].get("value", "")

        # Преобразуем в форму, удобную для TTS:
        # «+11°C, Облачно» → «плюс 11 градусов, облачно»
        if temp > 0:
            temp_spoken = f"плюс {temp} градусов"
        elif temp < 0:
            temp_spoken = f"минус {abs(temp)} градусов"
        else:
            temp_spoken = "ноль градусов"

        return f"{temp_spoken}, {desc.lower()}"

    except requests.RequestException as e:
        print(f"❌ [ПОГОДА] Ошибка запроса к wttr.in: {e}")
        return None
    except (ValueError, KeyError, IndexError) as e:
        print(f"❌ [ПОГОДА] Не удалось разобрать ответ: {e}")
        return None
