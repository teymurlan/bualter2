import sqlite3
from datetime import datetime

DB_NAME = "cleaning_bot.db"

def init_db():
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    
    cursor.execute('''CREATE TABLE IF NOT EXISTS employees (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT,
        role TEXT,
        salary REAL DEFAULT 0
    )''')
    
    cursor.execute('''CREATE TABLE IF NOT EXISTS tasks (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        employee_id INTEGER,
        address TEXT,
        task_type TEXT,
        status TEXT DEFAULT 'pending',
        start_time TEXT,
        end_time TEXT,
        geo TEXT,
        FOREIGN KEY(employee_id) REFERENCES employees(id)
    )''')
    
    cursor.execute('''CREATE TABLE IF NOT EXISTS finances (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        type TEXT,
        amount REAL,
        description TEXT,
        date TEXT
    )''')
    
    conn.commit()
    conn.close()

def add_employee(name, role):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("INSERT INTO employees (name, role) VALUES (?, ?)", (name, role))
    conn.commit()
    conn.close()

def get_employees():
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM employees")
    data = cursor.fetchall()
    conn.close()
    return data

def add_task(employee_id, address, task_type):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("INSERT INTO tasks (employee_id, address, task_type) VALUES (?, ?, ?)", (employee_id, address, task_type))
    conn.commit()
    conn.close()

def update_task_status(task_id, status, geo=None):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    time_field = "start_time" if status=="in_progress" else "end_time"
    cursor.execute(f"UPDATE tasks SET status=?, {time_field}=?, geo=? WHERE id=?", (status, datetime.now(), geo, task_id))
    conn.commit()
    conn.close()
