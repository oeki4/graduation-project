import os
import io
import threading
import subprocess

import requests
import numpy as np
import sounddevice as sd

# miniaudio используется для декодирования MP3 без внешних программ
try:
    import miniaudio
    _MINIAUDIO_AVAILABLE = True
except ImportError:
    _MINIAUDIO_AVAILABLE = False
    print("⚠️ [STREAMER] Библиотека miniaudio не установлена. "
          "Для работы на Windows выполните: pip install miniaudio")

# Размер начального буфера перед стартом воспроизведения.
# 512 КБ ≈ 30–60 секунд аудио при 64–128 кбит/с — этого достаточно,
# чтобы начать играть немедленно, пока остаток файла докачивается.
_PREBUFFER_BYTES = 512 * 1024


class AudioStreamer:
    """
    Класс для воспроизведения аудио по прямым URL.

    - Linux / Raspberry Pi: стриминг через системный процесс cvlc или ffplay.
    - Windows: двухфазный стриминг без сторонних программ:
        Фаза 1 — скачать первые ~512 КБ → декодировать → начать играть.
        Фаза 2 — пока идёт фаза 1, фоново докачивается остаток файла;
                 после окончания фазы 1 плавно продолжаем с полного файла.
      Требует: pip install miniaudio
    """

    def __init__(self, assistant=None):
        self.assistant = assistant

        # --- состояние для Windows-плеера ---
        self._stop_event = threading.Event()
        self._playback_thread: threading.Thread | None = None

        # --- состояние для Linux-процесса ---
        self._current_playback_process: subprocess.Popen | None = None

    # ------------------------------------------------------------------
    # Публичный интерфейс
    # ------------------------------------------------------------------

    def play_url(self, url: str) -> bool:
        """Воспроизводит аудио по прямой URL-ссылке."""
        self.stop()
        print(f"🎵 [STREAMER] Запуск воспроизведения: {url}")

        if os.name == 'nt':
            return self._play_windows(url)
        else:
            return self._play_linux(url)

    def stop(self):
        """Останавливает текущее воспроизведение."""
        # Останавливаем Windows-поток
        if self._playback_thread and self._playback_thread.is_alive():
            print("🛑 [STREAMER] Остановка Python-плеера...")
            self._stop_event.set()
            self._playback_thread.join(timeout=3)
            sd.stop()

        # Останавливаем Linux-процесс
        if self._current_playback_process:
            try:
                print("🛑 [STREAMER] Остановка системного плеера...")
                self._current_playback_process.terminate()
                self._current_playback_process.wait(timeout=2)
            except Exception:
                if self._current_playback_process:
                    self._current_playback_process.kill()
                print("⚠️ [STREAMER] Процесс плеера завершён принудительно.")
            finally:
                self._current_playback_process = None

    # ------------------------------------------------------------------
    # Windows: двухфазный стриминг
    # ------------------------------------------------------------------

    def _play_windows(self, url: str) -> bool:
        if not _MINIAUDIO_AVAILABLE:
            print("❌ [STREAMER] miniaudio не установлен. Установите: pip install miniaudio")
            return False

        self._stop_event = threading.Event()
        self._playback_thread = threading.Thread(
            target=self._stream_two_phase,
            args=(url, self._stop_event),
            daemon=True,
        )
        self._playback_thread.start()
        return True

    def _stream_two_phase(self, url: str, stop_event: threading.Event):
        """
        Фоновый поток: двухфазный стриминг.

        Фаза 1: как только накоплено _PREBUFFER_BYTES байт — декодируем
                их и начинаем воспроизведение, не дожидаясь полной загрузки.
        Фаза 2: пока идёт воспроизведение фазы 1, фоново докачивается весь
                файл. После завершения фазы 1 декодируем полный файл и
                продолжаем с позиции, на которой остановились.
        """
        try:
            buffer = io.BytesIO()          # растущий буфер с данными файла
            prebuf_ready = threading.Event()  # сигнал: первые N байт готовы
            dl_done = threading.Event()       # сигнал: файл скачан полностью

            # ── фоновая загрузка ──────────────────────────────────────
            def _download():
                try:
                    response = requests.get(url, stream=True, timeout=15)
                    response.raise_for_status()
                    total = 0
                    for chunk in response.iter_content(chunk_size=65_536):
                        if stop_event.is_set():
                            return
                        buffer.write(chunk)
                        total += len(chunk)
                        if total % (256 * 1024) < 65_536:
                            print(f"⬇️  [STREAMER] Загружено: {total // 1024} КБ")
                        # Сигналим, как только накоплен начальный буфер
                        if not prebuf_ready.is_set() and total >= _PREBUFFER_BYTES:
                            prebuf_ready.set()
                    print(f"✅ [STREAMER] Загрузка завершена: {total // 1024} КБ")
                finally:
                    dl_done.set()
                    prebuf_ready.set()  # на случай, если файл меньше _PREBUFFER_BYTES

            dl_thread = threading.Thread(target=_download, daemon=True)
            dl_thread.start()

            # ── ждём начального буфера ────────────────────────────────
            print(f"⏳ [STREAMER] Буферизация ({_PREBUFFER_BYTES // 1024} КБ)...")
            if not prebuf_ready.wait(timeout=30) or stop_event.is_set():
                return

            # ── ФАЗА 1: декодируем и играем то, что скачано ──────────
            buffer.seek(0)
            phase1_bytes = buffer.read()
            phase1_audio, channels, rate = self._decode_mp3(phase1_bytes)
            if phase1_audio is None:
                return

            duration1 = len(phase1_audio) / rate
            print(f"▶️  [STREAMER] Фаза 1: воспроизведение "
                  f"{duration1:.1f} сек ({len(phase1_bytes) // 1024} КБ)")

            frames_played = self._play_audio(phase1_audio, channels, rate, stop_event)

            if stop_event.is_set():
                return

            # ── ФАЗА 2: играем оставшуюся часть файла ────────────────
            # Ждём окончания загрузки (обычно уже завершена к этому моменту)
            if not dl_done.is_set():
                print("⏳ [STREAMER] Ожидание окончания загрузки...")
                dl_done.wait()

            if stop_event.is_set():
                return

            buffer.seek(0)
            full_bytes = buffer.read()

            # Если файл не изменился (всё уже было в фазе 1) — выходим
            if len(full_bytes) <= len(phase1_bytes):
                print("✅ [STREAMER] Воспроизведение завершено.")
                return

            full_audio, _, _ = self._decode_mp3(full_bytes)
            if full_audio is None:
                return

            # Пропускаем уже проигранные фреймы
            remaining = full_audio[frames_played:]
            if len(remaining) == 0:
                print("✅ [STREAMER] Воспроизведение завершено.")
                return

            duration2 = len(remaining) / rate
            print(f"▶️  [STREAMER] Фаза 2: продолжение "
                  f"({duration2:.1f} сек оставшегося аудио)")

            self._play_audio(remaining, channels, rate, stop_event)
            print("✅ [STREAMER] Воспроизведение завершено.")

        except requests.RequestException as e:
            print(f"❌ [STREAMER] Ошибка загрузки: {e}")
        except Exception as e:
            print(f"❌ [STREAMER] Неожиданная ошибка: {e}")

    # ------------------------------------------------------------------
    # Вспомогательные методы
    # ------------------------------------------------------------------

    @staticmethod
    def _decode_mp3(mp3_bytes: bytes):
        """
        Декодирует MP3-байты в numpy-массив PCM.
        Возвращает (audio_array, channels, sample_rate) или (None, None, None).
        Корректно обрабатывает неполный конец файла (усечённый MP3).
        """
        try:
            decoded = miniaudio.decode(
                mp3_bytes,
                output_format=miniaudio.SampleFormat.SIGNED16,
            )
            audio = np.frombuffer(decoded.samples, dtype=np.int16)
            channels = decoded.nchannels
            rate = decoded.sample_rate
            if channels > 1:
                audio = audio.reshape(-1, channels)
            return audio, channels, rate
        except miniaudio.DecodeError as e:
            print(f"❌ [STREAMER] Ошибка декодирования MP3: {e}")
            return None, None, None

    @staticmethod
    def _play_audio(audio: np.ndarray, channels: int,
                    sample_rate: int, stop_event: threading.Event) -> int:
        """
        Воспроизводит numpy-массив PCM через sounddevice.
        Возвращает количество фреймов, реально воспроизведённых до остановки.
        """
        pos = [0]
        done = threading.Event()

        def _callback(outdata, frames, _time, status):
            if stop_event.is_set():
                outdata[:] = 0
                done.set()
                raise sd.CallbackStop()

            start = pos[0]
            end = start + frames
            chunk = audio[start:end]

            if len(chunk) == 0:
                outdata[:] = 0
                done.set()
                raise sd.CallbackStop()

            if len(chunk) < frames:
                # Последний кусок — хвост заполняем тишиной
                if channels > 1:
                    outdata[:len(chunk)] = chunk
                    outdata[len(chunk):] = 0
                else:
                    outdata[:len(chunk), 0] = chunk
                    outdata[len(chunk):, 0] = 0
                pos[0] = end
                done.set()
                raise sd.CallbackStop()
            else:
                if channels > 1:
                    outdata[:] = chunk
                else:
                    outdata[:, 0] = chunk
                pos[0] = end

        with sd.OutputStream(
            samplerate=sample_rate,
            channels=channels,
            dtype='int16',
            callback=_callback,
        ):
            done.wait()

        return pos[0]  # сколько фреймов реально проиграно

    # ------------------------------------------------------------------
    # Linux / Raspberry Pi: системный процесс cvlc / ffplay
    # ------------------------------------------------------------------

    def _play_linux(self, url: str) -> bool:
        try:
            print("🚀 [STREAMER] Стриминг через CVLC (Linux/Pi)...")
            self._current_playback_process = subprocess.Popen(
                ["cvlc", "--play-and-exit", "--quiet", url],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
            return True
        except FileNotFoundError:
            print("⚠️ [STREAMER] cvlc не найден, пробую ffplay...")

        try:
            self._current_playback_process = subprocess.Popen(
                ["ffplay", "-nodisp", "-autoexit", url],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
            return True
        except FileNotFoundError:
            print("❌ [STREAMER] Ни cvlc, ни ffplay не найдены. "
                  "Установите: sudo apt install vlc")
            return False
