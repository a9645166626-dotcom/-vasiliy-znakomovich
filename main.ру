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


def db():
    return sqlite3.connect(DB)


def init_db():
    con = db()

    con.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY,
            name TEXT,
            age INTEGER,
            gender TEXT,
            looking_for TEXT,
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
            to_id INTEGER,
            UNIQUE(from_id, to_id)
        )
    """)

    con.commit()
    con.close()


def get_user(user_id):
    con = db()
    user = con.execute(
        "SELECT * FROM users WHERE id=?",
        (user_id,)
    ).fetchone()
    con.close()
    return user


def save(user_id, field, value):
    con = db()
    con.execute(
        f"UPDATE users SET {field}=? WHERE id=?",
        (value, user_id)
    )
    con.commit()
    con.close()


def menu():
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


def gender_keyboard():
    builder = InlineKeyboardBuilder()

    builder.button(
        text="👨 Мужской",
        callback_data="gender_male"
    )

    builder.button(
        text="👩 Женский",
        callback_data="gender_female"
    )

    builder.adjust(1)

    return builder.as_markup()


def looking_keyboard():
    builder = InlineKeyboardBuilder()

    builder.button(
        text="👨 Мужчин",
        callback_data="looking_male"
    )

    builder.button(
        text="👩 Женщин",
        callback_data="looking_female"
    )

    builder.button(
        text="👥 Всех",
        callback_data="looking_all"
    )

    builder.adjust(1)

    return builder.as_markup()


def profile_keyboard(user_id):
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


@dp.message(CommandStart())
async def start(message: Message):
    con = db()

    con.execute(
        "INSERT OR IGNORE INTO users(id, state) VALUES (?, ?)",
        (message.from_user.id, "name")
    )

    con.commit()
    con.close()

    user = get_user(message.from_user.id)

    if user and user[1] and user[2] and user[3]:

        await message.answer(
            "❤️ <b>Василий Знакомович</b>\n\n"
            "С возвращением!",
            parse_mode="HTML",
            reply_markup=menu()
        )

        return

    save(message.from_user.id, "state", "name")

    await message.answer(
        "❤️ <b>Василий Знакомович</b>\n\n"
        "Создадим твою анкету.\n\n"
        "1️⃣ Как тебя зовут?",
        parse_mode="HTML"
    )


@dp.message(F.text)
async def registration(message: Message):

    user = get_user(message.from_user.id)

    if not user:
        return

    state = user[10]

    if state == "name":

        save(message.from_user.id, "name", message.text[:40])
        save(message.from_user.id, "state", "age")

        await message.answer(
            "2️⃣ Сколько тебе лет?"
        )

    elif state == "age":

        try:
            age = int(message.text)
        except ValueError:
            await message.answer("Напиши возраст числом.")
            return

        if age < 13 or age > 100:
            await message.answer(
                "Возраст должен быть от 13 до 100 лет."
            )
            return

        save(message.from_user.id, "age", age)
        save(message.from_user.id, "state", "gender")

        await message.answer(
            "3️⃣ Выбери свой пол:",
            reply_markup=gender_keyboard()
        )

    elif state == "min_age":

        try:
            value = int(message.text)
        except ValueError:
            await message.answer("Напиши возраст числом.")
            return

        user_age = user[2]

        if user_age < 18:
            if value < 13 or value > 17:
                await message.answer(
                    "Для пользователей младше 18 лет можно выбирать только возраст 13–17."
                )
                return
        else:
            if value < 18 or value > 100:
                await message.answer(
                    "Для пользователей 18+ можно выбирать только 18+."
                )
                return

        save(message.from_user.id, "min_age", value)
        save(message.from_user.id, "state", "max_age")

        await message.answer(
            "6️⃣ До какого возраста ищем?"
        )

    elif state == "max_age":

        try:
            value = int(message.text)
        except ValueError:
            await message.answer("Напиши возраст числом.")
            return

        min_age = user[5]
        user_age = user[2]

        if value < min_age:
            await message.answer(
                "Максимальный возраст не может быть меньше минимального."
            )
            return

        if user_age < 18 and value > 17:
            await message.answer(
                "Для пользователей младше 18 лет максимум — 17."
            )
            return

        if user_age >= 18 and value < 18:
            await message.answer(
                "Для пользователей 18+ минимум — 18."
            )
            return

        save(message.from_user.id, "max_age", value)
        save(message.from_user.id, "state", "city")

        await message.answer(
            "7️⃣ В каком городе ты живёшь?"
        )

    elif state == "city":

        save(message.from_user.id, "city", message.text[:50])
        save(message.from_user.id, "state", "bio")

        await message.answer(
            "8️⃣ Расскажи немного о себе."
        )

    elif state == "bio":

        save(message.from_user.id, "bio", message.text[:500])
        save(message.from_user.id, "state", "photo")

        await message.answer(
            "9️⃣ Теперь отправь свою фотографию 📸"
        )

    elif state == "done":

        await message.answer(
            "Выбери действие:",
            reply_markup=menu()
        )


@dp.callback_query(F.data.startswith("gender_"))
async def gender(callback: CallbackQuery):

    value = callback.data.replace("gender_", "")

    save(callback.from_user.id, "gender", value)
    save(callback.from_user.id, "state", "looking")

    await callback.message.answer(
        "4️⃣ Кого ты хочешь видеть?",
        reply_markup=looking_keyboard()
    )

    await callback.answer()


@dp.callback_query(F.data.startswith("looking_"))
async def looking(callback: CallbackQuery):

    value = callback.data.replace("looking_", "")

    save(callback.from_user.id, "looking_for", value)
    save(callback.from_user.id, "state", "min_age")

    user = get_user(callback.from_user.id)

    if user[2] < 18:
        text = (
            "5️⃣ С какого возраста ищем?\n\n"
            "Можно выбирать только 13–17."
        )
    else:
        text = (
            "5️⃣ С какого возраста ищем?\n\n"
            "Можно выбирать только 18+."
        )

    await callback.message.answer(text)

    await callback.answer()


@dp.message(F.photo)
async def photo(message: Message):

    user = get_user(message.from_user.id)

    if not user:
        return

    if user[10] != "photo":
        return

    photo_id = message.photo[-1].file_id

    save(message.from_user.id, "photo", photo_id)
    save(message.from_user.id, "state", "done")

    await message.answer(
        "🎉 <b>Анкета готова!</b>\n\n"
        "Теперь можно смотреть анкеты.",
        parse_mode="HTML",
        reply_markup=menu()
    )


@dp.callback_query(F.data == "profile")
async def profile(callback: CallbackQuery):

    user = get_user(callback.from_user.id)

    if not user or not user[1]:

        await callback.message.answer(
            "Сначала создай анкету через /start."
        )

        await callback.answer()
        return

    (
        uid,
        _,
        name,
        age,
        gender_value,
        looking_for,
        min_age,
        max_age,
        city,
        bio,
        photo,
        state
    ) = user

    gender_text = (
        "👨 Мужской"
        if gender_value == "male"
        else "👩 Женский"
    )

    if looking_for == "male":
        looking_text = "👨 Мужчин"
    elif looking_for == "female":
        looking_text = "👩 Женщин"
    else:
        looking_text = "👥 Всех"

    text = (
        f"👤 <b>{name}</b>, {age}\n"
        f"{gender_text}\n"
        f"🔎 Ищу: {looking_text}\n"
        f"🎂 Возраст: {min_age}–{max_age}\n"
        f"📍 {city}\n\n"
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


@dp.callback_query(F.data == "browse")
async def browse(callback: CallbackQuery):

    me = get_user(callback.from_user.id)

    if not me or me[10] != "done":

        await callback.message.answer(
            "Сначала создай анкету через /start."
        )

        await callback.answer()
        return

    my_age = me[3]
    my_gender = me[4]
    looking_for = me[5]
    min_age = me[6]
    max_age = me[7]

    if my_age < 18:
        allowed_min = 13
        allowed_max = 17
    else:
        allowed_min = 18
        allowed_max = 100

    min_search = max(min_age, allowed_min)
    max_search = min(max_age, allowed_max)

    con = db()

    if looking_for == "all":

        query = """
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
            AND id NOT IN (
                SELECT to_id
                FROM reports
                WHERE from_id = ?
            )
            ORDER BY RANDOM()
            LIMIT 1
        """

        params = (
            callback.from_user.id,
            min_search,
            max_search,
            callback.from_user.id,
            callback.from_user.id
        )

    else:

        query = """
            SELECT *
            FROM users
            WHERE id != ?
            AND state = 'done'
            AND age BETWEEN ? AND ?
            AND gender = ?
            AND id NOT IN (
                SELECT to_id
                FROM likes
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

        params = (
            callback.from_user.id,
            min_search,
            max_search,
            looking_for,
            callback.from_user.id,
            callback.from_user.id
        )

    user = con.execute(
        query,
        params
    ).fetchone()

    con.close()

    if not user:

        await callback.message.answer(
            "😔 Подходящих анкет пока нет."
        )

        await callback.answer()
        return

    (
        uid,
        _,
        name,
        age,
        gender_value,
        _,
        _,
        _,
        city,
        bio,
        photo,
        _
    ) = user

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
            reply_markup=profile_keyboard(uid)
        )

    else:

        await callback.message.answer(
            text,
            parse_mode="HTML",
            reply_markup=profile_keyboard(uid)
        )

    await callback.answer()


@dp.callback_query(F.data.startswith("like:"))
async def like(callback: CallbackQuery):

    target = int(
        callback.data.split(":")[1]
    )

    me = callback.from_user.id

    con = db()

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

    await callback.answer("❤️ Нравится!")

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


@dp.callback_query(F.data.startswith("skip:"))
async def skip(callback: CallbackQuery):

    await callback.answer("👎 Пропущено")

    await browse(callback)


@dp.callback_query(F.data.startswith("report:"))
async def report(callback: CallbackQuery):

    target = int(
        callback.data.split(":")[1]
    )

    con = db()

    con.execute(
        """
        INSERT OR IGNORE INTO reports(from_id, to_id)
        VALUES (?, ?)
        """,
        (callback.from_user.id, target)
    )

    con.commit()
    con.close()

    await callback.answer(
        "🚨 Жалоба отправлена"
    )

    await callback.message.answer(
        "Жалоба зарегистрирована."
    )

    await browse(callback)


@dp.callback_query(F.data == "matches")
async def matches(callback: CallbackQuery):

    con = db()

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
