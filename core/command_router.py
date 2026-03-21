import os
import importlib.util

class CommandRouter:
    def __init__(self):
        """
        Роутер команд с динамической загрузкой навыков (плагинов).
        """
        self.routes = {}
        self.load_skills()
        
    def register_route(self, intent, handler):
        """Регистрирует новый обработчик для переданного интента."""
        self.routes[intent] = handler
        print(f"🔌 Успешно зарегистрирован интент: {intent}")

    def load_skills(self, skills_dir="skills"):
        """
        Динамически загружает все файлы навыков из папки skills.
        """
        # Определяем абсолютный путь к папке skills относительно этого файла
        base_dir = os.path.dirname(os.path.abspath(__file__))
        skills_path = os.path.join(base_dir, skills_dir)
        
        if not os.path.exists(skills_path):
            print(f"⚠️ Папка с навыками {skills_path} не найдена.")
            return

        print("🔄 Загрузка навыков (плагинов)...")
        for filename in os.listdir(skills_path):
            if filename.endswith(".py") and not filename.startswith("__"):
                module_name = filename[:-3]
                file_path = os.path.join(skills_path, filename)
                
                # Динамический импорт модуля
                spec = importlib.util.spec_from_file_location(module_name, file_path)
                if spec and spec.loader:
                    module = importlib.util.module_from_spec(spec)
                    try:
                        spec.loader.exec_module(module)
                        # Ищем функцию setup и вызываем её, передавая роутер
                        if hasattr(module, 'setup') and callable(module.setup):
                            module.setup(self)
                        else:
                            print(f"⚠️ В модуле {module_name} нет функции setup(router).")
                    except Exception as e:
                        print(f"❌ Ошибка при загрузке навыка {module_name}: {e}")

    def route_command(self, parsed_data, assistant_instance):
        """
        Принимает разобранные данные от IntentParser и вызывает нужный модуль.
        """
        intent = parsed_data.get("intent")
        entities = parsed_data.get("entities", {})

        print(f"🔀 [ROUTER] Маршрутизация интента: {intent} | Параметры: {entities}")

        if intent in self.routes:
            # Вызываем привязанную функцию и передаем ей все разобранные данные
            handler = self.routes[intent]
            handler(parsed_data, assistant_instance)
        else:
            print("🤖 Ассистент: Я не совсем понял эту команду или соответствующий модуль не подключен.")