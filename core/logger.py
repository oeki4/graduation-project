"""
Утилита визуального логирования действий ассистента.

Используется для построения наглядного терминального вывода:
секционные разделители, шкалы вероятностей интентов, цветовая
индикация состояний. Удобно для скриншотов в отчётах/диплом.
"""

import os
import sys
import time
import shutil
from datetime import datetime


# ── Windows: включаем поддержку ANSI escape sequences ─────────────
if os.name == "nt":
    os.system("")  # активирует VT-режим в Windows 10+

# ── Принудительный UTF-8 на stdout (нужно для Unicode-рамок и эмодзи) ──
try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")
except (AttributeError, Exception):
    pass


# ── Цвета ANSI ────────────────────────────────────────────────────
class C:
    RESET   = "\033[0m"
    BOLD    = "\033[1m"
    DIM     = "\033[2m"
    ITAL    = "\033[3m"

    BLACK   = "\033[30m"
    RED     = "\033[31m"
    GREEN   = "\033[32m"
    YELLOW  = "\033[33m"
    BLUE    = "\033[34m"
    MAGENTA = "\033[35m"
    CYAN    = "\033[36m"
    WHITE   = "\033[37m"
    GRAY    = "\033[90m"


def _width() -> int:
    """Ширина терминала, ограниченная 80 символами для красивых скриншотов."""
    return min(shutil.get_terminal_size((80, 20)).columns, 80)


def _ts() -> str:
    """Текущее время в формате HH:MM:SS."""
    return datetime.now().strftime("%H:%M:%S")


# ── Разделители ───────────────────────────────────────────────────

def heavy_line():
    print(f"{C.CYAN}{'═' * _width()}{C.RESET}")


def thin_line():
    print(f"{C.GRAY}{'─' * _width()}{C.RESET}")


# ── Секция: визуальная рамка вокруг блока пайплайна ───────────────

def section(title: str, emoji: str = "▶"):
    heavy_line()
    print(f"{emoji}  {C.BOLD}{title}{C.RESET}   {C.DIM}{_ts()}{C.RESET}")
    thin_line()


def end_section():
    heavy_line()
    print()


# ── Шаги пайплайна ────────────────────────────────────────────────

def step(emoji: str, label: str, value: str = ""):
    """Одна строка лога: эмодзи, ярлык, опциональное значение."""
    if value:
        print(f"  {emoji}  {label}: {C.BOLD}{value}{C.RESET}")
    else:
        print(f"  {emoji}  {label}")


def detail(text: str):
    """Деталь с отступом."""
    print(f"     {C.DIM}• {text}{C.RESET}")


def kv(key: str, value, indent: int = 2):
    """Пара ключ-значение."""
    pad = " " * indent
    print(f"{pad}{C.GRAY}{key}:{C.RESET} {value}")


# ── Результаты / статусы ──────────────────────────────────────────

def ok(text: str):
    print(f"  {C.GREEN}✓{C.RESET}  {text}")


def warn(text: str):
    print(f"  {C.YELLOW}⚠{C.RESET}  {text}")


def err(text: str):
    print(f"  {C.RED}✗{C.RESET}  {text}")


def info(text: str):
    print(f"  {C.BLUE}ℹ{C.RESET}  {text}")


# ── Визуализация вероятностей интентов ────────────────────────────

def intent_bars(scores: dict, predicted: str | None = None, width: int = 24):
    """
    Печатает горизонтальные шкалы вероятностей интентов:

         → узнать_погоду      ████████████████████████  98.4%
           включить_сказку    ▏                          0.6%
           ...
    """
    if not scores:
        return

    items = sorted(scores.items(), key=lambda x: x[1], reverse=True)
    name_w = max(len(name) for name in scores)

    for name, score in items:
        filled = int(round(score * width))
        bar = "█" * filled + "▏" * (1 if filled < width else 0) + " " * max(0, width - filled - 1)

        is_pred = (name == predicted)
        marker = f"{C.GREEN}→{C.RESET}" if is_pred else " "
        name_str = f"{C.BOLD}{name:<{name_w}}{C.RESET}" if is_pred else f"{C.DIM}{name:<{name_w}}{C.RESET}"
        bar_color = C.GREEN if is_pred else C.GRAY
        pct = f"{score * 100:5.1f}%"

        print(f"     {marker}  {name_str}  {bar_color}{bar}{C.RESET}  {pct}")


# ── Замер времени операции ────────────────────────────────────────

class Timer:
    """
    Контекстный менеджер для замера длительности.

    Пример:
        with logger.Timer("HTTP-запрос к wttr.in"):
            requests.get(...)
    """

    def __init__(self, label: str):
        self.label = label
        self.start = 0.0

    def __enter__(self):
        self.start = time.perf_counter()
        return self

    def __exit__(self, *exc):
        elapsed = time.perf_counter() - self.start
        if elapsed < 1:
            txt = f"{elapsed * 1000:.0f} мс"
        else:
            txt = f"{elapsed:.2f} с"
        print(f"     {C.DIM}⏱  {self.label}: {txt}{C.RESET}")


# ── Заголовок при запуске приложения ──────────────────────────────

def banner(name: str = "Голосовой ассистент"):
    heavy_line()
    title = f"   {name}".ljust(_width() - 1)
    print(f"{C.CYAN}{C.BOLD}{title}{C.RESET}")
    heavy_line()
    print()


# ── Подсистемы — короткие префиксы ────────────────────────────────

def system(label: str, message: str):
    """Системное сообщение от подсистемы (TTS, Recognizer, Streamer, ...)."""
    print(f"  {C.MAGENTA}[{label}]{C.RESET} {message}")
