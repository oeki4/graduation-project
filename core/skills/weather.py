from spacy.matcher import Matcher

def setup(router):
    """
    Регистрация интента прогноза погоды.
    """
    router.register_route("узнать_погоду", _module_weather)

def _module_weather(parsed_data, assistant):
    doc = parsed_data.get("spacy_doc")
    
    target_time = "сегодня"
    target_location = "текущем городе"
    
    if doc:
        matcher = Matcher(doc.vocab)
        
        # Паттерн для времени: ищем наречия времени (завтра, послезавтра, сегодня)
        time_pattern = [{"LEMMA": {"IN": ["завтра", "послезавтра", "сегодня", "сейчас", "вечером", "утром"]}}]
        matcher.add("TIME", [time_pattern])
        
        # Паттерн для локации: предлог ("в", "на") + сущ/собственное имя (например, "в Москве")
        loc_pattern = [{"POS": "ADP"}, {"POS": {"IN": ["NOUN", "PROPN"]}}]
        matcher.add("LOCATION", [loc_pattern])
        
        matches = matcher(doc)
        
        for match_id, start, end in matches:
            match_label = doc.vocab.strings[match_id]
            extracted_text = doc[start:end].text
            
            if match_label == "TIME":
                target_time = extracted_text
            elif match_label == "LOCATION":
                # Убираем предлог (start+1)
                target_location = doc[start+1:end].text

    print(f"🌤️ [МОДУЛЬ ПОГОДЫ] Запрос погоды.")
    print(f"   [ВРЕМЯ]: {target_time} | [МЕСТО]: {target_location}")
    print(f"   [ОРИГИНАЛ]: {parsed_data.get('original_text')}")
