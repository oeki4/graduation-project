# Инструкция по обучению и тестированию модели TextCategorizer

## Подготовка

### 1. Установка зависимостей

Убедитесь, что все зависимости установлены:

```powershell
cd f:\projects\graduation-project\nlp
pip install -r requirements.txt
```

Или если используете виртуальное окружение:

```powershell
# Создание виртуального окружения (если еще не создано)
python -m venv venv

# Активация виртуального окружения
.\venv\Scripts\Activate.ps1

# Установка зависимостей
pip install -r requirements.txt
```

## Обучение модели

### Запуск обучения

Скрипт `train_intent_classifier.py` автоматически:
- Создаёт обучающие данные (~300+ положительных и ~100+ отрицательных примеров)
- Обучает TextCategorizer на 30 итерациях
- Сохраняет модель в директорию `models/intent_classifier`
- Тестирует модель на примерах

**Команда для запуска:**

```powershell
cd f:\projects\graduation-project\nlp
python train_intent_classifier.py
```

### Параметры обучения

Вы можете изменить параметры обучения, отредактировав скрипт:

- `n_iter=30` - количество итераций обучения (можно увеличить для лучшего качества)
- `output_dir="models/intent_classifier"` - директория для сохранения модели
- `drop=0.2` - коэффициент dropout для регуляризации

Пример изменения количества итераций:

```python
# В конце файла train_intent_classifier.py
nlp = train_model(n_iter=50)  # Увеличить до 50 итераций
```

## Результаты обучения

После обучения вы увидите:

1. **Информацию о данных:**
   - Количество созданных примеров
   - Количество положительных и отрицательных примеров

2. **Процесс обучения:**
   - Потери на каждой 5-й итерации
   - Финальные потери

3. **Тестирование:**
   - Результаты на тестовых примерах
   - Уверенность модели для каждого интента

4. **Сохранение модели:**
   - Модель сохраняется в `models/intent_classifier/`

## Использование обученной модели

### Загрузка и использование в коде

```python
import spacy

# Загрузка обученной модели
nlp = spacy.load("models/intent_classifier")

# Тестирование на новом тексте
text = "включи сказку колобок"
doc = nlp(text)

# Получение результатов
intent_score = doc.cats.get("включить_сказку", 0.0)
other_score = doc.cats.get("другой_интент", 0.0)

# Определение интента
if intent_score > 0.5:
    print(f"Интент: включить_сказку (уверенность: {intent_score:.2%})")
else:
    print(f"Интент: другой_интент (уверенность: {other_score:.2%})")
```

### Интеграция с существующим кодом

Вы можете использовать обученную модель в `main.py`:

```python
import spacy

# Загрузка модели с классификатором интентов
nlp = spacy.load("models/intent_classifier")

def detect_intent(text: str) -> str | None:
    """
    Определяет интент из текста
    Возвращает 'включить_сказку' или None
    """
    doc = nlp(text.lower())
    intent_score = doc.cats.get("включить_сказку", 0.0)
    
    if intent_score > 0.5:
        return "включить_сказку"
    return None

# Пример использования
text = "включи сказку про колобка"
intent = detect_intent(text)
if intent == "включить_сказку":
    fairy_tale_name = extract_fairy_tale(text)
    print(f"Включаю сказку: {fairy_tale_name}")
```

## Тестирование на своих примерах

Вы можете создать отдельный скрипт для тестирования:

```python
# test_model.py
import spacy

# Загрузка обученной модели
nlp = spacy.load("models/intent_classifier")

# Ваши тестовые примеры
test_texts = [
    "включи сказку про репку",
    "поставь историю",
    "какая погода",
    "хочу послушать сказку",
]

for text in test_texts:
    doc = nlp(text)
    intent_score = doc.cats.get("включить_сказку", 0.0)
    predicted = "включить_сказку" if intent_score > 0.5 else "другой_интент"
    
    print(f"{text:50} -> {predicted:20} ({intent_score:.2%})")
```

Запуск:

```powershell
python test_model.py
```

## Структура файлов после обучения

```
nlp/
├── train_intent_classifier.py  # Скрипт обучения
├── main.py                      # Основной скрипт
├── requirements.txt             # Зависимости
├── models/
│   └── intent_classifier/       # Обученная модель
│       ├── meta.json
│       ├── config.cfg
│       ├── tokenizer/
│       ├── vocab/
│       └── ...
└── INSTRUCTIONS.md              # Этот файл
```

## Советы по улучшению модели

1. **Увеличьте количество итераций** (если модель недообучена):
   ```python
   nlp = train_model(n_iter=50)
   ```

2. **Добавьте больше примеров** в функцию `create_training_data()`:
   - Больше вариантов формулировок
   - Больше отрицательных примеров
   - Примеры с опечатками (если нужно)

3. **Настройте dropout** (если модель переобучена):
   ```python
   nlp.update(batch, losses=losses, drop=0.3)  # Увеличить dropout
   ```

4. **Используйте валидационный набор** для проверки качества:
   - Разделите данные на train/validation
   - Отслеживайте метрики на валидации

## Устранение проблем

### Ошибка "ModuleNotFoundError: No module named 'spacy'"
Установите зависимости:
```powershell
pip install -r requirements.txt
```

### Ошибка "OSError: [Errno 2] No such file or directory: 'ru_core_news_md'"
Убедитесь, что русская модель spaCy установлена:
```powershell
python -m spacy download ru_core_news_md
```

### Модель показывает низкую уверенность
- Увеличьте количество итераций обучения
- Добавьте больше обучающих примеров
- Проверьте баланс положительных и отрицательных примеров