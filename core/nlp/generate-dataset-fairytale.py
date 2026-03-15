import random

def generate_fairy_tale_intent_examples():
    """
    Генерирует примерно 50к примеров для интента "включи сказку"
    (после разделения 80/20 будет ~10к тестовых примеров)
    """

    # Расширенные базовые компоненты фраз
    action_words = [
        'включи', 'поставь', 'запусти', 'давай', 'открой', 'начни',
        'продолжи', 'воспроизведи', 'включи снова', 'поставь снова',
        'запусти снова', 'давай включим', 'давай послушаем', 'поставь мне',
        'включи мне', 'запусти мне', 'начни воспроизведение',
        'включи пожалуйста', 'поставь пожалуйста', 'запусти пожалуйста',
        'давай включи', 'давай поставим', 'давай запустим',
        'хочу послушать', 'хочу включить', 'хочу поставить',
        'можно включить', 'можно поставить', 'можно запустить',
        'вруби', 'включи-ка', 'поставь-ка', 'запусти-ка',
        'дай послушать', 'дай включить', 'дай поставить',
        'покажи сказку', 'покажи историю', 'покажи рассказ',
        'включи для', 'поставь для', 'запусти для',
        'начни сказку', 'начни историю', 'начни рассказ',
        'открой сказку', 'открой историю', 'открой рассказ',
    ]

    polite_words = [
        '', 'пожалуйста', 'пожалуйста,', 'будь добр', 'будь добра',
        'можно', 'мог бы ты', 'не мог бы ты', 'будь так добр',
        'очень прошу', 'умоляю', 'прошу тебя', 'пожалуйста, будь добр',
        'если можно', 'если не сложно', 'не откажи', 'сделай одолжение'
    ]

    fairy_tale_types = [
        'сказку', 'сказку', 'сказку', 'сказку',  # Увеличиваем вес основного варианта
        'историю', 'рассказ', 'аудиосказку', 'аудиокнигу',
        'детскую сказку', 'весёлую сказку', 'интересную сказку',
        'добрую сказку', 'волшебную сказку', 'сказку на ночь',
        'новую сказку', 'русскую сказку', 'народную сказку',
        'классическую сказку', 'любимую сказку', 'старую сказку',
        'короткую сказку', 'длинную сказку', 'красивую сказку',
        'музыкальную сказку', 'интерактивную сказку', 'анимированную сказку',
        'сказку для детей', 'сказку для малышей', 'сказку для ребёнка',
        'сказку перед сном', 'сказку на ночь', 'сказку на вечер',
        'историю для детей', 'рассказ для детей', 'аудиосказку для детей',
    ]

    # Словарь названий сказок с правильными падежами
    # Формат: {именительный: {винительный: '...', дательный: '...', творительный: '...'}}
    fairy_tale_names_dict = {
        'колобок': {
            'винительный': 'колобка',
            'дательный': 'колобку',
            'творительный': 'колобком'
        },
        'репка': {
            'винительный': 'репку',
            'дательный': 'репке',
            'творительный': 'репкой'
        },
        'теремок': {
            'винительный': 'теремок',
            'дательный': 'теремку',
            'творительный': 'теремком'
        },
        'курочка ряба': {
            'винительный': 'курочку рябу',
            'дательный': 'курочке рябе',
            'творительный': 'курочкой рябой'
        },
        'гуси-лебеди': {
            'винительный': 'гусей-лебедей',
            'дательный': 'гусям-лебедям',
            'творительный': 'гусями-лебедями'
        },
        'маша и медведь': {
            'винительный': 'машу и медведя',
            'дательный': 'маше и медведю',
            'творительный': 'машей и медведем'
        },
        'волк и семеро козлят': {
            'винительный': 'волка и семерых козлят',
            'дательный': 'волку и семерым козлятам',
            'творительный': 'волком и семью козлятами'
        },
        'три поросёнка': {
            'винительный': 'трёх поросят',
            'дательный': 'трём поросятам',
            'творительный': 'тремя поросятами'
        },
        'красная шапочка': {
            'винительный': 'красную шапочку',
            'дательный': 'красной шапочке',
            'творительный': 'красной шапочкой'
        },
        'золушка': {
            'винительный': 'золушку',
            'дательный': 'золушке',
            'творительный': 'золушкой'
        },
        'спящая красавица': {
            'винительный': 'спящую красавицу',
            'дательный': 'спящей красавице',
            'творительный': 'спящей красавицей'
        },
        'снежная королева': {
            'винительный': 'снежную королеву',
            'дательный': 'снежной королеве',
            'творительный': 'снежной королевой'
        },
        'русалочка': {
            'винительный': 'русалочку',
            'дательный': 'русалочке',
            'творительный': 'русалочкой'
        },
        'дикие лебеди': {
            'винительный': 'диких лебедей',
            'дательный': 'диким лебедям',
            'творительный': 'дикими лебедями'
        },
        'гадкий утёнок': {
            'винительный': 'гадкого утёнка',
            'дательный': 'гадкому утёнку',
            'творительный': 'гадким утёнком'
        },
        'дюймовочка': {
            'винительный': 'дюймовочку',
            'дательный': 'дюймовочке',
            'творительный': 'дюймовочкой'
        },
        'бременские музыканты': {
            'винительный': 'бременских музыкантов',
            'дательный': 'бременским музыкантам',
            'творительный': 'бременскими музыкантами'
        },
        'кот в сапогах': {
            'винительный': 'кота в сапогах',
            'дательный': 'коту в сапогах',
            'творительный': 'котом в сапогах'
        },
        'мальчик-с-пальчик': {
            'винительный': 'мальчика-с-пальчика',
            'дательный': 'мальчику-с-пальчику',
            'творительный': 'мальчиком-с-пальчиком'
        },
        'принцесса на горошине': {
            'винительный': 'принцессу на горошине',
            'дательный': 'принцессе на горошине',
            'творительный': 'принцессой на горошине'
        },
        'белоснежка': {
            'винительный': 'белоснежку',
            'дательный': 'белоснежке',
            'творительный': 'белоснежкой'
        },
        'рапунцель': {
            'винительный': 'рапунцель',
            'дательный': 'рапунцель',
            'творительный': 'рапунцель'
        },
        'аленький цветочек': {
            'винительный': 'аленький цветочек',
            'дательный': 'аленькому цветочку',
            'творительный': 'аленьким цветочком'
        },
        'конёк-горбунок': {
            'винительный': 'конька-горбунка',
            'дательный': 'коньку-горбунку',
            'творительный': 'коньком-горбунком'
        },
        'сказка о царе салтане': {
            'винительный': 'сказку о царе салтане',
            'дательный': 'сказке о царе салтане',
            'творительный': 'сказкой о царе салтане'
        },
        'сказка о рыбаке и рыбке': {
            'винительный': 'сказку о рыбаке и рыбке',
            'дательный': 'сказке о рыбаке и рыбке',
            'творительный': 'сказкой о рыбаке и рыбке'
        },
        'иван-царевич и серый волк': {
            'винительный': 'ивана-царевича и серого волка',
            'дательный': 'ивану-царевичу и серому волку',
            'творительный': 'иваном-царевичем и серым волком'
        },
        'царевна-лягушка': {
            'винительный': 'царевну-лягушку',
            'дательный': 'царевне-лягушке',
            'творительный': 'царевной-лягушкой'
        },
        'василиса прекрасная': {
            'винительный': 'василису прекрасную',
            'дательный': 'василисе прекрасной',
            'творительный': 'василисой прекрасной'
        },
        'сестрица алёнушка и братец иванушка': {
            'винительный': 'сестрицу алёнушку и братца иванушку',
            'дательный': 'сестрице алёнушке и братцу иванушке',
            'творительный': 'сестрицей алёнушкой и братцем иванушкой'
        },
        'лиса и журавль': {
            'винительный': 'лису и журавля',
            'дательный': 'лисе и журавлю',
            'творительный': 'лисой и журавлём'
        },
        'лиса и волк': {
            'винительный': 'лису и волка',
            'дательный': 'лисе и волку',
            'творительный': 'лисой и волком'
        },
        'заяц и ёж': {
            'винительный': 'зайца и ежа',
            'дательный': 'зайцу и ежу',
            'творительный': 'зайцем и ежом'
        },
        'лиса и заяц': {
            'винительный': 'лису и зайца',
            'дательный': 'лисе и зайцу',
            'творительный': 'лисой и зайцем'
        },
        'медведь и лиса': {
            'винительный': 'медведя и лису',
            'дательный': 'медведю и лисе',
            'творительный': 'медведем и лисой'
        },
        'волк и лиса': {
            'винительный': 'волка и лису',
            'дательный': 'волку и лисе',
            'творительный': 'волком и лисой'
        },
        'коза-дереза': {
            'винительный': 'козу-дерезу',
            'дательный': 'козе-дерезе',
            'творительный': 'козой-дерезой'
        },
        'лиса и тетерев': {
            'винительный': 'лису и тетерева',
            'дательный': 'лисе и тетереву',
            'творительный': 'лисой и тетеревом'
        },
        'петушок золотой гребешок': {
            'винительный': 'петушка золотого гребешка',
            'дательный': 'петушку золотому гребешку',
            'творительный': 'петушком золотым гребешком'
        },
        'лиса и дрозд': {
            'винительный': 'лису и дрозда',
            'дательный': 'лисе и дрозду',
            'творительный': 'лисой и дроздом'
        },
        'мужик и медведь': {
            'винительный': 'мужика и медведя',
            'дательный': 'мужику и медведю',
            'творительный': 'мужиком и медведем'
        },
    }

    # Список названий в именительном падеже для обратной совместимости
    fairy_tale_names = list(fairy_tale_names_dict.keys())

    prepositions = [
        '', 'про', 'о', 'под названием', 'с названием',
        'про историю', 'про рассказ', 'про сказку',
        'называется', 'которая называется', 'которая зовётся',
        'историю про', 'рассказ про', 'сказку про',
    ]

    modifiers = [
        '', 'для меня', 'для нас', 'для детей', 'для ребёнка',
        'для малыша', 'для малышей', 'для дочки', 'для сына',
        'на ночь', 'перед сном', 'в машине', 'в дороге',
        'на вечер', 'на сегодня', 'на завтра', 'сейчас',
        'прямо сейчас', 'немедленно', 'быстро', 'поскорее',
        'тихо', 'громко', 'негромко', 'тихонько',
        'в детской', 'в комнате', 'в спальне', 'в гостиной',
        'на кухне', 'в ванной', 'в саду', 'во дворе',
        'в парке', 'на прогулке', 'на даче', 'в гостях',
    ]

    pronouns = [
        '', 'мне', 'нам', 'детям', 'ребёнку',
        'малышу', 'малышам', 'дочке', 'сыну',
        'нашим детям', 'нашим малышам', 'моему ребёнку',
        'моим детям', 'нашей дочке', 'нашему сыну',
    ]

    connectors = [
        '', 'а', 'и', 'может быть', 'возможно',
        'а может', 'а может быть', 'или', 'или может',
        'а то', 'а то что', 'вот', 'вот бы',
        'так', 'так что', 'ну', 'ну что',
    ]

    # Генерация комбинаций
    examples = []

    # 1. Базовые комбинации (самые частые)
    print("1. Генерация базовых комбинаций...")
    base_count = len(examples)

    # Базовые паттерны с правильными падежами
    base_patterns = [
        ("{action} {tale_type} про {name_acc}", True),  # Винительный после "про"
        ("{action} {tale_type} {name_acc}", True),  # Винительный после глагола
        ("{action} про {name_acc}", True),  # Винительный после "про"
        ("{action} {name_acc}", True),  # Винительный после глагола
        ("{action} {tale_type} {name}", False),  # Именительный (для разнообразия)
    ]

    for pattern, use_case in base_patterns:
        for action in action_words[:12]:
            for tale_type in fairy_tale_types[:15]:
                for base_name in fairy_tale_names[:20]:
                    if random.random() < 0.5:
                        if use_case and base_name in fairy_tale_names_dict:
                            # Используем правильный падеж
                            name_acc = fairy_tale_names_dict[base_name].get('винительный', base_name)
                            phrase = pattern.format(
                                action=action,
                                tale_type=tale_type,
                                name_acc=name_acc,
                                name=base_name
                            ).strip()
                        else:
                            # Используем именительный падеж
                            phrase = pattern.format(
                                action=action,
                                tale_type=tale_type,
                                name_acc=base_name,
                                name=base_name
                            ).strip()
                        examples.append(phrase)

    print(f"   Сгенерировано: {len(examples) - base_count}")

    # 2. Комбинации с ошибками (разговорные формы)
    print("2. Генерация вариантов с ошибками...")
    base_count = len(examples)

    # Неправильные склонения и разговорные формы
    incorrect_tale_types = [
        'сказка', 'история', 'рассказ', 'аудиосказка', 'аудиокнига',
        'сказка', 'история', 'рассказ', 'сказка для детей',
        'детская сказка', 'весёлая сказка', 'интересная сказка',
    ]

    error_patterns = [
        ("{action} {tale_type} про {name_acc}", 0.8),
        ("{action} про {name_acc}", 0.7),
        ("давай {tale_type} про {name_acc}", 0.7),
        ("можно {action} {tale_type} про {name_acc}", 0.6),
        ("хочу {tale_type} про {name_acc}", 0.7),
        ("хочется {tale_type} про {name_acc}", 0.6),
        ("нужна {tale_type} про {name_acc}", 0.5),
        ("нужна мне {tale_type} про {name_acc}", 0.5),
        ("дай {tale_type} про {name_acc}", 0.6),
        ("дай мне {tale_type} про {name_acc}", 0.6),
        ("покажи {tale_type} про {name_acc}", 0.6),
        ("покажи мне {tale_type} про {name_acc}", 0.5),
    ]

    for pattern, prob in error_patterns:
        for action in action_words[:10]:
            for tale_type in incorrect_tale_types:
                for base_name in fairy_tale_names[:15]:
                    if random.random() < prob * 0.7:
                        # Используем правильный винительный падеж
                        if base_name in fairy_tale_names_dict:
                            name_acc = fairy_tale_names_dict[base_name].get('винительный', base_name)
                        else:
                            name_acc = base_name
                        
                        phrase = pattern.format(
                            action=action,
                            tale_type=tale_type,
                            name_acc=name_acc
                        ).strip()
                        examples.append(phrase)

    print(f"   Сгенерировано: {len(examples) - base_count}")

    # 3. Варианты с числительными и склонениями
    print("3. Генерация вариантов с числительными...")
    base_count = len(examples)

    number_stories = [
        ('три поросёнка', ['три поросёнка', 'трёх поросят', 'три поросёнок', 'про трёх поросят']),
        ('семь козлят', ['семь козлят', 'семи козлят', 'семь козлёнок', 'про семерых козлят']),
        ('три медведя', ['три медведя', 'трёх медведей', 'три медведь', 'про трёх медведей']),
        ('два жадных медвежонка', ['два жадных медвежонка', 'двух жадных медвежат', 'про двух жадных медвежат']),
        ('волк и семеро козлят', ['волк и семеро козлят', 'волк и семерых козлят', 'про волка и семерых козлят']),
        ('маша и медведь', ['маша и медведь', 'машу и медведя', 'про машу и медведя']),
    ]

    number_patterns = [
        "{action} {tale_type} про {variation}",
        "{action} {tale_type} {variation}",
        "{action} про {variation}",
        "{action} {variation}",
    ]

    for base_name, variations in number_stories:
        for variation in variations:
            for pattern in number_patterns:
                for action in action_words[:8]:
                    for tale_type in ['сказку', 'историю', 'рассказ', 'аудиосказку']:
                        if random.random() < 0.4:
                            phrase = pattern.format(
                                action=action,
                                tale_type=tale_type,
                                variation=variation
                            ).strip()
                            examples.append(phrase)

    print(f"   Сгенерировано: {len(examples) - base_count}")

    # 4. Вопросительные формы
    print("4. Генерация вопросительных форм...")
    base_count = len(examples)

    question_words = [
        'включишь', 'поставишь', 'запустишь', 'откроешь', 'начнёшь',
        'включишь ли', 'поставишь ли', 'запустишь ли', 'откроешь ли',
        'можешь включить', 'можешь поставить', 'можешь запустить',
        'сможешь включить', 'сможешь поставить', 'сможешь запустить',
        'включишь мне', 'поставишь мне', 'запустишь мне',
    ]

    question_prefixes = [
        'а', 'а можно', 'скажи', 'подскажи', 'скажи пожалуйста',
        'подскажи пожалуйста', 'а не мог бы ты', 'а не могла бы ты',
        'а не', 'а что если', 'а как насчёт', 'а может',
        'а может быть', 'а может ты', 'а ты можешь',
        'а ты не мог бы', 'а ты не могла бы', 'а ты',
    ]

    question_patterns = [
        ("{prefix} {q_word} {tale_type} про {name_acc}", True),
        ("{prefix} {q_word} {tale_type} {name_acc}", True),
        ("{prefix} {q_word} про {name_acc}", True),
        ("{prefix} {tale_type} про {name_acc}", True),
        ("{prefix} можно {tale_type} про {name_acc}", True),
        ("{prefix} можно включить {tale_type} про {name_acc}", True),
    ]

    for pattern, use_case in question_patterns:
        for q_word in question_words[:8]:
            for tale_type in fairy_tale_types[:12]:
                for base_name in fairy_tale_names[:15]:
                    for prefix in question_prefixes[:8]:
                        if random.random() < 0.3:
                            try:
                                if use_case and base_name in fairy_tale_names_dict:
                                    name_acc = fairy_tale_names_dict[base_name].get('винительный', base_name)
                                else:
                                    name_acc = base_name
                                
                                phrase = pattern.format(
                                    prefix=prefix,
                                    q_word=q_word,
                                    tale_type=tale_type,
                                    name_acc=name_acc,
                                    name=base_name
                                ).strip()
                                examples.append(phrase)
                            except KeyError:
                                # Пропускаем паттерны с неподходящими ключами
                                pass

    print(f"   Сгенерировано: {len(examples) - base_count}")

    # 5. Детализированные запросы
    print("5. Генерация детализированных запросов...")
    base_count = len(examples)

    detailed_phrases = [
        "Не мог бы ты {action} {tale_type} про {name_acc} {mod}",
        "Очень прошу {action} {tale_type} про {name_acc} {mod}",
        "Будь так добр, {action} {tale_type} про {name_acc} для {pron}",
        "Можно ли {action} {tale_type} про {name_acc} {mod}",
        "Не могла бы ты {action} {tale_type} про {name_acc} {mod}",
        "Умоляю {action} {tale_type} про {name_acc} {mod}",
        "Прошу тебя {action} {tale_type} про {name_acc} {mod}",
        "Сделай одолжение, {action} {tale_type} про {name_acc} {mod}",
        "Если можно, {action} {tale_type} про {name_acc} {mod}",
        "Если не сложно, {action} {tale_type} про {name_acc} {mod}",
        "Буду очень благодарен, если {action} {tale_type} про {name_acc} {mod}",
        "Буду очень благодарна, если {action} {tale_type} про {name_acc} {mod}",
        "Хотелось бы {action} {tale_type} про {name_acc} {mod}",
        "Хочется {action} {tale_type} про {name_acc} {mod}",
        "Мне нужно {action} {tale_type} про {name_acc} {mod}",
        "Нам нужно {action} {tale_type} про {name_acc} {mod}",
        "Детям нужно {action} {tale_type} про {name_acc} {mod}",
    ]

    for template in detailed_phrases:
        for action in action_words[:8]:
            for tale_type in fairy_tale_types[:10]:
                for base_name in fairy_tale_names[:12]:
                    for mod in modifiers[:6]:
                        for pron in ['меня', 'нас', 'наших детей', 'нашего ребёнка', 'наших малышей']:
                            if random.random() < 0.2:
                                try:
                                    if base_name in fairy_tale_names_dict:
                                        name_acc = fairy_tale_names_dict[base_name].get('винительный', base_name)
                                    else:
                                        name_acc = base_name
                                    
                                    phrase = template.format(
                                        action=action,
                                        tale_type=tale_type,
                                        name_acc=name_acc,
                                        name=base_name,
                                        mod=mod,
                                        pron=pron
                                    ).strip()
                                    examples.append(phrase)
                                except KeyError:
                                    pass

    print(f"   Сгенерировано: {len(examples) - base_count}")

    # 6. Имена в разных падежах (правильные склонения)
    print("6. Генерация вариантов с правильными падежами...")
    base_count = len(examples)

    # Паттерны с использованием правильных падежей
    case_patterns = [
        "{action} {tale_type} про {name_acc}",  # Винительный после "про"
        "{action} {tale_type} {name_acc}",  # Винительный после глагола
        "{action} про {name_acc}",  # Винительный после "про"
        "{action} {tale_type} для {name_gen}",  # Родительный после "для"
        "хочу послушать {name_acc}",  # Винительный
        "хочется {name_acc}",  # Винительный
        "нужна {tale_type} про {name_acc}",  # Винительный после "про"
        "дай {name_acc}",  # Винительный
        "дай мне {name_acc}",  # Винительный
    ]

    for base_name, cases in fairy_tale_names_dict.items():
        name_acc = cases.get('винительный', base_name)  # Винительный падеж
        name_dat = cases.get('дательный', base_name)  # Дательный падеж
        name_gen = name_acc  # Для "для" обычно используется винительный или родительный
        
        for pattern in case_patterns:
            for action in action_words[:8]:
                for tale_type in ['сказку', 'историю', 'рассказ', 'аудиосказку', 'детскую сказку']:
                    if random.random() < 0.3:
                        try:
                            phrase = pattern.format(
                                action=action,
                                tale_type=tale_type,
                                name_acc=name_acc,
                                name_dat=name_dat,
                                name_gen=name_gen
                            ).strip()
                            examples.append(phrase)
                        except KeyError:
                            # Если паттерн не требует всех падежей, пропускаем
                            pass

    print(f"   Сгенерировано: {len(examples) - base_count}")

    # 7. Эмоциональные варианты
    print("7. Генерация эмоциональных вариантов...")
    base_count = len(examples)

    emotional_prefixes = [
        'Ой,', 'Ах,', 'Вот бы', 'Очень хочется', 'Ужасно хочу',
        'Очень хочу', 'Так хочется', 'Ужасно хочется', 'Очень бы хотелось',
        'Ой, как хочется', 'Ах, как хочется', 'Вот бы можно было',
        'Очень прошу', 'Умоляю', 'Пожалуйста', 'Прошу тебя',
        'Очень нужно', 'Нам очень нужно', 'Детям очень нужно',
        'Ой, давай', 'Ах, давай', 'Ну давай', 'Давай же',
        'Пожалуйста, давай', 'Очень прошу, давай',
    ]

    emotional_suffixes = [
        ', хорошо?', ', ладно?', ', окей?', ', спасибо!',
        ', пожалуйста!', ', очень прошу!', ', умоляю!',
        ', а?', ', да?', ', можно?', ', можно же?',
        ', ну пожалуйста!', ', будь добр!', ', будь добра!',
        ', очень нужно!', ', срочно!', ', быстрее!',
        ', скорее!', ', поскорее!', ', немедленно!',
    ]

    emotional_patterns = [
        ("{prefix} {action} {tale_type} про {name_acc}{suffix}", True),
        ("{prefix} {action} {tale_type} {name_acc}{suffix}", True),
        ("{prefix} {action} про {name_acc}{suffix}", True),
        ("{prefix} можно {action} {tale_type} про {name_acc}{suffix}", True),
    ]

    for pattern, use_case in emotional_patterns:
        for prefix in emotional_prefixes[:10]:
            for action in action_words[:6]:
                for tale_type in fairy_tale_types[:8]:
                    for base_name in fairy_tale_names[:12]:
                        for suffix in emotional_suffixes[:8]:
                            if random.random() < 0.25:
                                try:
                                    if use_case and base_name in fairy_tale_names_dict:
                                        name_acc = fairy_tale_names_dict[base_name].get('винительный', base_name)
                                    else:
                                        name_acc = base_name
                                    
                                    phrase = pattern.format(
                                        prefix=prefix,
                                        action=action,
                                        tale_type=tale_type,
                                        name_acc=name_acc,
                                        name=base_name,
                                        suffix=suffix
                                    ).strip()
                                    examples.append(phrase)
                                except KeyError:
                                    pass

    print(f"   Сгенерировано: {len(examples) - base_count}")

    # 8. Смешанные стили и разговорные формы
    print("8. Генерация смешанных стилей...")
    base_count = len(examples)

    mixed_styles = [
        ("Так, {action}-ка {tale_type} про {name_acc}", 0.6),
        ("Давай-ка {action} {tale_type} про {name_acc}", 0.7),
        ("А не {action} ли нам {tale_type} про {name_acc}", 0.5),
        ("А не {action} ли ты {tale_type} про {name_acc}", 0.5),
        ("А что если {action} {tale_type} про {name_acc}", 0.5),
        ("А как насчёт того, чтобы {action} {tale_type} про {name_acc}", 0.4),
        ("Может {action} {tale_type} про {name_acc}", 0.6),
        ("Может быть {action} {tale_type} про {name_acc}", 0.6),
        ("А может {action} {tale_type} про {name_acc}", 0.6),
        ("Ну {action} {tale_type} про {name_acc}", 0.6),
        ("Ну давай {action} {tale_type} про {name_acc}", 0.7),
        ("Ну же {action} {tale_type} про {name_acc}", 0.5),
        ("Так вот, {action} {tale_type} про {name_acc}", 0.4),
        ("Знаешь что, {action} {tale_type} про {name_acc}", 0.4),
        ("Слушай, {action} {tale_type} про {name_acc}", 0.5),
        ("Слушай-ка, {action} {tale_type} про {name_acc}", 0.5),
    ]

    for template, prob in mixed_styles:
        for action in action_words[:8]:
            for tale_type in fairy_tale_types[:10]:
                for base_name in fairy_tale_names[:15]:
                    if random.random() < prob * 0.6:
                        try:
                            if base_name in fairy_tale_names_dict:
                                name_acc = fairy_tale_names_dict[base_name].get('винительный', base_name)
                            else:
                                name_acc = base_name
                            
                            phrase = template.format(
                                action=action,
                                tale_type=tale_type,
                                name_acc=name_acc,
                                name=base_name
                            ).strip()
                            examples.append(phrase)
                        except KeyError:
                            pass

    print(f"   Сгенерировано: {len(examples) - base_count}")

    # 9. Дополнительные паттерны с модификаторами
    print("9. Генерация вариантов с модификаторами...")
    base_count = len(examples)

    modifier_patterns = [
        ("{action} {tale_type} про {name_acc} {mod}", True),
        ("{action} {tale_type} {name_acc} {mod}", True),
        ("{action} про {name_acc} {mod}", True),
        ("{polite} {action} {tale_type} про {name_acc} {mod}", True),
        ("{action} {tale_type} про {name_acc} для {pron}", True),
        ("{action} {tale_type} {name_acc} для {pron}", True),
    ]

    for pattern, use_case in modifier_patterns:
        for action in action_words[:8]:
            for tale_type in fairy_tale_types[:10]:
                for base_name in fairy_tale_names[:12]:
                    for mod in modifiers[:6]:
                        for pron in pronouns[:4]:
                            for polite in polite_words[:3]:
                                if random.random() < 0.15:
                                    try:
                                        if use_case and base_name in fairy_tale_names_dict:
                                            name_acc = fairy_tale_names_dict[base_name].get('винительный', base_name)
                                        else:
                                            name_acc = base_name
                                        
                                        phrase = pattern.format(
                                            action=action,
                                            tale_type=tale_type,
                                            name_acc=name_acc,
                                            name=base_name,
                                            mod=mod,
                                            pron=pron,
                                            polite=polite
                                        ).strip()
                                        examples.append(phrase)
                                    except KeyError:
                                        pass

    print(f"   Сгенерировано: {len(examples) - base_count}")

    # 10. Разговорные и сленговые формы
    print("10. Генерация разговорных форм...")
    base_count = len(examples)

    slang_patterns = [
        "вруби {tale_type} про {name_acc}",
        "вруби-ка {tale_type} про {name_acc}",
        "дай {tale_type} про {name_acc}",
        "дай-ка {tale_type} про {name_acc}",
        "гони {tale_type} про {name_acc}",
        "гони-ка {tale_type} про {name_acc}",
        "включи-ка {tale_type} про {name_acc}",
        "поставь-ка {tale_type} про {name_acc}",
        "запусти-ка {tale_type} про {name_acc}",
        "давай {tale_type} про {name_acc}",
        "давай-ка {tale_type} про {name_acc}",
        "ну давай {tale_type} про {name_acc}",
        "ну давай-ка {tale_type} про {name_acc}",
        "хочу {tale_type} про {name_acc}",
        "хочется {tale_type} про {name_acc}",
        "нужна {tale_type} про {name_acc}",
        "нужна мне {tale_type} про {name_acc}",
    ]

    for pattern in slang_patterns:
        for tale_type in fairy_tale_types[:12]:
            for base_name in fairy_tale_names[:15]:
                if random.random() < 0.4:
                    if base_name in fairy_tale_names_dict:
                        name_acc = fairy_tale_names_dict[base_name].get('винительный', base_name)
                    else:
                        name_acc = base_name
                    
                    phrase = pattern.format(
                        tale_type=tale_type,
                        name_acc=name_acc
                    ).strip()
                    examples.append(phrase)

    print(f"   Сгенерировано: {len(examples) - base_count}")

    # 11. Варианты с предлогами и союзами
    print("11. Генерация вариантов с предлогами...")
    base_count = len(examples)

    preposition_patterns = [
        ("{action} {tale_type} про {name_acc}", True),  # Винительный после "про"
        ("{action} {tale_type} о {name}", False),  # Предложный после "о" (остаётся в именительном)
        ("{action} {tale_type} под названием {name}", False),  # Именительный
        ("{action} {tale_type} с названием {name}", False),  # Именительный
        ("{action} {tale_type} которая называется {name}", False),  # Именительный
        ("{action} {tale_type} которая зовётся {name}", False),  # Именительный
        ("{action} {tale_type} про историю {name_acc}", True),  # Винительный после "про"
        ("{action} {tale_type} про сказку {name_acc}", True),  # Винительный после "про"
    ]

    for pattern, use_case in preposition_patterns:
        for action in action_words[:8]:
            for tale_type in fairy_tale_types[:10]:
                for base_name in fairy_tale_names[:15]:
                    if random.random() < 0.4:
                        try:
                            if use_case and base_name in fairy_tale_names_dict:
                                name_acc = fairy_tale_names_dict[base_name].get('винительный', base_name)
                            else:
                                name_acc = base_name
                            
                            phrase = pattern.format(
                                action=action,
                                tale_type=tale_type,
                                name_acc=name_acc,
                                name=base_name
                            ).strip()
                            examples.append(phrase)
                        except KeyError:
                            pass

    print(f"   Сгенерировано: {len(examples) - base_count}")

    # 12. Дополнительные случайные комбинации для достижения ~50к
    print("12. Генерация дополнительных случайных комбинаций...")
    target_count = 50000
    additional_needed = target_count - len(examples)

    if additional_needed > 0:
        print(f"   Нужно добавить ещё {additional_needed} примеров")

        # Расширенные паттерны для генерации с правильными падежами
        extended_patterns = [
            ("{action} {tale_type} про {name_acc}", True),
            ("{action} {tale_type} {name_acc}", True),
            ("{action} про {name_acc}", True),
            ("{polite} {action} {tale_type} про {name_acc}", True),
            ("{action} {tale_type} про {name_acc} {mod}", True),
            ("{polite} {action} {tale_type} про {name_acc} {mod}", True),
            ("{action} {tale_type} про {name_acc} для {pron}", True),
            ("{prefix} {action} {tale_type} про {name_acc}", True),
            ("{action} {tale_type} про {name_acc}{suffix}", True),
        ]

        for _ in range(additional_needed):
            pattern, use_case = random.choice(extended_patterns)
            action = random.choice(action_words)
            tale_type = random.choice(fairy_tale_types)
            base_name = random.choice(fairy_tale_names)
            
            # Используем правильный падеж
            if use_case and base_name in fairy_tale_names_dict:
                name_acc = fairy_tale_names_dict[base_name].get('винительный', base_name)
            else:
                name_acc = base_name
            
            polite = random.choice(polite_words)
            mod = random.choice(modifiers)
            pron = random.choice(pronouns)
            prefix = random.choice(['', 'а', 'давай', 'можно', 'ну', 'а может'])
            suffix = random.choice(['', '!', '?', ', пожалуйста', ', хорошо?'])

            try:
                phrase = pattern.format(
                    action=action,
                    tale_type=tale_type,
                    name_acc=name_acc,
                    name=base_name,
                    polite=polite,
                    mod=mod,
                    pron=pron,
                    prefix=prefix,
                    suffix=suffix
                ).strip()
                # Очистка от лишних пробелов
                phrase = ' '.join(phrase.split())
                if phrase:
                    examples.append(phrase)
            except KeyError:
                pass

    # Удаление дубликатов и очистка
    print("\nУдаление дубликатов...")
    examples = list(set(examples))
    examples = [e.strip() for e in examples if e.strip()]

    # Если всё равно меньше целевого количества, добавим ещё
    if len(examples) < target_count:
        needed = target_count - len(examples)
        print(f"Догенерация {needed} примеров...")
        for _ in range(needed):
            action = random.choice(action_words)
            tale_type = random.choice(fairy_tale_types)
            base_name = random.choice(fairy_tale_names)
            # Используем правильный винительный падеж после "про"
            if base_name in fairy_tale_names_dict:
                name_acc = fairy_tale_names_dict[base_name].get('винительный', base_name)
            else:
                name_acc = base_name
            phrase = f"{action} {tale_type} про {name_acc}"
            examples.append(phrase)

    # Финальная очистка дубликатов
    examples = list(set(examples))

    # Финализация с вариациями пунктуации и пробелов
    final_examples = []
    for example in examples:
        final_examples.append(example)
        
        # Вариации с пунктуацией (не для всех, чтобы не было слишком много дубликатов)
        if random.random() < 0.1:
            # Добавляем запятую перед "про"
            if ' про ' in example:
                variant = example.replace(' про ', ', про ', 1)
                if variant != example:
                    final_examples.append(variant)
        
        if random.random() < 0.05:
            # Вариации с пробелами
            variant = example.replace('  ', ' ')
            if variant != example:
                final_examples.append(variant)

    # Удаляем дубликаты после финализации
    final_examples = list(set(final_examples))
    
    # Ограничиваем до разумного максимума (60к для запаса)
    final_examples = final_examples[:60000]

    print(f"Итого уникальных примеров: {len(final_examples)}")
    return final_examples

def save_examples_to_file(examples, filename="fairy_tale_intent_examples.txt"):
    """Сохраняет примеры в файл"""
    with open(filename, 'w', encoding='utf-8') as f:
        for example in examples:
            f.write(example + '\n')

    print(f"Сгенерировано {len(examples)} примеров")
    print(f"Примеры сохранены в файл: {filename}")

def main():
    # Генерация примеров
    examples = generate_fairy_tale_intent_examples()

    # Вывод статистики
    print(f"\n{'='*50}")
    print(f"Итого сгенерировано примеров: {len(examples)}")
    print(f"{'='*50}")

    print("\nПервые 30 примеров:")
    for i, example in enumerate(examples[:30], 1):
        print(f"{i:3}. {example}")

    print("\nПоследние 10 примеров:")
    for i, example in enumerate(examples[-10:], len(examples)-9):
        print(f"{i:3}. {example}")

    # Сохранение в файл
    save_examples_to_file(examples)

    # Разделение на тренировочные и тестовые наборы
    # Цель: ~10к тестовых примеров
    random.shuffle(examples)
    
    target_test_size = 10000
    if len(examples) >= target_test_size:
        # Если примеров достаточно, берём 10к для теста
        test_examples = examples[:target_test_size]
        train_examples = examples[target_test_size:]
    else:
        # Если примеров меньше, делим 80/20
        split_point = int(len(examples) * 0.8)
        train_examples = examples[:split_point]
        test_examples = examples[split_point:]

    with open("fairy_tale_train_examples.txt", 'w', encoding='utf-8') as f:
        for example in train_examples:
            f.write(example + '\n')

    with open("fairytale.txt", 'w', encoding='utf-8') as f:
        for example in test_examples:
            f.write(example + '\n')

    print(f"\nРазделено на:")
    print(f"  Тренировочные: {len(train_examples)} примеров")
    print(f"  Тестовые: {len(test_examples)} примеров")
    
    # Статистика по типам запросов
    print("\nСтатистика по типам запросов:")
    
    stats = {
        'содержит "включи"': sum(1 for e in examples if 'включи' in e.lower()),
        'содержит "поставь"': sum(1 for e in examples if 'поставь' in e.lower()),
        'содержит "запусти"': sum(1 for e in examples if 'запусти' in e.lower()),
        'содержит "сказк"': sum(1 for e in examples if 'сказк' in e.lower()),
        'содержит "про"': sum(1 for e in examples if ' про ' in e.lower()),
        'содержит "пожалуйста"': sum(1 for e in examples if 'пожалуйста' in e.lower()),
        'содержит "?"': sum(1 for e in examples if '?' in e),
        'содержит "!"': sum(1 for e in examples if '!' in e),
    }
    
    for key, value in stats.items():
        percentage = (value / len(examples) * 100) if examples else 0
        print(f"  {key}: {value} ({percentage:.1f}%)")

if __name__ == "__main__":
    main()