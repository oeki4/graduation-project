import spacy

nlp = spacy.load("ru_core_news_md")

text = ("Включи музыку")
doc = nlp(text)

print("Verbs:", [token.lemma_ for token in doc if token.pos_ == "VERB"])

for entity in doc.ents:
    print(entity.text, entity.label_)
