"""
Навык: гороскоп на сегодня для знака зодиака.

Источник данных: https://dvorec.ru/zodiak/today.php?AIM=93
Сайт работает в кодировке Windows-1251, парсится regex'ом по HTML-маркерам.

Особенность реализации: длинный текст гороскопа разбивается на предложения
и воспроизводится с пайплайн-синтезом — пока проигрывается предложение N,
в фоне синтезируется N+1. Пользователь начинает слышать ответ через
~3 секунды (а не через 20+ секунд после полного синтеза).
"""

import os
import sys
import re
import time
import threading
from queue import Queue
import requests
import pymorphy3

sys.path.append(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
import logger

_morph = pymorphy3.MorphAnalyzer()

_URL = "https://dvorec.ru/zodiak/today.php?AIM=93"

_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                  "AppleWebKit/537.36 (KHTML, like Gecko) "
                  "Chrome/120.0.0.0 Safari/537.36",
    "Accept-Language": "ru,en;q=0.5",
}

# Знаки зодиака в порядке появления на сайте (pic/zo01.gif … pic/zo12.gif)
_ZODIAC_SIGNS = [
    "овен", "телец", "близнецы", "рак", "лев", "дева",
    "весы", "скорпион", "стрелец", "козерог", "водолей", "рыбы",
]

# Лемматизация pymorphy3 для знаков. Pymorphy3 нормализует множественные
# формы в единственные («близнецов» → «близнец»), поэтому маппим обратно.
_LEMMA_TO_SIGN = {
    "овен":      "овен",
    "телец":     "телец",
    "близнецы":  "близнецы",
    "близнец":   "близнецы",   # pymorphy plural→singular
    "рак":       "рак",
    "лев":       "лев",
    "дева":      "дева",
    "весы":      "весы",
    "вес":       "весы",       # pymorphy plural→singular (хотя у "вес" другое значение)
    "скорпион":  "скорпион",
    "стрелец":   "стрелец",
    "козерог":   "козерог",
    "водолей":   "водолей",
    "рыбы":      "рыбы",
    "рыба":      "рыбы",       # pymorphy plural→singular
}


def setup(router):
    """Регистрация интента."""
    router.register_route("узнать_гороскоп", _module_horoscope)


# ------------------------------------------------------------------
# Главный обработчик
# ------------------------------------------------------------------

def _module_horoscope(parsed_data, assistant):
    text = parsed_data.get("original_text", "").lower().strip()

    logger.step("♈", "Навык", "horoscope.py")
    sign = _extract_sign(text)

    if sign:
        logger.detail(f"знак: {sign}")
        intro = f"Гороскоп для знака {sign} на сегодня."
    else:
        logger.detail("знак не указан → общий гороскоп")
        intro = "Общий гороскоп на сегодня."

    # Загружаем HTML страницы (один раз)
    with logger.Timer("загрузка dvorec.ru"):
        html = _fetch_html()
    if not html:
        assistant.speak("Не удалось получить гороскоп. Проверьте подключение к интернету.")
        return

    # Извлекаем текст
    horoscope_text = _extract_text(html, sign)
    if not horoscope_text:
        assistant.speak("Не удалось извлечь текст гороскопа со страницы.")
        return

    logger.detail(f"длина текста: {len(horoscope_text)} символов")

    # Разбиваем на предложения и воспроизводим с пайплайн-синтезом
    sentences = [intro] + _split_sentences(horoscope_text)
    logger.detail(f"предложений для озвучки: {len(sentences)}")

    # Запускаем пайплайн в ФОНОВОМ потоке — иначе главный поток в start()
    # будет заблокирован на ~20+ секунд воспроизведения, и Vosk не сможет
    # сообщить о новых командах (включая «стой»). Радио и сказки уже
    # работают в фоне — приводим гороскоп к той же модели.
    threading.Thread(
        target=_play_pipelined,
        args=(sentences, assistant),
        daemon=True,
    ).start()


# ------------------------------------------------------------------
# Извлечение знака из текста запроса
# ------------------------------------------------------------------

def _extract_sign(text: str) -> str | None:
    """Ищет упоминание знака зодиака, использует pymorphy3 для лемматизации."""
    words = re.findall(r"[а-яё]+", text.lower())
    for w in words:
        # Сначала прямое совпадение
        if w in _LEMMA_TO_SIGN:
            return _LEMMA_TO_SIGN[w]
        # Иначе через лемматизатор
        try:
            lemma = _morph.parse(w)[0].normal_form
            if lemma in _LEMMA_TO_SIGN:
                return _LEMMA_TO_SIGN[lemma]
        except Exception:
            pass
    return None


# ------------------------------------------------------------------
# Скрейпер dvorec.ru
# ------------------------------------------------------------------

def _fetch_html() -> str | None:
    """Загружает страницу гороскопа. Сайт в кодировке windows-1251."""
    try:
        resp = requests.get(_URL, headers=_HEADERS, timeout=8)
        resp.raise_for_status()
        resp.encoding = "windows-1251"
        return resp.text
    except requests.RequestException as e:
        logger.err(f"Ошибка загрузки гороскопа: {e}")
        return None


def _extract_text(html: str, sign: str | None) -> str | None:
    """
    Извлекает текст гороскопа из HTML.
    Если sign задан — берёт блок для конкретного знака (pic/zoNN.gif).
    Если нет — берёт общий блок вверху страницы (pic/zodiak_pent.gif).
    """
    if sign is None:
        # Общий гороскоп: <img src="pic/zodiak_pent.gif"> ... <td width="*">TEXT</td>
        pattern = r'pic/zodiak_pent\.gif.*?<td\s+width="\*">(.*?)</td>'
    else:
        # Знаковый: <img src="pic/zoNN.gif"> ... <font class="a_left_main">…</font><br><br>TEXT<br><br></td>
        idx = _ZODIAC_SIGNS.index(sign) + 1
        marker = f"pic/zo{idx:02d}.gif"
        pattern = (
            re.escape(marker) +
            r'.*?<font[^>]*class="a_left_main"[^>]*>[^<]+</font>'
            r'<br><br>(.*?)<br><br>'
        )

    m = re.search(pattern, html, re.DOTALL)
    if not m:
        return None

    raw = m.group(1)
    # Снимаем оставшиеся HTML-теги и сущности
    text = re.sub(r"<[^>]+>", " ", raw)
    text = (text.replace("&nbsp;", " ")
                .replace("&amp;", "&")
                .replace("&laquo;", "«")
                .replace("&raquo;", "»")
                .replace("&mdash;", "—")
                .replace("&ndash;", "–"))
    text = " ".join(text.split())
    return text or None


# ------------------------------------------------------------------
# Разбиение на предложения
# ------------------------------------------------------------------

def _split_sentences(text: str) -> list[str]:
    """Разбивает текст на предложения по точке/восклицанию/знаку вопроса."""
    sentences = re.split(r"(?<=[.!?])\s+", text)
    return [s.strip() for s in sentences if s.strip()]


# ------------------------------------------------------------------
# Пайплайн-воспроизведение: синтез следующего параллельно с проигрыванием
# ------------------------------------------------------------------

def _play_pipelined(sentences: list[str], assistant):
    """
    Параллельный синтез + проигрывание:
      - producer-поток синтезирует фразы по одной и кладёт пути в очередь
      - main-поток забирает готовые WAV и проигрывает их в порядке поступления

    Пока проигрывается N (~3-5 сек), в фоне готовится N+1 (~2-4 сек на Pi).
    В результате пользователь слышит непрерывную речь без пауз между
    предложениями. Время до первого звука = время синтеза первого
    предложения (~2-3 сек), а не суммарное (которое было бы 20+ сек).

    Прерывание: пользователь может сказать «стой» или новую команду —
    assistant._stop_all_audio() выставит _tts_cancel_event, продьюсер
    и консумер прекратят работу, текущий aplay-процесс будет убит.
    """
    tts = assistant.tts
    cancel = assistant._tts_cancel_event
    cancel.clear()
    ready: Queue = Queue(maxsize=4)
    SENTINEL = object()

    # Регистрируем все предложения в истории TTS — это защищает от
    # «ассистент услышал свой же гороскоп в микрофоне и снова его запустил»
    for s in sentences:
        assistant._recent_tts_phrases.append(s.lower())

    # Между предложениями делаем паузу побольше: на Raspberry Pi с I²S
    # микрофоном собственная речь ассистента физически забивает мик
    # рядом с динамиком. Длинная пауза — единственное окно, где Vosk
    # получает чистый звук и может расслышать «стой».
    GAP_SEC = 1.2

    # Существенное снижение громкости — 40% от базовой. На Pi это
    # единственное программное средство уменьшить эхо TTS в микрофоне,
    # пока не подключена аппаратная AEC через PulseAudio.
    VOLUME_DUCK = 0.40

    def producer():
        for sentence in sentences:
            if cancel.is_set():
                break
            try:
                cache_file = tts.synthesize_to_cache(sentence)
                ready.put(cache_file)
            except Exception as e:
                logger.err(f"Сбой синтеза предложения: {e}")
        ready.put(SENTINEL)

    assistant._tts_pipeline_active = True
    try:
        threading.Thread(target=producer, daemon=True).start()

        first = True
        while True:
            if cancel.is_set():
                break
            item = ready.get()
            if item is SENTINEL:
                break
            if cancel.is_set():
                break

            # Пауза между предложениями (но не перед первым)
            if not first:
                # Дробим паузу на куски — проверяем cancel чаще
                for _ in range(int(GAP_SEC * 10)):
                    if cancel.is_set():
                        break
                    time.sleep(0.1)
                if cancel.is_set():
                    break
            first = False

            try:
                base_vol = (assistant._software_volume
                            if os.name == "posix" else 1.0)
                tts.play_cached(item, volume=base_vol * VOLUME_DUCK)
            except Exception as e:
                logger.err(f"Сбой воспроизведения: {e}")
    finally:
        assistant._tts_pipeline_active = False

    if cancel.is_set():
        logger.detail("гороскоп прерван пользователем")
