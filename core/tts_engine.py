import torch
import sounddevice as sd

class TTSEngine:
    def __init__(self, speaker='aidar', sample_rate=24000):
        """
        Инициализация движка синтеза речи.
        'aidar' - отличный мужской голос, звучит естественно. 'eugene' тоже мужской.
        sample_rate снижен до 24000 для экономии ресурсов CPU без потери качества голоса.
        Доступные голоса: 'aidar', 'baya', 'kseniya', 'xenia', 'eugene'
        """
        print("🔊 Загрузка голосового модуля (Silero TTS)... Это может занять пару секунд.")
        self.device = torch.device('cpu')
        
        # Оптимизация PyTorch JIT для CPU (дает ускорение сопоставимое с ONNX)
        torch.set_num_threads(4)
        
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