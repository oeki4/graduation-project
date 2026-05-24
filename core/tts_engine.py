import os
import sys
import wave
import tempfile
import subprocess
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

    def speak(self, text, volume: float = 1.0):
        """
        Синтезирует текст в речь и сразу воспроизводит.

        Параметр volume (0.0–1.0) — программное масштабирование PCM
        перед воспроизведением. Используется на Linux/Pi, где
        I²S-DAC не имеет аппаратной регулировки громкости.
        На Windows volume игнорируется (там используется системная
        громкость через pycaw).
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

            # Конвертируем float32 → int16 с защитой от клиппинга.
            # Применяем volume сразу здесь, пока ещё в float — точнее.
            scaled_f32 = audio_f32 * (32767.0 * max(0.0, min(1.0, volume)))
            audio_i16 = scaled_f32.clip(-32768, 32767).astype(np.int16)

            # На Linux (Raspberry Pi) воспроизводим через subprocess + aplay:
            # sounddevice на медленных I²S DAC даёт стену underrun-ов.
            # aplay — родная утилита ALSA, сама управляет буферами, проверена.
            if os.name == "posix":
                _play_pcm_via_aplay(audio_i16, self.sample_rate, channels=1)
            else:
                sd.play(audio_i16, self.sample_rate, blocking=True)

        except Exception as e:
            print(f"❌ Ошибка при синтезе речи: {e}")


def _play_pcm_via_aplay(audio_i16: np.ndarray, sample_rate: int, channels: int = 1):
    """
    Пишет PCM-массив в временный WAV-файл и проигрывает через aplay.

    Использовать только на Linux. Это самый надёжный способ воспроизведения
    на Raspberry Pi с I²S-усилителем — обходит проблемы sounddevice/PortAudio
    с буферизацией на медленных DAC.
    """
    # Создаём временный WAV-файл с нужным форматом
    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
        tmp_path = f.name
    try:
        with wave.open(tmp_path, "wb") as wf:
            wf.setnchannels(channels)
            wf.setsampwidth(2)  # int16 = 2 байта
            wf.setframerate(sample_rate)
            wf.writeframes(audio_i16.tobytes())

        # aplay -q: тихий режим, без вывода в консоль
        subprocess.run(
            ["aplay", "-q", tmp_path],
            stderr=subprocess.DEVNULL,
            check=False,
        )
    finally:
        try:
            os.unlink(tmp_path)
        except Exception:
            pass