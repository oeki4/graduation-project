"""
Навык: поиск рецепта / информации о блюде.

Источник данных: Russian Wikipedia REST API.
Почему не povarenok.ru / eda.ru: они блокируют HTTP-запросы без браузера
(Cloudflare → 403). Wikipedia отдаёт стабильный JSON без ключа,
поддерживает русский язык и имеет статьи о подавляющем большинстве
популярных блюд (борщ, плов, оливье, пицца, лазанья и т. д.).

Wikipedia не даёт пошаговый рецепт — она даёт краткое описание блюда,
типичные ингредиенты и ссылку на полную статью. Для голосового
интерфейса это даже удобнее: длинные пошаговые инструкции на слух
воспринимаются плохо.
"""

import re
import urllib.parse
import requests

_WIKI_API   = "https://ru.wikipedia.org/w/api.php"
_WIKI_SUMM  = "https://ru.wikipedia.org/api/rest_v1/page/summary/"

_HEADERS = {
    "User-Agent": "VoiceAssistant/1.0 (graduation-project)",
    "Accept-Language": "ru,en;q=0.5",
}

# Стоп-слова — то, что НЕ является названием блюда
_STOP_WORDS = {
    # сама команда
    "найди", "найти", "ищу", "поищи", "поищем",
    "покажи", "показать", "дай", "дайте", "хочу", "нужен", "нужна",
    "поделись", "предложи", "посоветуй", "помоги", "выбрать",
    "расскажи", "узнать",
    # вопросительные слова
    "как", "какой", "какая", "какое", "какие",
    "что", "что-нибудь", "чего", "чему",
    # понятия рецепта
    "рецепт", "рецепта", "рецепты", "рецептом",
    "блюдо", "блюда", "блюдом", "какой-нибудь",
    "приготовить", "приготовь", "сделать", "сделай", "делать",
    "испечь", "испеки", "испеку",
    "можно", "будет",
    # обороты
    "из", "на", "с", "со", "для", "к", "ко", "и", "или",
    "пожалуйста", "плиз",
    # местоимения
    "мне", "нам", "ты", "мы", "его",
    # время приёма пищи (контекст, а не блюдо)
    "завтрак", "обед", "ужин",
}


def setup(router):
    """Регистрация интента поиска рецепта."""
    router.register_route("найти_рецепт", _module_recipe)


# ------------------------------------------------------------------
# Главный обработчик
# ------------------------------------------------------------------

def _module_recipe(parsed_data, assistant):
    text = parsed_data.get("original_text", "").lower().strip()

    query = _extract_query(text)
    print(f"🍳 [РЕЦЕПТ] Запрос: '{text}' → поиск: '{query or '(не задан)'}'")

    if not query:
        assistant.speak("Не поняла, какой рецепт найти. Уточните, пожалуйста.")
        return

    assistant.speak(f"Ищу информацию о {query}, одну секунду.")

    info = _search_wikipedia(query)
    if not info:
        assistant.speak(f"К сожалению, ничего не нашла по запросу {query}.")
        return

    title   = info["title"]
    extract = info["extract"]
    url     = info["url"]

    print(f"   ✅ Найдено: {title}")
    print(f"   URL: {url}")
    print(f"   Аннотация: {extract[:200]}{'...' if len(extract) > 200 else ''}")

    # Берём первые 2 предложения из аннотации — больше TTS не вытянет
    short = _first_sentences(extract, n=2)
    if not short:
        spoken = (f"Нашла статью {title}, но описание недоступно. "
                  f"Подробности на Википедии.")
    else:
        spoken = f"{title}. {short} Подробности на Википедии."

    assistant.speak(spoken)


# ------------------------------------------------------------------
# Извлечение названия блюда из текста запроса
# ------------------------------------------------------------------

def _extract_query(text: str) -> str:
    """
    Удаляет служебные слова и возвращает то, что предположительно —
    название блюда или ингредиент.

    Примеры:
      «как приготовить оливье»     → «оливье»
      «найди рецепт борща»         → «борща»
      «что приготовить из курицы»  → «курицы»
      «рецепт пиццы»               → «пиццы»
    """
    words = re.findall(r"[а-яёa-z][а-яёa-z-]+", text)
    significant = [w for w in words if w not in _STOP_WORDS]
    return " ".join(significant).strip()


# ------------------------------------------------------------------
# Wikipedia REST API
# ------------------------------------------------------------------

def _search_wikipedia(query: str) -> dict | None:
    """
    Ищет статью в русской Википедии.

    1. opensearch  — находит точное название статьи по запросу
                    (например: «борща» → «Борщ», «оливье» → «Оливье (салат)»)
    2. summary REST — возвращает краткую аннотацию найденной статьи

    Возвращает {"title", "extract", "url"} или None.
    """
    # ── 1. opensearch: ищем заголовок статьи ──────────────────────
    try:
        search_resp = requests.get(
            _WIKI_API,
            params={
                "action":    "opensearch",
                "search":    query,
                "limit":     5,           # берём топ-5 на случай неоднозначности
                "namespace": 0,
                "format":    "json",
            },
            headers=_HEADERS,
            timeout=8,
        )
        search_resp.raise_for_status()
        data = search_resp.json()
    except (requests.RequestException, ValueError) as e:
        print(f"❌ [WIKIPEDIA] Ошибка поиска: {e}")
        return None

    # opensearch возвращает массив [query, [titles], [descriptions], [urls]]
    if len(data) < 4 or not data[1]:
        print(f"⚠️  [WIKIPEDIA] По запросу '{query}' статей не найдено.")
        return None

    titles = data[1]
    urls   = data[3]

    # Берём первый результат, но если в нём есть disambiguation —
    # пробуем следующий
    chosen_title = titles[0]
    chosen_url   = urls[0]
    for t, u in zip(titles, urls):
        if "значения" not in t.lower():
            chosen_title, chosen_url = t, u
            break

    # ── 2. summary REST: получаем аннотацию ───────────────────────
    try:
        title_path = urllib.parse.quote(chosen_title.replace(" ", "_"))
        summ_resp = requests.get(
            _WIKI_SUMM + title_path,
            headers=_HEADERS,
            timeout=8,
        )
        summ_resp.raise_for_status()
        summ = summ_resp.json()
    except (requests.RequestException, ValueError) as e:
        print(f"❌ [WIKIPEDIA] Ошибка получения аннотации: {e}")
        return None

    extract = summ.get("extract", "").strip()
    if not extract:
        return None

    return {
        "title":   chosen_title,
        "extract": extract,
        "url":     chosen_url,
    }


# ------------------------------------------------------------------
# Утилиты
# ------------------------------------------------------------------

def _first_sentences(text: str, n: int = 2) -> str:
    """
    Возвращает первые n предложений текста.
    Учитывает русские особенности (точки в сокращениях не разделяют).
    """
    if not text:
        return ""
    # Убираем заголовки в скобках, навязчивые пометки
    text = re.sub(r"\s*\([^)]*\)", "", text)
    # Простое разделение по точке-восклицательному-вопросительному + пробел
    sentences = re.split(r"(?<=[.!?])\s+", text)
    return " ".join(sentences[:n]).strip()
