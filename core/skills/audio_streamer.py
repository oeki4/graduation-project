import os
import subprocess
import threading

class AudioStreamer:
    """
    Класс для СТРИМИНГА аудио по прямым ссылкам без скачивания во временные файлы.
    Это экономит память и время на Raspberry Pi.
    """
    # Будем хранить ссылку на текущий запущенный процесс игрока здесь, 
    # чтобы ассистент мог принудительно остановить проигрывание в любой момент.
    _current_playback_process = None

    def __init__(self, assistant=None):
        self.assistant = assistant

    def play_url(self, url):
        """
        Воспроизводит аудио напрямую из интернета (стриминг).
        """
        # Если что-то уже играет, пробуем остановить
        self.stop()
        
        print(f"🎵 [STREAMER] Попытка запуска прямого стрима: {url}")

        if os.name == 'posix': # Raspberry Pi / Linux
            # Используем cvlc (VLC без интерфейса) — он идеально стримит URL
            try:
                print("🚀 [STREAMER] Стриминг через CVLC (Linux/Pi)...")
                # --play-and-exit: закрыть плеер после окончания 
                # --quiet: не выводить лишние логи в консоль
                AudioStreamer._current_playback_process = subprocess.Popen(
                    ["cvlc", "--play-and-exit", "--quiet", url],
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL
                )
                return True
            except FileNotFoundError:
                print("❌ [STREAMER] Системный стример (cvlc) не найден. Установите: sudo apt install vlc")
                # На Raspberry Pi можно еще попробовать ffplay
                try:
                    AudioStreamer._current_playback_process = subprocess.Popen(
                        ["ffplay", "-nodisp", "-autoexit", url],
                        stdout=subprocess.DEVNULL,
                        stderr=subprocess.DEVNULL
                    )
                    return True
                except FileNotFoundError:
                    print("❌ [STREAMER] Альтернатива (ffplay) тоже не найдена.")
                    return False

        elif os.name == 'nt': # Windows
            # В Windows проще всего вызвать системный обработчик ссылки (браузер или плеер)
            try:
                print("🪟 [STREAMER] Стриминг через Windows Shell (откроется системный плеер)...")
                # Прямая ссылка откроется в плеере по умолчанию почти мгновенно
                os.startfile(url)
                return True
            except Exception as e:
                print(f"❌ [STREAMER] Ошибка стрима в Windows: {e}")
                return False

    def stop(self):
        """
        Останавливает текущее воспроизведение, если оно идет.
        """
        if AudioStreamer._current_playback_process:
            try:
                print("🛑 [STREAMER] Попытка принудительной остановки музыки...")
                AudioStreamer._current_playback_process.terminate()
                # Если системный процесс сопротивляется — убиваем его
                AudioStreamer._current_playback_process.wait(timeout=2)
                AudioStreamer._current_playback_process = None
            except Exception:
                if AudioStreamer._current_playback_process:
                    AudioStreamer._current_playback_process.kill()
                    AudioStreamer._current_playback_process = None
                print("⚠️ [STREAMER] Ошибка при плавном завершении плеера, процесс убит принудительно.")
