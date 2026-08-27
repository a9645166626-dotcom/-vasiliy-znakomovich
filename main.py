import os
import sqlite3
import asyncio

from aiogram import Bot, Dispatcher, F
from aiogram.filters import CommandStart
from aiogram.types import Message, CallbackQuery
from aiogram.utils.keyboard import InlineKeyboardBuilder

TOKEN = os.getenv("BOT_TOKEN")
DB = "dating.db"

dp = Dispatcher()


# =========================
# БАЗА ДАННЫХ
# =========================

def init_db():
    con = sqlite3.connect(DB)

    con.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY,
            name TEXT,
            age INTEGER,
            min_age INTEGER,
            max_age INTEGER,
            city TEXT,
            bio TEXT,
            photo TEXT,
            state TEXT
        )
    """)

    con.execute("""
        CREATE TABLE IF NOT EXISTS likes (
            from_id INTEGER,
            to_id INTEGER,
            UNIQUE(from_id, to_id)
        )
    """)

    con.execute("""
        CREATE TABLE IF NOT EXISTS reports (
            from_id INTEGER,
            to_id INTEGER
        )
    """)

    con.commit()
    con.close()


def get_user(user_id):
    con = sqlite3.connect(DB)

    user = con.execute(
        "SELECT * FROM users WHERE id=?",
        (user_id,)
    ).fetchone()

    con.close()

    return user


def save(user_id, field, value):
    con = sqlite3.connect(DB)

    con.execute(
        f"UPDATE users SET {field}=? WHERE id=?",
        (value, user_id)
    )

    con.commit()
    con.close()


# =========================
# КНОПКИ
# =========================

def main_menu():

    builder = InlineKeyboardBuilder()

    builder.button(
        text="🔎 Смотреть анкеты",
        callback_data="browse"
    )

    builder.button(
        text="👤 Моя анкета",
        callback_data="profile"
    )

    builder.button(
        text="💕 Мои мэтчи",
        callback_data="matches"
    )

    builder.adjust(1)

    return builder.as_markup()


def profile_buttons(user_id):

    builder = InlineKeyboardBuilder()

    builder.button(
        text="❤️ Нравится",
        callback_data=f"like:{user_id}"
    )

    builder.button(
        text="👎 Пропустить",
        callback_data=f"skip:{user_id}"
    )

    builder.button(
        text="🚫 Пожаловаться",
        callback_data=f"report:{user_id}"
    )

    builder.adjust(2, 1)

    return builder.as_markup()


# =========================
# START
# =========================

@dp.message(CommandStart())
async def start(message: Message):

    con = sqlite3.connect(DB)

    con.execute(
        """
        INSERT OR IGNORE INTO users(id, state)
        VALUES (?, ?)
        """,
        (message.from_user.id, "name")
    )

    con.commit()
    con.close()

    user = get_user(message.from_user.id)

    if user and user[1] and user[2]:

        await message.answer(
            "❤️ Василий Знакомович\n\n"
            "С возвращением!",
            reply_markup=main_menu()
        )

        return

    save(
        message.from_user.id,
        "state",
        "name"
    )

    await message.answer(
        "❤️ <b>Василий Знакомович</b>\n\n"
        "Создадим твою анкету.\n\n"
        "1️⃣ Как тебя зовут?",
        parse_mode="HTML"
    )


# =========================
# РЕГИСТРАЦИЯ
# =========================

@dp.message(F.text)
async def registration(message: Message):

    user = get_user(message.from_user.id)

    if not user:
        return

    state = user[8]

    # ИМЯ

    if state == "name":

        save(
            message.from_user.id,
            "name",
            message.text[:40]
        )

        save(
            message.from_user.id,
            "state",
            "age"
        )

        await message.answer(
            "2️⃣ Сколько тебе лет?"
        )

    # ВОЗРАСТ

    elif state == "age":

        try:

            age = int(message.text)

        except ValueError:

            await message.answer(
                "Напиши возраст числом."
            )

            return

        if age < 13 or age > 100:

            await message.answer(
                "Возраст должен быть от 13 до 100 лет."
            )

            return

        save(
            message.from_user.id,
            "age",
            age
        )

        save(
            message.from_user.id,
            "state",
            "min_age"
        )

        await message.answer(
            "3️⃣ С какого возраста ты хочешь видеть людей?\n\n"
            "Например: 16"
        )

    # МИНИМАЛЬНЫЙ ВОЗРАСТ

    elif state == "min_age":

        try:

            min_age = int(message.text)

        except ValueError:

            await message.answer(
                "Напиши число."
            )

            return

        user_age = user[2]

        if min_age < 13 or min_age > 100:

            await message.answer(
                "Возраст должен быть от 13 до 100."
            )

            return

        if user_age < 18 and min_age >= 18:

            await message.answer(
                "Для пользователей младше 18 лет можно выбирать только возраст до 17."
            )

            return

        if user_age >= 18 and min_age < 18:

            await message.answer(
                "Для пользователей 18+ можно выбирать только 18+."
            )

            return

        save(
            message.from_user.id,
            "min_age",
            min_age
        )

        save(
            message.from_user.id,
            "state",
            "max_age"
        )

        await message.answer(
            "4️⃣ До какого возраста ты хочешь видеть людей?\n\n"
            "Например: 25"
        )

    # МАКСИМАЛЬНЫЙ ВОЗРАСТ

    elif state == "max_age":

        try:

            max_age = int(message.text)

        except ValueError:

            await message.answer(
                "Напиши число."
            )

            return

        min_age = user[3]
        user_age = user[2]

        if max_age < min_age:

            await message.answer(
                "Максимальный возраст не может быть меньше минимального."
            )

            return

        if user_age < 18 and max_age >= 18:

            await message.answer(
                "Для пользователей младше 18 лет максимальный возраст — 17."
            )

            return

        if user_age >= 18 and max_age < 18:

            await message.answer(
                "Для пользователей 18+ минимальный возраст — 18."
            )

            return

        save(
            message.from_user.id,
            "max_age",
            max_age
        )

        save(
            message.from_user.id,
            "state",
            "city"
        )

        await message.answer(
            "5️⃣ В каком городе ты живёшь?"
        )

    # ГОРОД

    elif state == "city":

        save(
            message.from_user.id,
            "city",
            message.text[:50]
        )

        save(
            message.from_user.id,
            "state",
            "bio"
        )

        await message.answer(
            "6️⃣ Расскажи немного о себе."
        )

    # О СЕБЕ

    elif state == "bio":

        save(
            message.from_user.id,
            "bio",
            message.text[:500]
        )

        save(
            message.from_user.id,
            "state",
            "photo"
        )

        await message.answer(
            "7️⃣ Теперь отправь свою фотографию 📸"
        )

    # ГОТОВО

    elif state == "done":

        await message.answer(
            "Выбери действие:",
            reply_markup=main_menu()
        )


# =========================
# ФОТО
# =========================

@dp.message(F.photo)
async def photo(message: Message):

    user = get_user(message.from_user.id)

    if not user:
        return

    if user[8] != "photo":
        return

    photo_id = message.photo[-1].file_id

    save(
        message.from_user.id,
        "photo",
        photo_id
    )

    save(
        message.from_user.id,
        "state",
        "done"
    )

    await message.answer(
        "🎉 <b>Анкета готова!</b>\n\n"
        "Теперь можно смотреть анкеты.",
        parse_mode="HTML",
        reply_markup=main_menu()
    )


# =========================
# МОЯ АНКЕТА
# =========================

@dp.callback_query(F.data == "profile")
async def profile(callback: CallbackQuery):

    user = get_user(callback.from_user.id)

    if not user or not user[1]:

        await callback.message.answer(
            "Сначала создай анкету через /start."
        )

        await callback.answer()

        return

    _, uid, name, age, min_age, max_age, city, bio, photo, state = user

    text = (
        f"👤 <b>{name}</b>, {age}\n"
        f"📍 {city}\n"
        f"🔎 Ищу: {min_age}–{max_age}\n\n"
        f"{bio or 'Без описания'}"
    )

    if photo:

        await callback.message.answer_photo(
            photo,
            caption=text,
            parse_mode="HTML"
        )

    else:

        await callback.message.answer(
            text,
            parse_mode="HTML"
        )

    await callback.answer()


# =========================
# ПОИСК АНКЕТ
# =========================

@dp.callback_query(F.data == "browse")
async def browse(callback: CallbackQuery):

    me = get_user(callback.from_user.id)

    if not me or me[8] != "done":

        await callback.message.answer(
            "Сначала создай анкету через /start."
        )

        await callback.answer()

        return

    my_age = me[2]
    min_age = me[3]
    max_age = me[4]

    # Разделяем несовершеннолетних и взрослых

    if my_age < 18:

        min_allowed = 13
        max_allowed = 17

    else:

        min_allowed = 18
        max_allowed = 100

    min_search = max(min_age, min_allowed)
    max_search = min(max_age, max_allowed)

    con = sqlite3.connect(DB)

    user = con.execute(
        """
        SELECT *
        FROM users
        WHERE id != ?
        AND state = 'done'
        AND age BETWEEN ? AND ?
        AND id NOT IN (
            SELECT to_id
            FROM likes
            WHERE from_id = ?
        )
        ORDER BY RANDOM()
        LIMIT 1
        """,
        (
            callback.from_user.id,
            min_search,
            max_search,
            callback.from_user.id
        )
    ).fetchone()

    con.close()

    if not user:

        await callback.message.answer(
            "😔 Пока подходящих анкет нет.\n\n"
            "Попробуй зайти позже."
        )

        await callback.answer()

        return

    _, uid, name, age, umin, umax, city, bio, photo, state = user

    text = (
        f"👤 <b>{name}</b>, {age}\n"
        f"📍 {city}\n\n"
        f"{bio or 'Без описания'}"
    )

    if photo:

        await callback.message.answer_photo(
            photo,
            caption=text,
            parse_mode="HTML",
            reply_markup=profile_buttons(uid)
        )

    else:

        await callback.message.answer(
            text,
            parse_mode="HTML",
            reply_markup=profile_buttons(uid)
        )

    await callback.answer()


# =========================
# ЛАЙК
# =========================

@dp.callback_query(F.data.startswith("like:"))
async def like(callback: CallbackQuery):

    target = int(
        callback.data.split(":")[1]
    )

    me = callback.from_user.id

    con = sqlite3.connect(DB)

    con.execute(
        """
        INSERT OR IGNORE INTO likes(from_id, to_id)
        VALUES (?, ?)
        """,
        (me, target)
    )

    mutual = con.execute(
        """
        SELECT 1
        FROM likes
        WHERE from_id = ?
        AND to_id = ?
        """,
        (target, me)
    ).fetchone()

    target_user = con.execute(
        "SELECT name FROM users WHERE id=?",
        (target,)
    ).fetchone()

    con.commit()
    con.close()

    await callback.answer("❤️ Лайк!")

    if mutual:

        await callback.message.answer(
            f"💕 <b>Мэтч!</b>\n\n"
            f"Вы понравились друг другу с "
            f"<b>{target_user[0]}</b>!",
            parse_mode="HTML"
        )

        try:

            await callback.bot.send_message(
                target,
                "💕 У тебя новый взаимный лайк!"
            )

        except Exception:
            pass

    await browse(callback)


# =========================
# ПРОПУСК
# =========================

@dp.callback_query(F.data.startswith("skip:"))
async def skip(callback: CallbackQuery):

    await callback.answer(
        "👎 Пропущено"
    )

    await browse(callback)


# =========================
# ЖАЛОБА
# =========================

@dp.callback_query(F.data.startswith("report:"))
async def report(callback: CallbackQuery):

    target = int(
        callback.data.split(":")[1]
    )

    con = sqlite3.connect(DB)

    con.execute(
        """
        INSERT INTO reports(from_id, to_id)
        VALUES (?, ?)
        """,
        (callback.from_user.id, target)
    )

    con.commit()
    con.close()

    await callback.answer(
        "Жалоба отправлена"
    )

    await callback.message.answer(
        "🚨 Жалоба зарегистрирована."
    )

    await browse(callback)


# =========================
# МЭТЧИ
# =========================

@dp.callback_query(F.data == "matches")
async def matches(callback: CallbackQuery):

    con = sqlite3.connect(DB)

    rows = con.execute(
        """
        SELECT u.name, u.age, u.city
        FROM users u
        JOIN likes l1
            ON l1.to_id = u.id
        JOIN likes l2
            ON l2.from_id = u.id
            AND l2.to_id = ?
        WHERE l1.from_id = ?
        """,
        (
            callback.from_user.id,
            callback.from_user.id
        )
    ).fetchall()

    con.close()

    if not rows:

        await callback.message.answer(
            "💕 Пока взаимных симпатий нет."
        )

    else:

        text = "💕 <b>Твои мэтчи:</b>\n\n"

        for name, age, city in rows:

            text += (
                f"👤 {name}, {age}\n"
                f"📍 {city}\n\n"
            )

        await callback.message.answer(
            text,
            parse_mode="HTML"
        )

    await callback.answer()


# =========================
# ЗАПУСК
# =========================

async def main():

    if not TOKEN:

        raise RuntimeError(
            "BOT_TOKEN не найден."
        )

    init_db()

    bot = Bot(TOKEN)

    await dp.start_polling(bot)


if __name__ == "__main__":

    asyncio.run(main())
