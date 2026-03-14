import aiosqlite
import asyncio

DB_PATH = "cleaning_erp.db"

async def init_db():
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("""
            CREATE TABLE IF NOT EXISTS employees (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                telegram_id INTEGER UNIQUE,
                name TEXT NOT NULL,
                role TEXT DEFAULT 'worker',
                status TEXT DEFAULT 'active',
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        """)
        await db.execute("""
            CREATE TABLE IF NOT EXISTS jobs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                address TEXT NOT NULL,
                scheduled_at DATETIME NOT NULL,
                status TEXT DEFAULT 'pending',
                worker_id INTEGER,
                price REAL DEFAULT 0,
                cost REAL DEFAULT 0,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                started_at DATETIME,
                finished_at DATETIME,
                FOREIGN KEY(worker_id) REFERENCES employees(id)
            )
        """)
        await db.execute("""
            CREATE TABLE IF NOT EXISTS transactions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                type TEXT NOT NULL,
                amount REAL NOT NULL,
                category TEXT,
                description TEXT,
                employee_id INTEGER,
                job_id INTEGER,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY(employee_id) REFERENCES employees(id),
                FOREIGN KEY(job_id) REFERENCES jobs(id)
            )
        """)
        await db.commit()

async def get_user(tg_id: int):
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("SELECT * FROM employees WHERE telegram_id = ?", (tg_id,)) as cursor:
            return await cursor.fetchone()

async def get_employee_count():
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute("SELECT COUNT(*) FROM employees") as cursor:
            res = await cursor.fetchone()
            return res[0]

async def add_employee(name: str, tg_id: int, role: str):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("INSERT INTO employees (name, telegram_id, role) VALUES (?, ?, ?)", (name, tg_id, role))
        await db.commit()

async def get_active_jobs(worker_id: int):
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("SELECT * FROM jobs WHERE worker_id = ? AND status != 'completed'", (worker_id,)) as cursor:
            return await cursor.fetchall()

async def update_job_status(job_id: int, status: str, time_field: str = None):
    async with aiosqlite.connect(DB_PATH) as db:
        if time_field:
            await db.execute(f"UPDATE jobs SET status = ?, {time_field} = CURRENT_TIMESTAMP WHERE id = ?", (status, job_id))
        else:
            await db.execute("UPDATE jobs SET status = ? WHERE id = ?", (status, job_id))
        await db.commit()

async def add_transaction(t_type: str, amount: float, category: str, desc: str, emp_id: int = None):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("INSERT INTO transactions (type, amount, category, description, employee_id) VALUES (?, ?, ?, ?, ?)",
                         (t_type, amount, category, desc, emp_id))
        await db.commit()

async def get_stats():
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        income = await (await db.execute("SELECT SUM(amount) as s FROM transactions WHERE type='income'")).fetchone()
        expense = await (await db.execute("SELECT SUM(amount) as s FROM transactions WHERE type='expense'")).fetchone()
        return {"income": income['s'] or 0, "expense": expense['s'] or 0}
