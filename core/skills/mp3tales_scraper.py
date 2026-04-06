import requests
import re
import urllib.parse

class Mp3TalesScraper:
    BASE_URL = "http://mp3tales.info"
    SEARCH_URL = f"{BASE_URL}/tales/"
    AUDIO_URL_PREFIX = f"{BASE_URL}/audio/"

    def __init__(self):
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }

    def search_fairytale(self, query):
        """
        Ищет сказку по названию и возвращает URL первой найденной страницы.
        """
        try:
            # Кодируем запрос в Windows-1251 (CP1251)
            encoded_query = query.encode('cp1251')
            # Добавляем PageSpeed=noscript для обхода редиректов и упрощения верстки
            url = f"{self.SEARCH_URL}?wp=1&s={urllib.parse.quote_plus(encoded_query)}&PageSpeed=noscript"
            
            print(f"🔍 [SCRAPER] Поиск на: {url}")
            response = requests.get(url, headers=self.headers, timeout=10)
            response.encoding = 'cp1251'

            # --- ОТЛАДОЧНАЯ ИНФОРМАЦИЯ ---
            print(f"📊 [DEBUG] Статус-код: {response.status_code} | Всего текста: {len(response.text)} символов")
            if len(response.text) < 500:
                print(f"⚠️ [DEBUG] Слишком короткий ответ от сервера. Начало: {response.text[:200]}")
            # -------------------------------

            if response.status_code != 200:
                print(f"❌ [SCRAPER] Ошибка доступа к сайту: {response.status_code}")
                return None

            # Ищем ссылку на первую найденную сказку в HTML
            # Паттерн, который понимает разные кавычки и порядок атрибутов
            regex = r'href=[\"\'](/tales/\?id=\d+)[\"\'][^>]*class=[\"\']thumbnail[\"\']'
            match = re.search(regex, response.text)
            
            if not match:
                # Вторая попытка: более простой поиск любой ссылки с id
                print("🔎 [DEBUG] Основное совпадение не найдено, пробую упрощенный поиск любой ссылки с id...")
                match = re.search(r'href=[\"\'](/tales/\?id=\d+)[\"\']', response.text)

            if match:
                found_url = self.BASE_URL + match.group(1)
                print(f"✅ [SCRAPER] Страница найдена: {found_url}")
                return found_url
            
            # Если не нашли — сохраним страницу для анализа
            debug_file = "debug_search.html"
            try:
                with open(debug_file, "w", encoding="cp1251") as f:
                    f.write(response.text)
                print(f"⚠️ [SCRAPER] Сказка не найдена. Результат поиска сохранен в '{debug_file}'")
            except Exception as e_log:
                print(f"❌ [DEBUG] Не удалось записать лог-файл: {e_log}")

            return None
        except Exception as e:
            print(f"❌ [SCRAPER] Ошибка при поиске: {e}")
            return None
        except Exception as e:
            print(f"❌ [SCRAPER] Ошибка при поиске: {e}")
            return None

    def get_audio_url(self, page_url):
        """
        Парсит страницу сказки и извлекает прямую ссылку на MP3.
        """
        try:
            response = requests.get(page_url, headers=self.headers, timeout=10)
            if response.status_code != 200:
                return None

            # Ищем название файла в атрибуте data-file="tajna_tretej_planety.mp3"
            # Или в теге <source src="..."
            match = re.search(r'data-file="([^"]+\.mp3)"', response.text)
            if not match:
                # Попробуем альтернативный поиск через <source>
                match = re.search(r'<source [^>]*src="(https?://[^"]+\.mp3)"', response.text)
            
            if match:
                audio_file = match.group(1)
                # Если нашли только имя файла, добавляем префикс
                if not audio_file.startswith("http"):
                    return self.AUDIO_URL_PREFIX + audio_file
                return audio_file
            
            return None
        except Exception as e:
            print(f"❌ [SCRAPER] Ошибка при получении аудио: {e}")
            return None
