import express from 'express';
import { createServer as createViteServer } from 'vite';
import { Telegraf, Markup, Context } from 'telegraf';
import path from 'path';
import dotenv from 'dotenv';
import * as db from './database';
import * as ai from './ai_parser';

dotenv.config();

// --- Инициализация ---
db.initDb();
const bot = new Telegraf(process.env.TELEGRAM_BOT_TOKEN || '');

// --- FSM & Состояния (Простая реализация через Map) ---
const userState = new Map<number, { step: string, data: any }>();

// --- Меню и Клавиатуры ---
const getMainMenu = (role: string) => {
  if (role === 'worker') {
    return Markup.keyboard([
      ['📋 Мои заявки', '💰 Моя зарплата'],
      ['📍 Отправить гео', '⚙️ Настройки']
    ]).resize();
  }
  return Markup.keyboard([
    ['📊 Отчет', '👥 Команда'],
    ['➕ Заявка', '🎙 AI Команда'],
    ['💸 Финансы', '📜 Логи']
  ]).resize();
};

const jobControlButtons = (jobId: number) => Markup.inlineKeyboard([
  [Markup.button.callback('🚀 Начать', `job:start:${jobId}`)],
  [Markup.button.callback('✅ Завершить', `job:finish:${jobId}`)]
]);

// --- Хэндлеры Бота ---

bot.start(async (ctx) => {
  const user = db.employees.getByTgId(ctx.from.id);
  if (!user) return ctx.reply('❌ Вы не зарегистрированы. Обратитесь к админу.');
  ctx.reply(`👋 Привет, ${user.name}! Вы вошли как ${user.role}.`, getMainMenu(user.role));
});

bot.hears('📋 Мои заявки', async (ctx) => {
  const user = db.employees.getByTgId(ctx.from.id);
  const activeJobs = db.jobs.getForWorker(user.id);
  
  if (activeJobs.length === 0) return ctx.reply('📭 У вас нет активных заявок.');
  
  for (const job of activeJobs) {
    ctx.reply(
      `📍 Адрес: ${job.address}\n🕒 Время: ${job.scheduled_at}\nСтатус: ${job.status}`,
      jobControlButtons(job.id)
    );
  }
});

bot.hears('📊 Отчет', async (ctx) => {
  const stats = db.finance.getStats();
  ctx.reply(
    `📈 *Отчет ERP*\n\n` +
    `💰 Доход: ${stats.income} ₽\n` +
    `📉 Расход: ${stats.expense} ₽\n` +
    `🧼 Заявок в работе: ${stats.activeJobs}\n` +
    `👥 Сотрудников: ${stats.employees}`,
    { parse_mode: 'Markdown' }
  );
});

// Обработка колбэков (Фабрика)
bot.on('callback_query', async (ctx) => {
  const data = (ctx.callbackQuery as any).data as string;
  const [action, subAction, id] = data.split(':');
  const jobId = parseInt(id);

  if (action === 'job') {
    if (subAction === 'start') {
      db.jobs.updateStatus(jobId, 'in_progress', 'started_at');
      ctx.answerCbQuery('Работа начата!');
      ctx.editMessageText(ctx.callbackQuery.message?.text + '\n\n✅ Статус: В процессе');
    } else if (subAction === 'finish') {
      db.jobs.updateStatus(jobId, 'completed', 'finished_at');
      ctx.answerCbQuery('Работа завершена!');
      ctx.editMessageText(ctx.callbackQuery.message?.text + '\n\n🏁 Статус: Завершено');
    }
  }
});

// AI Парсинг команд
bot.on('text', async (ctx) => {
  const user = db.employees.getByTgId(ctx.from.id);
  if (!user || user.role === 'worker') return;

  const text = ctx.message.text;
  if (text.length > 10) {
    const res = await ai.parseCommand(text);
    
    if (res.action === 'expense') {
      db.finance.addTransaction('expense', res.amount, res.category, text, user.id);
      ctx.reply(`✅ Расход учтен: ${res.amount} ₽ (${res.category})`);
    } else if (res.action === 'income') {
      db.finance.addTransaction('income', res.amount, 'Cleaning', text, user.id);
      ctx.reply(`✅ Доход учтен: ${res.amount} ₽`);
    } else if (res.action === 'job_status') {
      db.jobs.updateStatus(res.job_id, res.value);
      ctx.reply(`✅ Статус заявки #${res.job_id} изменен на ${res.value}`);
    } else {
      ctx.reply('🤖 Команда не распознана AI. Попробуйте: "Расход 500 на химию"');
    }
  }
});

bot.launch().then(() => console.log('🚀 Bot is running'));

// --- Express Server (API для Dashboard) ---
async function startServer() {
  const app = express();
  app.use(express.json());

  app.get('/api/stats', (req, res) => res.json(db.finance.getStats()));
  app.get('/api/employees', (req, res) => res.json(db.employees.getAll()));
  app.post('/api/employees', (req, res) => {
    db.employees.add(req.body.name, req.body.telegram_id, req.body.role);
    res.json({ success: true });
  });
  app.get('/api/jobs', (req, res) => res.json(db.jobs.getAll()));
  app.post('/api/jobs', (req, res) => {
    db.jobs.add(req.body.address, req.body.scheduled_at, req.body.worker_id, req.body.price);
    res.json({ success: true });
  });
  app.get('/api/transactions', (req, res) => res.json(db.finance.getTransactions()));

  if (process.env.NODE_ENV !== 'production') {
    const vite = await createViteServer({ server: { middlewareMode: true }, appType: 'spa' });
    app.use(vite.middlewares);
  } else {
    const distPath = path.join(process.cwd(), 'dist');
    app.use(express.static(distPath));
    app.get('*', (req, res) => res.sendFile(path.join(distPath, 'index.html')));
  }

  app.listen(3000, '0.0.0.0', () => console.log('🌐 Server on http://localhost:3000'));
}

startServer();
