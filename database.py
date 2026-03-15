import sqlite3
from datetime import datetime

conn = sqlite3.connect("cleaning.db")
cursor = conn.cursor()

def init_db():

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


def get_orders():

    cursor.execute("SELECT * FROM orders")
    return cursor.fetchall()


def add_expense(name,amount):

    date = datetime.now().strftime("%Y-%m-%d")

    cursor.execute(
        "INSERT INTO expenses(name,amount,date) VALUES(?,?,?)",
        (name,amount,date)
    )

    conn.commit()


def get_expenses():

    cursor.execute("SELECT * FROM expenses")
    return cursor.fetchall()


def get_finance():

    cursor.execute("SELECT SUM(price) FROM orders")
    income = cursor.fetchone()[0] or 0

    cursor.execute("SELECT SUM(amount) FROM expenses")
    expense = cursor.fetchone()[0] or 0

    profit = income - expense

    return income, expense, profit
