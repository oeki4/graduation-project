from assistant import VoiceAssistant

def main():
    # Создаем ассистента и задаем ему имя
    assistant = VoiceAssistant(name="ассистент")

    # Запускаем
    assistant.start()

if __name__ == "__main__":
    main()