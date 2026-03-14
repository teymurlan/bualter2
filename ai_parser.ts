import { GoogleGenAI } from "@google/genai";
import dotenv from 'dotenv';

dotenv.config();

const ai = new GoogleGenAI({ apiKey: process.env.GEMINI_API_KEY || '' });

/**
 * Мощная функция парсинга команд через Google Gemini
 * Распознает интенты: доходы, расходы, зарплаты, статусы
 */
export async function parseCommand(text: string) {
  try {
    const response = await ai.models.generateContent({
      model: "gemini-3-flash-preview",
      contents: `Ты — AI-ассистент ERP системы клининга. Проанализируй команду: "${text}".
      Верни JSON с полями:
      - action: "income" | "expense" | "salary" | "bonus" | "job_status" | "report" | "unknown"
      - amount: number (сумма денег)
      - category: string (на что потратили или за что получили)
      - target: string (имя сотрудника, если применимо)
      - job_id: number (ID заявки, если применимо)
      - value: string (дополнительная информация)
      
      Примеры:
      "Купил химию на 1500" -> {action: "expense", amount: 1500, category: "химия"}
      "Зарплата Ивану 2000" -> {action: "salary", amount: 2000, target: "Иван"}
      "Заверши заявку 10" -> {action: "job_status", job_id: 10, value: "completed"}
      
      Отвечай ТОЛЬКО чистым JSON.`,
      config: { responseMimeType: "application/json" }
    });

    return JSON.parse(response.text);
  } catch (error) {
    console.error("AI Parser Error:", error);
    return { action: "unknown" };
  }
}
