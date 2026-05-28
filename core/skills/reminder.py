"""
Навык: голосовые напоминания с текстом.

Принимает фразы вида:
  «напомни через 5 минут полить цветы»
  «через час напомни выпить таблетку»
  «напомни в 18:30 позвонить маме»
  «разбуди меня через 30 минут»

Отличие от таймера: напоминание хранит текст и произносит его при
срабатывании («Напоминание: полить цветы»), плюс играет звуковой сигнал.

Поддерживает:
  - относительное время («через 5 минут», «через час»)
  - абсолютное время («в 18:30», «в полдень», «в 8 утра»)
  - произвольный текст после времени
  - отмену всех напоминаний
  - вывод списка активных напоминаний
"""

import os
import re
import sys
import threading
from datetime import datetime, timedelta

sys.path.append(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
import logger

# ------------------------------------------------------------------
# Глобальное состояние
# ------------------------------------------------------------------
# Каждое напоминание: {"timer": Timer, "text": str, "fire_at": datetime}
_active_reminders: list[dict] = []
_lock = threading.Lock()


# ------------------------------------------------------------------
# Числительные (копия из timer.py для независимости навыка)
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
    "полтора": 1.5, "полторы": 1.5, "полчаса": 0.5,
}

_UNITS = ["", "один", "два", "три", "четыре",
          "пять", "шесть", "семь", "восемь", "девять"]
_TEENS = ["десять", "одиннадцать", "двенадцать", "тринадцать", "четырнадцать",
          "пятнадцать", "шестнадцать", "семнадцать", "восемнадцать", "девятнадцать"]
_TENS = ["", "", "двадцать", "тридцать", "сорок",
         "пятьдесят", "шестьдесят", "семьдесят", "восемьдесят", "девяносто"]

# Слова, которые надо убрать при извлечении текста напоминания
_FILLER_VERBS = {
    "напомни", "напомнить", "напоминание", "напомните", "напоминай",
    "поставь", "поставить", "сделай", "запиши", "запомни",
    "разбуди", "разбудить", "будильник",
}
_FILLER_PRONOUNS = {
    "мне", "нам", "меня", "нас", "ты", "вы",
}
_FILLER_PARTICLES = {
    "пожалуйста", "плиз", "плз", "что", "чтобы",
}
_TIME_WORDS = {
    "через", "в", "во", "к", "ко", "на", "о", "об",
    "сегодня", "завтра", "сейчас", "утра", "вечера", "дня", "ночи",
    "час", "часа", "часов", "часик",
    "минута", "минуту", "минуты", "минут", "минутка",
    "секунда", "секунду", "секунды", "секунд",
}


def setup(router):
    """Регистрация интента напоминаний."""
    router.register_route("поставить_напоминание", _module_reminder)


# ------------------------------------------------------------------
# Главный обработчик
# ------------------------------------------------------------------

def _module_reminder(parsed_data, assistant):
    text = parsed_data.get("original_text", "").lower().strip()
    logger.step("⏰", "Навык", "reminder.py")

    # ── Команды управления ─────────────────────────────────────────
    if _is_cancel_command(text):
        _cancel_all_reminders(assistant)
        return

    if _is_list_command(text):
        _list_reminders(assistant)
        return

    # ── Парсим время и текст ───────────────────────────────────────
    seconds, reminder_text = _parse_reminder(text)

    if seconds is None or seconds <= 0:
        assistant.speak(
            "Не поняла, на когда поставить напоминание. "
            "Скажите, например: напомни через пять минут выпить чай."
        )
        return

    if seconds > 24 * 3600:
        assistant.speak("Слишком большой интервал. Максимум — двадцать четыре часа.")
        return

    _start_reminder(seconds, reminder_text, assistant)


# ------------------------------------------------------------------
# Распознавание команд управления
# ------------------------------------------------------------------

def _is_cancel_command(text: str) -> bool:
    cancel = ("отмени", "сбрось", "сбросить", "удали", "удалить",
              "очисти", "очистить", "убери", "сними", "выключи", "отключи")
    must_mention = "напомин"  # «напоминание», «напоминания»
    if must_mention not in text:
        return False
    return any(w in text for w in cancel)


def _is_list_command(text: str) -> bool:
    if "напомин" not in text:
        return False
    triggers = ("покажи", "список", "какие", "что у меня", "сколько",
                "есть ли", "проверь")
    return any(t in text for t in triggers)


# ------------------------------------------------------------------
# Парсинг: извлечение времени и текста
# ------------------------------------------------------------------

def _parse_reminder(text: str) -> tuple[int | None, str]:
    """
    Возвращает (seconds, reminder_text).
    Сначала пробуем абсолютное время («в 18:30», «в полдень»),
    потом относительное («через 5 минут»).
    """
    # 1. Абсолютное «в HH:MM»
    m = re.search(r"\bв\s+(\d{1,2}):(\d{2})\b", text)
    if m:
        h, mn = int(m.group(1)), int(m.group(2))
        if 0 <= h < 24 and 0 <= mn < 60:
            seconds = _seconds_until(h, mn)
            cleaned = text[:m.start()] + " " + text[m.end():]
            return seconds, _extract_reminder_text(cleaned)

    # 2. Абсолютное «в полдень» / «в полночь»
    if re.search(r"\bв\s+полдень\b", text):
        return _seconds_until(12, 0), _extract_reminder_text(
            re.sub(r"\bв\s+полдень\b", "", text)
        )
    if re.search(r"\bв\s+полночь\b", text):
        return _seconds_until(0, 0), _extract_reminder_text(
            re.sub(r"\bв\s+полночь\b", "", text)
        )

    # 3. Абсолютное «в N часов [утра|вечера]»
    m = re.search(r"\bв\s+(\d{1,2})\s*(?:час[ау]?|часов)?\s*(утра|вечера|дня|ночи)?\b", text)
    if m:
        h = int(m.group(1))
        period = m.group(2)
        if period == "вечера" and h < 12:
            h += 12
        elif period == "ночи" and h == 12:
            h = 0
        if 0 <= h < 24:
            seconds = _seconds_until(h, 0)
            cleaned = text[:m.start()] + " " + text[m.end():]
            return seconds, _extract_reminder_text(cleaned)

    # 4. Абсолютное «в N (словом) часов»
    m = re.search(
        r"\bв\s+([а-яё]+)\s+(?:час[ау]?|часов)\s*(утра|вечера|дня|ночи)?\b",
        text,
    )
    if m and m.group(1) in _RU_NUMBERS:
        h = int(_RU_NUMBERS[m.group(1)])
        period = m.group(2)
        if period == "вечера" and h < 12:
            h += 12
        if 0 <= h < 24:
            seconds = _seconds_until(h, 0)
            cleaned = text[:m.start()] + " " + text[m.end():]
            return seconds, _extract_reminder_text(cleaned)

    # 5. Относительное время («через 5 минут», «через час»)
    seconds, time_span = _extract_relative_duration(text)
    if seconds is not None:
        cleaned = text[:time_span[0]] + " " + text[time_span[1]:] if time_span else text
        return seconds, _extract_reminder_text(cleaned)

    return None, ""


def _seconds_until(hour: int, minute: int) -> int:
    """Сколько секунд до указанного часа:минуты (сегодня или завтра)."""
    now = datetime.now()
    target = now.replace(hour=hour, minute=minute, second=0, microsecond=0)
    if target <= now:
        target += timedelta(days=1)
    return int((target - now).total_seconds())


def _extract_relative_duration(text: str) -> tuple[int | None, tuple[int, int] | None]:
    """
    Ищет относительную длительность в тексте: «через 5 минут», «через час».
    Возвращает (seconds, (start, end)) — секунды и положение в строке для удаления.
    """
    total = 0
    found_match = None
    start_pos, end_pos = None, None

    # Часы
    h_match = _find_unit(text, r"час(?:а|ов|у|ик)?")
    if h_match:
        val, span = h_match
        total += int(val * 3600)
        start_pos = span[0] if start_pos is None else min(start_pos, span[0])
        end_pos = span[1] if end_pos is None else max(end_pos, span[1])
        found_match = True

    # Минуты
    m_match = _find_unit(text, r"минут[ауыка]?")
    if m_match:
        val, span = m_match
        total += int(val * 60)
        start_pos = span[0] if start_pos is None else min(start_pos, span[0])
        end_pos = span[1] if end_pos is None else max(end_pos, span[1])
        found_match = True

    # Секунды
    s_match = _find_unit(text, r"секунд[ауы]?")
    if s_match:
        val, span = s_match
        total += int(val)
        start_pos = span[0] if start_pos is None else min(start_pos, span[0])
        end_pos = span[1] if end_pos is None else max(end_pos, span[1])
        found_match = True

    # Учитываем «через» перед началом
    if found_match and start_pos is not None:
        through_match = re.search(r"\bчерез\b", text[:start_pos])
        if through_match:
            start_pos = through_match.start()

    if not found_match:
        return None, None
    return total, (start_pos, end_pos)


def _find_unit(text: str, unit_pattern: str):
    """
    Ищет «N <unit>» (цифрой) или «<числительное> <unit>».
    Возвращает (value, (start, end)) или None.
    """
    # Цифры
    m = re.search(rf"(\d+)\s*({unit_pattern})", text)
    if m:
        return float(m.group(1)), m.span()

    # Слова
    m = re.search(rf"((?:[а-яё]+\s+){{0,2}})({unit_pattern})", text)
    if m:
        prefix = m.group(1).strip()
        words = prefix.split() if prefix else []
        value = sum(_RU_NUMBERS[w] for w in words if w in _RU_NUMBERS)
        if value > 0:
            return value, m.span()
        # Единица без числа: «через час», «через минуту»
        if re.search(rf"\b{unit_pattern}\b", text):
            unit_match = re.search(rf"\b{unit_pattern}\b", text)
            return 1.0, unit_match.span()
    return None


def _extract_reminder_text(text: str) -> str:
    """
    Из текста (уже с удалённой временной частью) убирает служебные
    слова и возвращает то, что предположительно — текст напоминания.
    """
    words = re.findall(r"[а-яё-]+|\d+", text.lower())
    excluded = (_FILLER_VERBS | _FILLER_PRONOUNS | _FILLER_PARTICLES
                | _TIME_WORDS | set(_RU_NUMBERS.keys()))
    significant = [w for w in words if w not in excluded and not w.isdigit()]
    return " ".join(significant).strip()


# ------------------------------------------------------------------
# Запуск напоминания
# ------------------------------------------------------------------

def _start_reminder(seconds: int, reminder_text: str, assistant):
    rec: dict = {"timer": None, "text": reminder_text,
                 "fire_at": datetime.now() + timedelta(seconds=seconds)}

    def _on_fire():
        with _lock:
            if rec in _active_reminders:
                _active_reminders.remove(rec)
        logger.system("НАПОМИНАНИЕ", f"⏰ сработало: «{reminder_text}»")

        # Останавливаем фоновое аудио, чтобы уведомление было слышно
        try:
            assistant.streamer.stop()
        except Exception:
            pass

        # Сначала звук таймера, потом текст
        sound = os.path.join(
            os.path.dirname(os.path.abspath(__file__)),
            "..", "assets", "timer.mp3",
        )
        try:
            assistant._play_sound(sound)
        except Exception as e:
            logger.warn(f"Не удалось проиграть звук напоминания: {e}")

        if reminder_text:
            assistant.speak(f"Напоминание: {reminder_text}.")
        else:
            assistant.speak("Напоминание сработало.")

    t = threading.Timer(seconds, _on_fire)
    t.daemon = True
    t.start()
    rec["timer"] = t

    with _lock:
        _active_reminders.append(rec)

    duration_spoken = _format_duration_spoken(seconds)
    logger.detail(f"длительность: {seconds} сек ({duration_spoken})")
    logger.detail(f"текст: «{reminder_text or '(пусто)'}»")
    logger.detail(f"всего активных: {len(_active_reminders)}")

    if reminder_text:
        assistant.speak(f"Хорошо, через {duration_spoken} напомню: {reminder_text}.")
    else:
        assistant.speak(f"Напоминание поставлено на {duration_spoken}.")


# ------------------------------------------------------------------
# Управление напоминаниями
# ------------------------------------------------------------------

def _cancel_all_reminders(assistant):
    with _lock:
        active = list(_active_reminders)
        _active_reminders.clear()

    if not active:
        assistant.speak("Активных напоминаний нет.")
        return

    for rec in active:
        try:
            rec["timer"].cancel()
        except Exception:
            pass

    count = len(active)
    word = _form_reminder(count)
    logger.step("🚫", "Навык", f"reminder.py — отменено {count} напоминаний")
    if count == 1:
        assistant.speak("Напоминание отменено.")
    else:
        assistant.speak(f"Отменила {_number_to_words(count)} {word}.")


def _list_reminders(assistant):
    with _lock:
        active = list(_active_reminders)
    if not active:
        assistant.speak("У вас нет активных напоминаний.")
        return

    count = len(active)
    word = _form_reminder(count)
    parts = [f"У вас {_number_to_words(count, accusative=True)} {word}."]
    for rec in active:
        remaining = (rec["fire_at"] - datetime.now()).total_seconds()
        if remaining <= 0:
            continue
        time_spoken = _format_duration_spoken(int(remaining))
        if rec["text"]:
            parts.append(f"Через {time_spoken}: {rec['text']}.")
        else:
            parts.append(f"Через {time_spoken}.")

    assistant.speak(" ".join(parts))


# ------------------------------------------------------------------
# Утилиты озвучки (копии из timer.py)
# ------------------------------------------------------------------

def _format_duration_spoken(seconds: int) -> str:
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


def _form_reminder(n: int) -> str:
    n = abs(n) % 100
    if 11 <= n <= 14:
        return "напоминаний"
    last = n % 10
    if last == 1:
        return "напоминание"
    if 2 <= last <= 4:
        return "напоминания"
    return "напоминаний"
