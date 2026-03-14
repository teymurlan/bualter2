import google.generativeai as genai
import os
import json
from dotenv import load_dotenv

load_dotenv()

api_key = os.getenv("GEMINI_API_KEY")
if api_key:
    genai.configure(api_key=api_key)

async def parse_command(text: str):
    if not api_key:
        return {"type": "unknown"}
    
    model = genai.GenerativeModel('gemini-1.5-flash')
    prompt = f"""Парси команду для ERP клининга: "{text}". 
    Верни JSON: 
    type: "income" | "expense" | "salary" | "unknown",
    amount: число, 
    category: строка.
    Отвечай ТОЛЬКО чистым JSON."""
    
    try:
        response = model.generate_content(prompt)
        res_text = response.text.replace("```json", "").replace("```", "").strip()
        return json.loads(res_text)
    except:
        return {"type": "unknown"}
