from speech_recognizer import SpeechRecognizer
from intent_parser import IntentParser
from command_router import CommandRouter
from tts_engine import TTSEngine  # Подключаем новый класс
import sys
import sounddevice as sd
import soundfile as sf
import os


class VoiceAssistant:
    def __init__(self, name="Джарвис"):
        self.name = name.lower()
        self.is_running = False

        # Укажите путь к вашему звуковому файлу (желательно .wav)
        self.startup_sound_path = "./assets/start.mp3"

        print("⚙️ Инициализация систем...")
        try:
            self.tts = TTSEngine(speaker='baya') # Инициализируем голос первым
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

    def start(self):
        """Запуск главного цикла ассистента."""
        self.is_running = True
        greeting_text = "Системы активированы. Я готов к работе."

        # Воспроизводим звук успешного запуска
        print("🎵 Воспроизведение звука запуска...")
        self._play_sound(self.startup_sound_path)


        self.tts.speak(greeting_text)

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
        if self.is_running:
            self.is_running = False
            print("\n🔴 Отключение систем. До свидания!")
            farewell_text = "Отключаю питание. До свидания."
            self.tts.speak(farewell_text) # Прощаемся голосом
            sys.exit(0)

    def _process(self, text):
        if not text:
            return

        # 1. Отдаем текст парсеру на базе spaCy
        parsed_data = self.parser.parse(text)

        # 2. Отдаем разобранные данные роутеру для выполнения
        self.router.route_command(parsed_data, self)