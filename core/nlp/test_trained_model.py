import spacy
import os

def main():
    model_path = r"f:\projects\graduation-project\core\nlp\models\intent_model"
    
    print(f"Загрузка обученной модели из {model_path}...")
    if not os.path.exists(model_path):
        print("Ошибка: Модель не найдена! Сначала запустите train-model.py для её обучения.")
        return

    try:
        nlp = spacy.load(model_path)
    except Exception as e:
        print(f"Ошибка при загрузке модели: {e}")
        return

    print("Модель успешно загружена!")
    print("\n--- Тестирование классификатора интентов ---")
    print("Вводите фразы для проверки (или 'выход' / 'exit' для завершения).\n")

    while True:
        try:
            text = input("Вы: ")
        except (KeyboardInterrupt, EOFError):
            print("\nВыход...")
            break
            
        if text.strip().lower() in ['выход', 'exit', 'quit']:
            break
            
        if not text.strip():
            continue

        # Обработка текста
        doc = nlp(text)
        
        # Получение всех вероятностей
        cats = doc.cats
        
        if not cats:
            print("Предупреждение: Модель не вернула вероятностей. Убедитесь, что пайплайн textcat был обучен.")
            continue
            
        # Сортировка по убыванию вероятности
        sorted_cats = sorted(cats.items(), key=lambda item: item[1], reverse=True)
        
        # Лучший интент
        best_intent, best_score = sorted_cats[0]
        
        print(f"Модель: Интент -> {best_intent} (Уверенность: {best_score:.4f})")
        
        # Вывод остальных вероятностей, если хотите дебажить
        # print("        Все оценки:", ", ".join([f"{k}: {v:.4f}" for k, v in sorted_cats]))
        print("-" * 50)

if __name__ == "__main__":
    main()
