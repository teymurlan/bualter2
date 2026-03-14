import asyncio
import os
import sys
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.utils.keyboard import InlineKeyboardBuilder, ReplyKeyboardBuilder
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from dotenv import load_dotenv

load_dotenv()

import database as db
import ai_parser as ai

token = os.getenv("TELEGRAM_BOT_TOKEN")
if not token:
    print("Error: TELEGRAM_BOT_TOKEN not found")
    sys.exit(1)

bot = Bot(token=token)
dp = Dispatcher()

class Form(StatesGroup):
    waiting_ai = State()

def main_menu(role: str):
    kb = ReplyKeyboardBuilder()
    if role == 'worker':
        kb.row(types.KeyboardButton(text="📋 Мои заявки"))
    else:
        kb.row(types.KeyboardButton(text="📊 Отчет"), types.KeyboardButton(text="🎙 AI Команда"))
    return kb.as_markup(resize_keyboard=True)

@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    user = await db.get_user(message.from_user.id)
    
    if not user:
        count = await db.get_employee_count()
        if count == 0:
            await db.add_employee(message.from_user.full_name, message.from_user.id, "admin")
            user = await db.get_user(message.from_user.id)
            await message.answer("🌟 Вы зарегистрированы как первый Администратор!")
        else:
            await message.answer(f"❌ Доступ запрещен. Ваш ID: {message.from_user.id}")
            return
            
    await message.answer(f"✅ ERP Система готова. Роль: {user['role']}", reply_markup=main_menu(user['role']))

@dp.message(F.text == "📋 Мои заявки")
async def jobs_list(message: types.Message):
    user = await db.get_user(message.from_user.id)
    jobs = await db.get_active_jobs(user['id'])
    if not jobs:
        await message.answer("Нет назначенных заявок.")
        return
    for j in jobs:
        b = InlineKeyboardBuilder()
        b.button(text="🚀 Начать", callback_data=f"j:s:{j['id']}")
        b.button(text="✅ Готово", callback_data=f"j:f:{j['id']}")
        await message.answer(f"📍 {j['address']}", reply_markup=b.as_markup())

@dp.callback_query(F.data.startswith("j:"))
async def call_job(call: types.CallbackQuery):
    _, act, j_id = call.data.split(":")
    if act == "s":
        await db.update_job_status(int(j_id), "in_progress", "started_at")
        await call.answer("Начато")
    else:
        await db.update_job_status(int(j_id), "completed", "finished_at")
        await call.answer("Завершено")

@dp.message(F.text == "📊 Отчет")
async def show_report(message: types.Message):
    stats = await db.get_stats()
    await message.answer(f"📈 *Отчет*\n💰 Доход: {stats['income']} ₽\n📉 Расход: {stats['expense']} ₽", parse_mode="Markdown")

@dp.message(F.text == "🎙 AI Команда")
async def ai_start(message: types.Message, state: FSMContext):
    await message.answer("Введите команду...")
    await state.set_state(Form.waiting_ai)

@dp.message(Form.waiting_ai)
async def ai_proc(message: types.Message, state: FSMContext):
    res = await ai.parse_command(message.text)
    user = await db.get_user(message.from_user.id)
    if res['type'] in ['income', 'expense']:
        await db.add_transaction(res['type'], res['amount'], res['category'], message.text, user['id'])
        await message.answer(f"✅ Записано: {res['type']} {res['amount']} ₽")
    else:
        await message.answer("🤖 Не удалось распознать команду.")
    await state.clear()

async def main():
    await db.init_db()
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
