import aiosqlite
from datetime import datetime

class Database:
    def __init__(self, db_path="cleaning_erp.db"):
        self.db_path = db_path

    async def init(self):
        async with aiosqlite.connect(self.db_path) as db:
            # Юзеры и роли
            await db.execute('''CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY, role TEXT, name TEXT, balance REAL DEFAULT 0)''')
            # Заявки
            await db.execute('''CREATE TABLE IF NOT EXISTS tasks (
                id INTEGER PRIMARY KEY AUTOINCREMENT, address TEXT, 
                time TEXT, status TEXT, worker_id INTEGER, price REAL)''')
            # Финансы
            await db.execute('''CREATE TABLE IF NOT EXISTS transactions (
                id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER, 
                type TEXT, amount REAL, category TEXT, date TIMESTAMP)''')
            await db.commit()

    async def add_task(self, address, time, price):
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("INSERT INTO tasks (address, time, status, price) VALUES (?, ?, ?, ?)",
                             (address, time, 'new', price))
            await db.commit()

    async def get_tasks(self, worker_id=None):
        async with aiosqlite.connect(self.db_path) as db:
            if worker_id:
                cursor = await db.execute("SELECT * FROM tasks WHERE worker_id = ?", (worker_id,))
            else:
                cursor = await db.execute("SELECT * FROM tasks")
            return await cursor.fetchall()

    async def add_transaction(self, user_id, t_type, amount, category):
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("INSERT INTO transactions (user_id, type, amount, category, date) VALUES (?, ?, ?, ?, ?)",
                             (user_id, t_type, amount, category, datetime.now()))
            if t_type == 'salary':
                await db.execute("UPDATE users SET balance = balance + ? WHERE id = ?", (amount, user_id))
            await db.commit()
