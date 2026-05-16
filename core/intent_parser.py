import os
import sys
import spacy

sys.path.append(os.path.dirname(os.path.abspath(__file__)))
import logger


class IntentParser:
    def __init__(self, model_path="./nlp/models/intent_model"):
        """Инициализация парсера с загрузкой обученной модели."""
        logger.system("NLU", f"загрузка обученной модели из {model_path}")
        try:
            self.nlp = spacy.load(model_path)
            labels = list(self.nlp.get_pipe("textcat").labels) if "textcat" in self.nlp.pipe_names else []
            logger.system("NLU", f"модель загружена, классы: {', '.join(labels)}")
        except OSError:
            logger.err(f"Модель '{model_path}' не найдена — переход на заглушку")
            self.nlp = spacy.blank("ru")

    def parse(self, text):
        """
        Прогоняет текст через модель и возвращает структурированный интент.
        """
        doc = self.nlp(text.lower())

        # 1. Извлекаем интент (категорию текста).
        # Предполагаем, что ваша модель вернет словарь вероятностей doc.cats
        # Берем тот интент, у которого вероятность наивысшая
        intent_name = "UNKNOWN_COMMAND"
        if hasattr(doc, 'cats') and doc.cats:
            intent_name = max(doc.cats, key=doc.cats.get)

        # 2. Извлекаем параметры (именованные сущности).
        # Например: {"ROOM": "кухне", "DEVICE": "свет"}
        entities = {}
        for ent in doc.ents:
            entities[ent.label_] = ent.lemma_ # Берем начальную форму слова

        return {
            "intent": intent_name,
            "entities": entities,
            "original_text": text,
            "spacy_doc": doc
        }