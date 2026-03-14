import asyncio
import os
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.utils.keyboard import InlineKeyboardBuilder, ReplyKeyboardBuilder
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from dotenv import load_dotenv

import database as db
import ai_parser as ai

load_dotenv()

bot = Bot(token=os.getenv("TELEGRAM_BOT_TOKEN"))
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
        await message.answer(f"❌ ID {message.from_user.id} не в базе.")
        return
    await message.answer("Система готова.", reply_markup=main_menu(user['role']))

@dp.message(F.text == "📋 Мои заявки")
async def jobs_list(message: types.Message):
    user = await db.get_user(message.from_user.id)
    jobs = await db.get_active_jobs(user['id'])
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

@dp.message(F.text == "🎙 AI Команда")
async def ai_start(message: types.Message, state: FSMContext):
    await message.answer("Слушаю...")
    await state.set_state(Form.waiting_ai)

@dp.message(Form.waiting_ai)
async def ai_proc(message: types.Message, state: FSMContext):
    res = await ai.parse_command(message.text)
    user = await db.get_user(message.from_user.id)
    if res['type'] in ['income', 'expense']:
        await db.add_transaction(res['type'], res['amount'], res['category'], message.text, user['id'])
        await message.answer(f"✅ {res['type']} {res['amount']} ₽")
    else:
        await message.answer("Не понял.")
    await state.clear()

async def main():
    await db.init_db()
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
