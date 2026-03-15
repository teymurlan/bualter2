import logging

from aiogram import Bot, Dispatcher, types
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton
from aiogram.utils import executor

from database import *
from ai_parser import parse_order

TOKEN = "YOUR_BOT_TOKEN"

ADMIN_ID = 123456789

logging.basicConfig(level=logging.INFO)

bot = Bot(token=TOKEN)
dp = Dispatcher(bot)

init_db()

menu = ReplyKeyboardMarkup(resize_keyboard=True)

menu.add(
KeyboardButton("➕ сотрудник"),
KeyboardButton("👥 сотрудники")
)

menu.add(
KeyboardButton("🧾 новая заявка"),
KeyboardButton("💸 расход")
)

menu.add(
KeyboardButton("📊 отчет")
)

state = {}

@dp.message_handler(commands=['start'])
async def start(message: types.Message):

    if message.from_user.id != ADMIN_ID:
        return

    await message.answer("Панель управления клинингом", reply_markup=menu)


@dp.message_handler(lambda m: m.text == "➕ сотрудник")
async def add_emp(message: types.Message):

    state[message.from_user.id] = "employee"

    await message.answer(
    "Отправь:\nИмя | telegram_id | зарплата за заказ"
    )


@dp.message_handler(lambda m: m.text == "👥 сотрудники")
async def list_emp(message: types.Message):

    employees = get_employees()

    if not employees:
        await message.answer("Сотрудников нет")
        return

    text = "Сотрудники:\n\n"

    for e in employees:

        text += f"id:{e[0]} | {e[1]} | {e[3]} за заказ\n"

    await message.answer(text)


@dp.message_handler(lambda m: m.text == "🧾 новая заявка")
async def new_order(message: types.Message):

    state[message.from_user.id] = "order"

    await message.answer(
    "Отправь:\nКлиент | Адрес | Цена | id сотрудника"
    )


@dp.message_handler(lambda m: m.text == "💸 расход")
async def new_expense(message: types.Message):

    state[message.from_user.id] = "expense"

    await message.answer(
    "Отправь:\nНазвание | сумма"
    )


@dp.message_handler(lambda m: m.text == "📊 отчет")
async def report(message: types.Message):

    income,expense,profit = get_finance()

    text = f"""
Финансы

Доход: {income}
Расход: {expense}
Прибыль: {profit}
"""

    await message.answer(text)


@dp.message_handler()
async def handle(message: types.Message):

    user_state = state.get(message.from_user.id)

    if user_state == "employee":

        try:

            data = message.text.split("|")

            name = data[0].strip()
            telegram_id = int(data[1].strip())
            salary = int(data[2].strip())

            add_employee(name,telegram_id,salary)

            await message.answer("Сотрудник добавлен")

        except:

            await message.answer("Ошибка формата")

        state[message.from_user.id] = None


    elif user_state == "order":

        order = parse_order(message.text)

        if not order:

            await message.answer("Ошибка формата")
            return

        client,address,price,employee_id = order

        add_order(client,address,price,employee_id)

        await message.answer("Заявка добавлена")

        state[message.from_user.id] = None


    elif user_state == "expense":

        try:

            data = message.text.split("|")

            name = data[0].strip()
            amount = int(data[1].strip())

            add_expense(name,amount)

            await message.answer("Расход добавлен")

        except:

            await message.answer("Ошибка формата")

        state[message.from_user.id] = None


if __name__ == "__main__":

    executor.start_polling(dp, skip_updates=True)
