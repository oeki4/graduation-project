import os
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
            # Кодируем запрос в Windows-1251 (CP1251) — нативная кодировка сайта
            encoded_query = query.encode('cp1251')
            # Параметры поиска mp3tales.info:
            #   s   — поисковый запрос
            #   t   — режим AND (все слова должны встретиться)
            #   wz  — искать в заглавиях
            #   wp  — искать в описаниях
            url = f"{self.SEARCH_URL}?s={urllib.parse.quote_plus(encoded_query)}&t=AND&wz=1&wp=1"
            
            response = requests.get(url, headers=self.headers, timeout=10)
            response.encoding = 'cp1251'

            if response.status_code != 200:
                if os.environ.get("SCRAPER_DEBUG"):
                    print(f"   [SCRAPER] статус {response.status_code}")
                return None

            # Ищем ссылку на первую найденную сказку в HTML
            # Паттерн, который понимает разные кавычки и порядок атрибутов
            regex = r'href=[\"\'](/tales/\?id=\d+)[\"\'][^>]*class=[\"\']thumbnail[\"\']'
            match = re.search(regex, response.text)

            if not match:
                # Вторая попытка: более простой поиск любой ссылки с id
                match = re.search(r'href=[\"\'](/tales/\?id=\d+)[\"\']', response.text)

            if match:
                return self.BASE_URL + match.group(1)

            return None
        except Exception as e:
            if os.environ.get("SCRAPER_DEBUG"):
                print(f"   [SCRAPER] ошибка поиска: {e}")
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
            if os.environ.get("SCRAPER_DEBUG"):
                print(f"   [SCRAPER] ошибка получения аудио: {e}")
            return None
