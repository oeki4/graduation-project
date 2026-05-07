import os
import sys
import requests

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from audio_streamer import AudioStreamer

# Серверы radio-browser.info API (используем по очереди при сбоях)
_API_SERVERS = [
    "https://de1.api.radio-browser.info",
    "https://nl1.api.radio-browser.info",
    "https://at1.api.radio-browser.info",
]

# Слова, которые нужно убрать из текста команды, чтобы получить название станции
_STRIP_WORDS = [
    "включи", "поставь", "запусти", "давай", "открой", "найди",
    "проиграй", "воспроизведи", "хочу", "можно", "нужно",
    "пожалуйста", "послушать", "слушать",
    "онлайн", "интернет", "прямой эфир", "эфир", "радиоэфир",
    "радиостанцию", "радиостанция", "станцию", "станция",
    "радио", "мне", "нам",
]


def setup(router):
    """Регистрация интента воспроизведения радио."""
    router.register_route("включить_радио", _module_radio)


# ------------------------------------------------------------------
# Главный обработчик
# ------------------------------------------------------------------

def _module_radio(parsed_data, assistant):
    """Принимает команду, ищет станцию через API и запускает стриминг."""
    text = parsed_data.get("original_text", "").lower().strip()

    station_query = _extract_station_query(text)

    if station_query:
        print(f"📻 [РАДИО] Ищу станцию: «{station_query}»")
        assistant.tts.speak(f"Ищу {station_query}. Одну секунду.")
        station = _search_station(station_query)
    else:
        # Пользователь сказал просто «включи радио» без уточнения —
        # ищем популярное русское радио
        print("📻 [РАДИО] Станция не указана — ищу популярное русское радио.")
        assistant.tts.speak("Включаю популярное радио.")
        station = _search_station("", country_code="RU")

    if not station:
        assistant.tts.speak("Не удалось найти радиостанцию. Проверьте подключение к интернету.")
        return

    name = station["name"]
    url  = station["url_resolved"] or station["url"]
    codec   = station.get("codec", "")
    bitrate = station.get("bitrate", 0)

    print(f"✅ [РАДИО] Найдена станция: {name}")
    print(f"   URL: {url}")
    print(f"   Формат: {codec}, {bitrate} кбит/с")

    assistant.tts.speak(f"Включаю {name}.")

    # Регистрируем клик (хорошая практика для radio-browser.info)
    _register_click(station.get("stationuuid", ""))

    streamer = AudioStreamer(assistant)
    if not streamer.play_url(url):
        assistant.tts.speak("Не удалось запустить радио. Попробуйте другую станцию.")


# ------------------------------------------------------------------
# Извлечение названия станции из текста команды
# ------------------------------------------------------------------

def _extract_station_query(text: str) -> str:
    """
    Убирает из текста команды служебные слова и возвращает
    предполагаемое название станции.

    Примеры:
      «включи европу плюс»  → «европу плюс»
      «поставь маяк»        → «маяк»
      «включи радио»        → «» (станция не указана)
    """
    result = text
    # Удаляем составные фразы первыми, чтобы не оставить обрывков
    for word in sorted(_STRIP_WORDS, key=len, reverse=True):
        result = result.replace(word, " ")

    # Убираем лишние пробелы и знаки препинания
    result = " ".join(result.split()).strip(".,!?")
    return result


# ------------------------------------------------------------------
# Поиск станции через radio-browser.info REST API
# ------------------------------------------------------------------

def _search_station(query: str, country_code: str = "", limit: int = 5) -> dict | None:
    """
    Ищет радиостанцию по названию через radio-browser.info API.
    Возвращает словарь с данными первой найденной станции или None.

    Параметры запроса:
      name        — поисковый запрос
      countrycode — ограничение по стране (необязательно)
      limit       — максимальное число результатов
      order       — сортировка по clickcount (популярность)
      reverse     — по убыванию
      hidebroken  — скрыть недоступные станции
    """
    params = {
        "limit":      limit,
        "order":      "clickcount",
        "reverse":    "true",
        "hidebroken": "true",
    }
    if query:
        params["name"] = query
    if country_code:
        params["countrycode"] = country_code

    for server in _API_SERVERS:
        try:
            url = f"{server}/json/stations/search"
            print(f"🔍 [РАДИО API] Запрос: {url} | Параметры: {params}")

            response = requests.get(url, params=params, timeout=8,
                                    headers={"User-Agent": "VoiceAssistant/1.0"})
            response.raise_for_status()

            stations = response.json()
            if not stations:
                print(f"⚠️  [РАДИО API] Станций по запросу «{query}» не найдено.")
                return None

            # Берём первую станцию с непустым url_resolved
            for s in stations:
                if s.get("url_resolved") or s.get("url"):
                    return s

            return None

        except requests.RequestException as e:
            print(f"⚠️  [РАДИО API] Сервер {server} недоступен: {e}. Пробую следующий...")

    print("❌ [РАДИО API] Все серверы radio-browser.info недоступны.")
    return None


# ------------------------------------------------------------------
# Регистрация клика (телеметрия radio-browser.info)
# ------------------------------------------------------------------

def _register_click(station_uuid: str):
    """
    Отправляет уведомление о воспроизведении станции на radio-browser.info.
    Это помогает сервису отслеживать популярность станций.
    Выполняется в «тихом» режиме — ошибки не прерывают воспроизведение.
    """
    if not station_uuid:
        return
    try:
        server = _API_SERVERS[0]
        requests.get(
            f"{server}/json/url/{station_uuid}",
            timeout=3,
            headers={"User-Agent": "VoiceAssistant/1.0"},
        )
    except Exception:
        pass  # Телеметрия — некритична
