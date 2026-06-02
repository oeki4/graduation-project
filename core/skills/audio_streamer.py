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
# 256 КБ — достаточно, чтобы пропустить ID3-теги и найти валидный MP3-фрейм
# даже на потоках с высоким битрейтом.
_PREBUFFER_BYTES = 256 * 1024


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

    def _apply_volume(self, audio: np.ndarray) -> np.ndarray:
        """
        Программно масштабирует PCM int16 на коэффициент громкости из
        assistant._software_volume. На I²S-DAC без аппаратной громкости
        это единственный способ менять уровень звука при стриминге.
        Применяется к каждому декодированному чанку перед write().
        """
        if self.assistant is None:
            return audio
        volume = getattr(self.assistant, "_software_volume", 1.0)
        if volume >= 0.999:
            return audio
        # Масштабирование int16 через временный int32 (защита от overflow)
        scaled = (audio.astype(np.int32) * volume).clip(-32768, 32767).astype(np.int16)
        return scaled

    # ------------------------------------------------------------------
    # Публичный интерфейс
    # ------------------------------------------------------------------

    def is_active(self) -> bool:
        """True, если сейчас идёт воспроизведение (радио/сказка)."""
        if self._playback_thread is not None and self._playback_thread.is_alive():
            return True
        if self._current_playback_process is not None:
            return self._current_playback_process.poll() is None
        return False

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
        Фоновый поток: загружает MP3 чанками, декодирует каждые ~32 КБ
        через miniaudio.decode() и сразу отдаёт PCM в sounddevice.
        Задержка до старта воспроизведения ≈ 2 сек.
        """
        out_stream = None
        response = None
        try:
            response = requests.get(
                url, stream=True, timeout=15,
                headers={"User-Agent": "VoiceAssistant/1.0"},
            )
            response.raise_for_status()

            # Порция MP3 для декодирования: 32 КБ ≈ 2 сек аудио при 128 кбит/с
            CHUNK_BYTES = 32 * 1024

            accumulator = bytearray()
            channels = None
            rate = None

            for raw in response.iter_content(chunk_size=4096):
                if stop_event.is_set():
                    break
                if not raw:
                    continue

                accumulator.extend(raw)

                if len(accumulator) < CHUNK_BYTES:
                    continue

                # Декодируем накопленный MP3-чанк
                try:
                    decoded = miniaudio.decode(
                        bytes(accumulator),
                        output_format=miniaudio.SampleFormat.SIGNED16,
                    )
                except miniaudio.DecodeError:
                    # Чанк попал на середину фрейма — копим ещё
                    continue

                audio = np.frombuffer(decoded.samples, dtype=np.int16)
                if decoded.nchannels > 1:
                    audio = audio.reshape(-1, decoded.nchannels)

                # Открываем выходной стрим на первой удачной декодировке
                if out_stream is None:
                    channels = decoded.nchannels
                    rate = decoded.sample_rate
                    out_stream = sd.OutputStream(
                        samplerate=rate, channels=channels, dtype='int16'
                    )
                    out_stream.start()
                    print(f"▶️  [STREAMER] Радио: {rate} Гц, {channels} кан. — играю")

                # Применяем программную громкость и отправляем PCM в sounddevice
                out_stream.write(self._apply_volume(audio))
                accumulator.clear()

            print("✅ [STREAMER] Радио: поток завершён.")

        except requests.RequestException as e:
            print(f"❌ [STREAMER] Ошибка подключения к радио: {e}")
        except Exception as e:
            print(f"❌ [STREAMER] Ошибка стриминга: {e}")
        finally:
            if out_stream:
                try:
                    out_stream.stop()
                    out_stream.close()
                except Exception:
                    pass
            if response:
                try:
                    response.close()
                except Exception:
                    pass

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
                stop_event.set()
                return

            # ── ФАЗА 1: декодируем и играем то, что скачано ──────────
            # Если декод не удался (мало данных, ID3-теги, неполный фрейм) —
            # ждём ещё немного и пробуем снова, до 6 попыток (~3 сек ожидания).
            phase1_audio, channels, rate, phase1_bytes = None, None, None, b""
            for attempt in range(6):
                if stop_event.is_set():
                    return
                buffer.seek(0)
                phase1_bytes = buffer.read()
                phase1_audio, channels, rate = self._decode_mp3(phase1_bytes)
                if phase1_audio is not None:
                    break
                if dl_done.is_set():
                    # Файл скачан полностью, но декод всё равно не идёт — конец
                    break
                print(f"⏳ [STREAMER] Декод не удался, жду ещё данные (попытка {attempt + 1})...")
                threading.Event().wait(0.5)

            if phase1_audio is None:
                print("❌ [STREAMER] Не удалось декодировать MP3. Останавливаю загрузку.")
                stop_event.set()
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

    def _play_audio(self, audio: np.ndarray, channels: int,
                    sample_rate: int, stop_event: threading.Event) -> int:
        """
        Воспроизводит numpy-массив PCM через sounddevice.
        Возвращает количество фреймов, реально воспроизведённых до остановки.
        Программная громкость применяется внутри callback'а, чтобы
        изменения уровня вступали в силу в реальном времени.
        """
        pos = [0]
        done = threading.Event()
        streamer = self  # для замыкания внутри callback

        def _callback(outdata, frames, _time, status):
            if stop_event.is_set():
                outdata[:] = 0
                done.set()
                raise sd.CallbackStop()

            start = pos[0]
            end = start + frames
            chunk = streamer._apply_volume(audio[start:end])

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
        # Берём текущую программную громкость ассистента (0.0–1.0), чтобы
        # сказки/радио звучали на том же уровне, что и TTS. Без этого cvlc
        # играл на 100% системной громкости, а TTS — приглушённый через
        # _software_volume, отсюда разница в громкости.
        volume = 1.0
        if self.assistant is not None:
            volume = getattr(self.assistant, "_software_volume", 1.0)
        volume = max(0.0, min(1.0, volume))

        try:
            print(f"🚀 [STREAMER] Стриминг через CVLC (Linux/Pi), громкость {int(volume*100)}%...")
            # cvlc --gain: множитель усиления, 1.0 = нормальный уровень.
            self._current_playback_process = subprocess.Popen(
                ["cvlc", "--play-and-exit", "--quiet",
                 "--gain", f"{volume:.2f}", url],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
            return True
        except FileNotFoundError:
            print("⚠️ [STREAMER] cvlc не найден, пробую ffplay...")

        try:
            # ffplay -volume: целое 0–100.
            self._current_playback_process = subprocess.Popen(
                ["ffplay", "-nodisp", "-autoexit",
                 "-volume", str(int(volume * 100)), url],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
            return True
        except FileNotFoundError:
            print("❌ [STREAMER] Ни cvlc, ни ffplay не найдены. "
                  "Установите: sudo apt install vlc")
            return False
