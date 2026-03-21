def setup(router):
    """
    Регистрация неизвестного интента 'Other'.
    """
    router.register_route("OTHER", _module_other)

def _module_other(parsed_data, assistant):
    print("🤷 [ПРОЧИЙ МОДУЛЬ] Нераспознанный запрос или общий разговор.")
    # Для OTHER нам пока не нужна хитрая полезная нагрузка, просто печатаем оригинал
    print(f"   [ТЕКСТ]: {parsed_data.get('original_text')}")
