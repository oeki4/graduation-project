import os
import sys
import socket
import random
import requests

sys.path.append(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
import logger

# Резервный хардкод-список серверов radio-browser.info — на случай, если
# не удалось обнаружить серверы динамически (см. _discover_servers).
_FALLBACK_SERVERS = [
    "https://de1.api.radio-browser.info",
    "https://de2.api.radio-browser.info",
    "https://fi1.api.radio-browser.info",
]

# Кэш обнаруженных серверов (заполняется при первом запросе).
_DISCOVERED_SERVERS: list[str] = []

# ------------------------------------------------------------------
# Локальный фолбэк: прямые потоки популярных станций.
# Используется, когда radio-browser.info полностью недоступен
# (DNS-блокировки, отсутствие интернета у API, фаервол провайдера).
# Ключи — слова для нечёткого сопоставления с запросом пользователя.
# ------------------------------------------------------------------
_LOCAL_STATIONS = [
    (("европа", "плюс", "europa"),      "Европа Плюс",   "http://ep256.hostingradio.ru:8052/europaplus256.mp3"),
    (("дорожное", "дорога"),            "Дорожное радио", "http://dorognoe.hostingradio.ru:8000/radio"),
    (("русское",),                      "Русское Радио",  "http://rusradio.hostingradio.ru/rusradio128.mp3"),
    (("ретро", "retro"),                "Ретро FM",       "http://retroserver.streamr.ru:8043/retro256.mp3"),
    (("маяк",),                         "Радио Маяк",     "https://icecast-vgtrk.cdnvideo.ru/mayakfm"),
    (("энерджи", "energy", "энергия"),  "Радио ENERGY",   "http://ic7.101.ru:8000/v13_1"),
    (("шансон",),                       "Радио Шансон",   "http://chanson.hostingradio.ru:8041/chanson256.mp3"),
    (("вести", "fm"),                   "Вести ФМ",       "https://icecast-vgtrk.cdnvideo.ru/vestifm_mp3_192kbps"),
    (("юмор",),                         "Юмор ФМ",        "http://stream.radiojar.com/4ywdgup3bnzuv"),
    (("дача",),                         "Радио Дача",     "http://radiodacha.hostingradio.ru/radiodacha128.mp3"),
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

    logger.step("📻", "Навык", "radio.py")
    station_query = _extract_station_query(text)

    if station_query:
        logger.detail(f"ищу станцию: «{station_query}»")
        assistant.speak(f"Ищу {station_query}. Одну секунду.")
        with logger.Timer("поиск через radio-browser.info"):
            station = _search_station(station_query)
    else:
        logger.detail("станция не указана → беру популярное русское радио")
        assistant.speak("Включаю популярное радио.")
        with logger.Timer("поиск через radio-browser.info"):
            station = _search_station("", country_code="RU")

    # Фолбэк: если API недоступен, пробуем локальный список прямых потоков
    if not station:
        logger.warn("API недоступен — пробую локальный список станций")
        station = _find_local_station(station_query)
        if station:
            logger.ok(f"локальный фолбэк: {station['name']}")

    if not station:
        logger.err("станция не найдена")
        assistant.speak("Не удалось найти радиостанцию. Проверьте подключение к интернету.")
        return

    name = station["name"]
    url  = station["url_resolved"] or station["url"]
    codec   = station.get("codec", "")
    bitrate = station.get("bitrate", 0)

    logger.ok(f"найдена: {name.strip()}")
    logger.kv("URL", url, indent=5)
    logger.kv("формат", f"{codec}, {bitrate} кбит/с", indent=5)

    assistant.speak(f"Включаю {name}.")

    # Регистрируем клик (хорошая практика для radio-browser.info)
    _register_click(station.get("stationuuid", ""))

    if not assistant.streamer.play_stream(url):
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
# Динамическое обнаружение рабочих серверов radio-browser.info
# ------------------------------------------------------------------

def _discover_servers() -> list[str]:
    """
    Возвращает список актуальных серверов radio-browser.info.

    Официальный способ обнаружения: резолвим `all.api.radio-browser.info`,
    который через round-robin DNS отдаёт IP всех живых зеркал. Для каждого
    IP делаем обратный DNS-резолв, получая корректное имя сервера (нужно
    для SNI/TLS). Это надёжнее, чем хардкодить поддомены вроде nl1/at1,
    которые со временем удаляются из DNS.

    Результат кэшируется в _DISCOVERED_SERVERS на время работы программы.
    При неудаче возвращается резервный список _FALLBACK_SERVERS.
    """
    global _DISCOVERED_SERVERS
    if _DISCOVERED_SERVERS:
        return _DISCOVERED_SERVERS

    try:
        ips = socket.getaddrinfo("all.api.radio-browser.info", 443,
                                 type=socket.SOCK_STREAM)
        names = set()
        for entry in ips:
            addr = entry[4][0]
            try:
                host = socket.gethostbyaddr(addr)[0]
                names.add(f"https://{host}")
            except Exception:
                names.add(f"https://{addr}")  # хотя бы по IP

        if names:
            servers = list(names)
            random.shuffle(servers)
            _DISCOVERED_SERVERS = servers
            print(f"🌐 [РАДИО API] Обнаружено серверов: {len(servers)}")
            return servers
    except Exception as e:
        print(f"⚠️  [РАДИО API] Не удалось обнаружить серверы: {e}")

    return list(_FALLBACK_SERVERS)


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

    servers = _discover_servers()
    for server in servers[:4]:  # не более 4 попыток, чтобы не зависнуть надолго
        try:
            url = f"{server}/json/stations/search"
            print(f"🔍 [РАДИО API] Запрос: {url} | Параметры: {params}")

            response = requests.get(url, params=params, timeout=6,
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
# Локальный фолбэк — прямые потоки популярных станций
# ------------------------------------------------------------------

def _find_local_station(query: str) -> dict | None:
    """
    Подбирает станцию из локального списка по нечёткому совпадению.
    Используется, когда radio-browser.info недоступен.
    Возвращает словарь в том же формате, что и API, или None.
    """
    if not query:
        # Станция не указана — берём первую из списка (Европа Плюс)
        keywords, name, url = _LOCAL_STATIONS[0]
        return {"name": name, "url_resolved": url, "url": url,
                "codec": "MP3", "bitrate": 0, "stationuuid": ""}

    q = query.lower()
    for keywords, name, url in _LOCAL_STATIONS:
        if any(kw in q for kw in keywords):
            return {"name": name, "url_resolved": url, "url": url,
                    "codec": "MP3", "bitrate": 0, "stationuuid": ""}
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
        servers = _discover_servers()
        if not servers:
            return
        requests.get(
            f"{servers[0]}/json/url/{station_uuid}",
            timeout=3,
            headers={"User-Agent": "VoiceAssistant/1.0"},
        )
    except Exception:
        pass  # Телеметрия — некритична
