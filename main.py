import os
import sqlite3
import asyncio
import html

from aiogram import Bot, Dispatcher, F
from aiogram.filters import CommandStart
from aiogram.types import (
    Message,
    CallbackQuery,
    ReplyKeyboardMarkup,
    KeyboardButton,
)
from aiogram.utils.keyboard import InlineKeyboardBuilder


# =========================================================
# НАСТРОЙКИ
# =========================================================

TOKEN = os.getenv("BOT_TOKEN")

SUPPORT_USERNAME = "LISI_SUPPORT"

DB_NAME = "lisi.db"

dp = Dispatcher()


# =========================================================
# БАЗА ДАННЫХ
# =========================================================

def get_db():
    return sqlite3.connect(DB_NAME)


def init_db():
    con = get_db()
    cur = con.cursor()

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

    cur.execute("""
        CREATE TABLE IF NOT EXISTS likes (
            from_id INTEGER,
            to_id INTEGER,
            UNIQUE(from_id, to_id)
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS passes (
            from_id INTEGER,
            to_id INTEGER,
            UNIQUE(from_id, to_id)
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS reports (
            from_id INTEGER,
            to_id INTEGER,
            UNIQUE(from_id, to_id)
        )
    """)

    con.commit()
    con.close()


def get_user(user_id):
    con = get_db()

    user = con.execute(
        "SELECT * FROM users WHERE id = ?",
        (user_id,)
    ).fetchone()

    con.close()

    return user


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
        f"UPDATE users SET {field} = ? WHERE id = ?",
        (value, user_id)
    )

    con.commit()
    con.close()


# =========================================================
# ГЛАВНОЕ МЕНЮ
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
# INLINE-КНОПКИ
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


def support_keyboard():

    builder = InlineKeyboardBuilder()

    builder.button(
        text="🆘 Написать в поддержку",
        url=f"https://t.me/{SUPPORT_USERNAME}"
    )

    return builder.as_markup()


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
# START
# =========================================================

@dp.message(CommandStart())
async def start(message: Message):

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
            "Здесь можно находить людей для общения.\n\n"
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

    state = user[8]

    if state == "gender":

        await message.answer(
            "🦊 <b>Кто ты?</b>\n\n"
            "Выбери свой пол:",
            parse_mode="HTML",
            reply_markup=gender_keyboard()
        )

        return

    if state == "looking":

        await message.answer(
            "🦊 <b>Кого хочешь видеть?</b>\n\n"
            "Выбери вариант:",
            parse_mode="HTML",
            reply_markup=looking_keyboard()
        )

        return

    texts = {
        "name": "Как тебя зовут?",
        "age": "Сколько тебе лет?",
        "city": "В каком городе ты живёшь?",
        "bio": "Расскажи немного о себе.",
        "photo": "Отправь свою фотографию.",
    }

    await message.answer(
        "🦊 <b>Продолжим создание анкеты.</b>\n\n"
        + texts.get(state, "Продолжим."),
        parse_mode="HTML"
    )


# =========================================================
# МОЯ АНКЕТА
# =========================================================

async def show_my_profile(message: Message):

    user = get_user(message.from_user.id)

    if not user:

        await message.answer(
            "🦊 У тебя пока нет анкеты.\n\n"
            "Нажми /start, чтобы создать её."
        )

        return

    if user[8] != "done":

        await message.answer(
            "🦊 Твоя анкета ещё не создана полностью.\n\n"
            "Нажми /start и закончи регистрацию."
        )

        return

    (
        uid,
        telegram_id,
        name,
        age,
        gender,
        looking,
        city,
        bio,
        photo,
        state
    ) = user

    gender_text = (
        "♂️ Мужской"
        if gender == "male"
        else "♀️ Женский"
    )

    if looking == "male":
        looking_text = "♂️ Мужчин"
    elif looking == "female":
        looking_text = "♀️ Женщин"
    else:
        looking_text = "👥 Всех"

    safe_name = html.escape(str(name))
    safe_city = html.escape(str(city))
    safe_bio = (
        html.escape(str(bio))
        if bio
        else "Без описания"
    )

    text = (
        f"🦊 <b>{safe_name}</b>, {age}\n"
        f"━━━━━━━━━━━━━━\n\n"
        f"{gender_text}\n"
        f"🔎 Ищу: {looking_text}\n"
        f"📍 {safe_city}\n\n"
        f"💬 {safe_bio}\n\n"
        f"━━━━━━━━━━━━━━"
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
# КНОПКА МОЯ АНКЕТА
# =========================================================

@dp.message(F.text == "👤 Моя анкета")
async def my_profile_button(message: Message):

    await show_my_profile(message)


# =========================================================
# ПОКАЗ АНКЕТ
# =========================================================

async def show_profile(message: Message, user_id: int):

    me = get_user(user_id)

    if not me or me[8] != "done":

        await message.answer(
            "🦊 Сначала создай анкету через /start."
        )

        return

    my_age = me[2]
    looking_for = me[4]
    my_city = me[5]

    # Возрастная категория
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

    # Фильтр пола
    if looking_for != "all":

        query += """
            AND gender = ?
        """

        params.append(looking_for)

    # Уже просмотренные анкеты
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
            "🦊 <b>Подходящих анкет пока нет</b>\n"
            "━━━━━━━━━━━━━━\n\n"
            f"📍 Город: <b>{html.escape(str(my_city))}</b>\n\n"
            "Мы показываем анкеты из твоего города\n"
            "и подходящей возрастной категории.\n\n"
            "Попробуй зайти позже 🧡",
            parse_mode="HTML"
        )

        return

    (
        uid,
        telegram_id,
        name,
        age,
        gender,
        looking,
        city,
        bio,
        photo,
        state
    ) = person

    safe_name = html.escape(str(name))
    safe_city = html.escape(str(city))

    safe_bio = (
        html.escape(str(bio))
        if bio
        else "Пока ничего не рассказал(а)."
    )

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
# КНОПКА СМОТРЕТЬ АНКЕТЫ
# =========================================================

@dp.message(F.text == "🦊 Смотреть анкеты")
async def browse_button(message: Message):

    await show_profile(
        message,
        message.from_user.id
    )


# =========================================================
# МОИ ЛАЙКИ
# =========================================================

@dp.message(F.text == "❤️ Мои лайки")
async def likes_button(message: Message):

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
            f"🦊 <b>{html.escape(str(name))}</b>, {age}\n"
            f"📍 {html.escape(str(city))}\n\n"
        )

    await message.answer(
        text,
        parse_mode="HTML"
    )


# =========================================================
# МЭТЧИ
# =========================================================

@dp.message(F.text == "💕 Мои мэтчи")
async def matches_button(message: Message):

    my_id = message.from_user.id

    con = get_db()

    rows = con.execute(
        """
        SELECT DISTINCT u.id, u.name, u.age, u.city
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
            f"🧡 <b>{html.escape(str(name))}</b>, {age}\n"
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
async def settings_button(message: Message):

    await message.answer(
        "⚙️ <b>НАСТРОЙКИ ЛИСИ</b>\n"
        "━━━━━━━━━━━━━━\n\n"
        "Фильтры поиска работают автоматически:\n\n"
        "📍 твой город\n"
        "🎂 возрастная категория\n"
        "👤 выбранный пол\n\n"
        "Также можно пересоздать анкету.",
        parse_mode="HTML",
        reply_markup=settings_keyboard()
    )


# =========================================================
# ПОДДЕРЖКА
# =========================================================

@dp.message(F.text == "🆘 Поддержка")
async def support_button(message: Message):

    await message.answer(
        "🆘 <b>ПОДДЕРЖКА ЛИСИ</b>\n"
        "━━━━━━━━━━━━━━\n\n"
        "Если возникла проблема или есть предложение,\n"
        "напиши нашей поддержке.\n\n"
        "👇 Нажми кнопку ниже.",
        parse_mode="HTML",
        reply_markup=support_keyboard()
    )


# =========================================================
# ПЕРЕСОЗДАТЬ АНКЕТУ
# =========================================================

@dp.callback_query(F.data == "restart_profile")
async def restart_profile(callback: CallbackQuery):

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
# ЗАКРЫТЬ НАСТРОЙКИ
# =========================================================

@dp.callback_query(F.data == "close_settings")
async def close_settings(callback: CallbackQuery):

    try:
        await callback.message.delete()
    except Exception:
        pass

    await callback.answer()


# =========================================================
# ВЫБОР ПОЛА
# =========================================================

@dp.callback_query(F.data.startswith("gender:"))
async def choose_gender(callback: CallbackQuery):

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
        "🔎 <b>Кого хочешь видеть?</b>\n\n"
        "Выбери вариант:",
        parse_mode="HTML",
        reply_markup=looking_keyboard()
    )

    await callback.answer()


# =========================================================
# КОГО ИЩЕТ
# =========================================================

@dp.callback_query(F.data.startswith("looking:"))
async def choose_looking(callback: CallbackQuery):

    looking = callback.data.split(":")[1]

    user = get_user(callback.from_user.id)

    if not user:

        await callback.answer(
            "Ошибка. Напиши /start",
            show_alert=True
        )

        return

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
        "🦊 <b>ШАГ 5 / 7</b>\n"
        "━━━━━━━━━━━━━━\n\n"
        "📍 <b>В каком городе ты живёшь?</b>\n\n"
        "Укажи свой город.",
        parse_mode="HTML"
    )

    await callback.answer()


# =========================================================
# ЛАЙК
# =========================================================

@dp.callback_query(F.data.startswith("like:"))
async def like_profile(callback: CallbackQuery):

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
        INSERT OR IGNORE INTO likes(from_id, to_id)
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

    if mutual and target:

        target_name = html.escape(
            str(target[0])
        )

        try:
            target_chat = await callback.bot.get_chat(target_id)
            target_username = target_chat.username
        except Exception:
            target_username = None

        try:
            my_chat = await callback.bot.get_chat(my_id)
            my_username = my_chat.username
        except Exception:
            my_username = None

        if target_username:

            await callback.message.answer(
                "💕 <b>МЭТЧ!</b>\n"
                "━━━━━━━━━━━━━━\n\n"
                f"Вы понравились друг другу с "
                f"<b>{target_name}</b>! 🧡\n\n"
                "Теперь можно открыть Telegram-профиль.",
                parse_mode="HTML",
                reply_markup=match_keyboard(
                    target_username
                )
            )

        else:

            await callback.message.answer(
                "💕 <b>МЭТЧ!</b>\n"
                "━━━━━━━━━━━━━━\n\n"
                f"Вы понравились друг другу с "
                f"<b>{target_name}</b>! 🧡\n\n"
                "У пользователя скрыт username Telegram.",
                parse_mode="HTML"
            )

        try:

            if my_username:

                await callback.bot.send_message(
                    target_id,
                    "💕 <b>У тебя новый мэтч!</b>\n"
                    "━━━━━━━━━━━━━━\n\n"
                    "Вы понравились друг другу 🧡\n\n"
                    "Можно открыть профиль человека.",
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

    target_id = int(
        callback.data.split(":")[1]
    )

    my_id = callback.from_user.id

    con = get_db()

    con.execute(
        """
        INSERT OR IGNORE INTO passes(from_id, to_id)
        VALUES (?, ?)
        """,
        (my_id, target_id)
    )

    con.commit()
    con.close()

    await callback.answer("👋 Пропущено")

    await show_profile(
        callback.message,
        my_id
    )


# =========================================================
# ЖАЛОБА
# =========================================================

@dp.callback_query(F.data.startswith("report:"))
async def report_profile(callback: CallbackQuery):

    target_id = int(
        callback.data.split(":")[1]
    )

    my_id = callback.from_user.id

    con = get_db()

    con.execute(
        """
        INSERT OR IGNORE INTO reports(from_id, to_id)
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
# РЕГИСТРАЦИЯ — ИМЯ / ВОЗРАСТ / ГОРОД / BIO
# =========================================================

@dp.message(F.text)
async def registration(message: Message):

    text = message.text.strip()

    # Эти кнопки уже обработаны отдельными
    # обработчиками выше.
    menu_buttons = {
        "🦊 Смотреть анкеты",
        "👤 Моя анкета",
        "❤️ Мои лайки",
        "💕 Мои мэтчи",
        "⚙️ Настройки",
        "🆘 Поддержка",
    }

    if text in menu_buttons:
        return

    user = get_user(message.from_user.id)

    if not user:
        return

    state = user[8]

    # =====================================================
    # ИМЯ
    # =====================================================

    if state == "name":

        if len(text) < 2:

            await message.answer(
                "🦊 Имя должно содержать хотя бы 2 символа."
            )

            return

        if len(text) > 40:

            await message.answer(
                "🦊 Имя слишком длинное.\n"
                "Максимум 40 символов."
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

    # =====================================================
    # ВОЗРАСТ
    # =====================================================

    if state == "age":

        try:
            age = int(text)
        except ValueError:

            await message.answer(
                "🦊 Напиши возраст числом."
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

    # =====================================================
    # ГОРОД
    # =====================================================

    if state == "city":

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
            "Напиши пару слов.",
            parse_mode="HTML"
        )

        return

    # =====================================================
    # BIO
    # =====================================================

    if state == "bio":

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
# ФОТО
# =========================================================

@dp.message(F.photo)
async def receive_photo(message: Message):

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
        "🧡 Всё готово.\n\n"
        "Теперь можно смотреть анкеты,\n"
        "ставить лайки и находить мэтчи.\n\n"
        "👇 Выбирай действие:",
        parse_mode="HTML",
        reply_markup=main_keyboard()
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

    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
