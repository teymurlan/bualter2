import google.generativeai as genai
import json
import os
from dotenv import load_dotenv

load_dotenv()
genai.configure(api_key=os.getenv("GEMINI_KEY"))

model = genai.GenerativeModel('gemini-1.5-flash')

async def parse_user_command(text: str):
    prompt = f"""
    Проанализируй команду для управления клинингом и верни ТОЛЬКО JSON.
    Текст: "{text}"
    Возможные действия: add_expense, add_income, pay_salary, set_status.
    Формат ответа: {{"action": "название", "amount": число, "name": "имя", "task_id": число, "category": "текст"}}
    Если данных нет, ставь null.
    """
    
    response = model.generate_content(prompt)
    try:
        # Очистка от лишних символов Markdown, если Gemini их добавит
        clean_json = response.text.replace('```json', '').replace('```', '').strip()
        return json.loads(clean_json)
    except:
        return {"action": "unknown", "text": text}
