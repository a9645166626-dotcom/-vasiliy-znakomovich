import os
import sqlite3
import asyncio

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
# ЛИСИ 🦊
# =========================================================

TOKEN = os.getenv("BOT_TOKEN")
DB_NAME = "lisi.db"

# USERNAME ПОДДЕРЖКИ
SUPPORT_USERNAME = "lis_support"

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
            username TEXT,
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

    # Если база была создана старой версией —
    # добавляем username отдельно
    try:
        cur.execute("ALTER TABLE users ADD COLUMN username TEXT")
        con.commit()
    except sqlite3.OperationalError:
        pass

    con.close()


def get_user(user_id):
    con = get_db()

    user = con.execute(
        "SELECT * FROM users WHERE id=?",
        (user_id,)
    ).fetchone()

    con.close()

    return user


def set_value(user_id, field, value):
    allowed_fields = {
        "username",
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
        f"UPDATE users SET {field}=? WHERE id=?",
        (value, user_id)
    )

    con.commit()
    con.close()


# =========================================================
# НИЖНЕЕ МЕНЮ
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


# =========================================================
# START
# =========================================================

@dp.message(CommandStart())
async def start(message: Message):

    user = get_user(message.from_user.id)

    username = message.from_user.username

    if not user:

        con = get_db()

        con.execute(
            """
            INSERT INTO users(id, username, state)
            VALUES (?, ?, 'name')
            """,
            (
                message.from_user.id,
                username
            )
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

    # Обновляем username
    set_value(
        message.from_user.id,
        "username",
        username
    )

    if user[9] == "done":

        await message.answer(
            "🦊 <b>ЛИСИ</b>\n"
            "━━━━━━━━━━━━━━\n\n"
            "С возвращением 🧡\n\n"
            "Выбирай действие в меню ниже.",
            parse_mode="HTML",
            reply_markup=main_keyboard()
        )

        return

    await message.answer(
        "🦊 <b>Продолжим создание анкеты.</b>\n\n"
        "Как тебя зовут?",
        parse_mode="HTML"
    )


# =========================================================
# ТЕКСТОВАЯ РЕГИСТРАЦИЯ
# =========================================================

@dp.message(F.text)
async def registration(message: Message):

    text = message.text

    menu_buttons = [
        "🦊 Смотреть анкеты",
        "👤 Моя анкета",
        "❤️ Мои лайки",
        "💕 Мои мэтчи",
        "⚙️ Настройки",
        "🆘 Поддержка",
    ]

    if text in menu_buttons:
        return

    user = get_user(message.from_user.id)

    if not user:
        return

    state = user[9]

    # =====================================================
    # ИМЯ
    # =====================================================

    if state == "name":

        if len(text) > 40:

            await message.answer(
                "🦊 Имя слишком длинное.\n\n"
                "Напиши покороче."
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

    # =====================================================
    # ВОЗРАСТ
    # =====================================================

    elif state == "age":

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

    # =====================================================
    # ГОРОД
    # =====================================================

    elif state == "city":

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

    # =====================================================
    # BIO
    # =====================================================

    elif state == "bio":

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
            "📸 <b>Теперь отправь свою фотографию.</b>\n\n"
            "Лучше всего — обычное фото, где хорошо видно лицо.",
            parse_mode="HTML"
        )


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

    age = user[3]

    if age < 18:

        text = (
            "🦊 <b>ШАГ 5 / 7</b>\n"
            "━━━━━━━━━━━━━━\n\n"
            "📍 <b>В каком городе ты живёшь?</b>\n\n"
            "Тебе будут показываться только "
            "пользователи младше 18 лет."
        )

    else:

        text = (
            "🦊 <b>ШАГ 5 / 7</b>\n"
            "━━━━━━━━━━━━━━\n\n"
            "📍 <b>В каком городе ты живёшь?</b>\n\n"
            "Тебе будут показываться только "
            "пользователи 18+."
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

    user = get_user(message.from_user.id)

    if not user:
        return

    if user[9] != "photo":
        return

    photo_id = message.photo[-1].file_id

    set_value(
        message.from_user.id,
        "photo",
        photo_id
    )

    set_value(
        message.from_user.id,
        "username",
        message.from_user.username
    )

    set_value(
        message.from_user.id,
        "state",
        "done"
    )

    await message.answer(
        "🦊 <b>АНКЕТА ГОТОВА</b>\n"
        "━━━━━━━━━━━━━━\n\n"
        "🧡 Добро пожаловать в ЛИСИ.\n\n"
        "Теперь можно смотреть анкеты,\n"
        "ставить лайки и находить мэтчи.\n\n"
        "👇 Всё управление находится в меню.",
        parse_mode="HTML",
        reply_markup=main_keyboard()
    )


# =========================================================
# ПОКАЗ АНКЕТ
# =========================================================

async def show_profile(message_or_callback, user_id):

    me = get_user(user_id)

    if not me or me[9] != "done":

        target = (
            message_or_callback.message
            if isinstance(message_or_callback, CallbackQuery)
            else message_or_callback
        )

        await target.answer(
            "🦊 Сначала создай анкету через /start."
        )

        return

    my_age = me[3]
    looking_for = me[5]
    my_city = me[6]

    # =====================================================
    # ВОЗРАСТОВОЙ ФИЛЬТР
    # =====================================================

    if my_age < 18:

        min_age = 13
        max_age = 17

    else:

        min_age = 18
        max_age = 100

    con = get_db()

    # =====================================================
    # ПОЛ + ГОРОД + ВОЗРАСТ
    # =====================================================

    base_query = """
        SELECT *
        FROM users
        WHERE id != ?
        AND state = 'done'
        AND age BETWEEN ? AND ?
        AND LOWER(TRIM(city)) = LOWER(TRIM(?))
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
    """

    params = [
        user_id,
        min_age,
        max_age,
        my_city,
        user_id,
        user_id,
        user_id,
    ]

    if looking_for != "all":

        base_query += """
            AND gender = ?
        """

        params.append(looking_for)

    base_query += """
        ORDER BY RANDOM()
        LIMIT 1
    """

    person = con.execute(
        base_query,
        params
    ).fetchone()

    con.close()

    # =====================================================
    # НЕТ АНКЕТ
    # =====================================================

    if not person:

        target = (
            message_or_callback.message
            if isinstance(message_or_callback, CallbackQuery)
            else message_or_callback
        )

        await target.answer(
            "🦊 <b>Пока подходящих анкет нет</b>\n"
            "━━━━━━━━━━━━━━\n\n"
            "😔 В твоём городе пока не нашлось "
            "подходящих анкет.\n\n"
            "Попробуй зайти немного позже.",
            parse_mode="HTML"
        )

        return

    (
        uid,
        username,
        name,
        age,
        gender,
        looking,
        city,
        bio,
        photo,
        state
    ) = person

    text = (
        f"🦊 <b>{name}</b>, {age}\n"
        f"━━━━━━━━━━━━━━\n\n"
        f"📍 {city}\n\n"
        f"💬 {bio or 'Пока ничего не рассказал(а).'}\n\n"
        f"━━━━━━━━━━━━━━\n"
        f"🧡 Что скажешь?"
    )

    target = (
        message_or_callback.message
        if isinstance(message_or_callback, CallbackQuery)
        else message_or_callback
    )

    if photo:

        await target.answer_photo(
            photo=photo,
            caption=text,
            parse_mode="HTML",
            reply_markup=profile_keyboard(uid)
        )

    else:

        await target.answer(
            text,
            parse_mode="HTML",
            reply_markup=profile_keyboard(uid)
        )


# =========================================================
# 🦊 СМОТРЕТЬ АНКЕТЫ
# =========================================================

@dp.message(F.text == "🦊 Смотреть анкеты")
async def browse_message(message: Message):

    await show_profile(
        message,
        message.from_user.id
    )


# =========================================================
# 👤 МОЯ АНКЕТА
# =========================================================

@dp.message(F.text == "👤 Моя анкета")
async def my_profile(message: Message):

    user = get_user(message.from_user.id)

    if not user or user[9] != "done":

        await message.answer(
            "🦊 Сначала создай анкету через /start."
        )

        return

    (
        uid,
        username,
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

    username_text = (
        f"@{username}"
        if username
        else "Не указан"
    )

    text = (
        f"🦊 <b>{name}</b>, {age}\n"
        f"━━━━━━━━━━━━━━\n\n"
        f"{gender_text}\n"
        f"🔎 Ищу: {looking_text}\n"
        f"📍 {city}\n"
        f"👤 {username_text}\n\n"
        f"💬 {bio or 'Без описания'}"
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
# ❤️ МОИ ЛАЙКИ
# =========================================================

@dp.message(F.text == "❤️ Мои лайки")
async def my_likes(message: Message):

    con = get_db()

    rows = con.execute(
        """
        SELECT
            u.name,
            u.age,
            u.city,
            u.username
        FROM likes l
        JOIN users u
        ON u.id = l.to_id
        WHERE l.from_id = ?
        """,
        (message.from_user.id,)
    ).fetchall()

    con.close()

    if not rows:

        await message.answer(
            "❤️ <b>МОИ ЛАЙКИ</b>\n"
            "━━━━━━━━━━━━━━\n\n"
            "Пока ты никого не лайкнул(а).",
            parse_mode="HTML"
        )

        return

    text = (
        "❤️ <b>МОИ ЛАЙКИ</b>\n"
        "━━━━━━━━━━━━━━\n\n"
    )

    for name, age, city, username in rows:

        username_text = (
            f"@{username}"
            if username
            else "username не указан"
        )

        text += (
            f"🦊 <b>{name}</b>, {age}\n"
            f"📍 {city}\n"
            f"👤 {username_text}\n\n"
        )

    await message.answer(
        text,
        parse_mode="HTML"
    )


# =========================================================
# 💕 МЭТЧИ
# =========================================================

@dp.message(F.text == "💕 Мои мэтчи")
async def my_matches(message: Message):

    con = get_db()

    rows = con.execute(
        """
        SELECT
            u.id,
            u.name,
            u.age,
            u.city,
            u.username
        FROM users u
        JOIN likes a
        ON a.to_id = u.id
        JOIN likes b
        ON b.from_id = u.id
        WHERE a.from_id = ?
        AND b.to_id = ?
        """,
        (
            message.from_user.id,
            message.from_user.id
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

    for uid, name, age, city, username in rows:

        username_text = (
            f"@{username}"
            if username
            else "username не указан"
        )

        text += (
            f"🧡 <b>{name}</b>, {age}\n"
            f"📍 {city}\n"
            f"👤 {username_text}\n\n"
        )

    await message.answer(
        text,
        parse_mode="HTML"
    )


# =========================================================
# ❤️ ЛАЙК
# =========================================================

@dp.callback_query(F.data.startswith("like:"))
async def like(callback: CallbackQuery):

    target_id = int(
        callback.data.split(":")[1]
    )

    my_id = callback.from_user.id

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
        WHERE from_id=?
        AND to_id=?
        """,
        (target_id, my_id)
    ).fetchone()

    target = con.execute(
        """
        SELECT name, username
        FROM users
        WHERE id=?
        """,
        (target_id,)
    ).fetchone()

    con.commit()
    con.close()

    await callback.answer("❤️ Лайк!")

    if mutual and target:

        name = target[0]
        username = target[1]

        if username:

            profile_link = f"https://t.me/{username}"

            match_text = (
                "💕 <b>МЭТЧ!</b>\n"
                "━━━━━━━━━━━━━━\n\n"
                f"Вы понравились друг другу с "
                f"<b>{name}</b>!\n\n"
                "Теперь вы можете связаться друг с другом 👇"
            )

            builder = InlineKeyboardBuilder()

            builder.button(
                text="💬 Открыть профиль",
                url=profile_link
            )

            markup = builder.as_markup()

        else:

            match_text = (
                "💕 <b>МЭТЧ!</b>\n"
                "━━━━━━━━━━━━━━\n\n"
                f"Вы понравились друг другу с "
                f"<b>{name}</b>!\n\n"
                "У пользователя не указан username."
            )

            markup = None

        await callback.message.answer(
            match_text,
            parse_mode="HTML",
            reply_markup=markup
        )

        try:

            await callback.bot.send_message(
                target_id,
                "💕 <b>У тебя новый мэтч!</b>\n\n"
                "Кто-то тоже поставил тебе ❤️",
                parse_mode="HTML"
            )

        except Exception:
            pass

    await show_profile(
        callback,
        my_id
    )


# =========================================================
# 👎 ПРОПУСК
# =========================================================

@dp.callback_query(F.data.startswith("pass:"))
async def pass_profile(callback: CallbackQuery):

    target_id = int(
        callback.data.split(":")[1]
    )

    con = get_db()

    con.execute(
        """
        INSERT OR IGNORE INTO passes(from_id, to_id)
        VALUES (?, ?)
        """,
        (
            callback.from_user.id,
            target_id
        )
    )

    con.commit()
    con.close()

    await callback.answer("👋 Пропущено")

    await show_profile(
        callback,
        callback.from_user.id
    )


# =========================================================
# 🚨 ЖАЛОБА
# =========================================================

@dp.callback_query(F.data.startswith("report:"))
async def report(callback: CallbackQuery):

    target_id = int(
        callback.data.split(":")[1]
    )

    con = get_db()

    con.execute(
        """
        INSERT OR IGNORE INTO reports(from_id, to_id)
        VALUES (?, ?)
        """,
        (
            callback.from_user.id,
            target_id
        )
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
        callback,
        callback.from_user.id
    )


# =========================================================
# ⚙️ НАСТРОЙКИ
# =========================================================

@dp.message(F.text == "⚙️ Настройки")
async def settings(message: Message):

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

    await message.answer(
        "⚙️ <b>НАСТРОЙКИ</b>\n"
        "━━━━━━━━━━━━━━\n\n"
        "🔄 Пересоздать анкету\n\n"
        "В будущем сюда можно добавить "
        "дополнительные фильтры и настройки.",
        parse_mode="HTML",
        reply_markup=builder.as_markup()
    )


# =========================================================
# ЗАКРЫТЬ НАСТРОЙКИ
# =========================================================

@dp.callback_query(F.data == "close_settings")
async def close_settings(callback: CallbackQuery):

    await callback.message.delete()

    await callback.answer()


# =========================================================
# ПЕРЕСОЗДАТЬ АНКЕТУ
# =========================================================

@dp.callback_query(F.data == "restart_profile")
async def restart_profile(callback: CallbackQuery):

    con = get_db()

    con.execute(
        """
        UPDATE users
        SET name=NULL,
            age=NULL,
            gender=NULL,
            looking_for=NULL,
            city=NULL,
            bio=NULL,
            photo=NULL,
            state='name'
        WHERE id=?
        """,
        (callback.from_user.id,)
    )

    con.commit()
    con.close()

    await callback.message.answer(
        "🦊 <b>Начинаем заново.</b>\n\n"
        "Как тебя зовут?",
        parse_mode="HTML"
    )

    await callback.answer()


# =========================================================
# 🆘 ПОДДЕРЖКА
# =========================================================

@dp.message(F.text == "🆘 Поддержка")
async def support(message: Message):

    builder = InlineKeyboardBuilder()

    builder.button(
        text="🆘 Написать в поддержку",
        url=f"https://t.me/{SUPPORT_USERNAME}"
    )

    await message.answer(
        "🆘 <b>ПОДДЕРЖКА ЛИСИ</b>\n"
        "━━━━━━━━━━━━━━\n\n"
        "Если у тебя возникла проблема, "
        "вопрос или есть предложение — "
        "напиши нашей поддержке.\n\n"
        "Мы постараемся помочь 🦊",
        parse_mode="HTML",
        reply_markup=builder.as_markup()
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
