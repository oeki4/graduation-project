import torch
import sounddevice as sd
import ssl

ssl._create_default_https_context = ssl._create_unverified_context


class TTSEngine:
    def __init__(self, speaker='xenia', sample_rate=24000):
        """
        Инициализация движка синтеза речи (Silero v4_ru).

        Выбор голоса не влияет на время загрузки — модель одна, меняется
        только спикер. По качеству и естественности (от лучшего к худшему):
            'xenia'   — молодой женский, самый естественный (по умолчанию)
            'baya'    — спокойный женский, дикторский тон
            'kseniya' — взрослый женский
            'aidar'   — мужской, чуть «роботичнее»
            'eugene'  — мужской, наиболее формальный
            'random'  — случайный голос на каждый вызов

        sample_rate=24000 — баланс качества и нагрузки на CPU. 48000 даёт
        чуть более чистый звук, но синтез на Raspberry Pi становится в 2 раза
        медленнее (ощутимо при ответах ассистента).
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