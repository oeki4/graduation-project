import spacy
import os

def extract_fairytale_name(doc):
    """
    Извлекает название сказки из распознанного текста, опираясь на синтаксический анализ и простые эвристики (правила).
    В голосовых ассистентах (Алиса, Маруся) названия часто идут в связке с предлогами или глаголами.
    """
    # 1. Самый надежный паттерн: "сказка ПРО [что-то/кого-то]"
    # Мы проходим по списку слов и если находим "про", берем всё, что написано после него.
    for token in doc:
        if token.lower_ == "про":
            # Берем срез текста от следующего слова до конца фразы
            return doc[token.i + 1:].text.strip()
            
    # 2. Если предлог "про" не используется:
    # Пример: "поставь аудиосказку красная шапочка"
    # Ищем синонимы слова "сказка" и берем весь текст после них
    synonyms = ["сказка", "сказочка", "аудиосказка", "история"]
    for token in doc:
        # lemma_ — это начальная форма слова ("сказок", "сказку" -> "сказка")
        if token.lemma_ in synonyms or token.lower_ in synonyms:
            # Если после этого слова в предложении еще есть текст
            if token.i + 1 < len(doc):
                return doc[token.i + 1:].text.strip()
                
    # 3. Фолбэк (когда слово "сказка" вообще не назвали):
    # Пример: "включи колобка" или "давай колобка"
    # Ищем глаголы включения и берем текст после них.
    verbs = ["включить", "поставить", "запустить", "рассказать", "найти", "проиграть", "давать"]
    for token in doc:
        # Проверяем начальную форму глагола
        if token.lemma_ in verbs:
            if token.i + 1 < len(doc):
                name = doc[token.i + 1:].text.strip()
                # Удаляем слово вежливости, если оно осталось (например: "включи пожалуйста репку")
                name = name.lower().replace("пожалуйста", "").strip()
                if name: 
                    return name
                
    # 4. Если ничего не подошло (пользователь сказал просто "включи сказку")
    return None

def main():
    model_path = r"f:\projects\graduation-project\core\nlp\models\intent_model"
    
    print("Загружаем вашу обученную модель со всеми встроенными функциями spaCy...")
    try:
        nlp = spacy.load(model_path)
    except Exception as e:
        print(f"Ошибка загрузки модели: {e}")
        return
        
    print("Готово. Попробуйте написать различные варианты запросов, например:")
    print(" - 'Алиса, включи сказку про серого волка'")
    print(" - 'давай аудиосказку красная шапочка'")
    print(" - 'включи пожалуйста колобок'")
    print(" - 'расскажи сказку'")
    print("Для выхода напишите 'exit'.\n")
    
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
            
        # 1. Прогоняем текст через модель (работает и textcat и стандартные синтаксические парсеры ru_core_news_md)
        doc = nlp(text)
        
        # 2. Определяем интент
        cats = doc.cats
        if cats:
            best_intent, best_score = max(cats.items(), key=lambda x: x[1])
        else:
            best_intent, best_score = "UNKNOWN", 0.0
            
        print(f"➜ Распознанный интент: {best_intent} (вероятность: {best_score:.2f})")
        
        # 3. Логика (Слот-филлинг)
        if best_intent == "FAIRYTALE" and best_score > 0.4:
            # Раз мы поняли что это сказка, пытаемся выдернуть её название!
            fairytale = extract_fairytale_name(doc)
            
            if fairytale:
                # Название найдено — можем искать в базе данных или API
                print(f"➜ ✅ Найдено название сказки (аргумент API): «{fairytale.capitalize()}»")
                # print(f"Выполняется запрос: DB.find(title='{fairytale}')")
            else:
                # Интент распознан, но название сказки нет.
                # В реальном проекте голосовой помощник здесь переспросит:
                print("➜ ❌ Название сказки не найдено. (Помощник: 'Отлично! А какую именно сказку вы хотите послушать?')")
        else:
            print(f"➜ (Это другой интент - модуль извлечения сказки пропускаем)")
        print("-" * 50)

if __name__ == "__main__":
    main()
