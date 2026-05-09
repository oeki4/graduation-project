"""
Скрипт для обучения TextCategorizer для определения интентов голосового ассистента.
Поддерживаемые интенты: включить_сказку, узнать_погоду, включить_радио, другой_интент.
"""
import spacy
from spacy.training import Example
from spacy.util import minibatch, compounding
import random
from pathlib import Path


def _load_examples(filename: str, label: str) -> list:
    """Вспомогательная функция: загружает строки из файла и возвращает список."""
    examples = []
    try:
        with open(filename, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line:
                    examples.append(line)
        print(f"Загружено {len(examples)} примеров для '{label}' из {filename}")
    except FileNotFoundError:
        print(f"Предупреждение: файл {filename} не найден. Примеры для '{label}' пропущены.")
    except Exception as e:
        print(f"Ошибка при загрузке {filename}: {e}")
    return examples


def create_training_data():
    """
    Загружает обучающие примеры из текстовых файлов и формирует датасет.
    Каждому примеру присваивается вектор меток для всех четырёх интентов.
    """
    fairytale_examples = _load_examples("fairytale.txt", "включить_сказку")
    weather_examples   = _load_examples("weather.txt",   "узнать_погоду")
    radio_examples     = _load_examples("radio.txt",     "включить_радио")
    other_examples     = _load_examples("other.txt",     "другой_интент")

    training_data = []

    for text in fairytale_examples:
        training_data.append({
            "text": text,
            "cats": {
                "включить_сказку": 1.0,
                "узнать_погоду":   0.0,
                "включить_радио":  0.0,
                "другой_интент":   0.0,
            }
        })

    for text in weather_examples:
        training_data.append({
            "text": text,
            "cats": {
                "включить_сказку": 0.0,
                "узнать_погоду":   1.0,
                "включить_радио":  0.0,
                "другой_интент":   0.0,
            }
        })

    for text in radio_examples:
        training_data.append({
            "text": text,
            "cats": {
                "включить_сказку": 0.0,
                "узнать_погоду":   0.0,
                "включить_радио":  1.0,
                "другой_интент":   0.0,
            }
        })

    for text in other_examples:
        training_data.append({
            "text": text,
            "cats": {
                "включить_сказку": 0.0,
                "узнать_погоду":   0.0,
                "включить_радио":  0.0,
                "другой_интент":   1.0,
            }
        })

    return training_data


def evaluate_model(nlp, validation_examples):
    """
    Вычисляет метрики на валидационном наборе для всех категорий
    
    Returns:
        dict с метриками: accuracy, и метрики для каждой категории
    """
    correct = 0
    total = len(validation_examples)
    
    # Метрики для каждой категории
    categories = ["включить_сказку", "узнать_погоду", "включить_радио", "другой_интент"]
    category_metrics = {cat: {"tp": 0, "fp": 0, "fn": 0} for cat in categories}
    
    for example in validation_examples:
        # Получаем предсказание
        doc = nlp(example.reference.text)
        
        # Находим предсказанную категорию (с максимальным score)
        predicted_scores = {cat: doc.cats.get(cat, 0.0) for cat in categories}
        predicted_category = max(predicted_scores, key=predicted_scores.get)
        
        # Находим истинную категорию
        true_scores = {cat: example.reference.cats.get(cat, 0.0) for cat in categories}
        true_category = max(true_scores, key=true_scores.get)
        
        # Подсчитываем общую точность
        if predicted_category == true_category:
            correct += 1
            category_metrics[predicted_category]["tp"] += 1
        else:
            category_metrics[true_category]["fn"] += 1
            category_metrics[predicted_category]["fp"] += 1
    
    # Общая точность
    accuracy = correct / total if total > 0 else 0.0
    
    # Метрики для каждой категории
    category_results = {}
    for cat in categories:
        tp = category_metrics[cat]["tp"]
        fp = category_metrics[cat]["fp"]
        fn = category_metrics[cat]["fn"]
        
        precision = tp / (tp + fp) if (tp + fp) > 0 else 0.0
        recall = tp / (tp + fn) if (tp + fn) > 0 else 0.0
        f1 = 2 * (precision * recall) / (precision + recall) if (precision + recall) > 0 else 0.0
        
        category_results[cat] = {
            "precision": precision,
            "recall": recall,
            "f1": f1
        }
    
    return {
        "accuracy": accuracy,
        "categories": category_results
    }


def train_model(output_dir="models/intent_model", n_iter=40, patience=10, train_split=0.8):
    """
    Обучает TextCategorizer для определения интента "включить_сказку"
    с валидацией и early stopping для предотвращения переобучения

    Args:
        output_dir: Директория для сохранения модели
        n_iter: Максимальное количество итераций обучения (40 — достаточно
                для срабатывания early stopping, ранее 10 было мало)
        patience: Количество итераций без улучшения перед остановкой
        train_split: Доля данных для обучения (остальное - валидация)
    """
    # Загружаем базовую модель
    print("Загрузка базовой модели spaCy...")
    nlp = spacy.load("ru_core_news_md")

    # Конфигурация TextCategorizer с использованием статических векторов
    # из ru_core_news_md. По умолчанию textcat использует только BoW —
    # такая модель плохо обобщает синонимы (рассказ ≠ сказка ≠ история).
    # Ensemble = BoW (точные ключевые слова) + Tok2Vec со статическими
    # векторами (семантическая близость синонимов).
    textcat_config = {
        "model": {
            "@architectures": "spacy.TextCatEnsemble.v2",
            "linear_model": {
                "@architectures": "spacy.TextCatBOW.v3",
                "exclusive_classes": True,
                "ngram_size": 1,
                "no_output_layer": False,
                "length": 262144,
            },
            "tok2vec": {
                "@architectures": "spacy.Tok2Vec.v2",
                "embed": {
                    "@architectures": "spacy.MultiHashEmbed.v2",
                    "width": 64,
                    "rows": [2000, 2000, 1000, 1000, 1000, 1000],
                    "attrs": ["ORTH", "LOWER", "PREFIX", "SUFFIX", "SHAPE", "ID"],
                    "include_static_vectors": True,
                },
                "encode": {
                    "@architectures": "spacy.MaxoutWindowEncoder.v2",
                    "width": 64,
                    "depth": 2,
                    "window_size": 1,
                    "maxout_pieces": 3,
                },
            },
        }
    }

    # Удаляем старый textcat если есть, и добавляем с нашей конфигурацией
    if "textcat" in nlp.pipe_names:
        nlp.remove_pipe("textcat")
    textcat = nlp.add_pipe("textcat", config=textcat_config, last=True)
    
    # Добавляем метки категорий
    textcat.add_label("включить_сказку")
    textcat.add_label("узнать_погоду")
    textcat.add_label("включить_радио")
    textcat.add_label("другой_интент")
    
    # Создаём обучающие данные
    print("Создание обучающих данных...")
    training_data = create_training_data()
    print(f"Создано {len(training_data)} примеров для обучения")
    print(f"  - Примеров 'включить_сказку': {sum(1 for ex in training_data if ex['cats']['включить_сказку'] == 1.0)}")
    print(f"  - Примеров 'узнать_погоду':  {sum(1 for ex in training_data if ex['cats']['узнать_погоду'] == 1.0)}")
    print(f"  - Примеров 'включить_радио': {sum(1 for ex in training_data if ex['cats']['включить_радио'] == 1.0)}")
    print(f"  - Примеров 'другой_интент':  {sum(1 for ex in training_data if ex['cats']['другой_интент'] == 1.0)}")
    
    # Преобразуем данные в формат Example
    all_examples = []
    for item in training_data:
        doc = nlp.make_doc(item["text"])
        example = Example.from_dict(doc, {"cats": item["cats"]})
        all_examples.append(example)
    
    # Разделяем на train и validation
    random.shuffle(all_examples)
    split_idx = int(len(all_examples) * train_split)
    train_examples = all_examples[:split_idx]
    validation_examples = all_examples[split_idx:]
    
    print(f"\nРазделение данных:")
    print(f"  - Обучающий набор: {len(train_examples)} примеров")
    print(f"  - Валидационный набор: {len(validation_examples)} примеров")
    
    # Обучаем модель
    print(f"\n{'='*70}")
    print(f"НАЧАЛО ОБУЧЕНИЯ")
    print(f"{'='*70}")
    print(f"Максимум итераций: {n_iter}")
    print(f"Patience (early stopping): {patience}")
    print(f"Размер обучающего набора: {len(train_examples)} примеров")
    print(f"Размер валидационного набора: {len(validation_examples)} примеров")
    print(f"{'='*70}\n")
    nlp.begin_training()
    
    # Отключаем другие компоненты pipeline для ускорения
    other_pipes = [pipe for pipe in nlp.pipe_names if pipe != "textcat"]
    
    best_f1 = 0.0
    best_iteration = 0
    patience_counter = 0
    
    with nlp.disable_pipes(*other_pipes):
        for iteration in range(n_iter):
            # Перемешиваем примеры
            random.shuffle(train_examples)
            losses = {}
            
            # Создаём мини-батчи (более агрессивный рост размера: быстрее
            # сходимся к стабильным градиентам, но первые батчи маленькие
            # для лучшего исследования пространства)
            batches = list(minibatch(train_examples, size=compounding(4.0, 64.0, 1.005)))
            total_batches = len(batches)

            # Расписание dropout: 0.5 → 0.2 линейно по эпохам.
            # Высокий dropout в начале спасает от переобучения на маленьком
            # датасете, низкий в конце — позволяет точнее настроить веса.
            current_drop = max(0.2, 0.5 - (iteration / n_iter) * 0.3)
            
            # Обучаем на батчах с прогрессом
            processed_examples = 0
            for batch_idx, batch in enumerate(batches):
                nlp.update(batch, losses=losses, drop=current_drop)
                processed_examples += len(batch)
                
                # Показываем прогресс внутри итерации каждые 10% батчей
                if total_batches > 10 and (batch_idx + 1) % max(1, total_batches // 10) == 0:
                    progress = (batch_idx + 1) / total_batches * 100
                    loss_val = losses.get('textcat', 0.0)
                    print(f"  [Эпоха {iteration+1}] Батчи: [{batch_idx+1:4d}/{total_batches}] "
                          f"({progress:5.1f}%) | Примеров: {processed_examples:5d}/{len(train_examples)} | "
                          f"Loss: {loss_val:.4f}", end='\r')
            
            # Оцениваем на валидации каждую итерацию (но детально только каждые 5)
            metrics = evaluate_model(nlp, validation_examples)
            avg_f1 = sum(m['f1'] for m in metrics['categories'].values()) / len(metrics['categories'])
            
            # Краткое логирование на каждой итерации
            progress_pct = (iteration + 1) / n_iter * 100
            loss_val = losses.get('textcat', 0.0)
            
            # Определяем статус улучшения
            if avg_f1 > best_f1:
                status = "↑"
            elif avg_f1 == best_f1:
                status = "="
            else:
                status = "↓"
            
            print(f"\n[Эпоха {iteration+1:3d}/{n_iter}] ({progress_pct:5.1f}%) {status} | "
                  f"Loss: {loss_val:.6f} | "
                  f"Acc: {metrics['accuracy']:.4f} | "
                  f"F1: {avg_f1:.4f} | "
                  f"Drop: {current_drop:.3f}", end='')
            
            # Детальное логирование каждые 5 итераций или на последней
            if iteration % 5 == 0 or iteration == n_iter - 1:
                print(f"\n  {'─'*70}")
                print(f"  Детальные метрики на валидации:")
                print(f"    Общая точность: {metrics['accuracy']:.4f}")
                print(f"    Средний F1-score: {avg_f1:.4f}")
                print(f"    F1 по категориям:")
                for cat, cat_metrics in metrics['categories'].items():
                    print(f"      - {cat}: {cat_metrics['f1']:.4f} "
                          f"(Precision: {cat_metrics['precision']:.4f}, "
                          f"Recall: {cat_metrics['recall']:.4f})")
                print(f"    Обработано примеров: {processed_examples}/{len(train_examples)}")
                print(f"    Количество батчей: {total_batches}")
            else:
                print()  # Новая строка для краткого логирования
            
            # Early stopping: проверяем улучшение среднего F1-score
            if avg_f1 > best_f1:
                best_f1 = avg_f1
                best_iteration = iteration
                patience_counter = 0
                # Сохраняем лучшую модель
                output_path = Path(output_dir)
                output_path.mkdir(parents=True, exist_ok=True)
                nlp.to_disk(output_path)
                if iteration % 5 == 0 or iteration == n_iter - 1:
                    print(f"  ✓ Новый лучший результат! Модель сохранена (F1: {best_f1:.4f})")
                else:
                    print(f"  ✓ Новый лучший результат! (F1: {best_f1:.4f})")
            else:
                patience_counter += 1
                if iteration % 5 == 0 or iteration == n_iter - 1:
                    print(f"  Нет улучшения ({patience_counter}/{patience})")
            
            # Early stopping
            if patience_counter >= patience:
                print(f"\n{'='*70}")
                print(f"⚠ Early stopping на итерации {iteration+1}")
                print(f"Лучший результат был на итерации {best_iteration+1} (F1: {best_f1:.4f})")
                print(f"{'='*70}")
                break
    
    # Загружаем лучшую модель
    print(f"\nЗагрузка лучшей модели (итерация {best_iteration})...")
    nlp = spacy.load(output_dir)
    
    # Финальная оценка
    final_metrics = evaluate_model(nlp, validation_examples)
    print(f"\n{'='*60}")
    print("Финальные метрики на валидации:")
    print(f"{'='*60}")
    print(f"Общая точность (Accuracy): {final_metrics['accuracy']:.4f}")
    print(f"\nМетрики по категориям:")
    for cat, cat_metrics in final_metrics['categories'].items():
        print(f"\n  {cat}:")
        print(f"    Precision: {cat_metrics['precision']:.4f}")
        print(f"    Recall: {cat_metrics['recall']:.4f}")
        print(f"    F1-score: {cat_metrics['f1']:.4f}")
    
    print(f"\nМодель сохранена в: {Path(output_dir).absolute()}")
    
    return nlp


def test_model(nlp, test_texts):
    """
    Тестирует обученную модель на примерах
    
    Args:
        nlp: Обученная модель
        test_texts: Список текстов для тестирования
    """
    print("\n" + "="*60)
    print("Тестирование модели на новых примерах:")
    print("="*60)
    
    correct = 0
    total = len(test_texts)
    
    # Ожидаемые результаты (для проверки обобщения)
    expected_results = {
        # Положительные примеры
        "включи сказку колобок": "включить_сказку",
        "поставь сказку про волка и семерых козлят": "включить_сказку",
        "давай страшную сказку про ведьм": "включить_сказку",
        "запусти пожалуйста сказку про красную шапочку": "включить_сказку",
        "включи историю про репку": "включить_сказку",
        "поставь аудиосказку три поросёнка": "включить_сказку",
        "хочу послушать сказку про золушку": "включить_сказку",
        "можно включить сказку про снежную королеву": "включить_сказку",
        "включи мне сказку про принцессу": "включить_сказку",
        "поставь детскую сказку на ночь": "включить_сказку",
        "давай послушаем сказку": "включить_сказку",
        "запусти аудиокнигу про животных": "включить_сказку",
        
        # Примеры с ошибками произношения (должны распознаться как "включить_сказку")
        "давай история про трех щенят": "включить_сказку",
        "давай история про трёх щенят": "включить_сказку",
        "включи история про колобка": "включить_сказку",
        "поставь история про волка": "включить_сказку",
        "давай сказка про трех щенят": "включить_сказку",
        "включи сказка про репку": "включить_сказку",
        "поставь сказка про золушку": "включить_сказку",
        "давай рассказ про трех щенят": "включить_сказку",
        "включи рассказ про колобка": "включить_сказку",
        "можно история про трех щенят": "включить_сказку",
        "хочу сказка про трех щенят": "включить_сказку",
        "включи пожалуйста история про колобка": "включить_сказку",
        "поставь пожалуйста сказка про волка": "включить_сказку",
        "давай аудиосказка про трех щенят": "включить_сказку",
        "включи аудиокнига про колобка": "включить_сказку",
        "давай про трех щенят": "включить_сказку",
        "включи про колобка": "включить_сказку",
        "давай послушаем история про трех щенят": "включить_сказку",
        "хочу послушать сказка про трех щенят": "включить_сказку",
        
        # Примеры для интента "узнать_погоду"
        "какая погода": "узнать_погоду",
        "какая погода сегодня": "узнать_погоду",
        "какая погода завтра": "узнать_погоду",
        "скажи погоду": "узнать_погоду",
        "расскажи про погоду": "узнать_погоду",
        "покажи погоду": "узнать_погоду",
        "какая температура": "узнать_погоду",
        "какая температура на улице": "узнать_погоду",
        "будет ли дождь": "узнать_погоду",
        "будет ли снег": "узнать_погоду",
        "какая погода на неделю": "узнать_погоду",
        "прогноз погоды": "узнать_погоду",
        "сколько градусов": "узнать_погоду",
        "расскажи какая погода сегодня": "узнать_погоду",
        "покажи прогноз": "узнать_погоду",
        
        # Отрицательные примеры
        "включи музыку": "другой_интент",
        "расскажи новости": "другой_интент",
        "увеличь громкость": "другой_интент",
        "включи фильм": "другой_интент",
        "поставь сериал": "другой_интент",
        "какой сегодня день": "другой_интент",
        "помоги мне": "другой_интент",
        "что ты умеешь": "другой_интент",
        "включи свет": "другой_интент",
        "поставь радио": "другой_интент",
        "найди информацию": "другой_интент",
    }
    
    categories = ["включить_сказку", "узнать_погоду", "включить_радио", "другой_интент"]

    for text in test_texts:
        doc = nlp(text)

        # Получаем scores для всех категорий
        scores = {cat: doc.cats.get(cat, 0.0) for cat in categories}
        
        # Предсказанная категория - та, у которой максимальный score
        predicted_intent = max(scores, key=scores.get)
        predicted_score = scores[predicted_intent]
        
        expected = expected_results.get(text, "неизвестно")
        
        is_correct = predicted_intent == expected if expected != "неизвестно" else None
        if is_correct:
            correct += 1
        
        status = "✓" if is_correct else ("✗" if is_correct is False else "?")
        
        print(f"\n{status} Текст: '{text}'")
        print(f"   Предсказано: {predicted_intent} (уверенность: {predicted_score:.2%})")
        print(f"   Все scores: сказка={scores['включить_сказку']:.2%}, "
              f"погода={scores['узнать_погоду']:.2%}, "
              f"радио={scores['включить_радио']:.2%}, "
              f"другое={scores['другой_интент']:.2%}")
        if expected != "неизвестно":
            print(f"   Ожидалось: {expected}")
    
    if total > 0:
        accuracy = correct / total
        print(f"\n{'='*60}")
        print(f"Точность на тестовых примерах: {accuracy:.2%} ({correct}/{total})")
        print(f"{'='*60}")


if __name__ == "__main__":
    # Обучаем модель с валидацией и early stopping
    # n_iter - максимум итераций, patience - сколько итераций ждать без улучшения
    nlp = train_model(n_iter=40, patience=10, train_split=0.8)
    
    # Тестируем модель на новых примерах (не из обучающего набора)
    test_texts = [
        # Положительные примеры (должны распознаться как "включить_сказку")
        "включи сказку колобок",
        "поставь сказку про волка и семерых козлят",
        "давай страшную сказку про ведьм",
        "запусти пожалуйста сказку про красную шапочку",
        "включи историю про репку",
        "поставь аудиосказку три поросёнка",
        "хочу послушать сказку про золушку",
        "можно включить сказку про снежную королеву",
        "включи мне сказку про принцессу",
        "поставь детскую сказку на ночь",
        "давай послушаем сказку",
        "запусти аудиокнигу про животных",
        
        # Примеры с ошибками произношения и падежей (должны распознаться как "включить_сказку")
        "давай история про трех щенят",
        "давай история про трёх щенят",
        "включи история про колобка",
        "поставь история про волка",
        "давай сказка про трех щенят",
        "включи сказка про репку",
        "поставь сказка про золушку",
        "давай рассказ про трех щенят",
        "включи рассказ про колобка",
        "можно история про трех щенят",
        "хочу сказка про трех щенят",
        "включи пожалуйста история про колобка",
        "поставь пожалуйста сказка про волка",
        "давай аудиосказка про трех щенят",
        "включи аудиокнига про колобка",
        "давай про трех щенят",
        "включи про колобка",
        "давай послушаем история про трех щенят",
        "хочу послушать сказка про трех щенят",
        
        # Примеры для интента "узнать_погоду" (должны распознаться как "узнать_погоду")
        "какая погода",
        "какая погода сегодня",
        "какая погода завтра",
        "скажи погоду",
        "расскажи про погоду",
        "покажи погоду",
        "какая температура",
        "какая температура на улице",
        "будет ли дождь",
        "будет ли снег",
        "какая погода на неделю",
        "прогноз погоды",
        "сколько градусов",
        "расскажи какая погода сегодня",
        "покажи прогноз",
        
        # Примеры для интента "включить_радио"
        "включи радио",
        "поставь радио",
        "хочу слушать радио",
        "давай включим радио",
        "включи маяк",
        "поставь европу плюс",
        "включи русское радио",
        "давай радио",
        "запусти онлайн радио",
        "включи прямой эфир",

        # Отрицательные примеры (должны распознаться как "другой_интент")
        "включи музыку",
        "расскажи новости",
        "увеличь громкость",
        "включи фильм",
        "поставь сериал",
        "какой сегодня день",
        "помоги мне",
        "что ты умеешь",
        "включи свет",
        "найди информацию",
    ]
    
    test_model(nlp, test_texts)
    
    print("\n" + "="*60)
    print("Обучение завершено успешно!")
    print("="*60)