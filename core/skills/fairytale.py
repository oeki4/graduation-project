import os
import sys

# Добавляем текущую директорию навыков в путь поиска модулей
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from mp3tales_scraper import Mp3TalesScraper

def setup(router):
    """
    Регистрация интента чтения сказки.
    """
    router.register_route("FAIRYTALE", _module_fairytale)

def _module_fairytale(parsed_data, assistant):
    """
    Главный модуль управления сказками.
    """
    # 1. Извлечение названия сказки
    payload = _extract_name(parsed_data)
    
    if payload == "неизвестно":
        assistant.tts.speak("Я не совсем поняла название сказки. Попробуйте еще раз.")
        return

    # 2. Поиск и парсинг аудио (используем отдельный модуль)
    scraper = Mp3TalesScraper()
    assistant.tts.speak(f"Ищу сказку под названием {payload}. Одну секунду.")

    # Если пользователь попросил "любую", можно добавить логику случайного выбора
    # Но пока ищем то, что попросили
    page_url = scraper.search_fairytale(payload)
    
    if not page_url:
        assistant.tts.speak("К сожалению, я не нашла такую сказку на сайте МП3 тэйлс инфо.")
        return

    audio_url = scraper.get_audio_url(page_url)
    
    if not audio_url:
        assistant.tts.speak("Страница сказки найдена, но ссылка на аудиофайл скрыта или недоступна.")
        return

    # 3. Воспроизведение через стример
    print(f"🔗 [MARSHAL] Передаю ссылку на стриминг: {audio_url}")

    if assistant.streamer.play_url(audio_url):
        print(f"✅ [SUCCESS] Сказка '{payload}' запущена.")
    else:
        assistant.tts.speak("Не удалось запустить онлайн трансляцию аудио.")

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
