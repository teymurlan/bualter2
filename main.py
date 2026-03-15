import logging
import os
from aiogram import Bot, Dispatcher, types
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton
from aiogram.utils import executor

from datetime import datetime
import sqlite3

# ✅ Получаем данные из переменных окружения (устанавливаются прямо в Railway или в терминале)
TOKEN = os.environ.get("BOT_TOKEN")  # обязательно установи в Railway
ADMIN_ID = int(os.environ.get("ADMIN_ID", 0))  # твой Telegram ID

if not TOKEN or ADMIN_ID == 0:
    raise Exception("Установи переменные окружения BOT_TOKEN и ADMIN_ID!")

logging.basicConfig(level=logging.INFO)

bot = Bot(token=TOKEN)
dp = Dispatcher(bot)

# ====== база данных SQLite (в памяти или файл, но без дополнительных файлов конфигов) ======
conn = sqlite3.connect("cleaning.db")
cursor = conn.cursor()

cursor.execute("""
CREATE TABLE IF NOT EXISTS employees(
id INTEGER PRIMARY KEY AUTOINCREMENT,
name TEXT,
telegram_id INTEGER,
salary_per_order INTEGER
)
""")

cursor.execute("""
CREATE TABLE IF NOT EXISTS orders(
id INTEGER PRIMARY KEY AUTOINCREMENT,
client TEXT,
address TEXT,
price INTEGER,
employee_id INTEGER,
date TEXT
)
""")

cursor.execute("""
CREATE TABLE IF NOT EXISTS expenses(
id INTEGER PRIMARY KEY AUTOINCREMENT,
name TEXT,
amount INTEGER,
date TEXT
)
""")
conn.commit()

# ====== клавиатура ======
menu = ReplyKeyboardMarkup(resize_keyboard=True)
menu.add(KeyboardButton("➕ сотрудник"), KeyboardButton("👥 сотрудники"))
menu.add(KeyboardButton("🧾 новая заявка"), KeyboardButton("💸 расход"))
menu.add(KeyboardButton("📊 отчет"))

# ====== состояние FSM ======
state = {}

# ====== вспомогательные функции ======
def add_employee(name, telegram_id, salary):
    cursor.execute(
        "INSERT INTO employees(name,telegram_id,salary_per_order) VALUES(?,?,?)",
        (name, telegram_id, salary)
    )
    conn.commit()

def get_employees():
    cursor.execute("SELECT * FROM employees")
    return cursor.fetchall()

def add_order(client,address,price,employee_id):
    date = datetime.now().strftime("%Y-%m-%d")
    cursor.execute(
        "INSERT INTO orders(client,address,price,employee_id,date) VALUES(?,?,?,?,?)",
        (client,address,price,employee_id,date)
    )
    conn.commit()

def add_expense(name,amount):
    date = datetime.now().strftime("%Y-%m-%d")
    cursor.execute(
        "INSERT INTO expenses(name,amount,date) VALUES(?,?,?)",
        (name,amount,date)
    )
    conn.commit()

def get_finance():
    cursor.execute("SELECT SUM(price) FROM orders")
    income = cursor.fetchone()[0] or 0
    cursor.execute("SELECT SUM(amount) FROM expenses")
    expense = cursor.fetchone()[0] or 0
    profit = income - expense
    return income, expense, profit

def parse_order(text):
    try:
        data = text.split("|")
        client = data[0].strip()
        address = data[1].strip()
        price = int(data[2].strip())
        employee_id = int(data[3].strip())
        return client,address,price,employee_id
    except:
        return None

# ====== хэндлеры ======
@dp.message_handler(commands=['start'])
async def start(message: types.Message):
    if message.from_user.id != ADMIN_ID:
        return
    await message.answer("Панель управления клинингом", reply_markup=menu)

@dp.message_handler(lambda m: m.text == "➕ сотрудник")
async def add_emp(message: types.Message):
    state[message.from_user.id] = "employee"
    await message.answer("Отправь:\nИмя | telegram_id | зарплата за заказ")

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
    await message.answer("Отправь:\nКлиент | Адрес | Цена | id сотрудника")

@dp.message_handler(lambda m: m.text == "💸 расход")
async def new_expense(message: types.Message):
    state[message.from_user.id] = "expense"
    await message.answer("Отправь:\nНазвание | сумма")

@dp.message_handler(lambda m: m.text == "📊 отчет")
async def report(message: types.Message):
    income,expense,profit = get_finance()
    text = f"Финансы\nДоход: {income}\nРасход: {expense}\nПрибыль: {profit}"
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

# ====== запуск ======
if __name__ == "__main__":
    executor.start_polling(dp, skip_updates=True)
