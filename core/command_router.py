import os
import sys
import importlib.util

sys.path.append(os.path.dirname(os.path.abspath(__file__)))
import logger

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
        handler_name = getattr(handler, "__module__", "?") + "." + getattr(handler, "__name__", "?")
        logger.system("ROUTER", f"зарегистрирован интент {logger.C.BOLD}{intent}{logger.C.RESET} → {handler_name}")

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

        logger.system("ROUTER", f"загрузка плагинов из {skills_dir}/")
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

        if intent in self.routes:
            handler = self.routes[intent]
            logger.system("ROUTER", f"вызов {handler.__module__}.{handler.__name__}()")
            handler(parsed_data, assistant_instance)
        else:
            logger.err(f"в реестре нет обработчика для интента «{intent}»")
            assistant_instance.speak("Я не совсем поняла эту команду.")