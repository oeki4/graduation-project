from speech_recognizer import SpeechRecognizer
from intent_parser import IntentParser
from command_router import CommandRouter
from tts_engine import TTSEngine
from skills.audio_streamer import AudioStreamer
import logger
import sys
import re
import subprocess
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

        # Флаг: TTS сейчас говорит → голосовой ввод игнорируется (защита от эха)
        self._is_speaking = False

        # Состояние ducking: когда обнаружено имя в partial-распознавании,
        # громкость опускается до 25%, чтобы радио/сказка не заглушали
        # голосовую команду. После обработки восстанавливается прежний уровень.
        self._ducked = False
        self._pre_duck_volume = None
        self._unduck_watchdog: threading.Timer | None = None
        self._duck_target_pct = 25
        self._duck_watchdog_sec = 15.0

        logger.heavy_line()
        print(f"⚙️  {logger.C.BOLD}Инициализация систем...{logger.C.RESET}")
        logger.heavy_line()

        # Windows: один раз создаём COM-интерфейс для управления громкостью.
        # Если делать это на каждый _get/_set_volume, pycaw порождает кучу
        # COM-объектов, которые потом «грязно» отрелизиваются при GC и
        # засоряют stderr трейсбеками от _compointer_base.__del__.
        self._win_volume_iface = None
        if os.name == "nt":
            self._init_windows_volume()

        # На медленных I²S-DAC (voiceHAT, MAX98357A) при дефолтной
        # маленькой латентности sounddevice не успевает заполнять буфер →
        # underrun → хрипы. Принудительная высокая латентность даёт
        # ~200–300 мс буфера и устраняет проблему.
        sd.default.latency = "high"

        # Программная громкость для Linux (0.0–1.0). I²S-DAC без аппаратной
        # регулировки громкости — ALSA Master там бутафорский. Поэтому
        # масштабируем PCM-данные сами перед отправкой в aplay/sounddevice.
        # На Windows используется аппаратная регулировка через pycaw.
        self._software_volume = 1.0


        # Диагностика аудиоустройств — полезно при первой настройке на Pi
        if os.environ.get("AUDIO_DEBUG"):
            try:
                logger.system("AUDIO", "доступные устройства:")
                for i, dev in enumerate(sd.query_devices()):
                    io = []
                    if dev.get("max_input_channels", 0) > 0:
                        io.append("in")
                    if dev.get("max_output_channels", 0) > 0:
                        io.append("out")
                    print(f"     [{i}] {dev['name']:<40} ({'/'.join(io)}) "
                          f"sr={int(dev['default_samplerate'])}")
            except Exception as e:
                logger.warn(f"sd.query_devices() упало: {e}")

        # Если задана переменная окружения AUDIO_DEVICE — назначаем устройство
        # для sounddevice глобально (актуально для Raspberry Pi с I²S-HAT).
        # Можно указывать индексы (например, "0,0") или имена.
        audio_device = os.environ.get("AUDIO_DEVICE")
        if audio_device:
            try:
                parts = audio_device.split(",")
                if len(parts) == 2:
                    sd.default.device = (int(parts[0].strip()), int(parts[1].strip()))
                else:
                    sd.default.device = audio_device.strip()
                logger.system("AUDIO", f"устройство по умолчанию: {sd.default.device}")
            except Exception as e:
                logger.warn(f"Не удалось установить AUDIO_DEVICE={audio_device}: {e}")
        try:
            self.tts = TTSEngine()  # speaker='xenia' по умолчанию
            self.recognizer = SpeechRecognizer()
            self.parser = IntentParser(model_path="./nlp/models/intent_model")
            self.router = CommandRouter()
            # Единый стример для всего ассистента — навыки используют его,
            # а при новой команде он автоматически останавливается.
            self.streamer = AudioStreamer(self)
        except FileNotFoundError as e:
            print(f"❌ Критическая ошибка: {e}")
            sys.exit(1)

    def speak(self, text: str):
        """
        Произносит текст через TTS с защитой от эха.
        Пока ассистент говорит, голосовой ввод игнорируется —
        это предотвращает ситуацию, когда микрофон подхватывает
        голос TTS и интерпретирует его как новую команду.
        Используйте этот метод вместо self.tts.speak() везде, где
        нужна защита (в навыках: assistant.speak(...)).
        """
        logger.step("🔊", "TTS", f"«{text}»")
        self._is_speaking = True
        try:
            # На Linux передаём программную громкость в TTS, чтобы он
            # масштабировал PCM перед aplay. На Windows громкость
            # регулируется системно (pycaw), TTS гонит сэмплы как есть.
            volume = self._software_volume if os.name == "posix" else 1.0
            with logger.Timer("синтез + воспроизведение"):
                self.tts.speak(text, volume=volume)
        finally:
            self._is_speaking = False

    def _play_sound(self, file_path):
        """
        Внутренний метод для воспроизведения аудиофайлов.

        Читаем как int16 PCM и пишем через явный OutputStream — это даёт
        стабильное воспроизведение на Raspberry Pi с I²S-выходом
        (без хрипов и заниженной громкости, характерных для float32).
        """
        if not os.path.exists(file_path):
            print(f"⚠️ Звуковой файл {file_path} не найден. Пропускаю.")
            return

        try:
            # На Linux (Pi) для надёжности используем subprocess + aplay
            # (mpg123 для MP3, aplay для WAV). Sounddevice на медленном
            # I²S DAC даёт underrun, см. подробности в tts_engine.py.
            if os.name == "posix":
                # mpg123 -f принимает целое 0–32768 (32768 = 100%) —
                # программное масштабирование без правки ALSA.
                if file_path.lower().endswith(".mp3"):
                    vol_factor = int(self._software_volume * 32768)
                    subprocess.run(
                        ["mpg123", "-q", "-f", str(vol_factor), file_path],
                        stderr=subprocess.DEVNULL,
                        check=False,
                    )
                else:
                    subprocess.run(
                        ["aplay", "-q", file_path],
                        stderr=subprocess.DEVNULL,
                        check=False,
                    )
            else:
                # На Windows sounddevice работает нормально
                data, fs = sf.read(file_path, dtype="int16")
                sd.play(data, fs, blocking=True)
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
                    print(f"\n👤 {logger.C.BOLD}Ввод (консоль):{logger.C.RESET} {user_input}")
                    text = user_input.lower()
                    if self.name in text:
                        logger.step("✂️ ", "Wake-word удалён", f"«{self.name}»")
                        text = text.replace(self.name, "").strip()
                    try:
                        self._process(text)
                    finally:
                        self._unduck_audio()
            except EOFError:
                break
            except Exception as e:
                print(f"⚠️ Ошибка чтения консоли: {e}")

    def start(self):
        """Запуск главного цикла ассистента."""
        self.is_running = True
        greeting_text = "Системы активированы. Я готов к работе."

        logger.banner("Голосовой ассистент")
        logger.ok("Все подсистемы инициализированы")
        logger.kv("имя", f"«{self.name}»")
        logger.kv("модель TTS", "Silero v4_ru (xenia)")
        logger.kv("модель STT", "Vosk small-ru-0.22")
        logger.kv("модель NLU", "spaCy + кастомный textcat (5 классов)")
        print()

        # Воспроизводим звук успешного запуска
        logger.step("🎵", "Звук запуска")
        self._play_sound(self.startup_sound_path)

        self.speak(greeting_text)

        # Запускаем консольный слушатель в отдельном потоке
        threading.Thread(target=self._console_listener, daemon=True).start()

        try:
            # Включаем partial-результаты, чтобы реагировать на имя ассистента
            # ДО окончания реплики (через ducking приглушаем фон).
            for result in self.recognizer.listen(yield_partial=True):
                if not self.is_running:
                    break

                text = result["text"].lower()

                # Partial: предварительное распознавание ещё до финальной паузы.
                # Если в нём появилось имя ассистента — немедленно приглушаем
                # фоновое воспроизведение, чтобы лучше расслышать команду.
                if result["type"] == "partial":
                    if text and self.name in text and not self._is_speaking:
                        self._duck_audio()
                    continue

                # Final: команда распознана целиком, можно обрабатывать.
                if self._is_speaking:
                    # TTS говорит — игнорируем эхо
                    self._unduck_audio()
                    continue

                print(f"\n👤 {logger.C.BOLD}Ввод (голос):{logger.C.RESET} {text}")
                try:
                    if self.name in text:
                        logger.step("✂️ ", "Wake-word обнаружен и удалён", f"«{self.name}»")
                        clean_text = text.replace(self.name, "").strip()
                        self._process(clean_text)
                    else:
                        logger.detail("в реплике нет имени ассистента — игнорирую")
                finally:
                    # Возвращаем громкость в любом случае
                    self._unduck_audio()

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

        # Освобождаем COM-объект до сборщика мусора, иначе на Windows
        # будут шумные «ValueError: COM method call without VTable»
        if self._win_volume_iface is not None:
            try:
                self._win_volume_iface = None
            except Exception:
                pass

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
    # Auto-ducking: приглушение фонового воспроизведения на время команды
    # ------------------------------------------------------------------

    def _init_windows_volume(self):
        """Создаёт COM-интерфейс громкости один раз при старте (Windows)."""
        try:
            import comtypes
            try:
                comtypes.CoInitialize()
            except Exception:
                pass  # уже инициализирован в этом потоке

            from pycaw.pycaw import AudioUtilities, IAudioEndpointVolume
            from comtypes import CLSCTX_ALL
            from ctypes import cast, POINTER

            devices = AudioUtilities.GetSpeakers()
            interface = devices.Activate(IAudioEndpointVolume._iid_, CLSCTX_ALL, None)
            self._win_volume_iface = cast(interface, POINTER(IAudioEndpointVolume))
            logger.system("AUDIO", "COM-интерфейс громкости (pycaw) инициализирован")
        except Exception as e:
            logger.warn(f"pycaw недоступен — управление громкостью отключено: {e}")
            self._win_volume_iface = None

    def _get_current_volume(self) -> int | None:
        """Возвращает текущую системную громкость 0–100, или None при ошибке."""
        if os.name == "posix":
            return int(round(self._software_volume * 100))
        else:
            if self._win_volume_iface is None:
                return None
            try:
                return int(round(self._win_volume_iface.GetMasterVolumeLevelScalar() * 100))
            except Exception:
                return None

    def _duck_audio(self):
        """
        Опускает громкость для облегчения распознавания речи поверх
        играющего радио/сказки. Текущий уровень сохраняется и потом
        восстанавливается через _unduck_audio().
        """
        if self._ducked:
            return

        current = self._get_current_volume()
        if current is not None and current <= self._duck_target_pct:
            # Уже тихо — никаких действий не требуется
            return

        self._pre_duck_volume = current
        self._set_volume(self._duck_target_pct)
        self._ducked = True
        logger.system("AUDIO", f"📉 ducking {current}% → {self._duck_target_pct}% "
                                f"(услышал имя ассистента)")

        # Сторожевой таймер: если по какой-то причине _unduck_audio()
        # не будет вызван (нет финального распознавания, исключение и т. п.),
        # автоматически восстанавливаем громкость через _duck_watchdog_sec.
        if self._unduck_watchdog is not None:
            self._unduck_watchdog.cancel()
        self._unduck_watchdog = threading.Timer(
            self._duck_watchdog_sec, self._unduck_audio
        )
        self._unduck_watchdog.daemon = True
        self._unduck_watchdog.start()

    def _unduck_audio(self):
        """Возвращает громкость на уровень, бывший до ducking."""
        if not self._ducked:
            return

        if self._pre_duck_volume is not None:
            self._set_volume(self._pre_duck_volume)
            logger.system("AUDIO", f"📈 unducking → {self._pre_duck_volume}%")

        self._ducked = False
        self._pre_duck_volume = None
        if self._unduck_watchdog is not None:
            self._unduck_watchdog.cancel()
            self._unduck_watchdog = None

    # ------------------------------------------------------------------
    # Управление системной громкостью
    # ------------------------------------------------------------------

    def _volume_up(self):
        """Увеличивает громкость на 10%."""
        if os.name == "posix":
            self._software_volume = min(1.0, self._software_volume + 0.10)
        else:
            import ctypes
            ctypes.windll.user32.keybd_event(0xAF, 0, 0, 0)
            ctypes.windll.user32.keybd_event(0xAF, 0, 2, 0)

    def _volume_down(self):
        """Уменьшает громкость на 10%."""
        if os.name == "posix":
            self._software_volume = max(0.0, self._software_volume - 0.10)
        else:
            import ctypes
            ctypes.windll.user32.keybd_event(0xAE, 0, 0, 0)
            ctypes.windll.user32.keybd_event(0xAE, 0, 2, 0)

    def _set_volume(self, level: int):
        """
        Устанавливает громкость в процентах (0–100).
        Windows: системная громкость через pycaw.
        Linux: программное масштабирование PCM-данных в коде (см. speak/aplay).
        """
        level = max(0, min(100, level))
        if os.name == "posix":
            self._software_volume = level / 100.0
        else:
            if self._win_volume_iface is None:
                return
            try:
                self._win_volume_iface.SetMasterVolumeLevelScalar(level / 100.0, None)
            except Exception as e:
                logger.warn(f"Не удалось установить громкость: {e}")

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

        # Русские числительные: разбиваем по словам и складываем
        # «двадцать пять» → 20 + 5 = 25
        # «сто» → 100
        # «пятьдесят» → 50
        total = None
        for word in t.split():
            if word in self._RU_NUMBERS:
                if total is None:
                    total = 0
                total += self._RU_NUMBERS[word]
        return total

    # ------------------------------------------------------------------
    # Обработка команды
    # ------------------------------------------------------------------

    def _process(self, text):
        if not text:
            return

        t = text.lower().strip()

        logger.section(f"ВХОД  «{text}»", emoji="🎤")

        # ── 1. Команды, которые НЕ прерывают воспроизведение ──────────

        if t in ("стоп", "стой", "стопп", "стоп стоп", "остановись",
                 "остановить", "замолчи", "хватит", "отстань",
                 "выключи радио", "выключи сказку", "stop"):
            logger.step("⏹️ ", "Системная команда", "СТОП (прерывает воспроизведение)")
            self.streamer.stop()
            self.speak("Остановлено.")
            logger.end_section()
            return

        if t in ("громче", "сделай громче", "прибавь громкость",
                 "прибавь", "погромче"):
            logger.step("🔊", "Системная команда", "ГРОМЧЕ (NLU обойдён)")
            self._volume_up()
            self.speak("Громче.")
            logger.end_section()
            return

        if t in ("тише", "сделай тише", "убавь громкость",
                 "убавь", "потише"):
            logger.step("🔉", "Системная команда", "ТИШЕ (NLU обойдён)")
            self._volume_down()
            self.speak("Тише.")
            logger.end_section()
            return

        if t.startswith("громкость"):
            level = self._parse_volume_level(t)
            if level is not None:
                logger.step("🔊", "Системная команда", f"ГРОМКОСТЬ {level}%")
                self._set_volume(level)
                self.speak(f"Громкость {level} процентов.")
            else:
                logger.warn("Не удалось распознать уровень громкости")
                self.speak("Не понял уровень громкости. Скажите, например: громкость пятьдесят.")
            logger.end_section()
            return

        # ── 2. Прерывание текущего воспроизведения (barge-in) ─────────
        logger.step("✂️ ", "Barge-in: остановка текущего воспроизведения")
        self.streamer.stop()

        # ── 3. Системные команды управления питанием ──────────────────
        if any(w in t for w in ("перезагрузи", "перезагрузка", "ребут", "reboot")):
            logger.step("🔄", "Системная команда", "ПЕРЕЗАГРУЗКА")
            self.speak("Перезагружаю систему. Скоро вернусь.")
            os.system("sudo reboot" if os.name == 'posix' else "shutdown /r /t 0")
            return

        if any(w in t for w in ("выключи", "выключить", "отключи питание", "power off")):
            logger.step("🔴", "Системная команда", "ВЫКЛЮЧЕНИЕ")
            self.speak("Выключаю питание. До свидания.")
            os.system("sudo shutdown -h now" if os.name == 'posix' else "shutdown /s /t 0")
            return

        # ── 4. NLU — классификация интента через spaCy ────────────────
        logger.step("🧠", "NLU", "запускаю IntentParser (spaCy textcat)")
        with logger.Timer("анализ текста"):
            parsed_data = self.parser.parse(text)

        # Визуализируем результаты классификатора
        doc = parsed_data.get("spacy_doc")
        if doc is not None and hasattr(doc, "cats") and doc.cats:
            logger.detail("вероятности по классам:")
            logger.intent_bars(doc.cats, predicted=parsed_data["intent"])

        # Сущности
        entities = parsed_data.get("entities", {})
        if entities:
            logger.step("🏷️ ", "Сущности", str(entities))
        else:
            logger.step("🏷️ ", "Сущности", "(не извлечены)")

        # ── 5. Маршрутизация в нужный навык ───────────────────────────
        logger.step("🔀", "Маршрутизация", f"интент → {parsed_data['intent']}")
        logger.thin_line()

        self.router.route_command(parsed_data, self)

        logger.end_section()