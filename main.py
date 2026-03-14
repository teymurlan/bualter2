import os
import asyncio
import logging
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.filters.callback_data import CallbackData
from aiogram.client.default import DefaultBotProperties  # <-- ДОБАВЛЕН НОВЫЙ ИМПОРТ
from apscheduler.schedulers.asyncio import AsyncIOScheduler

import database as db
from ai_parser import parse_message, transcribe_audio

logging.basicConfig(level=logging.INFO)

# --- ИЗМЕНЕНА ИНИЦИАЛИЗАЦИЯ БОТА ---
bot = Bot(
    token=os.getenv("BOT_TOKEN", "YOUR_TOKEN"),
    default=DefaultBotProperties(parse_mode="HTML")
)
dp = Dispatcher()
scheduler = AsyncIOScheduler()

# ... дальше идет остальной код без изменений ...

# --- ПРОФЕССИОНАЛЬНЫЕ КНОПКИ (CallbackData) ---
class MenuCB(CallbackData, prefix="menu"):
    action: str

class OrderCB(CallbackData, prefix="order"):
    action: str
    order_id: int

# --- СОСТОЯНИЯ (FSM) ---
class AIConfirmState(StatesGroup):
    waiting_for_confirmation = State()

# --- ПРОВЕРКА ДОСТУПА ---
async def check_access(message: types.Message):
    user = await db.get_user(message.from_user.id)
    if not user:
        admin = await db.create_admin(message.from_user.id)
        if admin:
            await message.answer("👑 <b>Вы зарегистрированы как Главный Руководитель.</b>")
            return admin
    return user

# --- ГЛАВНОЕ МЕНЮ (ГЕНЕРАТОР) ---
def get_main_menu_kb(role: db.Role):
    if role == db.Role.ADMIN:
        return InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🧹 Активные заказы", callback_data=MenuCB(action="orders").pack())],
            [InlineKeyboardButton(text="👥 Сотрудники", callback_data=MenuCB(action="employees").pack()),
             InlineKeyboardButton(text="💰 Финансы", callback_data=MenuCB(action="finance").pack())],
            [InlineKeyboardButton(text="📊 Отчёт за день", callback_data=MenuCB(action="reports").pack())],
            [InlineKeyboardButton(text="🔗 Сгенерировать инвайт", callback_data=MenuCB(action="invite").pack())]
        ])
    else:
        return InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="💼 Мои заказы", callback_data=MenuCB(action="my_orders").pack())],
            [InlineKeyboardButton(text="💳 Мой баланс", callback_data=MenuCB(action="my_balance").pack())]
        ])

async def send_main_menu(message_or_call, user: db.User, edit=False):
    text = (
        f"🏢 <b>Панель управления</b>\n"
        f"👤 Роль: <b>{'Руководитель' if user.role == db.Role.ADMIN else 'Сотрудник'}</b>\n"
        f"➖➖➖➖➖➖➖➖➖➖\n"
    )
    if user.role == db.Role.ADMIN:
        text += "<i>💡 Отправьте мне текст или голосовое сообщение с задачей, и я автоматически внесу её в базу!</i>"
    else:
        text += "<i>💡 Здесь вы можете просматривать свои заказы и баланс.</i>"

    kb = get_main_menu_kb(user.role)
    
    if edit and isinstance(message_or_call, types.CallbackQuery):
        await message_or_call.message.edit_text(text, reply_markup=kb)
    elif isinstance(message_or_call, types.Message):
        await message_or_call.answer(text, reply_markup=kb)

# --- БАЗОВЫЕ КОМАНДЫ ---
@dp.message(Command("start"))
async def cmd_start(message: types.Message, state: FSMContext):
    await state.clear()
    args = message.text.split()
    if len(args) > 1:
        user = await db.register_user(args[1], message.from_user.id)
        if user:
            await message.answer(f"✅ <b>Добро пожаловать, {user.name}!</b> Вы успешно добавлены в систему.")
            return await send_main_menu(message, user)
        return await message.answer("❌ <b>Ошибка:</b> Неверный или устаревший invite-код.")
    
    user = await check_access(message)
    if not user:
        return await message.answer("⛔️ <b>Доступ ограничен.</b> Пожалуйста, используйте invite-ссылку от руководителя.")
    
    await send_main_menu(message, user)

# --- ОБРАБОТКА НАВИГАЦИИ (МЕНЮ) ---
@dp.callback_query(MenuCB.filter())
async def handle_menu(call: types.CallbackQuery, callback_data: MenuCB, state: FSMContext):
    user = await db.get_user(call.from_user.id)
    if not user: return await call.answer("Доступ запрещен", show_alert=True)

    action = callback_data.action
    back_kb = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="🔙 Назад в меню", callback_data=MenuCB(action="main").pack())]])

    if action == "main":
        await send_main_menu(call, user, edit=True)

    elif action == "invite" and user.role == db.Role.ADMIN:
        code = await db.create_invite("Новый сотрудник")
        bot_info = await bot.get_me()
        text = (
            f"🔗 <b>Ссылка-приглашение создана!</b>\n"
            f"➖➖➖➖➖➖➖➖➖➖\n"
            f"Отправьте эту ссылку новому сотруднику:\n"
            f"<code>https://t.me/{bot_info.username}?start={code}</code>\n\n"
            f"<i>⚠️ Ссылка одноразовая.</i>"
        )
        await call.message.edit_text(text, reply_markup=back_kb)

    elif action == "reports" and user.role == db.Role.ADMIN:
        stats = await db.get_stats("day")
        text = (
            f"📊 <b>Финансовый отчёт за сегодня</b>\n"
            f"➖➖➖➖➖➖➖➖➖➖\n"
            f"🟢 <b>Доходы:</b> {stats['income']:,.2f} ₽\n"
            f"🔴 <b>Расходы:</b> {stats['expense']:,.2f} ₽\n"
            f"➖➖➖➖➖➖➖➖➖➖\n"
            f"💰 <b>Чистая прибыль:</b> <u>{stats['profit']:,.2f} ₽</u>"
        )
        await call.message.edit_text(text, reply_markup=back_kb)

    elif action == "employees" and user.role == db.Role.ADMIN:
        emps = await db.get_all_employees()
        text = "👥 <b>Список сотрудников</b>\n➖➖➖➖➖➖➖➖➖➖\n"
        if emps:
            for e in emps:
                text += f"👤 <b>{e.name}</b>\n└ Баланс: <code>{e.balance:,.2f} ₽</code>\n\n"
        else:
            text += "<i>Сотрудников пока нет.</i>"
        await call.message.edit_text(text, reply_markup=back_kb)

    elif action == "orders" and user.role == db.Role.ADMIN:
        orders = await db.get_orders()
        text = "🧹 <b>Все заказы</b>\n➖➖➖➖➖➖➖➖➖➖\n"
        if orders:
            for o in orders:
                status_emoji = "✅" if o.status == db.OrderStatus.COMPLETED else "⏳"
                text += f"{status_emoji} <b>{o.address}</b> ({o.price} ₽)\n└ Тип: {o.clean_type}\n\n"
        else:
            text += "<i>Заказов пока нет.</i>"
        await call.message.edit_text(text, reply_markup=back_kb)

    elif action == "my_orders" and user.role == db.Role.EMPLOYEE:
        orders = await db.get_orders(user.id)
        active_orders = [o for o in orders if o.status != db.OrderStatus.COMPLETED]
        
        if not active_orders:
            await call.message.edit_text("🎉 <b>У вас нет активных заказов!</b>\nОтличная работа.", reply_markup=back_kb)
        else:
            # Показываем первый активный заказ (можно сделать пагинацию, но для простоты показываем списком с кнопками)
            text = "💼 <b>Ваши активные заказы:</b>\n➖➖➖➖➖➖➖➖➖➖\nВыберите заказ, чтобы завершить его:"
            kb = []
            for o in active_orders:
                kb.append([InlineKeyboardButton(text=f"✅ Завершить: {o.address[:15]}...", callback_data=OrderCB(action="complete", order_id=o.id).pack())])
            kb.append([InlineKeyboardButton(text="🔙 Назад", callback_data=MenuCB(action="main").pack())])
            await call.message.edit_text(text, reply_markup=InlineKeyboardMarkup(inline_keyboard=kb))

    elif action == "my_balance" and user.role == db.Role.EMPLOYEE:
        text = (
            f"💳 <b>Ваш финансовый кабинет</b>\n"
            f"➖➖➖➖➖➖➖➖➖➖\n"
            f"Текущий баланс к выплате:\n"
            f"💰 <b>{user.balance:,.2f} ₽</b>"
        )
        await call.message.edit_text(text, reply_markup=back_kb)

    await call.answer()

# --- ОБРАБОТКА ЗАКАЗОВ СОТРУДНИКАМИ ---
@dp.callback_query(OrderCB.filter(F.action == "complete"))
async def complete_order(call: types.CallbackQuery, callback_data: OrderCB):
    await db.update_order_status(callback_data.order_id, db.OrderStatus.COMPLETED)
    await call.answer("Заказ успешно завершен!", show_alert=True)
    # Возвращаем в меню
    user = await db.get_user(call.from_user.id)
    await send_main_menu(call, user, edit=True)

# --- ИИ: ГОЛОС И ТЕКСТ ---
@dp.message(F.voice)
async def handle_voice(message: types.Message, state: FSMContext):
    user = await check_access(message)
    if user and user.role == db.Role.ADMIN:
        msg = await message.answer("🎙 <i>Слушаю и расшифровываю...</i>")
        file = await bot.get_file(message.voice.file_id)
        path = f"voice_{message.voice.file_id}.ogg"
        await bot.download_file(file.file_path, path)
        text = await transcribe_audio(path)
        os.remove(path)
        await msg.edit_text(f"🗣 <b>Распознано:</b>\n<i>«{text}»</i>")
        await process_ai_logic(msg, text, state)

@dp.message(F.text)
async def handle_text(message: types.Message, state: FSMContext):
    user = await check_access(message)
    if user and user.role == db.Role.ADMIN:
        msg = await message.answer("🤖 <i>Анализирую запрос...</i>")
        await process_ai_logic(msg, message.text, state)
    elif user:
        await message.answer("ℹ️ <b>Сотрудники используют только кнопки меню.</b>")

# --- ЛОГИКА ИИ И СОЗДАНИЕ КРАСИВЫХ ЧЕКОВ ---
async def process_ai_logic(msg: types.Message, text: str, state: FSMContext):
    data = await parse_message(text)
    action = data.get("action_type")
    
    if action in ["finance", "order"]:
        await state.set_state(AIConfirmState.waiting_for_confirmation)
        await state.update_data(parsed_data=data)
        
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="✅ Подтвердить и сохранить", callback_data="ai_confirm")],
            [InlineKeyboardButton(text="❌ Отменить", callback_data="ai_cancel")]
        ])
        
        if action == "finance":
            cat_emoji = "🟢" if data.get('category') == "income" else "🔴"
            cat_name = {"income": "Доход", "expense": "Расход", "salary": "Зарплата", "advance": "Аванс", "purchase": "Закупка"}.get(data.get('category'), "Операция")
            
            preview = (
                f"🧾 <b>Чек финансовой операции</b>\n"
                f"➖➖➖➖➖➖➖➖➖➖\n"
                f"{cat_emoji} <b>Тип:</b> {cat_name}\n"
                f"💰 <b>Сумма:</b> {data.get('amount'):,.2f} ₽\n"
                f"👤 <b>Сотрудник:</b> {data.get('employee_name') or '<i>Не указан</i>'}\n"
                f"📝 <b>Комментарий:</b> {data.get('comment') or '<i>Нет</i>'}\n"
                f"➖➖➖➖➖➖➖➖➖➖\n"
                f"Всё верно?"
            )
        else:
            preview = (
                f"🧾 <b>Карточка нового заказа</b>\n"
                f"➖➖➖➖➖➖➖➖➖➖\n"
                f"📍 <b>Адрес:</b> {data.get('address')}\n"
                f"💰 <b>Сумма:</b> {data.get('price'):,.2f} ₽\n"
                f"🏷 <b>Тип уборки:</b> {data.get('clean_type')}\n"
                f"👷‍♂️ <b>Назначен:</b> {data.get('employee_name') or '<i>В резерве</i>'}\n"
                f"➖➖➖➖➖➖➖➖➖➖\n"
                f"Всё верно?"
            )
            
        await msg.edit_text(preview, reply_markup=kb)
        
    elif action == "analytics":
        stats = await db.get_stats(data.get("period", "day"))
        text = (
            f"📊 <b>Аналитика по вашему запросу</b>\n"
            f"➖➖➖➖➖➖➖➖➖➖\n"
            f"🟢 <b>Доходы:</b> {stats['income']:,.2f} ₽\n"
            f"🔴 <b>Расходы:</b> {stats['expense']:,.2f} ₽\n"
            f"➖➖➖➖➖➖➖➖➖➖\n"
            f"💰 <b>Прибыль:</b> <u>{stats['profit']:,.2f} ₽</u>"
        )
        await msg.edit_text(text)
    else:
        await msg.edit_text("❓ <b>Не удалось распознать команду.</b>\nПопробуйте сформулировать иначе.")

# --- ПОДТВЕРЖДЕНИЕ ИИ ---
@dp.callback_query(F.data.in_(["ai_confirm", "ai_cancel"]))
async def handle_ai_confirmation(call: types.CallbackQuery, state: FSMContext):
    if call.data == "ai_cancel":
        await state.clear()
        return await call.message.edit_text("❌ <b>Действие отменено.</b>")
    
    data = await state.get_data()
    action_data = data.get("parsed_data")
    
    if not action_data:
        return await call.message.edit_text("⏳ <b>Время ожидания истекло.</b> Повторите запрос.")
    
    action = action_data.get("action_type")
    if action == "finance":
        emp = await db.get_user_by_name(action_data.get("employee_name", "")) if action_data.get("employee_name") else None
        await db.add_transaction(action_data.get("amount", 0), action_data.get("category", "expense"), action_data.get("comment", ""), emp.id if emp else None)
        await call.message.edit_text("✅ <b>Успешно!</b> Финансовая операция сохранена в базу.")
    elif action == "order":
        emp = await db.get_user_by_name(action_data.get("employee_name", "")) if action_data.get("employee_name") else None
        await db.create_order(action_data.get("address", "Не указан"), action_data.get("price", 0), action_data.get("clean_type", "Стандарт"), assigned_to=emp.id if emp else None)
        await call.message.edit_text("✅ <b>Успешно!</b> Заказ создан и добавлен в систему.")
    
    await state.clear()
    await call.answer()

# --- ЕЖЕДНЕВНЫЙ ОТЧЕТ ---
async def daily_report():
    async with db.AsyncSessionLocal() as session:
        admin = (await session.execute(db.select(db.User).where(db.User.role == db.Role.ADMIN))).scalars().first()
        if admin and admin.tg_id:
            stats = await db.get_stats("day")
            text = (
                f"🌙 <b>Вечерний итог дня</b>\n"
                f"➖➖➖➖➖➖➖➖➖➖\n"
                f"🟢 Доходы: {stats['income']:,.2f} ₽\n"
                f"🔴 Расходы: {stats['expense']:,.2f} ₽\n"
                f"💰 <b>Прибыль: {stats['profit']:,.2f} ₽</b>"
            )
            await bot.send_message(admin.tg_id, text)

async def main():
    await db.init_db()
    scheduler.add_job(daily_report, 'cron', hour=20)
    scheduler.start()
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
