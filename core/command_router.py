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
        # Сохраняем ссылки на загруженные модули — нужны для post-init
        # хука, который вызывается, когда ассистент полностью готов.
        self._loaded_modules = {}
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
                        self._loaded_modules[module_name] = module
                        # Ищем функцию setup и вызываем её, передавая роутер
                        if hasattr(module, 'setup') and callable(module.setup):
                            module.setup(self)
                        else:
                            print(f"⚠️ В модуле {module_name} нет функции setup(router).")
                    except Exception as e:
                        print(f"❌ Ошибка при загрузке навыка {module_name}: {e}")

    def notify_assistant_ready(self, assistant):
        """
        Уведомляет навыки, что ассистент полностью инициализирован.
        Если у навыка есть функция on_assistant_ready(assistant), она будет
        вызвана. Используется навыками, которым нужно восстановить состояние
        (напоминания, отложенные задачи и т. п.) после перезапуска программы.
        """
        for name, module in self._loaded_modules.items():
            if hasattr(module, "on_assistant_ready") and callable(module.on_assistant_ready):
                try:
                    module.on_assistant_ready(assistant)
                except Exception as e:
                    logger.warn(f"on_assistant_ready упал в навыке {name}: {e}")

    def route_command(self, parsed_data, assistant_instance):
        """
        Принимает разобранные данные от IntentParser и вызывает нужный модуль.
        """
        intent = parsed_data.get("intent")
        entities = parsed_data.get("entities", {})

        if intent in self.routes:
            handler = self.routes[intent]
            if os.environ.get("NLU_DEBUG"):
                logger.system("ROUTER", f"→ {handler.__module__}.{handler.__name__}()")
            handler(parsed_data, assistant_instance)
        else:
            logger.err(f"в реестре нет обработчика для интента «{intent}»")
            assistant_instance.speak("Я не совсем поняла эту команду.")