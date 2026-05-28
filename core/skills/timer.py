"""
Навык: таймер с обратным отсчётом и голосовым уведомлением.

Поддерживает:
  - постановку таймера на часы / минуты / секунды (любая комбинация)
  - и цифры, и числительные прописью («5 минут», «пять минут»)
  - несколько одновременно работающих таймеров
  - отмену всех таймеров одной командой

Реализовано на threading.Timer — таймер работает в фоне, по истечении
вызывает assistant.speak() с уведомлением.
"""

import os
import sys
import re
import threading

sys.path.append(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
import logger

# ------------------------------------------------------------------
# Глобальное состояние: список активных таймеров
# ------------------------------------------------------------------
_active_timers: list[threading.Timer] = []
_lock = threading.Lock()


# ------------------------------------------------------------------
# Числительные прописью → цифры (1–100)
# ------------------------------------------------------------------
_RU_NUMBERS = {
    "один": 1, "одна": 1, "одну": 1, "одно": 1,
    "два": 2, "две": 2, "двух": 2,
    "три": 3, "трёх": 3, "трех": 3,
    "четыре": 4, "четырёх": 4, "четырех": 4,
    "пять": 5, "пяти": 5,
    "шесть": 6, "шести": 6,
    "семь": 7, "семи": 7,
    "восемь": 8, "восьми": 8,
    "девять": 9, "девяти": 9,
    "десять": 10, "десяти": 10,
    "одиннадцать": 11, "двенадцать": 12, "тринадцать": 13,
    "четырнадцать": 14, "пятнадцать": 15, "шестнадцать": 16,
    "семнадцать": 17, "восемнадцать": 18, "девятнадцать": 19,
    "двадцать": 20, "тридцать": 30, "сорок": 40,
    "пятьдесят": 50, "шестьдесят": 60, "семьдесят": 70,
    "восемьдесят": 80, "девяносто": 90, "сто": 100,
    "полтора": 1.5, "полторы": 1.5,
}

# ------------------------------------------------------------------
# Цифры → слова (для озвучки)
# ------------------------------------------------------------------
_UNITS = ["", "один", "два", "три", "четыре",
          "пять", "шесть", "семь", "восемь", "девять"]
_TEENS = ["десять", "одиннадцать", "двенадцать", "тринадцать", "четырнадцать",
          "пятнадцать", "шестнадцать", "семнадцать", "восемнадцать", "девятнадцать"]
_TENS = ["", "", "двадцать", "тридцать", "сорок",
         "пятьдесят", "шестьдесят", "семьдесят", "восемьдесят", "девяносто"]


# ------------------------------------------------------------------
# Регистрация
# ------------------------------------------------------------------

def setup(router):
    router.register_route("поставить_таймер", _module_timer)


# ------------------------------------------------------------------
# Главный обработчик
# ------------------------------------------------------------------

def _module_timer(parsed_data, assistant):
    text = parsed_data.get("original_text", "").lower().strip()

    # ── Команда отмены: отмени / сбрось / останови / убери таймер ──
    cancel_words = ("отмени", "сбрось", "сбросить", "останови", "удали",
                    "выключи", "убери", "сними", "отключи")
    if any(w in text for w in cancel_words):
        _cancel_all_timers(assistant)
        return

    # ── Постановка таймера: парсим длительность ───────────────────
    seconds = _parse_duration(text)
    if seconds is None or seconds <= 0:
        assistant.speak("Не поняла, на сколько ставить таймер. "
                        "Скажите, например: таймер на пять минут.")
        return

    if seconds > 24 * 3600:
        assistant.speak("Слишком большой интервал. Максимум — двадцать четыре часа.")
        return

    _start_timer(seconds, assistant)


# ------------------------------------------------------------------
# Парсинг длительности
# ------------------------------------------------------------------

def _parse_duration(text: str) -> int | None:
    """
    Извлекает длительность из текста, возвращает количество секунд.

    Поддерживает:
      - «5 минут», «30 секунд», «2 часа»
      - «пять минут», «тридцать секунд»
      - комбинации: «1 час 30 минут»
      - синонимы: «секунда/секунд/секунды», «минута/минут/минуты», «час/часа/часов»
      - «через час» / «на час» — без числа = 1
    """
    total = 0
    found = False

    # Часы
    h = _extract_unit(text, r"час(?:а|ов|у)?")
    if h is not None:
        total += int(h * 3600)
        found = True

    # Минуты
    m = _extract_unit(text, r"минут[ауы]?")
    if m is not None:
        total += int(m * 60)
        found = True

    # Секунды
    s = _extract_unit(text, r"секунд[ауы]?")
    if s is not None:
        total += int(s)
        found = True

    return total if found else None


def _extract_unit(text: str, unit_pattern: str) -> float | None:
    """
    Ищет в тексте число (цифрами или прописью) перед заданной единицей.

    Возвращает значение или None если единица не найдена.
    Если единица есть, но числа нет — возвращает 1 («поставь таймер на час»).
    """
    # Цифры: ищем «<число> <единица>»
    m = re.search(rf"(\d+)\s*{unit_pattern}", text)
    if m:
        return float(m.group(1))

    # Слова: ищем «<числительное> <единица>», в т.ч. составные «двадцать пять минут»
    # Берём до двух слов перед единицей и складываем.
    m = re.search(rf"((?:[а-яё]+\s+){{0,2}})({unit_pattern})", text)
    if m:
        prefix = m.group(1).strip()
        words = prefix.split() if prefix else []
        value = sum(_RU_NUMBERS[w] for w in words if w in _RU_NUMBERS)
        if value > 0:
            return value
        # Единица без числа: «на час», «через минуту»
        if re.search(rf"\b{unit_pattern}\b", text):
            return 1.0

    return None


# ------------------------------------------------------------------
# Управление таймерами
# ------------------------------------------------------------------

def _start_timer(seconds: int, assistant):
    timer = None  # forward declaration для замыкания

    def _on_fire():
        with _lock:
            if timer in _active_timers:
                _active_timers.remove(timer)
        logger.system("ТАЙМЕР", f"⏰ сработал! ({seconds} сек)")
        # Останавливаем фоновое аудио (радио/сказку), чтобы уведомление
        # было хорошо слышно
        try:
            assistant.streamer.stop()
        except Exception:
            pass
        # Сначала проигрываем характерный звук таймера (мелодия будильника),
        # затем озвучиваем голосом — пользователь слышит звон даже если
        # сейчас не у ассистента
        timer_sound = os.path.join(
            os.path.dirname(os.path.abspath(__file__)),
            "..", "assets", "timer.mp3",
        )
        try:
            assistant._play_sound(timer_sound)
        except Exception as e:
            logger.warn(f"Не удалось проиграть звук таймера: {e}")
        assistant.speak("Время вышло. Таймер сработал.")

    timer = threading.Timer(seconds, _on_fire)
    timer.daemon = True
    timer.start()

    with _lock:
        _active_timers.append(timer)

    duration_spoken = _format_duration_spoken(seconds)
    logger.step("⏱️ ", "Навык", "timer.py")
    logger.detail(f"длительность: {seconds} сек ({duration_spoken})")
    logger.detail(f"всего активных таймеров: {len(_active_timers)}")
    assistant.speak(f"Поставила таймер на {duration_spoken}.")


def _cancel_all_timers(assistant):
    with _lock:
        active = list(_active_timers)
        _active_timers.clear()

    if not active:
        assistant.speak("Активных таймеров нет.")
        return

    for t in active:
        t.cancel()

    count = len(active)
    word = _form_timer(count)
    logger.step("🚫", "Навык", f"timer.py — отмена {count} таймер(а/ов)")
    if count == 1:
        assistant.speak("Таймер отменён.")
    else:
        assistant.speak(f"Отменила {_number_to_words(count)} {word}.")


# ------------------------------------------------------------------
# Утилиты для озвучки
# ------------------------------------------------------------------

def _format_duration_spoken(seconds: int) -> str:
    """Форматирует длительность для TTS: 90 → «одну минуту тридцать секунд»."""
    h = seconds // 3600
    m = (seconds % 3600) // 60
    s = seconds % 60

    parts = []
    if h > 0:
        parts.append(f"{_number_to_words(h, accusative=True)} {_form_hour(h)}")
    if m > 0:
        parts.append(f"{_number_to_words(m, accusative=True)} {_form_minute(m)}")
    if s > 0:
        parts.append(f"{_number_to_words(s, accusative=True)} {_form_second(s)}")
    return " ".join(parts) if parts else "ноль секунд"


def _number_to_words(n: int, accusative: bool = False) -> str:
    """
    Число 0–100 → слова. accusative=True даёт винительный падеж для
    единиц женского рода: «1 минуту» (а не «один минуту»).
    """
    if n == 0:
        return "ноль"
    if n == 1:
        return "одну" if accusative else "один"
    if n == 2:
        return "две" if accusative else "два"
    if n < 10:
        return _UNITS[n]
    if n < 20:
        return _TEENS[n - 10]
    if n == 100:
        return "сто"
    tens, units = divmod(n, 10)
    if units == 0:
        return _TENS[tens]
    return f"{_TENS[tens]} {_number_to_words(units, accusative)}"


def _form_hour(n: int) -> str:
    n = abs(n) % 100
    if 11 <= n <= 14:
        return "часов"
    last = n % 10
    if last == 1:
        return "час"
    if 2 <= last <= 4:
        return "часа"
    return "часов"


def _form_minute(n: int) -> str:
    n = abs(n) % 100
    if 11 <= n <= 14:
        return "минут"
    last = n % 10
    if last == 1:
        return "минуту"
    if 2 <= last <= 4:
        return "минуты"
    return "минут"


def _form_second(n: int) -> str:
    n = abs(n) % 100
    if 11 <= n <= 14:
        return "секунд"
    last = n % 10
    if last == 1:
        return "секунду"
    if 2 <= last <= 4:
        return "секунды"
    return "секунд"


def _form_timer(n: int) -> str:
    n = abs(n) % 100
    if 11 <= n <= 14:
        return "таймеров"
    last = n % 10
    if last == 1:
        return "таймер"
    if 2 <= last <= 4:
        return "таймера"
    return "таймеров"
