import os
import sys
import json
import queue
import sounddevice as sd
from vosk import Model, KaldiRecognizer

class SpeechRecognizer:
    def __init__(self, model_path="vosk-model", samplerate=16000, device=None):
        """
        Инициализация распознавателя речи.
        """
        self.model_path = model_path
        self.samplerate = samplerate
        self.device = device
        self.q = queue.Queue()

        # Проверка наличия модели перед запуском
        if not os.path.exists(self.model_path):
            raise FileNotFoundError(f"Модель не найдена по пути: {self.model_path}. Пожалуйста, скачайте её.")

        # Инициализация Vosk
        self.model = Model(self.model_path)
        self.recognizer = KaldiRecognizer(self.model, self.samplerate)

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
        with sd.RawInputStream(samplerate=self.samplerate, blocksize=8000,
                               device=self.device, dtype='int16',
                               channels=1, callback=self._audio_callback):
            while True:
                data = self.q.get()

                if self.recognizer.AcceptWaveform(data):
                    # Получаем итоговый результат (когда человек сделал паузу)
                    result_json = json.loads(self.recognizer.Result())
                    text = result_json.get("text", "")
                    if text: # Возвращаем только если текст не пустой
                        yield {"type": "final", "text": text}
                else:
                    # Получаем промежуточный результат (во время речи)
                    if yield_partial:
                        partial_json = json.loads(self.recognizer.PartialResult())
                        partial_text = partial_json.get("partial", "")
                        if partial_text:
                            yield {"type": "partial", "text": partial_text}