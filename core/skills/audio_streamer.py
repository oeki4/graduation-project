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

# Размер начального буфера перед стартом воспроизведения для файлов (сказки).
# 64 КБ ≈ 4 сек аудио при 128 кбит/с — достаточно, чтобы начать играть быстро.
_PREBUFFER_BYTES = 64 * 1024

# Размер порции фреймов при стриминге радио (фреймов PCM за один вызов)
_RADIO_FRAMES_PER_READ = 4096


class _HttpStream(io.RawIOBase):
    """
    Обёртка над requests-стримингом как файлоподобный объект для miniaudio.
    Позволяет декодировать аудио по мере загрузки без ожидания полного скачивания.
    """

    def __init__(self, url: str, stop_event: threading.Event):
        self._stop = stop_event
        self._buf = b""
        self._exhausted = False
        self._response = requests.get(
            url, stream=True, timeout=15,
            headers={"User-Agent": "VoiceAssistant/1.0"},
        )
        self._response.raise_for_status()
        self._iter = self._response.iter_content(chunk_size=8192)

    def readinto(self, b):
        if self._stop.is_set() or self._exhausted:
            return 0
        # Дочитываем из буфера или загружаем следующий чанк
        while len(self._buf) < len(b):
            try:
                chunk = next(self._iter)
                if chunk:
                    self._buf += chunk
            except StopIteration:
                self._exhausted = True
                break
        n = min(len(b), len(self._buf))
        if n == 0:
            return 0
        b[:n] = self._buf[:n]
        self._buf = self._buf[n:]
        return n

    def readable(self):
        return True

    def close(self):
        try:
            self._response.close()
        except Exception:
            pass
        super().close()


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
        """Воспроизводит аудиофайл по URL (двухфазный буфер — для сказок)."""
        self.stop()
        print(f"🎵 [STREAMER] Запуск воспроизведения файла: {url}")

        if os.name == 'nt':
            return self._play_windows(url)
        else:
            return self._play_linux(url)

    def play_stream(self, url: str) -> bool:
        """
        Истинный стриминг для живого радио (бесконечный поток).
        Декодирует и воспроизводит MP3 по мере получения данных —
        воспроизведение начинается через ~1–2 сек после вызова.
        """
        self.stop()
        if not _MINIAUDIO_AVAILABLE:
            print("❌ [STREAMER] miniaudio не установлен: pip install miniaudio")
            return False

        print(f"📻 [STREAMER] Запуск радио стриминга: {url}")
        self._stop_event = threading.Event()
        self._playback_thread = threading.Thread(
            target=self._stream_radio,
            args=(url, self._stop_event),
            daemon=True,
        )
        self._playback_thread.start()
        return True

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
    # Радио: истинный HTTP-стриминг без буферизации полного файла
    # ------------------------------------------------------------------

    def _stream_radio(self, url: str, stop_event: threading.Event):
        """
        Фоновый поток: открывает HTTP-поток, декодирует MP3 порциями
        через miniaudio и сразу отдаёт PCM в sounddevice.
        Задержка до старта воспроизведения ≈ 1–2 сек.
        """
        http_stream = None
        try:
            http_stream = _HttpStream(url, stop_event)
            buffered = io.BufferedReader(http_stream, buffer_size=32768)

            ma_stream = miniaudio.stream_any(
                buffered,
                source_format=miniaudio.FileFormat.MP3,
                output_format=miniaudio.SampleFormat.SIGNED16,
                nchannels=2,
                sample_rate=44100,
                frames_to_read=_RADIO_FRAMES_PER_READ,
            )

            # Берём первый фрейм чтобы узнать реальные параметры потока
            first = next(ma_stream, None)
            if first is None or stop_event.is_set():
                return

            channels = first.nchannels
            rate = first.sample_rate
            print(f"▶️  [STREAMER] Радио: {rate} Гц, {channels} кан. — начало воспроизведения")

            with sd.OutputStream(samplerate=rate, channels=channels, dtype='int16') as out:
                # Воспроизводим первый фрейм
                audio = np.frombuffer(first.samples, dtype=np.int16)
                if channels > 1:
                    audio = audio.reshape(-1, channels)
                out.write(audio)

                # Непрерывно читаем и воспроизводим остальные фреймы
                for frame in ma_stream:
                    if stop_event.is_set():
                        break
                    audio = np.frombuffer(frame.samples, dtype=np.int16)
                    if channels > 1:
                        audio = audio.reshape(-1, channels)
                    out.write(audio)

            print("✅ [STREAMER] Радио: поток завершён.")

        except requests.RequestException as e:
            print(f"❌ [STREAMER] Ошибка подключения к радио: {e}")
        except Exception as e:
            print(f"❌ [STREAMER] Ошибка стриминга: {e}")
        finally:
            if http_stream:
                http_stream.close()

    # ------------------------------------------------------------------
    # Windows: двухфазный стриминг (для файлов — сказки)
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
