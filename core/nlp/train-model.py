import spacy
from spacy.training.example import Example
from spacy.tokens import DocBin
import random
import json
import os

def load_data(filepath, label):
    """Загружает данные из текстового файла и присваивает им метку."""
    if not os.path.exists(filepath):
        print(f"Файл {filepath} не найден!")
        return []
    with open(filepath, 'r', encoding='utf-8') as f:
        texts = [line.strip() for line in f if line.strip()]
    
    data = []
    for text in texts:
        data.append((text, label))
    return data

def build_spacy_format(data, all_labels):
    """Форматирует данные в словарь категорий, необходимый для spaCy."""
    formatted = []
    for text, label in data:
        cats = {l: (1.0 if l == label else 0.0) for l in all_labels}
        formatted.append((text, {"cats": cats}))
    return formatted

def create_docbin(data, nlp, out_path):
    """Создает бинарные файлы датасета .spacy для стандартного обучения."""
    doc_bin = DocBin()
    for text, annotations in data:
        doc = nlp.make_doc(text)
        doc.cats = annotations['cats']
        doc_bin.add(doc)
    doc_bin.to_disk(out_path)

def main():
    # Используем относительный путь, чтобы скрипт работал и на Windows, и на Raspberry Pi
    base_dir = os.path.dirname(os.path.abspath(__file__))
    
    # 1. Загрузка сырых данных
    fairytale_data = load_data(os.path.join(base_dir, "fairytale.txt"), "FAIRYTALE")
    weather_data = load_data(os.path.join(base_dir, "weather.txt"), "WEATHER")
    other_data = load_data(os.path.join(base_dir, "other.txt"), "OTHER")
    
    all_data = fairytale_data + weather_data + other_data
    
    if not all_data:
        print("Данные не найдены! Убедитесь, что txt файлы существуют и заполнены.")
        return

    # 2. Разделение данных случайным образом на train и dev выборку (80/20)
    random.shuffle(all_data)
    split_idx = int(len(all_data) * 0.8)
    train_texts = all_data[:split_idx]
    dev_texts = all_data[split_idx:]
    
    all_labels = ["FAIRYTALE", "WEATHER", "OTHER"]
    
    train_data = build_spacy_format(train_texts, all_labels)
    dev_data = build_spacy_format(dev_texts, all_labels)
    
    # 3. Сохранение датасетов в JSON для наглядности (по запросу)
    train_json_path = os.path.join(base_dir, "dataset_train.json")
    dev_json_path = os.path.join(base_dir, "dataset_dev.json")
    
    with open(train_json_path, 'w', encoding='utf-8') as f:
        json.dump(train_data, f, ensure_ascii=False, indent=2)
    with open(dev_json_path, 'w', encoding='utf-8') as f:
        json.dump(dev_data, f, ensure_ascii=False, indent=2)
        
    print(f"Сформированы JSON файлы датасета: {train_json_path} и {dev_json_path}")

    # 4. Инициализация базовой модели ru_core_news_md
    print("Загрузка базовой модели spaCy (ru_core_news_md)...")
    try:
        nlp = spacy.load("ru_core_news_md")
    except Exception as e:
        print("Модель ru_core_news_md не найдена.")
        print("Перед запуском скрипта выполните: python -m spacy download ru_core_news_md")
        return

    # Создание .spacy бинарных файлов датасета (стандарт spaCy v3)
    train_spacy_path = os.path.join(base_dir, "train.spacy")
    dev_spacy_path = os.path.join(base_dir, "dev.spacy")
    create_docbin(train_data, nlp, train_spacy_path)
    create_docbin(dev_data, nlp, dev_spacy_path)
    print(f"Сформированы .spacy датасет файлы: {train_spacy_path} и {dev_spacy_path}")

    # 5. Добавление textcat пайплайна в модель, если он отсутствует
    if "textcat" not in nlp.pipe_names:
        textcat = nlp.add_pipe("textcat", last=True)
    else:
        textcat = nlp.get_pipe("textcat")
        
    # Добавление названий интентов (лейблов)
    for label in all_labels:
        textcat.add_label(label)

    # Конвертация обучающих данных в объекты Example, необходимых для тренировки
    print("Подготовка тренировочных данных...")
    train_examples = []
    for text, annotations in train_data:
        doc = nlp.make_doc(text)
        example = Example.from_dict(doc, annotations)
        train_examples.append(example)

    # Отключение остальных пайплайнов (NER, tagger, parser), чтобы учился только textcat
    unaffected_pipes = [pipe for pipe in nlp.pipe_names if pipe != "textcat"]
    
    print("Начало обучения классификатора интентов...")
    with nlp.disable_pipes(*unaffected_pipes):
        # Инициализируем новые компоненты (textcat) с помощью обучающих примеров
        optimizer = nlp.initialize(lambda: train_examples)
        for i in range(15):  # Количество эпох
            random.shuffle(train_examples)
            losses = {}
            for example in train_examples:
                nlp.update([example], sgd=optimizer, losses=losses)
            print(f"Эпоха {i+1}, Значение функции потерь (Loss): {losses.get('textcat', 0.0):.4f}")

    # 6. Тестирование обученной модели на dev выборке
    print("\nПроверка модели на отложенной (dev) выборке:")
    correct = 0
    for text, annotations in dev_data:
        doc = nlp(text)
        predicted_label = max(doc.cats, key=doc.cats.get)
        actual_label = [k for k, v in annotations['cats'].items() if v == 1.0][0]
        if predicted_label == actual_label:
            correct += 1
    
    accuracy = correct / len(dev_data) if dev_data else 0
    print(f"Точность (Accuracy) на dev выборке: {accuracy*100:.2f}%")

    # 7. Сохранение обученной модели
    model_out = os.path.join(base_dir, "models", "intent_model")
    os.makedirs(model_out, exist_ok=True)
    nlp.to_disk(model_out)
    print(f"\nМодель успешно сохранена в папку {model_out}")
    print(f"Теперь вы можете загрузить её как: nlp = spacy.load('{model_out}')")

if __name__ == '__main__':
    main()
