import google.generativeai as genai
import os
import json
from dotenv import load_dotenv

load_dotenv()

genai.configure(api_key=os.getenv("GEMINI_API_KEY"))

async def parse_command(text: str):
    model = genai.GenerativeModel('gemini-1.5-flash')
    prompt = f"""Парси команду клининговой ERP: "{text}". 
    Верни JSON: type ("income", "expense", "salary", "unknown"), amount (число), category (строка).
    Отвечай ТОЛЬКО чистым JSON без кавычек в начале."""
    
    try:
        response = model.generate_content(prompt)
        res_text = response.text.replace("```json", "").replace("```", "").strip()
        return json.loads(res_text)
    except:
        return {"type": "unknown"}
