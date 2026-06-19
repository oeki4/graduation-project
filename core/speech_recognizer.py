import os
import sys
import json
import time
import queue
import sounddevice as sd
from vosk import Model, KaldiRecognizer

sys.path.append(os.path.dirname(os.path.abspath(__file__)))
import logger


class SpeechRecognizer:
    def __init__(self, model_path="vosk-model", samplerate=16000, device=None):
        """Инициализация распознавателя речи."""
        self.model_path = model_path
        self.samplerate = samplerate
        self.device = device
        self.q = queue.Queue()

        if not os.path.exists(self.model_path):
            raise FileNotFoundError(f"Модель не найдена по пути: {self.model_path}. Пожалуйста, скачайте её.")

        logger.system("STT", f"загрузка Vosk-модели из {model_path}/")
        self.model = Model(self.model_path)
        self.recognizer = KaldiRecognizer(self.model, self.samplerate)
        logger.system("STT", f"Vosk готов (sample rate {samplerate} Hz)")

    def _audio_callback(self, indata, frames, time, status):
        """Внутренний callback для передачи аудиоданных в очередь."""
        if status:
            print(status, file=sys.stderr)
        self.q.put(bytes(indata))

    def listen(self, yield_partial=False):
        """
        Генератор, который слушает микрофон в реальном времени.
        Возвращает словари с типом результата ('final' или 'partial') и самим текстом.
        """
        # Накапливаем чистое процессорное время декодирования Vosk за одну
        # фразу — от первого аудиоблока до финального результата. Это честная
        # метрика «как быстро модель переводит звук в текст».
        decode_ms = 0.0

        with sd.RawInputStream(samplerate=self.samplerate, blocksize=8000,
                               device=self.device, dtype='int16',
                               channels=1, callback=self._audio_callback):
            while True:
                data = self.q.get()

                t0 = time.perf_counter()
                is_final = self.recognizer.AcceptWaveform(data)
                decode_ms += (time.perf_counter() - t0) * 1000

                if is_final:
                    # Получаем итоговый результат (когда человек сделал паузу)
                    result_json = json.loads(self.recognizer.Result())
                    text = result_json.get("text", "")
                    if text:  # Возвращаем только если текст не пустой
                        yield {"type": "final", "text": text, "stt_ms": decode_ms}
                    decode_ms = 0.0  # сброс для следующей фразы
                else:
                    # Получаем промежуточный результат (во время речи)
                    if yield_partial:
                        partial_json = json.loads(self.recognizer.PartialResult())
                        partial_text = partial_json.get("partial", "")
                        if partial_text:
                            yield {"type": "partial", "text": partial_text}