import random
from collections import defaultdict

def generate_other_intent_examples():
    """
    Генерирует примерно 10к примеров для интента "другой_интент"
    Примеры НЕ должны относиться к интентам "включи_сказку" и "узнать_погоду"
    Все слова должны быть в правильных падежах
    """

    # Слова и фразы, которые НЕ должны встречаться (чтобы избежать пересечения с другими интентами)
    weather_keywords = [
        'погод', 'температур', 'градус', 'метео', 'прогноз', 'осадк',
        'дожд', 'снег', 'град', 'ливень', 'снегопад', 'туман', 'гроз',
        'ветер', 'ураган', 'шторм', 'тепл', 'холод', 'мороз', 'жара',
        'зонт', 'куртк', 'пальто', 'шапк', 'перчатк', 'осадки'
    ]

    story_keywords = [
        'сказк', 'истори', 'рассказ', 'книг', 'чтени', 'байк', 'легенд',
        'притч', 'басен', 'миф', 'сказоч', 'почитай', 'прочитай', 'включи',
        'послушать', 'аудио', 'диктор', 'чтец', 'литератур'
    ]

    # Категории фраз для "другого" интента
    categories = {
        'приветствия_прощания': [
            # Приветствия
            'Привет',
            'Здравствуй',
            'Доброе утро',
            'Добрый день',
            'Добрый вечер',
            'Приветствую тебя',
            'Рад тебя видеть',
            'Как дела',
            'Как жизнь',
            'Что нового',

            # Прощания
            'Пока',
            'До свидания',
            'До скорого',
            'Увидимся',
            'Всего доброго',
            'Спокойной ночи',
            'Доброй ночи',
            'До завтра',
            'Был рад общению',
            'Прощай'
        ],

        'команды_управления': [
            'Выключи музыку',
            'Поставь на паузу',
            'Сделай громче',
            'Уменьши звук',
            'Следующий трек',
            'Предыдущий трек',
            'Останови воспроизведение',
            'Продолжи играть',
            'Перемотай вперед',
            'Вернись назад'
        ],

        'вопросы_общие': [
            'Сколько времени',
            'Который час',
            'Какой сегодня день',
            'Какое сегодня число',
            'Какой день недели',
            'Какой месяц',
            'Какое сейчас время года',
            'Сколько дней до выходных',
            'Когда каникулы',
            'Какой праздник сегодня'
        ],

        'напоминания_таймеры': [
            'Напомни мне позвонить маме',
            'Установи таймер на 10 минут',
            'Поставь будильник на завтра',
            'Напомни о встрече в пятницу',
            'Создай напоминание о приеме у врача',
            'Таймер на полчаса пожалуйста',
            'Напомни купить молоко',
            'Будильник на семь утра',
            'Напомни взять документы',
            'Таймер для варки яиц'
        ],

        'вычисления_конвертации': [
            'Сколько будет пять плюс семь',
            'Посчитай двадцать умножить на три',
            'Каков квадратный корень из шестнадцати',
            'Конвертируй доллары в рубли',
            'Переведи километры в мили',
            'Сколько грамм в килограмме',
            'Пересчитай евро в доллары',
            'Сколько минут в двух часах',
            'Переведи цельсии в фаренгейты',
            'Сколько сантиметров в метре'
        ],

        'спорт_новости': [
            'Какие новости',
            'Что происходит в мире',
            'Расскажи последние новости',
            'Какие спортивные события сегодня',
            'Кто выиграл вчерашний матч',
            'Каков счет игры',
            'Кто лидирует в чемпионате',
            'Какие новости в политике',
            'Что нового в технологиях',
            'Какие культурные события'
        ],

        'развлечения_игры': [
            'Расскажи анекдот',
            'Загадай загадку',
            'Сыграем в игру',
            'Поиграем в слова',
            'Расскажи интересный факт',
            'Спой песню',
            'Потанцуем',
            'Какие фильмы вышли недавно',
            'Что посмотреть вечером',
            'Порекомендуй сериал'
        ],

        'личные_вопросы': [
            'Как тебя зовут',
            'Сколько тебе лет',
            'Кто твой создатель',
            'Где ты живешь',
            'Что ты умеешь',
            'Как твое настроение',
            'Ты человек или программа',
            'Что ты думаешь об искусственном интеллекте',
            'У тебя есть чувства',
            'Можешь ли ты учиться'
        ],

        'технические_запросы': [
            'Перезагрузи систему',
            'Обнови приложение',
            'Проверь соединение с интернетом',
            'Какая версия программы',
            'Сохрани настройки',
            'Сделай резервную копию',
            'Очисти кэш',
            'Оптимизируй память',
            'Проверь наличие обновлений',
            'Перейди в режим энергосбережения'
        ],

        'еда_рецепты': [
            'Как приготовить омлет',
            'Давай рецепт борща',
            'Что можно приготовить на ужин',
            'Как испечь блины',
            'Рецепт салата цезарь',
            'Как варить кофе',
            'Что приготовить из курицы',
            'Рецепт домашнего печенья',
            'Как сделать пиццу',
            'Рецепт вкусного супа'
        ],

        'покупки_шопинг': [
            'Где купить телефон',
            'Какие есть скидки сегодня',
            'Где найти дешевые авиабилеты',
            'Какой магазин работает круглосуточно',
            'Где купить продукты ночью',
            'Какие интернет-магазины доставляют быстро',
            'Где купить подарок на день рождения',
            'Какие распродажи идут сейчас',
            'Где купить книги со скидкой',
            'Как заказать доставку еды'
        ],

        'путешествия_транспорт': [
            'Как добраться до вокзала',
            'Расписание автобусов',
            'Когда ближайший поезд',
            'Как доехать до аэропорта',
            'Есть ли пробки на дорогах',
            'Где ближайшая остановка',
            'Какой маршрут самый быстрый',
            'Сколько стоит такси до центра',
            'Работает ли метро ночью',
            'Какой общественный транспорт ходит здесь'
        ],

        'образование_обучение': [
            'Объясни теорию относительности',
            'Как выучить английский язык',
            'Что такое фотосинтез',
            'Расскажи о древнем риме',
            'Как работает двигатель внутреннего сгорания',
            'Объясни математическую теорему',
            'Что такое квантовая физика',
            'Как писать сочинение',
            'Объясни грамматику русского языка',
            'Что такое днк'
        ],

        'работа_бизнес': [
            'Как составить резюме',
            'Где найти работу',
            'Как подготовиться к собеседованию',
            'Как вести деловую переписку',
            'Что такое тайм-менеджмент',
            'Как открыть свой бизнес',
            'Что такое маркетинг',
            'Как вести переговоры',
            'Что такое лидерство',
            'Как управлять проектом'
        ],

        'здоровье_медицина': [
            'Что делать при простуде',
            'Как снизить температуру',
            'Какие симптомы гриппа',
            'Когда обращаться к врачу',
            'Как правильно питаться',
            'Какие упражнения делать утром',
            'Как избавиться от головной боли',
            'Сколько нужно спать',
            'Как снять стресс',
            'Что такое здоровый образ жизни'
        ]
    }

    # Варианты вежливых форм и модификаторов
    polite_forms = [
        '',
        'пожалуйста',
        'будь добр',
        'будь любезен',
        'не мог бы ты',
        'можно',
        'сделай одолжение',
        'прошу тебя'
    ]

    # Варианты начала предложений
    starters = [
        '',
        'А',
        'И',
        'Ну',
        'Так',
        'Эй',
        'Послушай',
        'Скажи',
        'Подскажи',
        'Объясни',
        'Расскажи',
        'Помоги',
        'Пожалуйста'
    ]

    # Окончания и эмоциональные модификаторы
    endings = [
        '',
        '?',
        '.',
        '...',
        '!',
        '?!',
        'пожалуйста',
        'очень нужно',
        'срочно',
        'быстро'
    ]

    # Генерация примеров
    examples = set()

    print("Генерация примеров для интента 'другой_интент'...")

    # Счетчик по категориям
    category_counts = defaultdict(int)

    # Целевое количество примеров на категорию
    target_per_category = 10000 // len(categories)

    for category_name, phrases in categories.items():
        print(f"Категория: {category_name}")
        generated = 0

        while generated < target_per_category * 1.2:  # Генерируем с запасом
            base_phrase = random.choice(phrases)

            # Добавляем вежливую форму
            if random.random() < 0.3:
                polite = random.choice(polite_forms[1:])  # исключаем пустую строку
                if polite:
                    # Размещаем вежливую форму в начале или конце
                    if random.random() < 0.5:
                        phrase = f"{polite} {base_phrase.lower()}"
                    else:
                        phrase = f"{base_phrase} {polite}"
                else:
                    phrase = base_phrase
            else:
                phrase = base_phrase

            # Добавляем начало предложения
            if random.random() < 0.2:
                starter = random.choice(starters[1:])  # исключаем пустую строку
                if starter:
                    phrase = f"{starter} {phrase.lower()}"

            # Добавляем окончание
            if random.random() < 0.4:
                ending = random.choice(endings)
                if ending not in ['', 'пожалуйста', 'очень нужно', 'срочно', 'быстро']:
                    phrase = phrase + ending
                elif ending:
                    phrase = phrase + ' ' + ending

            # Проверяем, что фраза не содержит ключевых слов других интентов
            phrase_lower = phrase.lower()
            has_weather_keywords = any(keyword in phrase_lower for keyword in weather_keywords)
            has_story_keywords = any(keyword in phrase_lower for keyword in story_keywords)

            if not has_weather_keywords and not has_story_keywords:
                examples.add(phrase.strip())
                generated += 1
                category_counts[category_name] += 1

        print(f"  Сгенерировано: {category_counts[category_name]}")

    # Дополнительная генерация комбинированных фраз
    print("\nГенерация комбинированных фраз...")
    additional_needed = 10000 - len(examples)

    if additional_needed > 0:
        print(f"Догенерация {additional_needed} примеров...")

        # Шаблоны для комбинированных фраз
        combined_templates = [
            "{start} {phrase} {polite}",
            "{phrase}, {question}",
            "{phrase} и {another_phrase}",
            "Можешь ли ты {phrase}",
            "Хотелось бы {phrase_inf}",
            "Нужно {phrase_inf}",
            "Помоги {phrase_inf}",
            "Подскажи, как {phrase_inf}",
            "Расскажи, почему {question}",
            "Объясни, что такое {concept}"
        ]

        # Список всех базовых фраз из всех категорий
        all_phrases = []
        for category_phrases in categories.values():
            all_phrases.extend(category_phrases)

        # Список вопросов для вставки
        questions = [
            'почему так происходит',
            'как это работает',
            'что это значит',
            'зачем это нужно',
            'когда это появилось',
            'где это применяется',
            'кто это придумал',
            'сколько это стоит',
            'как часто это бывает',
            'что будет дальше'
        ]

        # Список концептов для объяснения
        concepts = [
            'искусственный интеллект',
            'виртуальная реальность',
            'блокчейн',
            'криптовалюта',
            'машинное обучение',
            'нейросеть',
            'интернет вещей',
            'большие данные',
            'кибербезопасность',
            'цифровая экономика'
        ]

        attempts = 0
        while len(examples) < 10000 and attempts < 20000:
            template = random.choice(combined_templates)

            if '{phrase_inf}' in template:
                base_phrase = random.choice(all_phrases).lower()
                # Преобразуем в инфинитив (упрощенно)
                phrase_inf = base_phrase
                phrase_inf = phrase_inf.replace('расскажи', 'рассказать')
                phrase_inf = phrase_inf.replace('объясни', 'объяснить')
                phrase_inf = phrase_inf.replace('покажи', 'показать')
                phrase_inf = phrase_inf.replace('найди', 'найти')

                phrase = template.format(
                    phrase_inf=phrase_inf,
                    start=random.choice(starters) if '{start}' in template else '',
                    polite=random.choice(polite_forms) if '{polite}' in template else '',
                    question=random.choice(questions) if '{question}' in template else '',
                    another_phrase=random.choice(all_phrases).lower() if '{another_phrase}' in template else '',
                    concept=random.choice(concepts) if '{concept}' in template else ''
                )
            elif '{concept}' in template:
                phrase = template.format(
                    concept=random.choice(concepts),
                    start=random.choice(starters) if '{start}' in template else '',
                    polite=random.choice(polite_forms) if '{polite}' in template else '',
                    question=random.choice(questions) if '{question}' in template else ''
                )
            elif '{question}' in template:
                phrase = template.format(
                    phrase=random.choice(all_phrases),
                    start=random.choice(starters) if '{start}' in template else '',
                    polite=random.choice(polite_forms) if '{polite}' in template else '',
                    question=random.choice(questions),
                    another_phrase=random.choice(all_phrases).lower() if '{another_phrase}' in template else ''
                )
            else:
                phrase = template.format(
                    phrase=random.choice(all_phrases),
                    start=random.choice(starters) if '{start}' in template else '',
                    polite=random.choice(polite_forms) if '{polite}' in template else '',
                    question=random.choice(questions) if '{question}' in template else '',
                    another_phrase=random.choice(all_phrases).lower() if '{another_phrase}' in template else ''
                )

            # Очистка лишних пробелов
            phrase = ' '.join(phrase.split()).strip()

            # Проверка на ключевые слова других интентов
            phrase_lower = phrase.lower()
            has_weather_keywords = any(keyword in phrase_lower for keyword in weather_keywords)
            has_story_keywords = any(keyword in phrase_lower for keyword in story_keywords)

            if not has_weather_keywords and not has_story_keywords:
                # Добавляем пунктуацию
                if not phrase[-1] in ['.', '!', '?', '...']:
                    if random.random() < 0.7:
                        phrase += random.choice(['.', '?', '!'])

                examples.add(phrase)

            attempts += 1

    # Преобразуем в список и ограничиваем 10000
    examples = list(examples)[:10000]

    print(f"\nУникальных примеров: {len(examples)}")

    # Вывод статистики по категориям
    print("\nСтатистика по типам запросов:")
    for category, count in sorted(category_counts.items(), key=lambda x: x[1], reverse=True):
        percentage = (count/len(examples)*100) if examples else 0
        print(f"  {category}: {count} ({percentage:.1f}%)")

    # Проверка на наличие запрещенных ключевых слов
    print("\nПроверка на пересечение с другими интентами...")
    conflicts = []
    for example in examples:
        example_lower = example.lower()
        weather_conflict = any(keyword in example_lower for keyword in weather_keywords)
        story_conflict = any(keyword in example_lower for keyword in story_keywords)

        if weather_conflict or story_conflict:
            conflicts.append(example)

    if conflicts:
        print(f"Найдено потенциальных конфликтов: {len(conflicts)}")
        print("Примеры конфликтов:")
        for conflict in conflicts[:5]:
            print(f"  - {conflict}")
    else:
        print("Конфликтов не найдено. Все примеры уникальны для интента 'другой_интент'")

    return examples

def save_examples_to_file(examples, filename="other_intent_examples.txt"):
    """Сохраняет примеры в файл"""
    with open(filename, 'w', encoding='utf-8') as f:
        for example in examples:
            f.write(example + '\n')

    print(f"\nСгенерировано {len(examples)} примеров")
    print(f"Примеры сохранены в файл: {filename}")

def main():
    # Генерация примеров
    examples = generate_other_intent_examples()

    # Вывод статистики
    print(f"\n{'='*50}")
    print(f"Итого сгенерировано примеров: {len(examples)}")
    print(f"{'='*50}")

    print("\nПервые 30 примеров:")
    for i, example in enumerate(examples[:30], 1):
        print(f"{i:3}. {example}")

    print("\nПоследние 20 примеров:")
    for i, example in enumerate(examples[-20:], len(examples)-19):
        print(f"{i:3}. {example}")

    # Сохранение в файл
    save_examples_to_file(examples)

    # Разделение на тренировочные и тестовые наборы
    random.shuffle(examples)
    split_point = int(len(examples) * 0.8)

    train_examples = examples[:split_point]
    test_examples = examples[split_point:]

    with open("other_intent_train_examples.txt", 'w', encoding='utf-8') as f:
        for example in train_examples:
            f.write(example + '\n')

    with open("other_intent_test_examples.txt", 'w', encoding='utf-8') as f:
        for example in test_examples:
            f.write(example + '\n')

    print(f"\nРазделено на:")
    print(f"  Тренировочные: {len(train_examples)} примеров")
    print(f"  Тестовые: {len(test_examples)} примеров")

    # Статистика по длине предложений
    print("\nСтатистика по длине предложений:")
    lengths = [len(e.split()) for e in examples]
    avg_length = sum(lengths) / len(lengths) if examples else 0

    print(f"  Средняя длина: {avg_length:.1f} слов")
    print(f"  Минимальная длина: {min(lengths)} слов")
    print(f"  Максимальная длина: {max(lengths)} слов")

    # Распределение по знакам препинания
    punctuation_stats = {
        'заканчивается на ?': sum(1 for e in examples if e.strip().endswith('?')),
        'заканчивается на .': sum(1 for e in examples if e.strip().endswith('.')),
        'заканчивается на !': sum(1 for e in examples if e.strip().endswith('!')),
        'содержит "пожалуйста"': sum(1 for e in examples if 'пожалуйста' in e.lower()),
        'является вопросом': sum(1 for e in examples if any(e.strip().endswith(p) for p in ['?', '?!']))
    }

    print("\nСтатистика по формам:")
    for key, value in punctuation_stats.items():
        percentage = (value/len(examples)*100) if examples else 0
        print(f"  {key}: {value} ({percentage:.1f}%)")

if __name__ == "__main__":
    main()