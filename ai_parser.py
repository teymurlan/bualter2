import os
import json
from google import genai
from google.genai import types

client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))

async def transcribe_audio(file_path: str) -> str:
    """Транскрибация голосовых сообщений с помощью Gemini 2.5 Flash."""
    try:
        with open(file_path, "rb") as audio_file:
            audio_data = audio_file.read()
            
        response = await client.aio.models.generate_content(
            model='gemini-2.5-flash',
            contents=[
                types.Part.from_bytes(data=audio_data, mime_type='audio/ogg'),
                "Транскрибируй это голосовое сообщение на русском языке. Верни ТОЛЬКО распознанный текст, без приветствий и комментариев."
            ]
        )
        return response.text.strip()
    except Exception as e:
        return f"Ошибка распознавания голоса: {str(e)}"

async def parse_message(text: str) -> dict:
    """
    Парсинг естественного языка с помощью Gemini.
    Строго возвращает JSON.
    """
    prompt = f"""
    Ты — AI-ассистент ERP-системы клининговой компании.
    Твоя задача — извлечь данные из текста и вернуть ИХ СТРОГО В ФОРМАТЕ JSON. Никакого текста до или после JSON.
    
    Определи action_type:
    1. "finance" - доходы, расходы, зарплаты, авансы, закупки.
    2. "order" - новые заказы на уборку.
    3. "analytics" - запросы статистики/отчетов.
    
    Форматы JSON:
    - Для "finance":
      {{"action_type": "finance", "category": "income"|"expense"|"salary"|"advance"|"purchase", "amount": float, "employee_name": "string или null", "date": "YYYY-MM-DD или null", "comment": "string"}}
    
    - Для "order":
      {{"action_type": "order", "address": "string", "price": float, "clean_type": "string", "date": "YYYY-MM-DD или null", "employee_name": "string или null"}}
    
    - Для "analytics":
      {{"action_type": "analytics", "period": "day"|"week"|"month"|"all"}}
    
    Сообщение пользователя: "{text}"
    """
    try:
        response = await client.aio.models.generate_content(
            model='gemini-2.5-flash',
            contents=prompt,
            config=types.GenerateContentConfig(
                response_mime_type="application/json",
                temperature=0.0
            )
        )
        # Очистка на случай, если Gemini вернет markdown блоки
        content = response.text.strip()
        if content.startswith("```json"): content = content[7:-3]
        elif content.startswith("```"): content = content[3:-3]
        
        return json.loads(content)
    except Exception as e:
        return {"action_type": "error", "error": str(e)}
