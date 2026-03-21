import spacy

class IntentParser:
    def __init__(self, model_path="./nlp/models/intent_model"):
        """
        Инициализация парсера с загрузкой вашей обученной модели.
        """
        print(f"🧠 Загрузка кастомной NLP-модели из '{model_path}'...")
        try:
            self.nlp = spacy.load(model_path)
        except OSError:
            print(f"⚠️ Модель '{model_path}' не найдена. Убедитесь, что скрипт обучения отработал.")
            # Для тестирования можно загрузить стандартную модель или создать заглушку
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