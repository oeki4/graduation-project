from speech_recognizer import SpeechRecognizer
from intent_parser import IntentParser
from command_router import CommandRouter
from tts_engine import TTSEngine
from skills.audio_streamer import AudioStreamer
import sys
import re
import sounddevice as sd
import soundfile as sf
import os
import threading


class VoiceAssistant:
    def __init__(self, name="Ассистент"):
        self.name = name.lower()
        self.is_running = False
        self._stopping = False

        # Укажите путь к вашему звуковому файлу (желательно .wav)
        self.startup_sound_path = "./assets/start.mp3"

        print("⚙️ Инициализация систем...")
        try:
            self.tts = TTSEngine(speaker='aidar')
            self.recognizer = SpeechRecognizer()
            self.parser = IntentParser(model_path="./nlp/models/intent_model")
            self.router = CommandRouter()
            # Единый стример для всего ассистента — навыки используют его,
            # а при новой команде он автоматически останавливается.
            self.streamer = AudioStreamer(self)
        except FileNotFoundError as e:
            print(f"❌ Критическая ошибка: {e}")
            sys.exit(1)

    def _play_sound(self, file_path):
        """Внутренний метод для воспроизведения аудиофайлов."""
        if not os.path.exists(file_path):
            print(f"⚠️ Звуковой файл {file_path} не найден. Пропускаю.")
            return

        try:
            # Читаем аудиофайл и воспроизводим его
            data, fs = sf.read(file_path)
            sd.play(data, fs)
            sd.wait() # Ждем, пока звук полностью не проиграется
        except Exception as e:
            print(f"❌ Ошибка воспроизведения звука: {e}")

    def _console_listener(self):
        """Слушает ввод с клавиатуры в отдельном потоке (для отладки/разработки)."""
        print("\n⌨️ [РЕЖИМ РАЗРАБОТКИ]: Вы можете вводить команды текстом и нажимать Enter.")
        while self.is_running:
            try:
                user_input = input()
                if not self.is_running:
                    break
                if user_input.strip():
                    print(f"👤 Вы (консоль): {user_input}")
                    text = user_input.lower()
                    if self.name in text:
                        text = text.replace(self.name, "").strip()
                    self._process(text)
            except EOFError:
                break
            except Exception as e:
                print(f"⚠️ Ошибка чтения консоли: {e}")

    def start(self):
        """Запуск главного цикла ассистента."""
        self.is_running = True
        greeting_text = "Системы активированы. Я готов к работе."

        # Воспроизводим звук успешного запуска
        print("🎵 Воспроизведение звука запуска...")
        self._play_sound(self.startup_sound_path)

        self.tts.speak(greeting_text)

        # Запускаем консольный слушатель в отдельном потоке
        threading.Thread(target=self._console_listener, daemon=True).start()

        try:
            for result in self.recognizer.listen(yield_partial=False):
                if not self.is_running:
                    break

                if result["type"] == "final":
                    text = result["text"].lower()
                    print(f"👤 Вы: {text}")
                    if self.name in text:
                        clean_text = text.replace(self.name, "").strip()
                        self._process(clean_text)

        except KeyboardInterrupt:
            self.stop()
        except Exception as e:
            print(f"❌ Ошибка в работе ассистента: {e}")
            self.stop()

    def stop(self):
        """Штатное выключение ассистента."""
        if getattr(self, '_stopping', False):
            return
        self._stopping = True
        
        self.is_running = False
        print("\n🔴 Отключение систем. До свидания!")

        # Останавливаем воспроизведение аудио если что-то играло
        try:
            self.streamer.stop()
        except Exception:
            pass

        try:
            farewell_text = "Отключаю питание. До свидания."
            self.tts.speak(farewell_text)
        except BaseException:
            # Игнорируем ошибки при выходе (повторный Ctrl+C, конфликты потоков)
            pass
        finally:
            # Принудительно убиваем все процессы и потоки
            os._exit(0)

    # ------------------------------------------------------------------
    # Управление системной громкостью
    # ------------------------------------------------------------------

    @staticmethod
    def _volume_up():
        """Увеличивает системную громкость."""
        print("🔊 [SYSTEM] Громкость +")
        if os.name == 'posix':
            os.system("amixer sset 'Master' 10%+")
        else:
            # Симуляция нажатия медиаклавиши Volume Up (0xAF) через Windows API
            import ctypes
            ctypes.windll.user32.keybd_event(0xAF, 0, 0, 0)
            ctypes.windll.user32.keybd_event(0xAF, 0, 2, 0)

    @staticmethod
    def _volume_down():
        """Уменьшает системную громкость."""
        print("🔉 [SYSTEM] Громкость -")
        if os.name == 'posix':
            os.system("amixer sset 'Master' 10%-")
        else:
            import ctypes
            ctypes.windll.user32.keybd_event(0xAE, 0, 0, 0)
            ctypes.windll.user32.keybd_event(0xAE, 0, 2, 0)

    @staticmethod
    def _set_volume(level: int):
        """
        Устанавливает системную громкость в процентах (0–100).
        Windows: использует pycaw (Core Audio API).
        Linux: использует amixer.
        """
        level = max(0, min(100, level))
        print(f"🔊 [SYSTEM] Установка громкости: {level}%")
        if os.name == 'posix':
            os.system(f"amixer sset 'Master' {level}%")
        else:
            try:
                from pycaw.pycaw import AudioUtilities, IAudioEndpointVolume
                from comtypes import CLSCTX_ALL
                from ctypes import cast, POINTER
                devices = AudioUtilities.GetSpeakers()
                interface = devices.Activate(IAudioEndpointVolume._iid_, CLSCTX_ALL, None)
                volume = cast(interface, POINTER(IAudioEndpointVolume))
                volume.SetMasterVolumeLevelScalar(level / 100.0, None)
            except ImportError:
                print("⚠️ [SYSTEM] pycaw не установлен: pip install pycaw")

    # Таблица перевода русских числительных в цифры (0–100)
    _RU_NUMBERS = {
        "ноль": 0, "нуль": 0,
        "один": 1, "одна": 1,
        "два": 2, "две": 2,
        "три": 3, "четыре": 4, "пять": 5, "шесть": 6,
        "семь": 7, "восемь": 8, "девять": 9, "десять": 10,
        "одиннадцать": 11, "двенадцать": 12, "тринадцать": 13,
        "четырнадцать": 14, "пятнадцать": 15, "шестнадцать": 16,
        "семнадцать": 17, "восемнадцать": 18, "девятнадцать": 19,
        "двадцать": 20, "тридцать": 30, "сорок": 40,
        "пятьдесят": 50, "шестьдесят": 60, "семьдесят": 70,
        "восемьдесят": 80, "девяносто": 90, "сто": 100,
    }

    def _parse_volume_level(self, text: str) -> int | None:
        """
        Извлекает уровень громкости из строки вида:
          «громкость 50», «громкость пятьдесят», «громкость пятьдесят процентов».
        Возвращает целое 0–100 или None, если число не найдено.
        """
        # Убираем слово «процентов/процента/%» и «громкость»
        t = re.sub(r"громкость|процентов|процента|%", "", text).strip()

        # Цифры
        m = re.search(r"\b(\d{1,3})\b", t)
        if m:
            return int(m.group(1))

        # Русские числительные: может быть «двадцать пять» → 25
        total = None
        for word, val in self._RU_NUMBERS.items():
            if word in t:
                if total is None:
                    total = val
                else:
                    # Складываем десятки + единицы (двадцать + пять = 25)
                    if val < 10:
                        total += val
                    else:
                        total = val
        return total

    # ------------------------------------------------------------------
    # Обработка команды
    # ------------------------------------------------------------------

    def _process(self, text):
        if not text:
            return

        t = text.lower().strip()

        # ── 1. Команды, которые НЕ прерывают воспроизведение ──────────

        # Стоп — остановить текущее воспроизведение
        if t in ("стоп", "стопп", "стоп стоп", "остановись", "замолчи",
                 "хватит", "отстань", "тихо", "stop"):
            print("⏹️  [SYSTEM] Стоп.")
            self.streamer.stop()
            self.tts.speak("Остановлено.")
            return

        # Громкость выше
        if t in ("громче", "сделай громче", "прибавь громкость",
                 "прибавь", "погромче"):
            self._volume_up()
            self.tts.speak("Громче.")
            return

        # Громкость ниже
        if t in ("тише", "сделай тише", "убавь громкость",
                 "убавь", "потише"):
            self._volume_down()
            self.tts.speak("Тише.")
            return

        # Установить конкретный уровень громкости: «громкость 50»
        if t.startswith("громкость"):
            level = self._parse_volume_level(t)
            if level is not None:
                self._set_volume(level)
                self.tts.speak(f"Громкость {level} процентов.")
            else:
                self.tts.speak("Не понял уровень громкости. Скажите, например: громкость пятьдесят.")
            return

        # ── 2. Все остальные команды прерывают текущее воспроизведение ─
        self.streamer.stop()

        # ── 3. Системные команды ───────────────────────────────────────
        if any(w in t for w in ("перезагрузи", "перезагрузка", "ребут", "reboot")):
            print("🔄 [SYSTEM] Перезагрузка системы...")
            self.tts.speak("Перезагружаю систему. Скоро вернусь.")
            os.system("sudo reboot" if os.name == 'posix' else "shutdown /r /t 0")
            return

        if any(w in t for w in ("выключи", "выключить", "отключи питание", "power off")):
            print("🔴 [SYSTEM] Выключение системы...")
            self.tts.speak("Выключаю питание. До свидания.")
            os.system("sudo shutdown -h now" if os.name == 'posix' else "shutdown /s /t 0")
            return

        # ── 4. NLP — маршрутизация через spaCy ────────────────────────
        parsed_data = self.parser.parse(text)
        self.router.route_command(parsed_data, self)