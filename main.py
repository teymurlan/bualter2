import os
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, CallbackQueryHandler, ContextTypes, MessageHandler, filters
from database import init_db, add_employee, get_employees, add_task, update_task_status
from ai_parser import parse_command

TOKEN = os.getenv("TELEGRAM_TOKEN")

init_db()

# Команды бота
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    await update.message.reply_text(f"Привет, {user.first_name}! Выберите роль:", reply_markup=InlineKeyboardMarkup([
        [InlineKeyboardButton("Сотрудник", callback_data="role_employee")],
        [InlineKeyboardButton("Менеджер", callback_data="role_manager")]
    ]))

async def button(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    if query.data == "role_employee":
        await query.edit_message_text("Вы вошли как сотрудник. Используйте /tasks для просмотра заявок.")
    elif query.data == "role_manager":
        await query.edit_message_text("Вы вошли как менеджер. Используйте /employees для управления сотрудниками.")

async def employees(update: Update, context: ContextTypes.DEFAULT_TYPE):
    data = get_employees()
    msg = "\n".join([f"{e[0]}: {e[1]} ({e[2]})" for e in data]) or "Сотрудников нет"
    await update.message.reply_text(msg)

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    command = parse_command(update.message.text)
    if command["action"] == "add_expense":
        await update.message.reply_text(f"Добавлен расход: {command['amount']}")
    elif command["action"] == "pay_salary":
        await update.message.reply_text(f"Выплачена зарплата: {command['amount']}")
    elif command["action"] == "start_task":
        await update.message.reply_text("Заявка начата")
    elif command["action"] == "complete_task":
        await update.message.reply_text("Заявка завершена")
    else:
        await update.message.reply_text("Неизвестная команда")

app = ApplicationBuilder().token(TOKEN).build()
app.add_handler(CommandHandler("start", start))
app.add_handler(CommandHandler("employees", employees))
app.add_handler(CallbackQueryHandler(button))
app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

app.run_polling()
