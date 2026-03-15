from assistant import VoiceAssistant

def main():
    # Создаем ассистента и задаем ему имя
    jarvis = VoiceAssistant(name="джарвис")

    # Запускаем
    jarvis.start()

if __name__ == "__main__":
    main()