import re

async def transcribe_audio(file_path: str) -> str:
    """Заглушка для голосовых сообщений без OpenAI"""
    return "⚠️ Распознавание голоса отключено (требуется API-ключ OpenAI)."

async def parse_message(text: str) -> dict:
    """
    Локальный парсер текста без использования нейросетей.
    Ищет ключевые слова и цифры.
    """
    text_lower = text.lower()
    
    # Ищем первую попавшуюся цифру в тексте (это будет сумма)
    numbers = re.findall(r'\d+', text)
    amount = float(numbers[0]) if numbers else 0.0

    # 1. Проверка на запрос аналитики
    if any(word in text_lower for word in ["отчет", "статистика", "аналитика", "итоги", "сколько"]):
        return {"action_type": "analytics", "period": "day"}

    # 2. Проверка на финансы
    finance_map = {
        "доход": "income", "оплата": "income",
        "расход": "expense", "потратил": "expense", 
        "купил": "purchase", "закупка": "purchase", "химия": "purchase",
        "зарплата": "salary", "зп": "salary",
        "аванс": "advance"
    }
    
    for word, category in finance_map.items():
        if word in text_lower:
            return {
                "action_type": "finance",
                "category": category,
                "amount": amount,
                "employee_name": None, # Без ИИ сложно точно вытащить имя
                "comment": text
            }

    # 3. Проверка на создание заказа
    if any(word in text_lower for word in ["уборка", "заказ", "клининг", "адрес"]):
        # Убираем ключевые слова, чтобы оставить только адрес
        address = text_lower.replace("уборка", "").replace("заказ", "").replace(str(int(amount)), "").strip()
        return {
            "action_type": "order",
            "address": address.capitalize() if address else "Адрес из описания",
            "price": amount,
            "clean_type": "Стандарт",
            "employee_name": None
        }

    return {"action_type": "unknown"}
