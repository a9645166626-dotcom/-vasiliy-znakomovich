import os
import sqlite3
import asyncio
import html

from aiogram import Bot, Dispatcher, F
from aiogram.filters import CommandStart, Command
from aiogram.types import (
    Message,
    CallbackQuery,
    ReplyKeyboardMarkup,
    KeyboardButton,
)
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.context import FSMContext
from aiogram.fsm.storage.memory import MemoryStorage


# =========================================================
# НАСТРОЙКИ
# =========================================================

TOKEN = os.getenv("BOT_TOKEN")

# ТВОЙ TELEGRAM ID
ADMIN_ID = int(os.getenv("ADMIN_ID", "8159222970"))

# Юзернейм поддержки БЕЗ @
SUPPORT_USERNAME = "LISI_SUPPORT"

DB_NAME = "lisi.db"


# =========================================================
# BOT / DISPATCHER
# =========================================================

storage = MemoryStorage()

dp = Dispatcher(storage=storage)


# =========================================================
# СОСТОЯНИЯ
# =========================================================

class BroadcastState(StatesGroup):
    waiting_for_message = State()


# =========================================================
# БАЗА ДАННЫХ
# =========================================================

def get_db():
    return sqlite3.connect(DB_NAME)


def init_db():

    con = get_db()
    cur = con.cursor()

    # -----------------------------------------------------
    # USERS — РОВНО 9 ПОЛЕЙ
    # -----------------------------------------------------

    cur.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY,
            name TEXT,
            age INTEGER,
            gender TEXT,
            looking_for TEXT,
            city TEXT,
            bio TEXT,
            photo TEXT,
            state TEXT DEFAULT 'name'
        )
    """)

    # -----------------------------------------------------
    # ЛАЙКИ
    # -----------------------------------------------------

    cur.execute("""
        CREATE TABLE IF NOT EXISTS likes (
            from_id INTEGER,
            to_id INTEGER,
            UNIQUE(from_id, to_id)
        )
    """)

    # -----------------------------------------------------
    # ПРОПУСКИ
    # -----------------------------------------------------

    cur.execute("""
        CREATE TABLE IF NOT EXISTS passes (
            from_id INTEGER,
            to_id INTEGER,
            UNIQUE(from_id, to_id)
        )
    """)

    # -----------------------------------------------------
    # ЖАЛОБЫ
    # -----------------------------------------------------

    cur.execute("""
        CREATE TABLE IF NOT EXISTS reports (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            from_id INTEGER,
            to_id INTEGER,
            status TEXT DEFAULT 'pending',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(from_id, to_id)
        )
    """)

    # -----------------------------------------------------
    # БЛОКИРОВКИ
    # -----------------------------------------------------

    cur.execute("""
        CREATE TABLE IF NOT EXISTS admin_blocks (
            user_id INTEGER PRIMARY KEY,
            blocked_by INTEGER,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    con.commit()
    con.close()


# =========================================================
# ПОЛУЧИТЬ ПОЛЬЗОВАТЕЛЯ
# =========================================================

def get_user(user_id):

    con = get_db()

    user = con.execute(
        "SELECT * FROM users WHERE id = ?",
        (user_id,)
    ).fetchone()

    con.close()

    return user


# =========================================================
# ПРОВЕРКА АДМИНА
# =========================================================

def is_admin(user_id):

    return user_id == ADMIN_ID


# =========================================================
# ПРОВЕРКА БЛОКИРОВКИ
# =========================================================

def is_blocked(user_id):

    # Админ никогда не блокируется
    if user_id == ADMIN_ID:
        return False

    con = get_db()

    result = con.execute(
        """
        SELECT 1
        FROM admin_blocks
        WHERE user_id = ?
        """,
        (user_id,)
    ).fetchone()

    con.close()

    return result is not None


async def check_blocked(message: Message):

    if is_blocked(message.from_user.id):

        await message.answer(
            "🚫 <b>ДОСТУП ОГРАНИЧЕН</b>\n"
            "━━━━━━━━━━━━━━\n\n"
            "Твоя возможность пользоваться ботом "
            "ограничена администрацией ЛИСИ.",
            parse_mode="HTML"
        )

        return True

    return False


# =========================================================
# ИЗМЕНЕНИЕ ПОЛЯ
# =========================================================

def set_value(user_id, field, value):

    allowed_fields = {
        "name",
        "age",
        "gender",
        "looking_for",
        "city",
        "bio",
        "photo",
        "state",
    }

    if field not in allowed_fields:
        return

    con = get_db()

    con.execute(
        f"""
        UPDATE users
        SET {field} = ?
        WHERE id = ?
        """,
        (value, user_id)
    )

    con.commit()
    con.close()


# =========================================================
# ОСНОВНАЯ КЛАВИАТУРА
# =========================================================

def main_keyboard():

    return ReplyKeyboardMarkup(
        keyboard=[
            [
                KeyboardButton(text="🦊 Смотреть анкеты"),
                KeyboardButton(text="👤 Моя анкета"),
            ],
            [
                KeyboardButton(text="❤️ Мои лайки"),
                KeyboardButton(text="💕 Мои мэтчи"),
            ],
            [
                KeyboardButton(text="⚙️ Настройки"),
                KeyboardButton(text="🆘 Поддержка"),
            ],
        ],
        resize_keyboard=True,
        is_persistent=True,
    )


# =========================================================
# ПОЛ
# =========================================================

def gender_keyboard():

    builder = InlineKeyboardBuilder()

    builder.button(
        text="♂️ Мужской",
        callback_data="gender:male"
    )

    builder.button(
        text="♀️ Женский",
        callback_data="gender:female"
    )

    builder.adjust(2)

    return builder.as_markup()


# =========================================================
# КОГО ИЩЕТ
# =========================================================

def looking_keyboard():

    builder = InlineKeyboardBuilder()

    builder.button(
        text="♂️ Мужчин",
        callback_data="looking:male"
    )

    builder.button(
        text="♀️ Женщин",
        callback_data="looking:female"
    )

    builder.button(
        text="👥 Всех",
        callback_data="looking:all"
    )

    builder.adjust(2, 1)

    return builder.as_markup()


# =========================================================
# АНКЕТА
# =========================================================

def profile_keyboard(user_id):

    builder = InlineKeyboardBuilder()

    builder.button(
        text="❤️ Нравится",
        callback_data=f"like:{user_id}"
    )

    builder.button(
        text="👎 Пропустить",
        callback_data=f"pass:{user_id}"
    )

    builder.button(
        text="🚨 Пожаловаться",
        callback_data=f"report:{user_id}"
    )

    builder.adjust(2, 1)

    return builder.as_markup()


# =========================================================
# МЭТЧ
# =========================================================

def match_keyboard(username):

    builder = InlineKeyboardBuilder()

    if username:

        builder.button(
            text="💬 Открыть профиль",
            url=f"https://t.me/{username}"
        )

    builder.adjust(1)

    return builder.as_markup()


# =========================================================
# НАСТРОЙКИ
# =========================================================

def settings_keyboard():

    builder = InlineKeyboardBuilder()

    builder.button(
        text="🔄 Пересоздать анкету",
        callback_data="restart_profile"
    )

    builder.button(
        text="❌ Закрыть",
        callback_data="close_settings"
    )

    builder.adjust(1)

    return builder.as_markup()


# =========================================================
# АДМИН-ПАНЕЛЬ
# =========================================================

def admin_keyboard():

    builder = InlineKeyboardBuilder()

    builder.button(
        text="👥 Пользователи",
        callback_data="admin:users"
    )

    builder.button(
        text="🚨 Жалобы",
        callback_data="admin:reports"
    )

    builder.button(
        text="🚫 Заблокированные",
        callback_data="admin:blocked"
    )

    builder.button(
        text="📊 Статистика",
        callback_data="admin:stats"
    )

    builder.button(
        text="📢 Рассылка",
        callback_data="admin:broadcast"
    )

    builder.button(
        text="❌ Закрыть",
        callback_data="admin:close"
    )

    builder.adjust(2, 1, 1, 1)

    return builder.as_markup()


# =========================================================
# START
# =========================================================

@dp.message(CommandStart())
async def start(message: Message, state: FSMContext):

    # Если админ сейчас пишет рассылку — не сбиваем состояние
    current_state = await state.get_state()

    if current_state == BroadcastState.waiting_for_message.state:
        return

    if await check_blocked(message):
        return

    user = get_user(message.from_user.id)

    if not user:

        con = get_db()

        con.execute(
            """
            INSERT INTO users(id, state)
            VALUES (?, 'name')
            """,
            (message.from_user.id,)
        )

        con.commit()
        con.close()

        await message.answer(
            "🦊 <b>ЛИСИ</b>\n"
            "━━━━━━━━━━━━━━\n\n"
            "Добро пожаловать.\n\n"
            "Здесь люди находят новых людей,\n"
            "общение и интересные знакомства.\n\n"
            "Давай создадим твою анкету ✨\n\n"
            "🧡 <b>Как тебя зовут?</b>",
            parse_mode="HTML"
        )

        return

    if user[8] == "done":

        await message.answer(
            "🦊 <b>ЛИСИ</b>\n"
            "━━━━━━━━━━━━━━\n\n"
            "С возвращением 🧡\n\n"
            "Выбирай действие в меню ниже.",
            parse_mode="HTML",
            reply_markup=main_keyboard()
        )

        return

    current_state = user[8]

    if current_state == "gender":

        await message.answer(
            "🦊 <b>Кто ты?</b>\n\n"
            "Выбери свой пол:",
            parse_mode="HTML",
            reply_markup=gender_keyboard()
        )

        return

    if current_state == "looking":

        await message.answer(
            "🦊 <b>Кого хочешь видеть?</b>\n\n"
            "Выбери вариант:",
            parse_mode="HTML",
            reply_markup=looking_keyboard()
        )

        return

    state_text = {
        "name": "Как тебя зовут?",
        "age": "Сколько тебе лет?",
        "city": "В каком городе ты живёшь?",
        "bio": "Расскажи немного о себе.",
        "photo": "Отправь свою фотографию.",
    }

    await message.answer(
        "🦊 <b>Продолжим создание анкеты.</b>\n\n"
        + state_text.get(
            current_state,
            "Продолжим."
        ),
        parse_mode="HTML"
    )


# =========================================================
# АДМИН — /admin
# =========================================================

@dp.message(Command("admin"))
async def admin_command(message: Message, state: FSMContext):

    if not is_admin(message.from_user.id):

        await message.answer(
            "⛔ Доступ запрещён."
        )

        return

    await state.clear()

    con = get_db()

    users_count = con.execute(
        "SELECT COUNT(*) FROM users"
    ).fetchone()[0]

    profiles_count = con.execute(
        """
        SELECT COUNT(*)
        FROM users
        WHERE state = 'done'
        """
    ).fetchone()[0]

    reports_count = con.execute(
        """
        SELECT COUNT(*)
        FROM reports
        WHERE status = 'pending'
        """
    ).fetchone()[0]

    blocked_count = con.execute(
        "SELECT COUNT(*) FROM admin_blocks"
    ).fetchone()[0]

    con.close()

    await message.answer(
        "🦊 <b>АДМИН-ПАНЕЛЬ ЛИСИ</b>\n"
        "━━━━━━━━━━━━━━\n\n"
        f"👥 Пользователей: <b>{users_count}</b>\n"
        f"📝 Анкет: <b>{profiles_count}</b>\n"
        f"🚨 Новых жалоб: <b>{reports_count}</b>\n"
        f"🚫 Заблокировано: <b>{blocked_count}</b>\n\n"
        "Выбери раздел:",
        parse_mode="HTML",
        reply_markup=admin_keyboard()
    )


# =========================================================
# АДМИН — CALLBACK
# =========================================================

@dp.callback_query(F.data.startswith("admin:"))
async def admin_callback(
    callback: CallbackQuery,
    state: FSMContext
):

    if not is_admin(callback.from_user.id):

        await callback.answer(
            "⛔ Доступ запрещён.",
            show_alert=True
        )

        return

    action = callback.data.split(":")[1]

    # -----------------------------------------------------
    # ЗАКРЫТЬ
    # -----------------------------------------------------

    if action == "close":

        await state.clear()

        try:
            await callback.message.delete()
        except Exception:
            pass

        await callback.answer()

        return

    # -----------------------------------------------------
    # РАССЫЛКА
    # -----------------------------------------------------

    if action == "broadcast":

        await state.set_state(
            BroadcastState.waiting_for_message
        )

        builder = InlineKeyboardBuilder()

        builder.button(
            text="❌ Отмена",
            callback_data="broadcast_cancel"
        )

        await callback.message.edit_text(
            "📢 <b>РАССЫЛКА</b>\n"
            "━━━━━━━━━━━━━━\n\n"
            "Отправь мне сообщение, которое нужно "
            "разослать пользователям.\n\n"
            "Можно отправить:\n"
            "• обычный текст\n"
            "• фото с подписью\n"
            "• видео\n"
            "• документ\n\n"
            "После отправки я разошлю его всем "
            "пользователям бота.\n\n"
            "👇 <b>Жду сообщение.</b>",
            parse_mode="HTML",
            reply_markup=builder.as_markup()
        )

        await callback.answer()

        return

    # -----------------------------------------------------
    # ПОЛЬЗОВАТЕЛИ
    # -----------------------------------------------------

    if action == "users":

        con = get_db()

        rows = con.execute(
            """
            SELECT id, name, age, city, state
            FROM users
            ORDER BY id DESC
            LIMIT 20
            """
        ).fetchall()

        con.close()

        if not rows:

            await callback.message.edit_text(
                "👥 <b>Пользователей пока нет.</b>",
                parse_mode="HTML",
                reply_markup=admin_keyboard()
            )

            await callback.answer()

            return

        text = (
            "👥 <b>ПОСЛЕДНИЕ ПОЛЬЗОВАТЕЛИ</b>\n"
            "━━━━━━━━━━━━━━\n\n"
        )

        for uid, name, age, city, profile_state in rows:

            name_text = html.escape(
                str(name)
            ) if name else "Без имени"

            city_text = html.escape(
                str(city)
            ) if city else "Не указан"

            status = (
                "🚫"
                if is_blocked(uid)
                else "🟢"
            )

            text += (
                f"{status} <code>{uid}</code> — "
                f"<b>{name_text}</b>\n"
                f"🎂 {age or '-'} | "
                f"📍 {city_text}\n\n"
            )

        await callback.message.edit_text(
            text,
            parse_mode="HTML",
            reply_markup=admin_keyboard()
        )

        await callback.answer()

        return

    # -----------------------------------------------------
    # ЖАЛОБЫ
    # -----------------------------------------------------

    if action == "reports":

        con = get_db()

        reports = con.execute(
            """
            SELECT id, from_id, to_id, created_at
            FROM reports
            WHERE status = 'pending'
            ORDER BY id DESC
            LIMIT 20
            """
        ).fetchall()

        con.close()

        if not reports:

            await callback.message.edit_text(
                "🚨 <b>ЖАЛОБ НЕТ</b>\n\n"
                "Новых жалоб на рассмотрении нет.",
                parse_mode="HTML",
                reply_markup=admin_keyboard()
            )

            await callback.answer()

            return

        text = (
            "🚨 <b>ЖАЛОБЫ</b>\n"
            "━━━━━━━━━━━━━━\n\n"
        )

        builder = InlineKeyboardBuilder()

        for report_id, from_id, to_id, created_at in reports:

            text += (
                f"🚨 Жалоба <b>#{report_id}</b>\n"
                f"От: <code>{from_id}</code>\n"
                f"На: <code>{to_id}</code>\n"
                f"📅 {created_at}\n\n"
            )

            builder.button(
                text=f"👁 Жалоба #{report_id}",
                callback_data=f"reportview:{report_id}"
            )

        builder.adjust(1)

        builder.button(
            text="⬅️ Назад",
            callback_data="adminback"
        )

        await callback.message.edit_text(
            text,
            parse_mode="HTML",
            reply_markup=builder.as_markup()
        )

        await callback.answer()

        return

    # -----------------------------------------------------
    # ЗАБЛОКИРОВАННЫЕ
    # -----------------------------------------------------

    if action == "blocked":

        con = get_db()

        rows = con.execute(
            """
            SELECT b.user_id, u.name, u.age, u.city
            FROM admin_blocks b
            LEFT JOIN users u
            ON u.id = b.user_id
            ORDER BY b.created_at DESC
            LIMIT 20
            """
        ).fetchall()

        con.close()

        if not rows:

            await callback.message.edit_text(
                "🚫 <b>ЗАБЛОКИРОВАННЫХ НЕТ</b>",
                parse_mode="HTML",
                reply_markup=admin_keyboard()
            )

            await callback.answer()

            return

        builder = InlineKeyboardBuilder()

        text = (
            "🚫 <b>ЗАБЛОКИРОВАННЫЕ</b>\n"
            "━━━━━━━━━━━━━━\n\n"
        )

        for uid, name, age, city in rows:

            name_text = html.escape(
                str(name)
            ) if name else "Без имени"

            city_text = html.escape(
                str(city)
            ) if city else "-"

            text += (
                f"🚫 <b>{name_text}</b>\n"
                f"ID: <code>{uid}</code>\n"
                f"🎂 {age or '-'} | "
                f"📍 {city_text}\n\n"
            )

            builder.button(
                text=f"🔓 Разблокировать {uid}",
                callback_data=f"unblock:{uid}"
            )

        builder.adjust(1)

        builder.button(
            text="⬅️ Назад",
            callback_data="adminback"
        )

        await callback.message.edit_text(
            text,
            parse_mode="HTML",
            reply_markup=builder.as_markup()
        )

        await callback.answer()

        return

    # -----------------------------------------------------
    # СТАТИСТИКА
    # -----------------------------------------------------

    if action == "stats":

        con = get_db()

        users = con.execute(
            "SELECT COUNT(*) FROM users"
        ).fetchone()[0]

        profiles = con.execute(
            """
            SELECT COUNT(*)
            FROM users
            WHERE state = 'done'
            """
        ).fetchone()[0]

        likes = con.execute(
            "SELECT COUNT(*) FROM likes"
        ).fetchone()[0]

        passes = con.execute(
            "SELECT COUNT(*) FROM passes"
        ).fetchone()[0]

        reports = con.execute(
            "SELECT COUNT(*) FROM reports"
        ).fetchone()[0]

        pending_reports = con.execute(
            """
            SELECT COUNT(*)
            FROM reports
            WHERE status = 'pending'
            """
        ).fetchone()[0]

        blocked = con.execute(
            "SELECT COUNT(*) FROM admin_blocks"
        ).fetchone()[0]

        matches = con.execute(
            """
            SELECT COUNT(*)
            FROM likes a
            JOIN likes b
            ON a.from_id = b.to_id
            AND a.to_id = b.from_id
            WHERE a.from_id < a.to_id
            """
        ).fetchone()[0]

        con.close()

        await callback.message.edit_text(
            "📊 <b>СТАТИСТИКА ЛИСИ</b>\n"
            "━━━━━━━━━━━━━━\n\n"
            f"👥 Пользователей: <b>{users}</b>\n"
            f"📝 Анкет: <b>{profiles}</b>\n"
            f"🚫 Заблокировано: <b>{blocked}</b>\n\n"
            f"❤️ Лайков: <b>{likes}</b>\n"
            f"👎 Пропусков: <b>{passes}</b>\n"
            f"💕 Мэтчей: <b>{matches}</b>\n\n"
            f"🚨 Жалоб: <b>{reports}</b>\n"
            f"⏳ На рассмотрении: <b>{pending_reports}</b>",
            parse_mode="HTML",
            reply_markup=admin_keyboard()
        )

        await callback.answer()

        return


# =========================================================
# ОТМЕНА РАССЫЛКИ
# =========================================================

@dp.callback_query(F.data == "broadcast_cancel")
async def broadcast_cancel(
    callback: CallbackQuery,
    state: FSMContext
):

    if not is_admin(callback.from_user.id):

        await callback.answer(
            "⛔ Доступ запрещён.",
            show_alert=True
        )

        return

    await state.clear()

    await callback.message.edit_text(
        "🦊 <b>АДМИН-ПАНЕЛЬ ЛИСИ</b>\n"
        "━━━━━━━━━━━━━━\n\n"
        "Рассылка отменена.\n\n"
        "Выбери раздел:",
        parse_mode="HTML",
        reply_markup=admin_keyboard()
    )

    await callback.answer(
        "Рассылка отменена."
    )


# =========================================================
# РАССЫЛКА — ПОЛУЧЕНИЕ СООБЩЕНИЯ
# =========================================================

@dp.message(BroadcastState.waiting_for_message)
async def process_broadcast(
    message: Message,
    state: FSMContext
):

    # Дополнительная проверка
    if not is_admin(message.from_user.id):

        await state.clear()

        return

    # -----------------------------------------------------
    # НЕ ДАЁМ РАССЫЛКАТЬ КОМАНДЫ
    # -----------------------------------------------------

    if message.text and message.text.startswith("/"):

        await message.answer(
            "⚠️ Для рассылки отправь обычное сообщение.\n\n"
            "Если хочешь отменить рассылку — нажми "
            "кнопку «Отмена»."
        )

        return

    # -----------------------------------------------------
    # ПОЛУЧАЕМ ВСЕХ ПОЛЬЗОВАТЕЛЕЙ
    # -----------------------------------------------------

    con = get_db()

    users = con.execute(
        """
        SELECT id
        FROM users
        """
    ).fetchall()

    blocked_users = con.execute(
        """
        SELECT user_id
        FROM admin_blocks
        """
    ).fetchall()

    con.close()

    blocked_ids = {
        row[0]
        for row in blocked_users
    }

    # -----------------------------------------------------
    # СТАТИСТИКА
    # -----------------------------------------------------

    total = 0
    success = 0
    failed = 0

    await message.answer(
        "📢 <b>Рассылка началась...</b>\n\n"
        f"👥 Всего пользователей: <b>{len(users)}</b>\n"
        "⏳ Отправляю сообщения...",
        parse_mode="HTML"
    )

    # -----------------------------------------------------
    # РАССЫЛКА
    # -----------------------------------------------------

    for row in users:

        user_id = row[0]

        # Заблокированным не отправляем
        if user_id in blocked_ids:
            continue

        total += 1

        try:

            await message.copy_to(
                chat_id=user_id
            )

            success += 1

        except Exception:

            failed += 1

        # Небольшая пауза между сообщениями
        await asyncio.sleep(0.05)

    # -----------------------------------------------------
    # ЗАВЕРШАЕМ
    # -----------------------------------------------------

    await state.clear()

    await message.answer(
        "📢 <b>РАССЫЛКА ЗАВЕРШЕНА</b>\n"
        "━━━━━━━━━━━━━━\n\n"
        f"👥 Получателей: <b>{total}</b>\n"
        f"✅ Доставлено: <b>{success}</b>\n"
        f"❌ Не доставлено: <b>{failed}</b>\n\n"
        "🦊 Админ-панель:",
        parse_mode="HTML",
        reply_markup=admin_keyboard()
    )


# =========================================================
# АДМИН — НАЗАД
# =========================================================

@dp.callback_query(F.data == "adminback")
async def admin_back(callback: CallbackQuery):

    if not is_admin(callback.from_user.id):

        await callback.answer(
            "⛔ Доступ запрещён.",
            show_alert=True
        )

        return

    await callback.message.edit_text(
        "🦊 <b>АДМИН-ПАНЕЛЬ ЛИСИ</b>\n\n"
        "Выбери раздел:",
        parse_mode="HTML",
        reply_markup=admin_keyboard()
    )

    await callback.answer()


# =========================================================
# ПРОСМОТР ЖАЛОБЫ
# =========================================================

@dp.callback_query(F.data.startswith("reportview:"))
async def report_view(callback: CallbackQuery):

    if not is_admin(callback.from_user.id):

        await callback.answer(
            "⛔ Доступ запрещён.",
            show_alert=True
        )

        return

    report_id = int(
        callback.data.split(":")[1]
    )

    con = get_db()

    report = con.execute(
        """
        SELECT from_id, to_id, status, created_at
        FROM reports
        WHERE id = ?
        """,
        (report_id,)
    ).fetchone()

    con.close()

    if not report:

        await callback.answer(
            "Жалоба не найдена.",
            show_alert=True
        )

        return

    from_id, to_id, status, created_at = report

    target = get_user(to_id)

    builder = InlineKeyboardBuilder()

    builder.button(
        text="🚫 Заблокировать",
        callback_data=f"block:{to_id}:{report_id}"
    )

    builder.button(
        text="✅ Отклонить жалобу",
        callback_data=f"dismiss:{report_id}"
    )

    builder.button(
        text="⬅️ К жалобам",
        callback_data="admin:reports"
    )

    builder.adjust(1)

    if target:

        # =================================================
        # ВАЖНО: USERS = РОВНО 9 ПОЛЕЙ
        # =================================================

        (
            uid,
            name,
            age,
            gender,
            looking,
            city,
            bio,
            photo,
            profile_state
        ) = target

        safe_name = html.escape(
            str(name)
        ) if name else "Без имени"

        safe_city = html.escape(
            str(city)
        ) if city else "-"

        safe_bio = html.escape(
            str(bio)
        ) if bio else "Без описания"

        text = (
            f"🚨 <b>ЖАЛОБА #{report_id}</b>\n"
            "━━━━━━━━━━━━━━\n\n"
            f"👤 На пользователя:\n"
            f"<b>{safe_name}</b>, {age or '-'}\n"
            f"ID: <code>{to_id}</code>\n"
            f"📍 {safe_city}\n\n"
            f"💬 {safe_bio}\n\n"
            f"👤 Жалобу отправил: "
            f"<code>{from_id}</code>\n"
            f"📅 {created_at}\n"
            f"Статус: <b>{status}</b>"
        )

    else:

        text = (
            f"🚨 <b>ЖАЛОБА #{report_id}</b>\n\n"
            f"Пользователь <code>{to_id}</code> "
            "не найден."
        )

    await callback.message.edit_text(
        text,
        parse_mode="HTML",
        reply_markup=builder.as_markup()
    )

    await callback.answer()


# =========================================================
# БЛОКИРОВКА
# =========================================================

@dp.callback_query(F.data.startswith("block:"))
async def block_user(callback: CallbackQuery):

    if not is_admin(callback.from_user.id):

        await callback.answer(
            "⛔ Доступ запрещён.",
            show_alert=True
        )

        return

    parts = callback.data.split(":")

    user_id = int(parts[1])
    report_id = int(parts[2])

    if user_id == ADMIN_ID:

        await callback.answer(
            "Нельзя заблокировать администратора.",
            show_alert=True
        )

        return

    con = get_db()

    con.execute(
        """
        INSERT OR IGNORE INTO admin_blocks(
            user_id,
            blocked_by
        )
        VALUES (?, ?)
        """,
        (user_id, ADMIN_ID)
    )

    con.execute(
        """
        UPDATE reports
        SET status = 'resolved'
        WHERE id = ?
        """,
        (report_id,)
    )

    con.commit()
    con.close()

    await callback.answer(
        "Пользователь заблокирован."
    )

    await callback.message.edit_text(
        "🚫 <b>ПОЛЬЗОВАТЕЛЬ ЗАБЛОКИРОВАН</b>\n\n"
        f"ID: <code>{user_id}</code>\n\n"
        "Он больше не сможет пользоваться ботом.",
        parse_mode="HTML",
        reply_markup=admin_keyboard()
    )

    try:

        await callback.bot.send_message(
            user_id,
            "🚫 <b>Доступ ограничен</b>\n\n"
            "Твоя возможность пользоваться ботом "
            "ЛИСИ ограничена администрацией.",
            parse_mode="HTML"
        )

    except Exception:
        pass


# =========================================================
# РАЗБЛОКИРОВКА
# =========================================================

@dp.callback_query(F.data.startswith("unblock:"))
async def unblock_user(callback: CallbackQuery):

    if not is_admin(callback.from_user.id):

        await callback.answer(
            "⛔ Доступ запрещён.",
            show_alert=True
        )

        return

    user_id = int(
        callback.data.split(":")[1]
    )

    con = get_db()

    con.execute(
        """
        DELETE FROM admin_blocks
        WHERE user_id = ?
        """,
        (user_id,)
    )

    con.commit()
    con.close()

    await callback.answer(
        "Пользователь разблокирован."
    )

    await callback.message.edit_text(
        "✅ <b>ПОЛЬЗОВАТЕЛЬ РАЗБЛОКИРОВАН</b>\n\n"
        f"ID: <code>{user_id}</code>",
        parse_mode="HTML",
        reply_markup=admin_keyboard()
    )

    try:

        await callback.bot.send_message(
            user_id,
            "✅ <b>Доступ восстановлен.</b>\n\n"
            "Ты снова можешь пользоваться ЛИСИ.",
            parse_mode="HTML"
        )

    except Exception:
        pass


# =========================================================
# ОТКЛОНИТЬ ЖАЛОБУ
# =========================================================

@dp.callback_query(F.data.startswith("dismiss:"))
async def dismiss_report(callback: CallbackQuery):

    if not is_admin(callback.from_user.id):

        await callback.answer(
            "⛔ Доступ запрещён.",
            show_alert=True
        )

        return

    report_id = int(
        callback.data.split(":")[1]
    )

    con = get_db()

    con.execute(
        """
        UPDATE reports
        SET status = 'dismissed'
        WHERE id = ?
        """,
        (report_id,)
    )

    con.commit()
    con.close()

    await callback.answer(
        "Жалоба отклонена."
    )

    await callback.message.edit_text(
        "✅ <b>ЖАЛОБА ОТКЛОНЕНА</b>\n\n"
        f"Жалоба #{report_id} закрыта.",
        parse_mode="HTML",
        reply_markup=admin_keyboard()
    )


# =========================================================
# РЕГИСТРАЦИЯ
# =========================================================

REGISTRATION_BUTTONS = {
    "🦊 Смотреть анкеты",
    "👤 Моя анкета",
    "❤️ Мои лайки",
    "💕 Мои мэтчи",
    "⚙️ Настройки",
    "🆘 Поддержка",
}


@dp.message(
    F.text,
    ~F.text.in_(REGISTRATION_BUTTONS)
)
async def registration(
    message: Message,
    state: FSMContext
):

    # Не обрабатываем сообщение как регистрацию,
    # если сейчас идёт рассылка
    current_state = await state.get_state()

    if current_state == BroadcastState.waiting_for_message.state:
        return

    if await check_blocked(message):
        return

    text = message.text.strip()

    user = get_user(message.from_user.id)

    if not user:
        return

    profile_state = user[8]

    # -----------------------------------------------------
    # ИМЯ
    # -----------------------------------------------------

    if profile_state == "name":

        if len(text) > 40:

            await message.answer(
                "🦊 Имя слишком длинное.\n\n"
                "Напиши максимум 40 символов."
            )

            return

        if len(text) < 2:

            await message.answer(
                "🦊 Напиши хотя бы 2 символа."
            )

            return

        set_value(
            message.from_user.id,
            "name",
            text
        )

        set_value(
            message.from_user.id,
            "state",
            "age"
        )

        await message.answer(
            "🦊 <b>ШАГ 2 / 7</b>\n"
            "━━━━━━━━━━━━━━\n\n"
            "🎂 <b>Сколько тебе лет?</b>\n\n"
            "Напиши число от 13 до 100.",
            parse_mode="HTML"
        )

        return

    # -----------------------------------------------------
    # ВОЗРАСТ
    # -----------------------------------------------------

    if profile_state == "age":

        try:

            age = int(text)

        except ValueError:

            await message.answer(
                "🦊 Напиши возраст именно числом."
            )

            return

        if age < 13 or age > 100:

            await message.answer(
                "🦊 Возраст должен быть от 13 до 100."
            )

            return

        set_value(
            message.from_user.id,
            "age",
            age
        )

        set_value(
            message.from_user.id,
            "state",
            "gender"
        )

        await message.answer(
            "🦊 <b>ШАГ 3 / 7</b>\n"
            "━━━━━━━━━━━━━━\n\n"
            "✨ <b>Кто ты?</b>\n\n"
            "Выбери свой пол:",
            parse_mode="HTML",
            reply_markup=gender_keyboard()
        )

        return

    # -----------------------------------------------------
    # ГОРОД
    # -----------------------------------------------------

    if profile_state == "city":

        if len(text) > 60:

            await message.answer(
                "🦊 Название города слишком длинное."
            )

            return

        set_value(
            message.from_user.id,
            "city",
            text
        )

        set_value(
            message.from_user.id,
            "state",
            "bio"
        )

        await message.answer(
            "🦊 <b>ШАГ 6 / 7</b>\n"
            "━━━━━━━━━━━━━━\n\n"
            "💬 <b>Расскажи немного о себе.</b>\n\n"
            "Напиши пару слов — это увидят другие.",
            parse_mode="HTML"
        )

        return

    # -----------------------------------------------------
    # BIO
    # -----------------------------------------------------

    if profile_state == "bio":

        set_value(
            message.from_user.id,
            "bio",
            text[:500]
        )

        set_value(
            message.from_user.id,
            "state",
            "photo"
        )

        await message.answer(
            "🦊 <b>ШАГ 7 / 7</b>\n"
            "━━━━━━━━━━━━━━\n\n"
            "📸 <b>Теперь отправь фотографию.</b>",
            parse_mode="HTML"
        )

        return


# =========================================================
# ПОЛ
# =========================================================

@dp.callback_query(F.data.startswith("gender:"))
async def choose_gender(callback: CallbackQuery):

    if is_blocked(callback.from_user.id):

        await callback.answer(
            "🚫 Доступ ограничен.",
            show_alert=True
        )

        return

    gender = callback.data.split(":")[1]

    set_value(
        callback.from_user.id,
        "gender",
        gender
    )

    set_value(
        callback.from_user.id,
        "state",
        "looking"
    )

    await callback.message.edit_text(
        "🦊 <b>ШАГ 4 / 7</b>\n"
        "━━━━━━━━━━━━━━\n\n"
        "🔎 <b>Кого хочешь видеть?</b>",
        parse_mode="HTML",
        reply_markup=looking_keyboard()
    )

    await callback.answer()


# =========================================================
# КОГО ИЩЕТ
# =========================================================

@dp.callback_query(F.data.startswith("looking:"))
async def choose_looking(callback: CallbackQuery):

    if is_blocked(callback.from_user.id):

        await callback.answer(
            "🚫 Доступ ограничен.",
            show_alert=True
        )

        return

    looking = callback.data.split(":")[1]

    user = get_user(callback.from_user.id)

    if not user:

        await callback.answer(
            "Ошибка. Напиши /start.",
            show_alert=True
        )

        return

    age = user[2]

    if age < 18:

        text = (
            "🦊 <b>ШАГ 5 / 7</b>\n"
            "━━━━━━━━━━━━━━\n\n"
            "📍 <b>В каком городе ты живёшь?</b>\n\n"
            "Для пользователей младше 18 лет "
            "показываются только анкеты 13–17."
        )

    else:

        text = (
            "🦊 <b>ШАГ 5 / 7</b>\n"
            "━━━━━━━━━━━━━━\n\n"
            "📍 <b>В каком городе ты живёшь?</b>\n\n"
            "Для пользователей 18+ "
            "показываются только анкеты 18+."
        )

    set_value(
        callback.from_user.id,
        "looking_for",
        looking
    )

    set_value(
        callback.from_user.id,
        "state",
        "city"
    )

    await callback.message.edit_text(
        text,
        parse_mode="HTML"
    )

    await callback.answer()


# =========================================================
# ФОТО
# =========================================================

@dp.message(F.photo)
async def receive_photo(message: Message):

    if await check_blocked(message):
        return

    user = get_user(message.from_user.id)

    if not user:
        return

    if user[8] != "photo":
        return

    photo_id = message.photo[-1].file_id

    set_value(
        message.from_user.id,
        "photo",
        photo_id
    )

    set_value(
        message.from_user.id,
        "state",
        "done"
    )

    await message.answer(
        "🦊 <b>АНКЕТА ГОТОВА!</b>\n"
        "━━━━━━━━━━━━━━\n\n"
        "🧡 Добро пожаловать в ЛИСИ.\n\n"
        "Теперь ты можешь смотреть анкеты,\n"
        "ставить лайки и находить мэтчи.\n\n"
        "👇 Всё управление находится в меню.",
        parse_mode="HTML",
        reply_markup=main_keyboard()
    )


# =========================================================
# ПОКАЗ АНКЕТ
# =========================================================

async def show_profile(message, user_id):

    if is_blocked(user_id):

        await message.answer(
            "🚫 Доступ ограничен."
        )

        return

    me = get_user(user_id)

    if not me or me[8] != "done":

        await message.answer(
            "🦊 Сначала создай анкету через /start."
        )

        return

    my_age = me[2]
    looking_for = me[4]
    my_city = me[5]

    # -----------------------------------------------------
    # ВОЗРАСТ
    # -----------------------------------------------------

    if my_age < 18:

        min_age = 13
        max_age = 17

    else:

        min_age = 18
        max_age = 100

    con = get_db()

    query = """
        SELECT *
        FROM users
        WHERE id != ?
        AND state = 'done'
        AND age BETWEEN ? AND ?
        AND LOWER(TRIM(city)) = LOWER(TRIM(?))
    """

    params = [
        user_id,
        min_age,
        max_age,
        my_city
    ]

    # -----------------------------------------------------
    # ПОЛ
    # -----------------------------------------------------

    if looking_for != "all":

        query += """
            AND gender = ?
        """

        params.append(looking_for)

    # -----------------------------------------------------
    # ИСКЛЮЧАЕМ ОБРАБОТАННЫЕ
    # -----------------------------------------------------

    query += """
        AND id NOT IN (
            SELECT to_id
            FROM likes
            WHERE from_id = ?
        )

        AND id NOT IN (
            SELECT to_id
            FROM passes
            WHERE from_id = ?
        )

        AND id NOT IN (
            SELECT to_id
            FROM reports
            WHERE from_id = ?
        )

        AND id NOT IN (
            SELECT user_id
            FROM admin_blocks
        )

        ORDER BY RANDOM()
        LIMIT 1
    """

    params.extend([
        user_id,
        user_id,
        user_id
    ])

    person = con.execute(
        query,
        params
    ).fetchone()

    con.close()

    if not person:

        await message.answer(
            "🦊 <b>Пока подходящих анкет нет</b>\n"
            "━━━━━━━━━━━━━━\n\n"
            f"📍 Город: <b>"
            f"{html.escape(str(my_city))}</b>\n\n"
            "Мы показываем людей из твоего города\n"
            "и подходящей возрастной категории.\n\n"
            "Попробуй зайти позже 🧡",
            parse_mode="HTML"
        )

        return

    # =====================================================
    # USERS = 9 ПОЛЕЙ
    # =====================================================

    (
        uid,
        name,
        age,
        gender,
        looking,
        city,
        bio,
        photo,
        profile_state
    ) = person

    safe_name = html.escape(
        str(name)
    )

    safe_city = html.escape(
        str(city)
    )

    safe_bio = html.escape(
        str(bio)
    ) if bio else "Пока ничего не рассказал(а)."

    text = (
        f"🦊 <b>{safe_name}</b>, {age}\n"
        f"━━━━━━━━━━━━━━\n\n"
        f"📍 {safe_city}\n\n"
        f"💬 {safe_bio}\n\n"
        f"━━━━━━━━━━━━━━\n"
        f"🧡 Что скажешь?"
    )

    if photo:

        await message.answer_photo(
            photo=photo,
            caption=text,
            parse_mode="HTML",
            reply_markup=profile_keyboard(uid)
        )

    else:

        await message.answer(
            text,
            parse_mode="HTML",
            reply_markup=profile_keyboard(uid)
        )


# =========================================================
# СМОТРЕТЬ АНКЕТЫ
# =========================================================

@dp.message(F.text == "🦊 Смотреть анкеты")
async def browse_message(message: Message):

    if await check_blocked(message):
        return

    await show_profile(
        message,
        message.from_user.id
    )


# =========================================================
# ЛАЙК
# =========================================================

@dp.callback_query(F.data.startswith("like:"))
async def like(callback: CallbackQuery):

    if is_blocked(callback.from_user.id):

        await callback.answer(
            "🚫 Доступ ограничен.",
            show_alert=True
        )

        return

    target_id = int(
        callback.data.split(":")[1]
    )

    my_id = callback.from_user.id

    if target_id == my_id:

        await callback.answer(
            "Нельзя лайкнуть себя 😄",
            show_alert=True
        )

        return

    con = get_db()

    con.execute(
        """
        INSERT OR IGNORE INTO likes(
            from_id,
            to_id
        )
        VALUES (?, ?)
        """,
        (my_id, target_id)
    )

    mutual = con.execute(
        """
        SELECT 1
        FROM likes
        WHERE from_id = ?
        AND to_id = ?
        """,
        (target_id, my_id)
    ).fetchone()

    target = con.execute(
        """
        SELECT name
        FROM users
        WHERE id = ?
        """,
        (target_id,)
    ).fetchone()

    con.commit()
    con.close()

    await callback.answer("❤️ Лайк!")

    # -----------------------------------------------------
    # МЭТЧ
    # -----------------------------------------------------

    if mutual and target:

        target_name = html.escape(
            str(target[0])
        )

        try:

            target_chat = await callback.bot.get_chat(
                target_id
            )

            target_username = target_chat.username

        except Exception:

            target_username = None

        try:

            my_chat = await callback.bot.get_chat(
                my_id
            )

            my_username = my_chat.username

        except Exception:

            my_username = None

        if target_username:

            await callback.message.answer(
                "💕 <b>МЭТЧ!</b>\n"
                "━━━━━━━━━━━━━━\n\n"
                f"Вы понравились друг другу "
                f"с <b>{target_name}</b>! 🧡\n\n"
                "Теперь вы можете открыть профиль "
                "друг друга.",
                parse_mode="HTML",
                reply_markup=match_keyboard(
                    target_username
                )
            )

        else:

            await callback.message.answer(
                "💕 <b>МЭТЧ!</b>\n\n"
                f"Вы понравились друг другу "
                f"с <b>{target_name}</b>! 🧡\n\n"
                "У пользователя скрыт username Telegram.",
                parse_mode="HTML"
            )

        # -------------------------------------------------
        # УВЕДОМЛЕНИЕ ВТОРОГО
        # -------------------------------------------------

        try:

            if my_username:

                await callback.bot.send_message(
                    target_id,
                    "💕 <b>У тебя новый мэтч!</b>\n"
                    "━━━━━━━━━━━━━━\n\n"
                    "Вы понравились друг другу 🧡\n\n"
                    "Можешь открыть профиль человека "
                    "и начать общение.",
                    parse_mode="HTML",
                    reply_markup=match_keyboard(
                        my_username
                    )
                )

            else:

                await callback.bot.send_message(
                    target_id,
                    "💕 <b>У тебя новый мэтч!</b>\n\n"
                    "Вы понравились друг другу 🧡",
                    parse_mode="HTML"
                )

        except Exception:
            pass

    await show_profile(
        callback.message,
        my_id
    )


# =========================================================
# ПРОПУСК
# =========================================================

@dp.callback_query(F.data.startswith("pass:"))
async def pass_profile(callback: CallbackQuery):

    if is_blocked(callback.from_user.id):

        await callback.answer(
            "🚫 Доступ ограничен.",
            show_alert=True
        )

        return

    target_id = int(
        callback.data.split(":")[1]
    )

    my_id = callback.from_user.id

    con = get_db()

    con.execute(
        """
        INSERT OR IGNORE INTO passes(
            from_id,
            to_id
        )
        VALUES (?, ?)
        """,
        (my_id, target_id)
    )

    con.commit()
    con.close()

    await callback.answer(
        "👋 Пропущено"
    )

    await show_profile(
        callback.message,
        my_id
    )


# =========================================================
# ЖАЛОБА
# =========================================================

@dp.callback_query(F.data.startswith("report:"))
async def report(callback: CallbackQuery):

    if is_blocked(callback.from_user.id):

        await callback.answer(
            "🚫 Доступ ограничен.",
            show_alert=True
        )

        return

    target_id = int(
        callback.data.split(":")[1]
    )

    my_id = callback.from_user.id

    if target_id == my_id:

        await callback.answer(
            "Нельзя пожаловаться на себя.",
            show_alert=True
        )

        return

    con = get_db()

    con.execute(
        """
        INSERT OR IGNORE INTO reports(
            from_id,
            to_id
        )
        VALUES (?, ?)
        """,
        (my_id, target_id)
    )

    con.commit()
    con.close()

    await callback.answer(
        "🚨 Жалоба отправлена"
    )

    await callback.message.answer(
        "🚨 <b>Жалоба принята.</b>\n\n"
        "Спасибо, что помогаешь делать ЛИСИ безопаснее.",
        parse_mode="HTML"
    )

    await show_profile(
        callback.message,
        my_id
    )


# =========================================================
# МОЯ АНКЕТА
# =========================================================

@dp.message(F.text == "👤 Моя анкета")
async def my_profile(message: Message):

    if await check_blocked(message):
        return

    user = get_user(message.from_user.id)

    if not user or user[8] != "done":

        await message.answer(
            "🦊 Сначала создай анкету через /start."
        )

        return

    # =====================================================
    # USERS = 9 ПОЛЕЙ
    # =====================================================

    (
        uid,
        name,
        age,
        gender,
        looking,
        city,
        bio,
        photo,
        profile_state
    ) = user

    if gender == "male":

        gender_text = "♂️ Мужской"

    else:

        gender_text = "♀️ Женский"

    if looking == "male":

        looking_text = "♂️ Мужчин"

    elif looking == "female":

        looking_text = "♀️ Женщин"

    else:

        looking_text = "👥 Всех"

    safe_name = html.escape(
        str(name)
    )

    safe_city = html.escape(
        str(city)
    )

    safe_bio = html.escape(
        str(bio)
    ) if bio else "Без описания"

    text = (
        f"🦊 <b>{safe_name}</b>, {age}\n"
        f"━━━━━━━━━━━━━━\n\n"
        f"{gender_text}\n"
        f"🔎 Ищу: {looking_text}\n"
        f"📍 {safe_city}\n\n"
        f"💬 {safe_bio}"
    )

    if photo:

        await message.answer_photo(
            photo=photo,
            caption=text,
            parse_mode="HTML"
        )

    else:

        await message.answer(
            text,
            parse_mode="HTML"
        )


# =========================================================
# МОИ ЛАЙКИ
# =========================================================

@dp.message(F.text == "❤️ Мои лайки")
async def my_likes(message: Message):

    if await check_blocked(message):
        return

    con = get_db()

    rows = con.execute(
        """
        SELECT u.id, u.name, u.age, u.city
        FROM likes l
        JOIN users u
        ON u.id = l.to_id
        WHERE l.from_id = ?
        ORDER BY u.name
        """,
        (message.from_user.id,)
    ).fetchall()

    con.close()

    if not rows:

        await message.answer(
            "❤️ <b>МОИ ЛАЙКИ</b>\n"
            "━━━━━━━━━━━━━━\n\n"
            "Пока ты никого не лайкнул(а).\n\n"
            "Начни смотреть анкеты 🦊",
            parse_mode="HTML"
        )

        return

    text = (
        "❤️ <b>МОИ ЛАЙКИ</b>\n"
        "━━━━━━━━━━━━━━\n\n"
    )

    for uid, name, age, city in rows:

        text += (
            f"🦊 <b>{html.escape(str(name))}</b>, "
            f"{age}\n"
            f"📍 {html.escape(str(city))}\n\n"
        )

    await message.answer(
        text,
        parse_mode="HTML"
    )


# =========================================================
# МОИ МЭТЧИ
# =========================================================

@dp.message(F.text == "💕 Мои мэтчи")
async def my_matches(message: Message):

    if await check_blocked(message):
        return

    my_id = message.from_user.id

    con = get_db()

    rows = con.execute(
        """
        SELECT DISTINCT
            u.id,
            u.name,
            u.age,
            u.city
        FROM users u

        JOIN likes a
        ON a.to_id = u.id

        JOIN likes b
        ON b.from_id = u.id
        AND b.to_id = ?

        WHERE a.from_id = ?

        ORDER BY u.name
        """,
        (
            my_id,
            my_id
        )
    ).fetchall()

    con.close()

    if not rows:

        await message.answer(
            "💕 <b>МОИ МЭТЧИ</b>\n"
            "━━━━━━━━━━━━━━\n\n"
            "Пока взаимных симпатий нет.\n\n"
            "Продолжай смотреть анкеты 🦊",
            parse_mode="HTML"
        )

        return

    text = (
        "💕 <b>МОИ МЭТЧИ</b>\n"
        "━━━━━━━━━━━━━━\n\n"
    )

    for uid, name, age, city in rows:

        text += (
            f"🧡 <b>{html.escape(str(name))}</b>, "
            f"{age}\n"
            f"📍 {html.escape(str(city))}\n\n"
        )

    await message.answer(
        text,
        parse_mode="HTML"
    )


# =========================================================
# НАСТРОЙКИ
# =========================================================

@dp.message(F.text == "⚙️ Настройки")
async def settings(message: Message):

    if await check_blocked(message):
        return

    await message.answer(
        "⚙️ <b>НАСТРОЙКИ ЛИСИ</b>\n"
        "━━━━━━━━━━━━━━\n\n"
        "Здесь ты можешь пересоздать свою анкету.\n\n"
        "Фильтры поиска работают автоматически:\n"
        "📍 город\n"
        "🎂 возрастная категория\n"
        "👤 пол",
        parse_mode="HTML",
        reply_markup=settings_keyboard()
    )


# =========================================================
# ЗАКРЫТЬ НАСТРОЙКИ
# =========================================================

@dp.callback_query(F.data == "close_settings")
async def close_settings(callback: CallbackQuery):

    if is_blocked(callback.from_user.id):

        await callback.answer(
            "🚫 Доступ ограничен.",
            show_alert=True
        )

        return

    try:

        await callback.message.delete()

    except Exception:
        pass

    await callback.answer()


# =========================================================
# ПЕРЕСОЗДАТЬ АНКЕТУ
# =========================================================

@dp.callback_query(F.data == "restart_profile")
async def restart_profile(callback: CallbackQuery):

    if is_blocked(callback.from_user.id):

        await callback.answer(
            "🚫 Доступ ограничен.",
            show_alert=True
        )

        return

    con = get_db()

    con.execute(
        """
        UPDATE users
        SET name = NULL,
            age = NULL,
            gender = NULL,
            looking_for = NULL,
            city = NULL,
            bio = NULL,
            photo = NULL,
            state = 'name'
        WHERE id = ?
        """,
        (callback.from_user.id,)
    )

    con.commit()
    con.close()

    await callback.message.answer(
        "🦊 <b>Начинаем создание анкеты заново.</b>\n\n"
        "🧡 Как тебя зовут?",
        parse_mode="HTML"
    )

    await callback.answer()


# =========================================================
# ПОДДЕРЖКА
# =========================================================

@dp.message(F.text == "🆘 Поддержка")
async def support(message: Message):

    if await check_blocked(message):
        return

    builder = InlineKeyboardBuilder()

    builder.button(
        text="🆘 Написать в поддержку",
        url=f"https://t.me/{SUPPORT_USERNAME}"
    )

    await message.answer(
        "🆘 <b>ПОДДЕРЖКА ЛИСИ</b>\n"
        "━━━━━━━━━━━━━━\n\n"
        "Если у тебя возникла проблема или есть "
        "предложение — напиши нашей поддержке.\n\n"
        "👇 Нажми кнопку ниже.",
        parse_mode="HTML",
        reply_markup=builder.as_markup()
    )


# =========================================================
# ОЖИДАНИЕ ФОТО
# =========================================================

@dp.message(F.text)
async def waiting_for_photo(message: Message):

    if await check_blocked(message):
        return

    user = get_user(message.from_user.id)

    if not user:
        return

    if user[8] == "photo":

        await message.answer(
            "📸 Сейчас я жду твою фотографию.\n\n"
            "Просто отправь фото сюда."
        )


# =========================================================
# ЗАПУСК
# =========================================================

async def main():

    if not TOKEN:

        raise RuntimeError(
            "BOT_TOKEN не найден в Railway Variables."
        )

    init_db()

    bot = Bot(TOKEN)

    print("🦊 ЛИСИ запущен!")
    print(f"👑 ADMIN_ID: {ADMIN_ID}")

    await dp.start_polling(bot)


# =========================================================
# MAIN
# =========================================================

if __name__ == "__main__":
    asyncio.run(main())
