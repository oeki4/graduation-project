import random

def generate_weather_intent_examples():
    """
    Генерирует 10к примеров для интента "узнать_погоду"
    """

    # Базовые компоненты фраз
    action_words = [
        'какая', 'расскажи', 'покажи', 'скажи', 'дай', 'сообщи',
        'озвучь', 'узнай', 'проверь', 'посмотри', 'подскажи',
        'уточни', 'проинформируй', 'изложи', 'объясни', 'просвети',
        'сообщи о', 'передай', 'открой', 'загугли', 'посоветуй'
    ]

    weather_nouns = [
        'погода', 'погода', 'погода', 'погода',  # Увеличиваем вес
        'температура', 'прогноз', 'метеосводка', 'метеоданные',
        'градусы', 'градус', 'погодные условия', 'метеопрогноз',
        'погодка', 'погодка сегодня', 'метеообстановка',
        'климатические условия', 'атмосферные явления', 'синоптика'
    ]

    time_periods = [
        '', 'сегодня', 'завтра', 'послезавтра', 'сейчас', 'в данный момент',
        'на сегодня', 'на завтра', 'на неделю', 'на ближайшую неделю',
        'на выходные', 'на субботу', 'на воскресенье', 'на вечер',
        'на ночь', 'на утро', 'на полдень', 'на следующую неделю',
        'на месяц', 'в ближайшие дни', 'в течение дня', 'к вечеру',
        'утром', 'днём', 'вечером', 'ночью', 'в обед', 'после обеда',
        'к ночи', 'рано утром', 'поздно вечером', 'в полдень',
        'в 3 часа', 'в 5 вечера', 'в 10 утра', 'через час',
        'через два часа', 'позже', 'потом', 'к тому времени'
    ]

    locations = [
        '', 'у нас', 'здесь', 'в городе', 'в Москве', 'в Санкт-Петербурге',
        'в регионе', 'в области', 'на улице', 'за окном', 'в Подмосковье',
        'в деревне', 'на даче', 'в центре', 'на окраине', 'в пригороде',
        'в этом районе', 'в той местности', 'где я нахожусь',
        'в моём городе', 'в твоём городе', 'в столице',
        'в северной части', 'в южной части', 'на западе', 'на востоке',
        'в Сибири', 'на Урале', 'на Кавказе', 'в Крыму'
    ]

    polite_words = [
        '', 'пожалуйста', 'будь добр', 'можно', 'не мог бы ты',
        'будь любезен', 'прошу', 'мог бы ты', 'сможешь ли ты',
        'не затруднит ли тебя', 'удели минутку', 'помоги',
        'окажи услугу', 'сделай одолжение'
    ]

    precipitation_types = [
        'дождь', 'снег', 'град', 'ливень', 'снегопад', 'мокрый снег',
        'метель', 'туман', 'гроза', 'ветер', 'сильный ветер', 'ураган',
        'шторм', 'шквал', 'смерч', 'торнадо', 'изморозь', 'иней',
        'гололёд', 'гололедица', 'слякоть', 'морось', 'мгла', 'смог',
        'пыльная буря', 'песчаная буря'
    ]

    temperature_words = [
        'температура', 'градусы', 'градус', 'тепло', 'прохлада',
        'холод', 'мороз', 'жара', 'зной', 'прохладно', 'морозно',
        'жарко', 'тепло', 'холодно', 'столбик термометра',
        'показания термометра', 'сколько градусов', 'температурный режим'
    ]

    clothing_items = [
        'зонт', 'плащ', 'куртку', 'пальто', 'шапку', 'перчатки',
        'шарф', 'сапоги', 'дождевик', 'теплую одежду', 'легкую одежду',
        'солнцезащитные очки', 'солнечную шляпу', 'резиновые сапоги',
        'непромокаемую обувь', 'ветровку', 'пуховик', 'свитер'
    ]

    weather_verbs = [
        'идёт', 'пойдёт', 'льёт', 'накрапывает', 'моросит',
        'дует', 'свистит', 'воет', 'метёт', 'валит',
        'светит', 'греет', 'печёт', 'жарит', 'морозит',
        'подморозивает', 'холодает', 'теплеет', 'потеплеет',
        'похолодает', 'прояснится', 'затянется', 'рассеется'
    ]

    # Генерация комбинаций
    examples = []

    print("Генерация погодных запросов...")

    # 1. Базовые вопросы о погоде (самые частые)
    print("1. Базовые вопросы...")
    for action in action_words[:10]:
        for weather in weather_nouns[:12]:
            for time in time_periods[:15]:
                for location in locations[:10]:
                    # Основной вариант
                    if time and location:
                        examples.append(f"{action} {weather} {time} {location}")
                    elif time:
                        examples.append(f"{action} {weather} {time}")
                    elif location:
                        examples.append(f"{action} {weather} {location}")
                    else:
                        examples.append(f"{action} {weather}")

                    # Добавляем варианты с предлогом "про"
                    if random.random() < 0.3:
                        examples.append(f"{action} про {weather} {time} {location}".strip())

    print(f"   Сгенерировано: {len(examples)}")

    # 2. Вопросы об осадках
    print("2. Вопросы об осадках...")
    base_count = len(examples)

    precip_questions = [
        "будет ли {precip} {time} {location}",
        "пойдет ли {precip} {time} {location}",
        "ожидается ли {precip} {time} {location}",
        "как с {precip} {time} {location}",
        "что с {precip} {time} {location}",
        "будет {precip} или нет {time} {location}",
        "обещают ли {precip} {time} {location}",
        "прогнозируют ли {precip} {time} {location}",
        "есть ли вероятность {precip} {time} {location}",
        "возможен ли {precip} {time} {location}",
    ]

    for pattern in precip_questions:
        for precip in precipitation_types[:15]:
            for time in time_periods[:12]:
                for location in locations[:8]:
                    if random.random() < 0.6:
                        phrase = pattern.format(
                            precip=precip,
                            time=time,
                            location=location
                        ).strip()
                        examples.append(phrase)

                        # Вариант с глаголом
                        if random.random() < 0.4:
                            verb = random.choice(weather_verbs[:8])
                            examples.append(f"{verb} ли {precip} {time} {location}".strip())

    print(f"   Добавлено: {len(examples) - base_count}")

    # 3. Вопросы о температуре
    print("3. Вопросы о температуре...")
    base_count = len(examples)

    temp_questions = [
        "какая {temp} {time} {location}",
        "сколько {temp_word} {time} {location}",
        "какова {temp} {time} {location}",
        "что по температуре {time} {location}",
        "какие градусы {time} {location}",
        "температурный фон {time} {location}",
        "на сколько градусов {time} {location}",
        "какой градус {time} {location}",
        "какое значение температуры {time} {location}",
    ]

    temp_words = ['градусов', 'градуса', 'градус', 'по Цельсию', 'по Фаренгейту']

    for pattern in temp_questions:
        for temp in temperature_words[:8]:
            for time in time_periods[:12]:
                for location in locations[:8]:
                    for temp_word in temp_words[:4]:
                        if random.random() < 0.5:
                            phrase = pattern.format(
                                temp=temp,
                                temp_word=temp_word,
                                time=time,
                                location=location
                            ).strip()
                            examples.append(phrase)

                            # Добавляем сравнения
                            if random.random() < 0.3:
                                comparisons = ['теплее чем', 'холоднее чем', 'так же как', 'по сравнению с']
                                comp = random.choice(comparisons)
                                examples.append(f"{phrase} {comp} вчера".strip())

    print(f"   Добавлено: {len(examples) - base_count}")

    # 4. Вежливые формы
    print("4. Вежливые формы...")
    base_count = len(examples)

    polite_patterns = [
        "{polite} {action} {weather} {time} {location}",
        "{action} {weather} {time} {location} {polite}",
        "{polite} скажи {weather} {time}",
        "можно {action} {weather} {time}",
        "{polite} уточни {weather} {time}",
        "{polite} проинформируй о {weather} {time}",
        "не откажи в просьбе {action} {weather}",
        "будь другом {action} {weather} {time}",
    ]

    for pattern in polite_patterns:
        for polite in polite_words[1:8]:  # только вежливые слова (не пустые)
            for action in action_words[:8]:
                for weather in weather_nouns[:8]:
                    for time in time_periods[:8]:
                        for location in locations[:6]:
                            if random.random() < 0.4:
                                phrase = pattern.format(
                                    polite=polite,
                                    action=action,
                                    weather=weather,
                                    time=time,
                                    location=location
                                ).strip()
                                examples.append(phrase)

    print(f"   Добавлено: {len(examples) - base_count}")

    # 5. Вопросительные формы
    print("5. Вопросительные формы...")
    base_count = len(examples)

    question_forms = [
        "включишь прогноз погоды",
        "покажешь погоду",
        "расскажешь про погоду",
        "скажешь какая погода",
        "сообщишь температуру",
        "узнаешь прогноз",
        "проверишь метеосводку",
        "озвучишь погодные условия",
        "поделишься информацией о погоде",
        "просмотришь прогноз",
        "заглянешь в прогноз",
        "сможешь сказать про погоду",
        "сумеешь узнать погоду",
        "сможешь проверить",
    ]

    for q_form in question_forms:
        for time in time_periods[:8]:
            for location in locations[:6]:
                if random.random() < 0.6:
                    examples.append(f"{q_form} {time} {location}".strip())

                    # Добавляем с "мне"
                    if random.random() < 0.3:
                        examples.append(f"{q_form} мне {time} {location}".strip())

    print(f"   Добавлено: {len(examples) - base_count}")

    # 6. Разговорные и сленговые формы
    print("6. Разговорные формы...")
    base_count = len(examples)

    slang_forms = [
        "чё по погоде",
        "чё по погоде {time}",
        "как там на улице {time}",
        "что на улице {time}",
        "погодка какая {time}",
        "будет {precip} {time}",
        "льёт или нет {time}",
        "дует или нет {time}",
        "тепло или холодно {time}",
        "мокро или сухо {time}",
        "солнце или тучи {time}",
        "ясно или облачно {time}",
        "ветрено или тихо {time}",
        "мороз или оттепель {time}",
        "что там по градусам",
        "сколько на термометре",
        "что показывает термометр",
        "как за окном",
        "что за окном творится",
        "как там с погодкой",
    ]

    for pattern in slang_forms:
        for time in time_periods[:8]:
            for precip in precipitation_types[:5]:
                if random.random() < 0.5:
                    phrase = pattern.format(
                        time=time,
                        precip=precip
                    ).strip()
                    examples.append(phrase)

                    # Добавляем смайлики и эмоции
                    if random.random() < 0.2:
                        emoticons = [' :)', ' :(', ' :D', ' :/', ' :P', ' ;)']
                        examples.append(phrase + random.choice(emoticons))

    print(f"   Добавлено: {len(examples) - base_count}")

    # 7. Практические вопросы
    print("7. Практические вопросы...")
    base_count = len(examples)

    practical_questions = [
        "как одеться {time}",
        "что надеть {time}",
        "нужен ли {item} {time}",
        "брать ли {item} {time}",
        "можно гулять {time}",
        "подходит ли погода для прогулки {time}",
        "можно ехать на велосипеде {time}",
        "стоит ли планировать пикник {time}",
        "можно сушить белье на улице {time}",
        "стоит ли открывать окна {time}",
        "нужно ли поливать растения {time}",
        "можно ли мыть машину {time}",
        "стоит ли брать {item} с собой",
        "как лучше одеться {time}",
        "что посоветуешь надеть {time}",
        "какая одежда подойдет {time}",
        "нужно ли утепляться {time}",
        "можно ли ходить без шапки {time}",
    ]

    for pattern in practical_questions:
        for time in time_periods[:10]:
            for location in locations[:5]:
                for item in clothing_items[:8]:
                    if random.random() < 0.4:
                        # Форматируем шаблон с доступными ключами
                        formatted_phrase = pattern.format(time=time, item=item)
                        # Добавляем location отдельно
                        full_phrase = f"{formatted_phrase} {location}".strip()
                        examples.append(full_phrase)

    print(f"   Добавлено: {len(examples) - base_count}")

    # 8. Сравнительные вопросы
    print("8. Сравнительные вопросы...")
    base_count = len(examples)

    comparison = [
        "теплее ли сегодня чем вчера",
        "холоднее ли завтра чем сегодня",
        "такая же погода как вчера",
        "отличается ли погода от вчерашней",
        "будет ли теплее к вечеру",
        "похолодает или потеплеет {time}",
        "солнечнее или облачнее {time}",
        "дождливее или суше {time}",
        "ветренее или тише {time}",
        "морознее или теплее {time}",
        "сравни с прошлой неделей",
        "как изменится погода {time}",
        "что лучше: сегодня или завтра",
        "в какой день погода лучше",
        "когда будет теплее",
        "когда будет холоднее",
        "когда прекратится {precip}",
        "когда начнется {precip}",
        "до какого числа будет {precip}",
        "с какого дня будет {weather}",
    ]

    for pattern in comparison:
        for time in time_periods[:8]:
            for precip in precipitation_types[:4]:
                for weather in weather_nouns[:4]:
                    if random.random() < 0.3:
                        phrase = pattern.format(
                            time=time,
                            precip=precip,
                            weather=weather
                        ).strip()
                        examples.append(phrase)

    print(f"   Добавлено: {len(examples) - base_count}")

    # 9. Эмоциональные и экспрессивные формы
    print("9. Эмоциональные формы...")
    base_count = len(examples)

    emotions = [
        "Ой, {action} {weather} {time}",
        "Ах, какая {weather} {time}",
        "Интересно, какая {weather} {time}",
        "Скажи, какая {weather} {time}",
        "Подскажи, что с погодой {time}",
        "Не поверишь, {action} {weather}",
        "Представляешь, {weather} {time}",
        "Вообрази, {weather} {time}",
        "Поверишь ли, {action} {weather}",
        "Знаешь, {action} {weather} {time}",
        "Кстати, {action} {weather}",
        "Между прочим, {weather} {time}",
        "К слову, {action} {weather}",
        "Я тут подумал, {weather} {time}",
        "Мне любопытно, {weather} {time}",
        "Мне интересно, {action} {weather}",
        "Хотелось бы знать, {weather} {time}",
        "Любопытно было бы, {action} {weather}",
    ]

    for pattern in emotions:
        for action in action_words[:6]:
            for weather in weather_nouns[:6]:
                for time in time_periods[:6]:
                    if random.random() < 0.3:
                        phrase = pattern.format(
                            action=action,
                            weather=weather,
                            time=time
                        ).strip()
                        examples.append(phrase)

    print(f"   Добавлено: {len(examples) - base_count}")

    # 10. Ошибочные формы (неправильные склонения, опечатки)
    print("10. Ошибочные формы...")
    base_count = len(examples)

    error_forms = [
        ("погоду", "погода"),
        ("погоде", "погода"),
        ("погоды", "погода"),
        ("температуру", "температура"),
        ("температуре", "температура"),
        ("температуры", "температура"),
        ("градусов", "градусы"),
        ("градусах", "градусы"),
        ("дождя", "дождь"),
        ("дожде", "дождь"),
        ("дождю", "дождь"),
        ("снега", "снег"),
        ("снеге", "снег"),
        ("снегу", "погода"),
        ("ветра", "ветер"),
        ("ветре", "ветер"),
        ("ветру", "ветер"),
        ("погодку", "погодка"),
        ("градуса", "градус"),
        ("температурка", "температура"),
    ]

    error_patterns = [
        "скажи {error} {time}",
        "какая {error} {time}",
        "будет {error} {time}",
        "сколько {error} {time}",
        "как с {error} {time}",
        "что с {error} {time}",
        "есть ли {error} {time}",
        "пойдет ли {error} {time}",
        "ожидается ли {error} {time}",
    ]

    for error, correct in error_forms[:15]:
        for pattern in error_patterns:
            for time in time_periods[:8]:
                if random.random() < 0.4:
                    examples.append(pattern.format(error=error, time=time).strip())

                    # Добавляем с опечатками
                    if random.random() < 0.2:
                        typo_phrase = pattern.format(error=error, time=time).strip()
                        typo_phrase = typo_phrase.replace('какая', 'какой').replace('скажи', 'скаже')
                        examples.append(typo_phrase)

    print(f"   Добавлено: {len(examples) - base_count}")

    # 11. Вопросы о конкретных погодных явлениях
    print("11. Конкретные погодные явления...")
    base_count = len(examples)

    specific_questions = [
        "когда будет рассвет {location}",
        "когда закат {location}",
        "влажность воздуха {time} {location}",
        "атмосферное давление {time} {location}",
        "скорость ветра {time} {location}",
        "направление ветра {time} {location}",
        "видимость {time} {location}",
        "облачность {time} {location}",
        "точка росы {time} {location}",
        "индекс ультрафиолета {time} {location}",
        "качество воздуха {time} {location}",
        "уровень осадков {time} {location}",
        "вероятность грозы {time} {location}",
        "сила осадков {time} {location}",
        "продолжительность {precip} {time}",
        "интенсивность {precip} {time}",
    ]

    for pattern in specific_questions:
        for time in time_periods[:8]:
            for location in locations[:6]:
                for precip in precipitation_types[:5]:
                    if random.random() < 0.3:
                        phrase = pattern.format(
                            time=time,
                            location=location,
                            precip=precip
                        ).strip()
                        examples.append(phrase)

    print(f"   Добавлено: {len(examples) - base_count}")

    # 12. Комбинированные вопросы
    print("12. Комбинированные вопросы...")
    base_count = len(examples)

    combined_patterns = [
        "{weather} и {temp} {time}",
        "{precip} и {temp} {time}",
        "{weather} с учетом {precip} {time}",
        "как {weather} и {temp} {time}",
        "что по {weather} и {temp} {time}",
        "{weather} вместе с {precip} {time}",
        "и {weather} и {temp} {time}",
        "не только {weather} но и {temp}",
        "{weather} а также {temp} {time}",
        "кроме {weather} еще и {temp}",
    ]

    for pattern in combined_patterns:
        for weather in weather_nouns[:6]:
            for temp in temperature_words[:5]:
                for precip in precipitation_types[:4]:
                    for time in time_periods[:6]:
                        if random.random() < 0.4:
                            phrase = pattern.format(
                                weather=weather,
                                temp=temp,
                                precip=precip,
                                time=time
                            ).strip()
                            examples.append(phrase)

    print(f"   Добавлено: {len(examples) - base_count}")

    # 13. Вопросы с числительными и временем - ИСПРАВЛЕННЫЙ БЛОК
    print("13. Вопросы с числительными...")
    base_count = len(examples)

    numerical_questions = [
        "погода на {number} дней",
        "прогноз на {number} суток",
        "температура в {hour} часов",
        "погода к {hour} часам",
        "градусы в {hour}:00",
        "прогноз до {number_day} числа",
        "погода с {number1} по {number2}",
        "температура завтра в {hour}",
        "сколько будет в {hour} вечера",
        "прогноз на {number} часов вперед",
    ]

    numbers = ['2', '3', '4', '5', '6', '7', '10', '14']
    hours = ['8', '9', '10', '11', '12', '13', '14', '15', '16', '17', '18', '19', '20', '21', '22']
    days = ['5', '10', '15', '20', '25', '30']

    for pattern in numerical_questions:
        for number in numbers[:6]:
            for hour in hours[:8]:
                for number1 in days[:3]:
                    for number2 in days[3:6]:
                        if random.random() < 0.3:
                            try:
                                phrase = pattern.format(
                                    number=number,
                                    hour=hour,
                                    number_day=number1,  # Исправлено: был day, стал number_day
                                    number1=number1,     # Исправлено: был day1, стал number1
                                    number2=number2      # Исправлено: был day2, стал number2
                                ).strip()
                                examples.append(phrase)
                            except KeyError:
                                # Если в шаблоне нет некоторых ключей, пропускаем
                                continue

    print(f"   Добавлено: {len(examples) - base_count}")

    # 14. Диалоговые формы
    print("14. Диалоговые формы...")
    base_count = len(examples)

    dialog_forms = [
        "а {weather} {time}",
        "а {temp} {time}",
        "а {precip} {time}",
        "и еще {weather} {time}",
        "кстати {weather} {time}",
        "да, и {weather} {time}",
        "так, {weather} {time}",
        "хм, {weather} {time}",
        "ага, {weather} {time}",
        "ясно, а {weather} {time}",
        "понятно, а {temp} {time}",
        "спасибо, а {weather} {time}",
        "хорошо, а {precip} {time}",
        "ладно, {weather} {time}",
        "окей, {weather} {time}",
    ]

    for pattern in dialog_forms:
        for weather in weather_nouns[:6]:
            for temp in temperature_words[:4]:
                for precip in precipitation_types[:4]:
                    for time in time_periods[:6]:
                        if random.random() < 0.3:
                            phrase = pattern.format(
                                weather=weather,
                                temp=temp,
                                precip=precip,
                                time=time
                            ).strip()
                            examples.append(phrase)

    print(f"   Добавлено: {len(examples) - base_count}")

    # 15. Команды и императивы
    print("15. Команды и императивы...")
    base_count = len(examples)

    commands = [
        "{action} {weather}",
        "{action} про {weather}",
        "{action} о {weather}",
        "{action} сейчас же {weather}",
        "{action} немедленно {weather}",
        "{action} быстрее {weather}",
        "{action} скорее {weather}",
        "{action} побыстрее {weather}",
        "ну-ка {action} {weather}",
        "давай {action} {weather}",
        "а ну-ка {action} {weather}",
        "быстро {action} {weather}",
    ]

    for pattern in commands:
        for action in action_words[:8]:
            for weather in weather_nouns[:8]:
                for time in time_periods[:6]:
                    if random.random() < 0.4:
                        phrase = pattern.format(
                            action=action,
                            weather=weather
                        ).strip()
                        if time:
                            phrase = f"{phrase} {time}".strip()
                        examples.append(phrase)

    print(f"   Добавлено: {len(examples) - base_count}")

    # 16. Упрощенные формы запросов
    print("16. Упрощенные формы...")
    base_count = len(examples)

    simple_forms = [
        "погода",
        "погода?",
        "погода!",
        "прогноз",
        "температура",
        "градусы",
        "дождь",
        "снег",
        "ветер",
        "сегодня погода",
        "завтра погода",
        "сейчас погода",
        "погода сегодня",
        "погода завтра",
        "погода сейчас",
        "какая погода",
        "сколько градусов",
        "будет дождь",
        "будет снег",
    ]

    for form in simple_forms:
        for location in locations[:5]:
            if random.random() < 0.5:
                examples.append(f"{form} {location}".strip())
        examples.append(form)

    print(f"   Добавлено: {len(examples) - base_count}")

    # 17. Смешанные вопросы
    print("17. Смешанные вопросы...")
    base_count = len(examples)

    mixed_patterns = [
        "{action} {weather} и {temp}",
        "{action} про {weather} и {precip}",
        "как {weather} и будет ли {precip}",
        "что по {weather} и какая {temp}",
        "{weather} а также {precip}",
        "интересует {weather} и {temp}",
    ]

    for pattern in mixed_patterns:
        for action in action_words[:6]:
            for weather in weather_nouns[:6]:
                for temp in temperature_words[:4]:
                    for precip in precipitation_types[:4]:
                        for time in time_periods[:6]:
                            if random.random() < 0.3:
                                phrase = pattern.format(
                                    action=action,
                                    weather=weather,
                                    temp=temp,
                                    precip=precip
                                ).strip()
                                if time:
                                    phrase = f"{phrase} {time}".strip()
                                examples.append(phrase)

    print(f"   Добавлено: {len(examples) - base_count}")

    # Удаление дубликатов
    print("\nУдаление дубликатов...")
    examples = list(set(examples))
    examples = [e.strip() for e in examples if e.strip()]

    print(f"Уникальных примеров после удаления дубликатов: {len(examples)}")

    # Если меньше 10к, добавляем дополнительные комбинации
    if len(examples) < 10000:
        needed = 10000 - len(examples)
        print(f"\nДогенерация {needed} примеров...")

        simple_patterns = [
            "{action} {weather} {time}",
            "какая {weather} {time}",
            "сколько градусов {time}",
            "будет ли {precip} {time}",
            "что с погодой {time}",
            "{action} мне {weather} {time}",
            "интересует {weather} {time}",
            "хочу знать {weather} {time}",
            "интересно про {weather} {time}",
            "нужна информация о {weather} {time}",
            "требуется {weather} {time}",
            "необходимо узнать {weather} {time}",
            "желательно знать {weather} {time}",
            "хотел бы узнать {weather} {time}",
            "мне бы {weather} {time}",
        ]

        for _ in range(needed):
            pattern = random.choice(simple_patterns)
            action = random.choice(action_words)
            weather = random.choice(weather_nouns)
            time = random.choice(time_periods[1:])  # не пустое время
            precip = random.choice(precipitation_types)

            phrase = pattern.format(
                action=action,
                weather=weather,
                time=time,
                precip=precip
            ).strip()

            # Добавляем разнообразие в регистр и пунктуацию
            variations = [
                phrase,
                phrase.capitalize(),
                phrase.lower(),
                phrase + '?',
                phrase + '!',
                phrase + '...',
                phrase + ', пожалуйста',
                'Мне нужно: ' + phrase,
                'Скажи: ' + phrase,
                'Интересует: ' + phrase,
                ]

            examples.append(random.choice(variations))

    # Ещё раз удаляем дубликаты
    examples = list(set(examples))

    # Ограничиваем 10000
    examples = examples[:10000]

    # Финальная обработка: добавляем различные формы пунктуации и регистра
    print("\nФинальная обработка примеров...")

    final_examples = []
    for example in examples:
        # Основная форма
        final_examples.append(example)

        # Варианты с пунктуацией (с меньшей вероятностью для сохранения разнообразия)
        if random.random() < 0.15:
            punct_options = ['?', '!', '...', '?!', '!?', '.']
            final_examples.append(example + random.choice(punct_options))

        # Варианты с разным регистром
        if random.random() < 0.1:
            final_examples.append(example.upper())
        if random.random() < 0.1:
            final_examples.append(example.capitalize())

        # Добавляем пробелы в начале/конце (реальные данные могут содержать)
        if random.random() < 0.05:
            final_examples.append(' ' + example)
        if random.random() < 0.05:
            final_examples.append(example + ' ')
        if random.random() < 0.02:
            final_examples.append(' ' + example + ' ')

    # Убираем дубликаты и ограничиваем 10000
    final_examples = list(set(final_examples))
    final_examples = final_examples[:10000]

    return final_examples

def save_examples_to_file(examples, filename="weather_intent_examples.txt"):
    """Сохраняет примеры в файл"""
    with open(filename, 'w', encoding='utf-8') as f:
        for example in examples:
            f.write(example + '\n')

    print(f"\nСгенерировано {len(examples)} примеров")
    print(f"Примеры сохранены в файл: {filename}")

def analyze_examples(examples):
    """Анализирует сгенерированные примеры"""
    print(f"\n{'='*60}")
    print(f"АНАЛИЗ СГЕНЕРИРОВАННЫХ ПРИМЕРОВ")
    print(f"{'='*60}")
    print(f"Всего примеров: {len(examples)}")

    # Анализ длины примеров
    lengths = [len(e.split()) for e in examples]
    avg_length = sum(lengths) / len(lengths)
    print(f"Средняя длина запроса: {avg_length:.1f} слов")
    print(f"Минимальная длина: {min(lengths)} слов")
    print(f"Максимальная длина: {max(lengths)} слов")

    # Статистика по ключевым словам
    keywords = {
        'погод': 'погода',
        'температур': 'температура',
        'градус': 'градусы',
        'дожд': 'дождь',
        'снег': 'снег',
        'ветер': 'ветер',
        'облач': 'облачность',
        'солн': 'солнце',
        'туч': 'тучи',
        'гроз': 'гроза',
        'туман': 'туман',
        'град': 'град',
        'ливень': 'ливень',
        'метель': 'метель',
        'сегодня': 'сегодня',
        'завтра': 'завтра',
        'недел': 'неделя',
        'утр': 'утро',
        'вечер': 'вечер',
        'ноч': 'ночь',
        'дн': 'день',
        'мокр': 'мокрый',
        'сух': 'сухой',
        'тепл': 'тепло',
        'холод': 'холод',
        'жар': 'жара',
        'мороз': 'мороз',
    }

    print(f"\nЧастота ключевых слов:")
    for key, display in keywords.items():
        count = sum(1 for e in examples if key in e.lower())
        percentage = (count/len(examples)*100)
        if percentage > 1:  # Показываем только частые слова
            print(f"  {display:15}: {count:5} ({percentage:5.1f}%)")

    # Статистика по типам запросов
    print(f"\nСтатистика по типам запросов:")
    stats = {
        'вопросительные (? или начинается с "как"/"сколько"/"будет ли")':
            sum(1 for e in examples if '?' in e or
                e.lower().startswith(('как', 'сколько', 'будет ли', 'пойдет ли', 'ожидается ли'))),
        'вежливые формы (пожалуйста/будь добр/прошу)':
            sum(1 for e in examples if any(word in e.lower() for word in ['пожалуйста', 'будь добр', 'прошу', 'будь любезен'])),
        'разговорные/сленговые':
            sum(1 for e in examples if any(word in e.lower() for word in ['чё', 'погодка', 'как там', 'что там'])),
        'с указанием времени':
            sum(1 for e in examples if any(word in e.lower() for word in ['сегодня', 'завтра', 'утро', 'вечер', 'ночь', 'день'])),
        'с указанием места':
            sum(1 for e in examples if any(word in e.lower() for word in ['москв', 'городе', 'улиц', 'окн', 'здесь', 'у нас'])),
        'практические вопросы (как одеться/нужен ли зонт)':
            sum(1 for e in examples if any(word in e.lower() for word in ['одеться', 'надеть', 'зонт', 'гулять', 'пикник'])),
    }

    for key, value in stats.items():
        percentage = (value/len(examples)*100)
        print(f"  {key:50}: {value:5} ({percentage:5.1f}%)")

def main():
    # Генерация примеров
    examples = generate_weather_intent_examples()

    # Анализ сгенерированных примеров
    analyze_examples(examples)

    print(f"\n{'='*50}")
    print(f"Итого сгенерировано примеров: {len(examples)}")
    print(f"{'='*50}")

    print("\nПервые 30 примеров для проверки:")
    print("-" * 50)
    for i, example in enumerate(examples[:30], 1):
        print(f"{i:3}. {example}")

    print("\nПримеры из разных категорий:")
    print("-" * 50)

    # Показываем примеры разных типов
    categories = {
        'Короткие': [e for e in examples if len(e.split()) <= 3],
        'Длинные': [e for e in examples if len(e.split()) >= 10],
        'Вежливые': [e for e in examples if 'пожалуйста' in e.lower()],
        'Сленговые': [e for e in examples if 'чё по погод' in e.lower()],
        'Практические': [e for e in examples if 'зонт' in e.lower()],
        'Сравнительные': [e for e in examples if 'теплее чем' in e.lower() or 'холоднее чем' in e.lower()],
    }

    for cat_name, cat_examples in categories.items():
        if cat_examples:
            print(f"\n{cat_name} (примеры):")
            for i, example in enumerate(cat_examples[:3], 1):
                print(f"  {example}")
            print(f"  ... и ещё {len(cat_examples)-3 if len(cat_examples)>3 else 0}")

    # Сохранение в файл
    save_examples_to_file(examples, "weather.txt")

    # Разделение на тренировочные и тестовые наборы
    random.shuffle(examples)
    split_point = int(len(examples) * 0.8)

    train_examples = examples[:split_point]
    test_examples = examples[split_point:]

    with open("узнать_погоду_train.txt", 'w', encoding='utf-8') as f:
        for example in train_examples:
            f.write(example + '\n')

    with open("узнать_погоду_test.txt", 'w', encoding='utf-8') as f:
        for example in test_examples:
            f.write(example + '\n')

    print(f"\nРазделено на:")
    print(f"  Тренировочные: {len(train_examples)} примеров")
    print(f"  Тестовые: {len(test_examples)} примеров")
    print(f"  Соотношение: {len(train_examples)/len(examples)*100:.1f}% / {len(test_examples)/len(examples)*100:.1f}%")

if __name__ == "__main__":
    main()