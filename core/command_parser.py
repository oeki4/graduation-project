import spacy

class CommandParser:
    def __init__(self, model_name="ru_core_news_sm"):
        print("🧠 Инициализация NLP-модуля (spaCy)...")
        try:
            # Загружаем языковую модель
            self.nlp = spacy.load(model_name)
        except OSError:
            print(f"❌ Модель '{model_name}' не найдена.")
            print(f"Выполните команду: python -m spacy download {model_name}")
            raise

    def parse(self, text):
        """
        Анализирует текст и извлекает действие (глагол) и объект (существительное).
        Возвращает словарь с начальными формами слов.
        """
        doc = self.nlp(text.lower())

        action = None
        target = None

        # Проходим по каждому слову в предложении
        for token in doc:
            # Игнорируем стоп-слова (междометия, предлоги и т.д.), если нужно
            if token.is_stop:
                continue

            # Ищем корень предложения (обычно это глагол-действие)
            if token.dep_ == "ROOT" and token.pos_ == "VERB":
                action = token.lemma_  # Берем начальную форму (включи -> включать)

            # Ищем прямое дополнение (объект действия)
            elif token.dep_ in ("obj", "nsubj") and token.pos_ in ("NOUN", "PROPN"):
                target = token.lemma_  # (свет -> свет, лампу -> лампа)

        return {
            "original_text": text,
            "action": action,
            "target": target
        }