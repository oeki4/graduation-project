from speech_recognizer import SpeechRecognizer
from intent_parser import IntentParser
from command_router import CommandRouter
from tts_engine import TTSEngine  # Подключаем новый класс
import sys
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
            self.tts = TTSEngine(speaker='aidar') # Используем мужской голос Aidar
            self.recognizer = SpeechRecognizer()
            self.parser = IntentParser(model_path="./nlp/models/intent_model")
            self.router = CommandRouter() # Создаем наш диспетчер
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
        
        try:
            farewell_text = "Отключаю питание. До свидания."
            self.tts.speak(farewell_text) # Прощаемся голосом
        except BaseException:
            # Игнорируем ошибки при выходе (повторный Ctrl+C, конфликты потоков)
            pass
        finally:
            # Принудительно убиваем все процессы и потоки
            os._exit(0)

    def _process(self, text):
        if not text:
            return

        # --- Системные команды ---
        reboot_words = ["перезагрузи", "перезагрузка", "ребут", "reboot"]
        if any(word in text.lower() for word in reboot_words):
            print("🔄 [SYSTEM] Перезагрузка системы...")
            self.tts.speak("Перезагружаю систему. Скоро вернусь.")
            if os.name == 'posix':
                os.system("sudo reboot")
            else:
                os.system("shutdown /r /t 0")
            return

        shutdown_words = ["выключи", "выключить", "отключи питание", "power off"]
        if any(word in text.lower() for word in shutdown_words):
            print("🔴 [SYSTEM] Выключение системы...")
            self.tts.speak("Выключаю питание. До свидания.")
            if os.name == 'posix':
                os.system("sudo shutdown -h now")
            else:
                os.system("shutdown /s /t 0")
            return

        # Управление громкостью
        if "громче" in text.lower() or "прибавь" in text.lower():
            print("🔊 [SYSTEM] Громкость +10%")
            if os.name == 'posix':
                os.system("amixer sset 'Master' 10%+")
            else:
                print("⚠️ Громкость изменена (эмуляция для Windows)")
            self.tts.speak("Делаю громче.")
            return

        if "тише" in text.lower() or "убавь" in text.lower():
            print("🔉 [SYSTEM] Громкость -10%")
            if os.name == 'posix':
                os.system("amixer sset 'Master' 10%-")
            else:
                print("⚠️ Громкость изменена (эмуляция для Windows)")
            self.tts.speak("Сделала потише.")
            return

        # 1. Отдаем текст парсеру на базе spaCy
        parsed_data = self.parser.parse(text)

        # 2. Отдаем разобранные данные роутеру для выполнения
        self.router.route_command(parsed_data, self)