"""
Навык: поиск рецепта по запросу пользователя.

Источник данных: povarenok.ru (поиск через HTTP, без API-ключа).
Структура страницы рецепта использует Schema.org Recipe markup,
поэтому ингредиенты извлекаются регулярными выражениями стабильно.
"""

import re
import urllib.parse
import requests

_BASE_URL = "https://www.povarenok.ru"
_SEARCH_URL = f"{_BASE_URL}/recipes/search/"

_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                  "AppleWebKit/537.36 (KHTML, like Gecko) "
                  "Chrome/120.0.0.0 Safari/537.36",
    "Accept-Language": "ru,en;q=0.5",
}

# Стоп-слова — то, что НЕ является названием блюда
_STOP_WORDS = {
    # сама команда
    "найди", "найти", "ищу", "поищи", "поищем",
    "покажи", "показать", "дай", "дайте", "хочу", "нужен", "нужна",
    "поделись", "предложи", "посоветуй", "помоги", "выбрать",
    "расскажи", "узнать",
    # понятия рецепта
    "рецепт", "рецепта", "рецепты", "рецептом",
    "блюдо", "блюда", "блюдом", "что-нибудь", "что", "какой-нибудь",
    "приготовить", "приготовь", "сделать", "сделай",
    "испечь", "испеки", "испеку",
    # категории/типы (оставляем — могут быть запросом)
    # «суп», «салат» — НЕ стоп-слова
    # обороты
    "из", "на", "с", "со", "для", "к", "ко",
    "пожалуйста", "плиз",
    # местоимения
    "мне", "нам", "ты", "мы",
    # время приёма пищи (это, скорее, контекст)
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
    print(f"🍳 [РЕЦЕПТ] Запрос: '{text}' → ключ поиска: '{query or '(не задан)'}'")

    if not query:
        assistant.speak("Не поняла, какой рецепт найти. Уточните, пожалуйста.")
        return

    assistant.speak(f"Ищу рецепт {query}, одну секунду.")

    recipe = _search_recipe(query)
    if not recipe:
        assistant.speak(f"К сожалению, не удалось найти рецепт {query}.")
        return

    title = recipe["title"]
    ingredients = recipe["ingredients"]
    url = recipe["url"]

    print(f"   ✅ Найдено: {title}")
    print(f"   URL: {url}")
    print(f"   Ингредиенты ({len(ingredients)}): {', '.join(ingredients[:10])}")

    # Озвучиваем основные ингредиенты (не больше 8 — чтобы не утомлять)
    if ingredients:
        ing_short = ", ".join(ingredients[:8])
        spoken = (f"Нашла рецепт. {title}. "
                  f"Основные ингредиенты: {ing_short}. "
                  f"Полный рецепт смотрите на сайте поваренок ру.")
    else:
        spoken = (f"Нашла рецепт. {title}. "
                  f"Подробности смотрите на сайте поваренок ру.")

    assistant.speak(spoken)


# ------------------------------------------------------------------
# Извлечение названия блюда из текста запроса
# ------------------------------------------------------------------

def _extract_query(text: str) -> str:
    """
    Удаляет служебные слова и возвращает то, что предположительно —
    название блюда или ингредиент.

    Примеры:
      «найди рецепт борща»          → «борща»
      «как приготовить плов»        → «плов»
      «что приготовить из курицы»   → «курицы»
      «рецепт салата цезарь»        → «салата цезарь»
    """
    words = re.findall(r"[а-яёa-z][а-яёa-z-]+", text)
    significant = [w for w in words if w not in _STOP_WORDS]
    return " ".join(significant).strip()


# ------------------------------------------------------------------
# Скрейпер povarenok.ru
# ------------------------------------------------------------------

def _search_recipe(query: str) -> dict | None:
    """
    Ищет рецепт на povarenok.ru, открывает первый результат и возвращает:
        {
            "title":       "Борщ украинский",
            "ingredients": ["свёкла", "капуста", ...],
            "url":         "https://www.povarenok.ru/recipes/show/12345/",
        }
    Возвращает None при ошибке сети или если результатов нет.
    """
    # 1. Поиск
    try:
        params = {"name": query}
        print(f"🔍 [ПОВАРЁНОК] Поиск: {_SEARCH_URL}?name={urllib.parse.quote(query)}")
        response = requests.get(_SEARCH_URL, params=params,
                                headers=_HEADERS, timeout=10)
        response.raise_for_status()
    except requests.RequestException as e:
        print(f"❌ [ПОВАРЁНОК] Ошибка поиска: {e}")
        return None

    # 2. Извлекаем URL первого рецепта (паттерн /recipes/show/<id>/)
    match = re.search(r'href="(/recipes/show/\d+/[^"]*)"', response.text)
    if not match:
        print("⚠️  [ПОВАРЁНОК] В выдаче нет ни одного рецепта.")
        return None

    recipe_url = _BASE_URL + match.group(1)
    print(f"   → Открываю рецепт: {recipe_url}")

    # 3. Загружаем страницу рецепта
    try:
        page = requests.get(recipe_url, headers=_HEADERS, timeout=10)
        page.raise_for_status()
        html = page.text
    except requests.RequestException as e:
        print(f"❌ [ПОВАРЁНОК] Ошибка загрузки рецепта: {e}")
        return None

    # 4. Заголовок: <h1 itemprop="name">...</h1>
    title_match = re.search(
        r'<h1[^>]*itemprop="name"[^>]*>([^<]+)</h1>', html
    )
    title = title_match.group(1).strip() if title_match else query

    # 5. Ингредиенты: <span itemprop="recipeIngredient">...</span>
    # На povarenok.ru каждое поле часто имеет itemprop="recipeIngredient",
    # либо они оформлены ссылками внутри блока ингредиентов.
    ingredients = re.findall(
        r'itemprop="recipeIngredient"[^>]*>([^<]+)<',
        html,
    )
    if not ingredients:
        # Запасной паттерн — ссылки в блоке ингредиентов
        ingredients = re.findall(
            r'<a[^>]*class="[^"]*ingredient[^"]*"[^>]*>([^<]+)</a>',
            html,
        )

    # Чистим: лишние пробелы, дубликаты, пустые
    ingredients = [_clean(ing) for ing in ingredients]
    ingredients = [ing for ing in ingredients if ing]
    ingredients = list(dict.fromkeys(ingredients))  # убираем дубли с порядком

    return {
        "title": _clean(title),
        "ingredients": ingredients,
        "url": recipe_url,
    }


def _clean(s: str) -> str:
    """Снимает HTML-сущности и лишние пробелы."""
    s = s.replace("&nbsp;", " ").replace("&amp;", "&")
    s = s.replace("&laquo;", "«").replace("&raquo;", "»")
    s = s.replace("&mdash;", "—").replace("&ndash;", "–")
    return " ".join(s.split()).strip()
