import os
import json
from openai import AsyncOpenAI

client = AsyncOpenAI(api_key=os.getenv("OPENAI_API_KEY"))

async def transcribe_audio(file_path: str) -> str:
    """Transcribes voice messages using Whisper API."""
    with open(file_path, "rb") as audio_file:
        transcript = await client.audio.transcriptions.create(model="whisper-1", file=audio_file)
        return transcript.text

async def parse_message(text: str) -> dict:
    """
    Natural language parsing.
    Extracts: employee name, amount, operation type, date.
    Normalizes and formats the text.
    """
    prompt = f"""
    Analyze the following message for a cleaning company ERP system.
    Extract the data and return ONLY a valid JSON object. Normalize text, fix typos, and detect dates.
    
    Determine the action_type:
    1. "finance" - for income, expense, salary, advance, or purchase.
    2. "order" - for new cleaning orders.
    3. "analytics" - for requesting stats/reports.
    
    JSON Formats:
    - For "finance":
      {{"action_type": "finance", "category": "income"|"expense"|"salary"|"advance"|"purchase", "amount": float, "employee_name": "string or null", "date": "YYYY-MM-DD or null", "comment": "string"}}
    
    - For "order":
      {{"action_type": "order", "address": "string", "price": float, "clean_type": "string", "date": "YYYY-MM-DD or null", "employee_name": "string or null"}}
    
    - For "analytics":
      {{"action_type": "analytics", "period": "day"|"week"|"month"|"all"}}
    
    Message to parse: "{text}"
    """
    try:
        response = await client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.0
        )
        content = response.choices[0].message.content.strip()
        if content.startswith("```json"): content = content[7:-3]
        elif content.startswith("```"): content = content[3:-3]
        return json.loads(content)
    except Exception as e:
        return {"action_type": "error", "error": str(e)}
