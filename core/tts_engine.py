import os
import sys
import torch
import numpy as np
import sounddevice as sd
import ssl

sys.path.append(os.path.dirname(os.path.abspath(__file__)))
import logger

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
        logger.system("TTS", f"загрузка Silero v4_ru (голос: {speaker}, sr={sample_rate}) ...")
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
            logger.system("TTS", "Silero готов")
        except Exception as e:
            print(f"❌ Ошибка загрузки Silero TTS: {e}")
            raise

    def speak(self, text):
        """
        Синтезирует текст в речь и сразу воспроизводит.

        Реализация специально использует int16 PCM и явный sd.OutputStream,
        а не sd.play() с float32. Причина: ALSA-plug + dmix на Raspberry Pi
        с I²S-усилителем (MAX98357A, voiceHAT и т. п.) при float32 выдаёт
        хрипы и сильно занижает громкость. С int16 поток идёт чисто.
        """
        if not text:
            return

        try:
            # Silero выдаёт float32 в диапазоне [-1.0, 1.0]
            audio_tensor = self.model.apply_tts(
                text=text,
                speaker=self.speaker,
                sample_rate=self.sample_rate,
                put_accent=True,
                put_yo=True,
            )
            audio_f32 = audio_tensor.numpy()

            # Конвертируем float32 → int16 с защитой от клиппинга
            audio_i16 = (audio_f32 * 32767.0).clip(-32768, 32767).astype(np.int16)

            # Явный OutputStream с указанными channels/dtype — стабильнее на I²S
            with sd.OutputStream(
                samplerate=self.sample_rate,
                channels=1,
                dtype="int16",
            ) as out:
                out.write(audio_i16)

        except Exception as e:
            print(f"❌ Ошибка при синтезе речи: {e}")