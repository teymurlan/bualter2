import Database from 'better-sqlite3';
import { Employee, Job, Transaction, AuditLog } from './src/types';

const db = new Database('cleaning_erp.db');

/**
 * Инициализация всех таблиц SQL
 */
export function initDb() {
  db.exec(`
    CREATE TABLE IF NOT EXISTS employees (
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      telegram_id INTEGER UNIQUE,
      name TEXT NOT NULL,
      role TEXT DEFAULT 'worker',
      status TEXT DEFAULT 'active',
      created_at DATETIME DEFAULT CURRENT_TIMESTAMP
    );

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
    );

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
    );

    CREATE TABLE IF NOT EXISTS audit_logs (
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      employee_id INTEGER,
      action TEXT NOT NULL,
      details TEXT,
      created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
      FOREIGN KEY(employee_id) REFERENCES employees(id)
    );
  `);

  // Создание дефолтного админа
  const admin = db.prepare('SELECT * FROM employees WHERE role = "admin"').get();
  if (!admin) {
    db.prepare('INSERT INTO employees (name, telegram_id, role) VALUES (?, ?, ?)').run('Admin', 0, 'admin');
  }
}

/**
 * Функции для работы с сотрудниками
 */
export const employees = {
  getAll: () => db.prepare('SELECT * FROM employees').all() as Employee[],
  getByTgId: (tgId: number) => db.prepare('SELECT * FROM employees WHERE telegram_id = ?').get(tgId) as Employee,
  add: (name: string, tgId: number, role: string) => 
    db.prepare('INSERT INTO employees (name, telegram_id, role) VALUES (?, ?, ?)').run(name, tgId, role),
  updateStatus: (id: number, status: string) => 
    db.prepare('UPDATE employees SET status = ? WHERE id = ?').run(status, id)
};

/**
 * Функции для работы с заявками
 */
export const jobs = {
  getAll: () => db.prepare(`
    SELECT jobs.*, employees.name as worker_name 
    FROM jobs LEFT JOIN employees ON jobs.worker_id = employees.id
    ORDER BY scheduled_at DESC
  `).all() as Job[],
  getForWorker: (workerId: number) => 
    db.prepare('SELECT * FROM jobs WHERE worker_id = ? AND status != "completed"').all(workerId) as Job[],
  add: (address: string, date: string, workerId: number, price: number) =>
    db.prepare('INSERT INTO jobs (address, scheduled_at, worker_id, price) VALUES (?, ?, ?, ?)').run(address, date, workerId, price),
  updateStatus: (id: number, status: string, timeField?: string) => {
    const query = timeField 
      ? `UPDATE jobs SET status = ?, ${timeField} = CURRENT_TIMESTAMP WHERE id = ?`
      : `UPDATE jobs SET status = ? WHERE id = ?`;
    return db.prepare(query).run(status, id);
  }
};

/**
 * Функции для работы с финансами
 */
export const finance = {
  getStats: () => ({
    income: (db.prepare('SELECT SUM(amount) as s FROM transactions WHERE type="income"').get() as any).s || 0,
    expense: (db.prepare('SELECT SUM(amount) as s FROM transactions WHERE type="expense"').get() as any).s || 0,
    activeJobs: (db.prepare('SELECT COUNT(*) as c FROM jobs WHERE status != "completed"').get() as any).c,
    employees: (db.prepare('SELECT COUNT(*) as c FROM employees').get() as any).c
  }),
  getTransactions: () => db.prepare('SELECT * FROM transactions ORDER BY created_at DESC').all() as Transaction[],
  addTransaction: (type: string, amount: number, category: string, desc: string, empId?: number) =>
    db.prepare('INSERT INTO transactions (type, amount, category, description, employee_id) VALUES (?, ?, ?, ?, ?)')
      .run(type, amount, category, desc, empId)
};

/**
 * Логирование действий
 */
export function logAction(empId: number, action: string, details: string) {
  db.prepare('INSERT INTO audit_logs (employee_id, action, details) VALUES (?, ?, ?)').run(empId, action, details);
}
