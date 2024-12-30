from aiogram import Bot, Dispatcher, types, F
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.fsm.state import State, StatesGroup
import sqlite3
import asyncio
import logging
import random

# Токен Бота
BOT_TOKEN = ""

# Ініціалізація бота
bot = Bot(token=BOT_TOKEN)
storage = MemoryStorage()
dp = Dispatcher(bot=bot, storage=storage)

# Настройка логування
logging.basicConfig(level=logging.INFO)


# Ініціалізація бази данних
def init_db():
    conn = sqlite3.connect("dating_bot.db")
    cursor = conn.cursor()
    cursor.execute('''CREATE TABLE IF NOT EXISTS profiles (
                        user_id INTEGER PRIMARY KEY,
                        name TEXT,
                        age INTEGER,
                        gender TEXT,
                        bio TEXT,
                        photo TEXT)''')
    conn.commit()
    conn.close()


init_db()


# Стан для створення і редагування анкети
class Form(StatesGroup):
    name = State()
    age = State()
    gender = State()
    bio = State()
    photo = State()
    edit_name = State()
    edit_age = State()
    edit_gender = State()
    edit_bio = State()
    edit_photo = State()


# Головне меню
def main_menu():
    keyboard = ReplyKeyboardMarkup(resize_keyboard=True, keyboard=[
        [KeyboardButton(text="Моя анкета")],
        [KeyboardButton(text="Шукати анкети")],
        [KeyboardButton(text="Видалити анкету")]
    ])
    return keyboard


# Команда /start
@dp.message(Command("start"))
async def cmd_start(message: types.Message, state: FSMContext):
    keyboard = ReplyKeyboardMarkup(resize_keyboard=True, keyboard=[
        [KeyboardButton(text="Створити анкету")]
    ])
    await message.answer("Вітаю! Натисніть на кнопку, щоб створити вашу анкету.", reply_markup=keyboard)


# Обробка кнопки "Створити анкету"
@dp.message(F.text == "Створити анкету")
async def create_profile_start(message: types.Message, state: FSMContext):
    await message.answer("Як вас звати?")
    await state.set_state(Form.name)

# Обробка ім'я
@dp.message(Form.name)
async def process_name(message: types.Message, state: FSMContext):
    await state.update_data(name=message.text)
    await message.answer("Скільки вам років?")
    await state.set_state(Form.age)

# Обробка віку
@dp.message(Form.age)
async def process_age(message: types.Message, state: FSMContext):
    if not message.text.isdigit():
        await message.answer("Будь ласка, введіть число.")
        return
    await state.update_data(age=int(message.text))

    keyboard = ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="Чоловік")],
            [KeyboardButton(text="Жінка")]
        ],
        resize_keyboard=True
    )

    await message.answer("Ваша стать:", reply_markup=keyboard)
    await state.set_state(Form.gender)


# Обробка статі
@dp.message(Form.gender)
async def process_gender(message: types.Message, state: FSMContext):
    if message.text not in ["Чоловік", "Жінка"]:
        await message.answer("Оберіть один із варіантів.")
        return
    await state.update_data(gender=message.text)

    keyboard = ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="Чоловік")],
            [KeyboardButton(text="Жінка")]
        ],
        resize_keyboard=True
    )
    await message.answer("Напишіть про себе.")
    await state.set_state(Form.bio)

# Обробка біографії
@dp.message(Form.bio)
async def process_bio(message: types.Message, state: FSMContext):
    await state.update_data(bio=message.text)
    await message.answer("Завантажте ваше фото.")
    await state.set_state(Form.photo)


# Обробка фото
@dp.message(Form.photo, F.content_type == "photo")
async def process_photo(message: types.Message, state: FSMContext):
    photo_id = message.photo[-1].file_id
    data = await state.get_data()
    user_id = message.from_user.id

    # Збереження анкети в базу данних
    conn = sqlite3.connect("dating_bot.db")
    cursor = conn.cursor()
    cursor.execute('''REPLACE INTO profiles (user_id, name, age, gender, bio, photo)
                      VALUES (?, ?, ?, ?, ?, ?)''',
                   (user_id, data["name"], data["age"], data["gender"], data["bio"], photo_id))
    conn.commit()
    conn.close()

    await message.answer("Ваша анкета успішно збереження!", reply_markup=main_menu())
    await state.clear()


# Перегляд своєї анкети
@dp.message(F.text == "Моя анкета")
async def my_profile(message: types.Message):
    conn = sqlite3.connect("dating_bot.db")
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM profiles WHERE user_id = ?", (message.from_user.id,))
    profile = cursor.fetchone()
    conn.close()

    if profile:
        text = (f"Ваші дані:\nІм'я: {profile[1]}\nВік: {profile[2]}\n"
                f"Стать: {profile[3]}\nПро себе: {profile[4]}")

        keyboard = ReplyKeyboardMarkup(resize_keyboard=True, keyboard=[
            [KeyboardButton(text="Редагувати ім'я"), KeyboardButton(text="Редагувати вік")],
            [KeyboardButton(text="Редагувати стать"), KeyboardButton(text="Редагувати фото")],
            [KeyboardButton(text="Редагувати біографію")],
            [KeyboardButton(text="Повернутись до головного меню")]
        ])

        await message.answer_photo(photo=profile[5], caption=text, reply_markup=keyboard)
    else:
        await message.answer("Ви ще не заповнили анкету.")


# Функції для редагування анкети
@dp.message(F.text == "Редагувати ім'я")
async def edit_name(message: types.Message, state: FSMContext):
    await message.answer("Введіть нове ім'я:")
    await state.set_state(Form.edit_name)


@dp.message(Form.edit_name)
async def process_edit_name(message: types.Message, state: FSMContext):
    user_id = message.from_user.id
    conn = sqlite3.connect("dating_bot.db")
    cursor = conn.cursor()
    cursor.execute("UPDATE profiles SET name = ? WHERE user_id = ?", (message.text, user_id))
    conn.commit()
    conn.close()
    await message.answer("Ваше ім'я успішно оновлено!", reply_markup=main_menu())
    await state.clear()


@dp.message(F.text == "Редагувати вік")
async def edit_age(message: types.Message, state: FSMContext):
    await message.answer("Введіть новий вік:")
    await state.set_state(Form.edit_age)


@dp.message(Form.edit_age)
async def process_edit_age(message: types.Message, state: FSMContext):
    if not message.text.isdigit():
        await message.answer("Будь ласка, введіть число.")
        return
    user_id = message.from_user.id
    conn = sqlite3.connect("dating_bot.db")
    cursor = conn.cursor()
    cursor.execute("UPDATE profiles SET age = ? WHERE user_id = ?", (int(message.text), user_id))
    conn.commit()
    conn.close()
    await message.answer("Ваш вік успішно оновлено!", reply_markup=main_menu())
    await state.clear()


@dp.message(F.text == "Редагувати стать")
async def edit_gender(message: types.Message, state: FSMContext):
    keyboard = ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="Чоловік")],
            [KeyboardButton(text="Жінка")]
        ],
        resize_keyboard=True
    )
    await message.answer("Виберіть вашу стать:", reply_markup=keyboard)
    await state.set_state(Form.edit_gender)


@dp.message(Form.edit_gender)
async def process_edit_gender(message: types.Message, state: FSMContext):
    if message.text not in ["Чоловік", "Жінка"]:
        await message.answer("Оберіть один із варіантів.")
        return
    user_id = message.from_user.id
    conn = sqlite3.connect("dating_bot.db")
    cursor = conn.cursor()
    cursor.execute("UPDATE profiles SET gender = ? WHERE user_id = ?", (message.text, user_id))
    conn.commit()
    conn.close()
    await message.answer("Вашу стать успішно оновлено!", reply_markup=main_menu())
    await state.clear()


@dp.message(F.text == "Редагувати біографію")
async def edit_bio(message: types.Message, state: FSMContext):
    await message.answer("Введіть новий текст про себе:")
    await state.set_state(Form.edit_bio)


@dp.message(Form.edit_bio)
async def process_edit_bio(message: types.Message, state: FSMContext):
    user_id = message.from_user.id
    conn = sqlite3.connect("dating_bot.db")
    cursor = conn.cursor()
    cursor.execute("UPDATE profiles SET bio = ? WHERE user_id = ?", (message.text, user_id))
    conn.commit()
    conn.close()
    await message.answer("Ваша біографія успішно оновлена!", reply_markup=main_menu())
    await state.clear()


@dp.message(F.text == "Редагувати фото")
async def edit_photo(message: types.Message, state: FSMContext):
    await message.answer("Завантажте нове фото.")
    await state.set_state(Form.edit_photo)


@dp.message(Form.edit_photo, F.content_type == "photo")
async def process_edit_photo(message: types.Message, state: FSMContext):
    photo_id = message.photo[-1].file_id
    user_id = message.from_user.id
    conn = sqlite3.connect("dating_bot.db")
    cursor = conn.cursor()
    cursor.execute("UPDATE profiles SET photo = ? WHERE user_id = ?", (photo_id, user_id))
    conn.commit()
    conn.close()
    await message.answer("Ваше фото успішно оновлено!", reply_markup=main_menu())
    await state.clear()


# Функція пошуку анкет
@dp.message(F.text == "Шукати анкети")
async def search_profiles(message: types.Message, state: FSMContext):
    user_id = message.from_user.id

    # Отримуємо всі доступні анкети
    conn = sqlite3.connect("dating_bot.db")
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM profiles WHERE user_id != ?", (user_id,))
    all_profiles = cursor.fetchall()
    conn.close()

    if not all_profiles:
        await message.answer("Нажаль, поки не має доступних анкет.")
        return

    # Отримуємо профілі які залишились зі стану
    data = await state.get_data()
    remaining_profiles = data.get("remaining_profiles", all_profiles.copy())

    # Якщо список пустий, починаємо знову
    if not remaining_profiles:
        await message.answer("Анкети закінчилися. Починаємо заново.")
        remaining_profiles = all_profiles.copy()

    # Обираємо випадковий профіль
    profile = random.choice(remaining_profiles)
    remaining_profiles.remove(profile)  # Видаляємо обраний профіль зі списку

    # Зберігаємо оновлений список в стан
    await state.update_data(remaining_profiles=remaining_profiles, current_profile=profile)

    # Формуємо текст і клавіатуру
    text = (f"Ім'я: {profile[1]}\nВік: {profile[2]}\n"
            f"Стать: {profile[3]}\nПро себе: {profile[4]}")

    keyboard = ReplyKeyboardMarkup(resize_keyboard=True, keyboard=[
        [KeyboardButton(text="Наступна анкета")],
        [KeyboardButton(text="Познайомитись")],
        [KeyboardButton(text="Повернутись до головного меню")]
    ])

    await message.answer_photo(photo=profile[5], caption=text, reply_markup=keyboard)


@dp.message(F.text == "Наступна анкета")
async def next_profile(message: types.Message, state: FSMContext):
    await search_profiles(message, state)  # Повторно викликаємо поршук анкет


@dp.message(F.text == "Познайомитись")
async def meet_profile(message: types.Message, state: FSMContext):
    data = await state.get_data()
    profile = data.get("current_profile")
    if profile:
        user_id = profile[0]
        await message.answer(f"Ось посилання на профіль цього користувача: tg://user?id={user_id}")
    else:
        await message.answer("Не вдалося знайти інформацію про поточну анкету. Спробуйте знову.")



# Видалення анкети
@dp.message(F.text == "Видалити анкету")
async def delete_profile(message: types.Message):
    user_id = message.from_user.id
    conn = sqlite3.connect("dating_bot.db")
    cursor = conn.cursor()
    cursor.execute("DELETE FROM profiles WHERE user_id = ?", (user_id,))
    conn.commit()
    conn.close()

    keyboard = ReplyKeyboardMarkup(resize_keyboard=True, keyboard=[
        [KeyboardButton(text="Створити анкету")]
    ])
    await message.answer("Ваша анкета видалена. Натисніть на кнопку, щоб створити нову.", reply_markup=keyboard)



# Повернення в головне меню
@dp.message(F.text == "Повернутись до головного меню")
async def back_to_main_menu(message: types.Message):
    await message.answer("Ви в головному меню.", reply_markup=main_menu())


# Обробка невідомих команд або текстів
@dp.message()
async def unknown_message(message: types.Message):
    await message.answer("Вибачте, я не розумію цю команду. Спробуйте обрати з меню.")


# Запуск бота
async def main():
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
