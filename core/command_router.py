class CommandRouter:
    def __init__(self):
        """
        Регистрируем маршруты: связываем имена интентов с конкретными функциями-обработчими.
        """
        self.routes = {
            "SYSTEM_STOP": self._module_system_stop,
            "SMART_HOME_LIGHT": self._module_smart_home_light,
            "SET_TIMER": self._module_timer
        }

    def route_command(self, parsed_data, assistant_instance):
        """
        Принимает разобранные данные от IntentParser и вызывает нужный модуль.
        assistant_instance передается, чтобы модули могли управлять самим ассистентом (например, выключить его).
        """
        intent = parsed_data.get("intent")
        entities = parsed_data.get("entities", {})

        print(f"🔀 [ROUTER] Маршрутизация интента: {intent} | Параметры: {entities}")

        if intent in self.routes:
            # Вызываем привязанную функцию и передаем ей параметры
            handler = self.routes[intent]
            handler(entities, assistant_instance)
        else:
            print("🤖 Ассистент: Я не совсем понял эту команду или соответствующий модуль не подключен.")

    # ==========================================
    # Ниже идут заглушки для ваших конкретных модулей
    # В идеале эти функции будут импортироваться из других файлов (например, из modules/smart_home.py)
    # ==========================================

    def _module_system_stop(self, entities, assistant):
        print("🤖 Ассистент: Инициирую протокол завершения работы.")
        assistant.stop()

    def _module_smart_home_light(self, entities, assistant):
        room = entities.get("ROOM", "основной комнате")
        action = entities.get("ACTION", "переключить")
        print(f"🔌 [МОДУЛЬ УМНОГО ДОМА] Пытаюсь {action} свет в локации: {room}")
        # Здесь будет реальный вызов API умного дома

    def _module_timer(self, entities, assistant):
        duration = entities.get("TIME", "5 минут")
        print(f"⏱️ [МОДУЛЬ ТАЙМЕРА] Устанавливаю таймер на {duration}.")