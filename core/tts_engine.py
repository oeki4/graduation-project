import torch
import sounddevice as sd

class TTSEngine:
    def __init__(self, speaker='baya', sample_rate=48000):
        """
        Инициализация движка синтеза речи.
        Доступные голоса (speaker): 'aidar', 'baya', 'kseniya', 'xenia', 'eugene'
        """
        print("🔊 Загрузка голосового модуля (Silero TTS)... Это может занять пару секунд.")
        self.device = torch.device('cpu')
        self.speaker = speaker
        self.sample_rate = sample_rate

        try:
            # Загрузка модели из torch hub (при первом запуске скачается кэш)
            self.model, _ = torch.hub.load(
                repo_or_dir='snakers4/silero-models',
                model='silero_tts',
                language='ru',
                speaker='v4_ru'
            )
            self.model.to(self.device)
            print("✅ Голосовой модуль успешно загружен.")
        except Exception as e:
            print(f"❌ Ошибка загрузки Silero TTS: {e}")
            raise

    def speak(self, text):
        """
        Синтезирует текст в речь и сразу воспроизводит.
        """
        if not text:
            return

        try:
            # Генерация аудио-тензора
            audio_tensor = self.model.apply_tts(
                text=text,
                speaker=self.speaker,
                sample_rate=self.sample_rate,
                put_accent=True,
                put_yo=True
            )

            # Конвертируем тензор PyTorch в обычный массив numpy
            audio_np = audio_tensor.numpy()

            # Воспроизводим звук
            sd.play(audio_np, self.sample_rate)
            sd.wait()  # Блокируем выполнение кода, пока фраза не будет досказана до конца

        except Exception as e:
            print(f"❌ Ошибка при синтезе речи: {e}")