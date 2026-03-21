from spacy.matcher import Matcher

def setup(router):
    """
    Регистрация интента чтения сказки.
    """
    router.register_route("FAIRYTALE", _module_fairytale)

def _module_fairytale(parsed_data, assistant):
    doc = parsed_data.get("spacy_doc")
    
    payload = "неизвестно"
    
    if doc:
        matcher = Matcher(doc.vocab)
        # Паттерн: ищем слово "сказка" (или синонимы), за которым следует одно или несколько существительных, прилагательных или собственных имен (название сказки)
        pattern = [
            {"LEMMA": {"IN": ["сказка", "песня", "история"]}}, 
            {"POS": {"IN": ["NOUN", "PROPN", "ADJ"]}, "OP": "+"}
        ]
        
        # Альтернативный паттерн: глагол "включи" + сразу название (например, "включи колобок")
        pattern2 = [
            {"LEMMA": {"IN": ["включить", "рассказать", "почитать", "прочитать"]}},
            {"POS": {"IN": ["NOUN", "PROPN", "ADJ"]}, "OP": "+"}
        ]
        
        matcher.add("FAIRYTALE_NAME", [pattern, pattern2])
        matches = matcher(doc)
        
        if matches:
            # Берем самое длинное совпадение, если их несколько
            match_id, start, end = max(matches, key=lambda x: x[2] - x[1])
            # Название сказки идет сразу после триггерного слова (сказка / включить), то есть берем текст со start+1
            payload = doc[start+1:end].text
            
            # Очистка если захватили лишнее
            payload = payload.replace("пожалуйста", "").strip()

    print(f"📖 [МОДУЛЬ СКАЗОК] Пользователь попросил сказку. Название: '{payload}'")
    # Дополнительно выведем в консоль сырой текст для отладки
    print(f"   [ОРИГИНАЛ]: {parsed_data.get('original_text')}")
