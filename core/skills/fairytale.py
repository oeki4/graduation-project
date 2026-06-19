import os
import sys
import time

# Добавляем текущую директорию навыков в путь поиска модулей
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))

from mp3tales_scraper import Mp3TalesScraper
import logger

def setup(router):
    """
    Регистрация интента чтения сказки.
    """
    router.register_route("включить_сказку", _module_fairytale)

def _module_fairytale(parsed_data, assistant):
    """
    Главный модуль управления сказками.
    """
    # 1. Извлечение названия сказки
    payload = _extract_name(parsed_data)
    logger.metric("🏷️ ", "Параметры", note=f"сказка: {payload}")

    if payload == "неизвестно":
        assistant.speak("Я не совсем поняла название сказки. Попробуйте еще раз.")
        return

    # 2. Поиск и парсинг аудио (отдельный модуль, с замером времени)
    scraper = Mp3TalesScraper()
    assistant.speak(f"Ищу сказку под названием {payload}. Одну секунду.")

    t0 = time.perf_counter()
    page_url = scraper.search_fairytale(payload)
    audio_url = scraper.get_audio_url(page_url) if page_url else None
    http_ms = (time.perf_counter() - t0) * 1000
    logger.metric("🌐", "mp3tales.info (поиск)", http_ms,
                  payload if audio_url else "не найдено")

    if not page_url:
        assistant.speak("К сожалению, я не нашла такую сказку на сайте МП3 тэйлс инфо.")
        return

    if not audio_url:
        assistant.speak("Страница сказки найдена, но ссылка на аудиофайл недоступна.")
        return

    # 3. Воспроизведение через стример
    if assistant.streamer.play_url(audio_url):
        logger.metric("▶️ ", "Воспроизведение", note=payload)
    else:
        assistant.speak("Не удалось запустить онлайн трансляцию аудио.")

def _extract_name(parsed_data):
    """
    Умное извлечение названия из текста.
    """
    text = parsed_data.get("original_text", "").lower().strip()
    
    types = [
        "аудиосказку про", "аудиосказка про", "сказку про", "сказка про", 
        "историю про", "история про", "рассказ про",
        "аудиосказку", "аудиосказка", "сказку", "сказка", 
        "историю", "история", "рассказ"
    ]
    commands = ["включи", "поставь", "расскажи", "найди", "прочитай", "запусти", "слушаем", "проиграй"]

    name = ""

    # Ищем тип контента
    for t in types:
        if t in text:
            parts = text.split(t, 1)
            if len(parts) > 1 and parts[1].strip():
                name = parts[1].strip()
                break
            
    # Если название всё еще пустое, отрезаем просто командный глагол
    if not name:
        for cmd in commands:
            if cmd in text:
                parts = text.split(cmd, 1)
                if len(parts) > 1 and parts[1].strip():
                    name = parts[1].strip()
                    break

    # Финальная чистка
    if name:
        name = name.replace("пожалуйста", "").replace("плиз", "").strip()
        return name
    
    return "неизвестно"
