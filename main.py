import asyncio
import os
from aiogram import Bot, Dispatcher, F, types
from aiogram.filters import Command
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.utils.keyboard import InlineKeyboardBuilder
from dotenv import load_dotenv

from database import Database
from ai_parser import parse_user_command

load_dotenv()
bot = Bot(token=os.getenv("BOT_TOKEN"))
dp = Dispatcher(storage=MemoryStorage())
db = Database()

# --- КЛАВИАТУРЫ ---
def get_main_menu(role):
    builder = InlineKeyboardBuilder()
    if role == 'admin':
        builder.button(text="➕ Создать задачу", callback_data="create_task")
        builder.button(text="💰 Отчет по деньгам", callback_data="fin_report")
    else:
        builder.button(text="📋 Мои задачи", callback_data="my_tasks")
    builder.adjust(1)
    return builder.as_markup()

# --- ХЭНДЛЕРЫ ---
@dp.message(Command("start"))
async def start(message: types.Message):
    # В реальности тут проверка роли из БД
    await message.answer(f"Привет, {message.from_user.full_name}! Я твой ERP-помощник.", 
                         reply_markup=get_main_menu('admin'))

@dp.message(F.text)
async def handle_ai_commands(message: types.Message):
    """Обработка текстовых команд через AI"""
    if message.text.startswith('/'): return
    
    data = await parse_user_command(message.text)
    
    if data['action'] == 'add_expense':
        await db.add_transaction(message.from_user.id, 'expense', data['amount'], data['category'])
        await message.answer(f"✅ Записал расход: {data['amount']} руб. на {data['category']}")
    elif data['action'] == 'pay_salary':
        await message.answer(f"💸 Начисляю зарплату {data['name']}: {data['amount']} руб.")
    else:
        await message.answer("🤖 Я получил команду, но не уверен, что делать. Уточни запрос.")

@dp.callback_query(F.data == "my_tasks")
async def show_tasks(callback: types.CallbackQuery):
    tasks = await db.get_tasks()
    res = "📅 Актуальные задачи:\n"
    for t in tasks:
        res += f"📍 {t[1]} | ⏰ {t[2]} | Статус: {t[3]}\n"
    await callback.message.answer(res)

# --- ЗАПУСК ---
async def main():
    await db.init()
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
