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
    Извлекает название города.

    Стратегия:
      1. Если в тексте есть «в|во|на <слово>» — берём это слово.
      2. Иначе — последнее «значимое» слово (не из стоп-листа).
      3. Лемматизируем результат через pymorphy3:
         «воронеже» → «воронеж», «москве» → «москва».
    """
    # Все слова и временные маркеры исключаем из кандидатов
    excluded = _STOP_WORDS | set(_TIME_KEYWORDS.keys())

    # 1. Паттерн «в|во|на <город>»
    m = re.search(r"\b(?:в|во|на)\s+([а-яё][а-яё-]+)", text)
    if m:
        candidate = m.group(1)
        if candidate not in excluded:
            return _normalize(candidate)

    # 2. Последнее значимое слово
    words = re.findall(r"[а-яё][а-яё-]+", text)
    candidates = [w for w in words if w not in excluded]
    if candidates:
        return _normalize(candidates[-1])

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
    Возвращает короткое описание погоды для города.
    wttr.in поддерживает русские города и понимает кириллицу.
    Формат: «температура, описание» (например, «+9°C, облачно»).
    """
    try:
        # %t — температура, %C — текстовое описание (sky condition)
        response = requests.get(
            f"https://wttr.in/{city}",
            params={"format": "%t, %C", "lang": "ru", "M": ""},
            timeout=6,
            headers={"User-Agent": "VoiceAssistant/1.0"},
        )
        response.raise_for_status()
        text = response.text.strip()
        # Ответ wttr.in для несуществующего города содержит «Unknown location»
        if "unknown" in text.lower() or len(text) > 80:
            return None
        return text
    except requests.RequestException as e:
        print(f"❌ [ПОГОДА] Ошибка запроса к wttr.in: {e}")
        return None
