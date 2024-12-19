import aiosqlite
import asyncio
import logging
from aiogram import Bot, Dispatcher, types
from aiogram.filters.command import Command
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram import F
import json
from datetime import datetime

# Включаем логирование
logging.basicConfig(level=logging.INFO)


def load_config():
    try:
        with open("config.json", "r") as file:
            return json.load(file)
    except (FileNotFoundError, json.JSONDecodeError) as e:
        logging.error("Ошибка загрузки config.json: %s", e)
        raise


def load_quiz_data():
    try:
        with open("quiz_data.json", "r", encoding="utf-8") as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError) as e:
        logging.error("Ошибка загрузки quiz_data.json: %s", e)
        raise


# Загрузка конфигурации
config = load_config()
# Загрузка вопросов
quiz_data = load_quiz_data()

bot = Bot(token=config["API_TOKEN"])
dp = Dispatcher()

DB_NAME = 'quiz_bot.db'


def generate_options_keyboard(answer_options, correct_index):
    builder = InlineKeyboardBuilder()
    for i, option in enumerate(answer_options):
        builder.add(
            types.InlineKeyboardButton(
                text=option,
                callback_data=f"answer_{i}"
            )
        )
    builder.adjust(1)
    return builder.as_markup()


async def get_user_state(user_id):
    async with aiosqlite.connect(DB_NAME) as db:
        async with db.execute('SELECT question_index, level, correct_count FROM quiz_state WHERE user_id = ?',
                              (user_id,)) as cursor:
            result = await cursor.fetchone()
            if result:
                return result[0], result[1], result[2]
            return 0, None, 0


async def update_user_state(user_id, question_index=None, level=None, correct_count=None):
    current_question_index, current_level, current_correct = await get_user_state(user_id)
    if question_index is None:
        question_index = current_question_index
    if level is None:
        level = current_level
    if correct_count is None:
        correct_count = current_correct
    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute(
            'INSERT OR REPLACE INTO quiz_state (user_id, question_index, level, correct_count) VALUES (?, ?, ?, ?)',
            (user_id, question_index, level, correct_count)
        )
        await db.commit()


async def save_user_answer(user_id, question_index, user_answer, correct):
    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute(
            'INSERT OR REPLACE INTO quiz_user_answers (user_id, question_index, user_answer, correct) VALUES (?, ?, ?, ?)',
            (user_id, question_index, user_answer, 1 if correct else 0)
        )
        await db.commit()


async def get_user_answers(user_id):
    async with aiosqlite.connect(DB_NAME) as db:
        async with db.execute(
                'SELECT question_index, user_answer, correct FROM quiz_user_answers WHERE user_id = ? ORDER BY question_index',
                (user_id,)
        ) as cursor:
            return await cursor.fetchall()


@dp.callback_query(F.data.startswith("answer_"))
async def handle_answer(callback: types.CallbackQuery):
    user_id = callback.from_user.id
    current_question_index, current_level, correct_count = await get_user_state(user_id)
    if current_level is None or current_question_index >= len(quiz_data[str(current_level)]):
        await callback.message.answer("Квиз уже завершен или состояние некорректно.")
        return

    chosen_str = callback.data.split("_")[1]
    chosen_index = int(chosen_str)

    await callback.bot.edit_message_reply_markup(
        chat_id=user_id,
        message_id=callback.message.message_id,
        reply_markup=None
    )

    question_data = quiz_data[str(current_level)][current_question_index]
    correct_option = question_data['correct_option']
    user_answer = question_data['options'][chosen_index]
    correct_answer = question_data['options'][correct_option]

    is_correct = (chosen_index == correct_option)
    if is_correct:
        correct_count += 1
        await callback.message.answer(f"✅ Верно! Ваш ответ: {user_answer}")
    else:
        await callback.message.answer(f"❌ Неверно! Ваш ответ: {user_answer}\n✅ Правильный ответ: {correct_answer}")

    await save_user_answer(user_id, current_question_index, user_answer, is_correct)

    current_question_index += 1
    await update_user_state(user_id, question_index=current_question_index, correct_count=correct_count)

    if current_question_index < len(quiz_data[str(current_level)]):
        await get_question(callback.message, user_id)
    else:
        total_questions = len(quiz_data[str(current_level)])
        await save_result(user_id, correct_count, current_level)
        result_text = await generate_result_table(user_id, current_level, correct_count, total_questions)
        await callback.message.answer(result_text)


@dp.callback_query(F.data.startswith("level_"))
async def choose_level(callback: types.CallbackQuery):
    user_id = callback.from_user.id
    try:
        chosen_level = int(callback.data.split("_")[1])
        if str(chosen_level) not in quiz_data:
            await callback.message.answer("Указанный уровень сложности недоступен.")
            return
        await callback.bot.edit_message_reply_markup(
            chat_id=user_id,
            message_id=callback.message.message_id,
            reply_markup=None
        )
        await update_user_state(user_id, question_index=0, level=chosen_level, correct_count=0)
        await clear_user_answers(user_id)
        await callback.message.answer(f"Вы выбрали уровень сложности {chosen_level}. Начнем игру!")
        await new_quiz(callback.message, user_id)
    except ValueError:
        await callback.message.answer("Произошла ошибка при выборе уровня сложности.")


@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    builder = InlineKeyboardBuilder()
    builder.add(types.InlineKeyboardButton(text="♟ Начать игру", callback_data="start_game"))
    builder.add(types.InlineKeyboardButton(text="📊 Статистика", callback_data="show_stats"))
    builder.adjust(1)
    await message.answer("Добро пожаловать в квиз!", reply_markup=builder.as_markup())


@dp.callback_query(F.data == "start_game")
async def start_game(callback: types.CallbackQuery):
    user_id = callback.from_user.id
    await callback.bot.edit_message_reply_markup(
        chat_id=user_id,
        message_id=callback.message.message_id,
        reply_markup=None
    )
    builder = InlineKeyboardBuilder()
    builder.add(types.InlineKeyboardButton(text="\u2b50 Легкий", callback_data="level_1"),
                types.InlineKeyboardButton(text="\ud83d\udd25 Средний", callback_data="level_2"),
                types.InlineKeyboardButton(text="🧠 Сложный", callback_data="level_3"))
    await callback.message.answer("Выберите уровень сложности:", reply_markup=builder.as_markup())


@dp.callback_query(F.data == "show_stats")
async def show_stats_callback(callback: types.CallbackQuery):
    user_id = callback.from_user.id
    await callback.bot.edit_message_reply_markup(
        chat_id=user_id,
        message_id=callback.message.message_id,
        reply_markup=None
    )
    result_text = await generate_stats_text(user_id)
    await callback.message.answer(result_text)


@dp.message(Command("stats"))
async def cmd_stats(message: types.Message):
    user_id = message.from_user.id
    result_text = await generate_stats_text(user_id)
    await message.answer(result_text)


async def generate_stats_text(user_id):
    async with aiosqlite.connect(DB_NAME) as db:
        async with db.execute('SELECT level, last_score, last_played FROM quiz_results WHERE user_id = ?',
                              (user_id,)) as cursor:
            results = await cursor.fetchall()
    if not results:
        return "У вас еще нет статистики, пройдите квиз!\nНажмите /start и выберите «Начать игру»."

    lines = ["Ваша статистика по последним прохождениям:"]
    for level, last_score, last_played in results:
        total_questions = len(quiz_data.get(str(level), []))
        lines.append(
            f"\nУровень: {level}\n"
            f"Счет: {last_score}/{total_questions}\n"
            f"Пройдено: {last_played}"
        )

    lines.append("\nДля возвращения в меню нажмите /start.")
    return "\n".join(lines)


async def get_question(message, user_id):
    current_question_index, current_level, correct_count = await get_user_state(user_id)
    if current_level is None:
        await message.answer("Невозможно получить вопрос: уровень не выбран.")
        return
    if current_question_index >= len(quiz_data[str(current_level)]):
        await message.answer("Это был последний вопрос. Квиз завершен!")
        return

    question_data = quiz_data[str(current_level)][current_question_index]
    correct_index = question_data['correct_option']
    opts = question_data['options']
    kb = generate_options_keyboard(opts, correct_index)
    await message.answer(question_data['question'], reply_markup=kb)


async def new_quiz(message, user_id):
    await get_question(message, user_id)


async def save_result(user_id, correct_count, level):
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute(
            'INSERT OR REPLACE INTO quiz_results (user_id, level, last_score, last_played) VALUES (?, ?, ?, ?)',
            (user_id, level, correct_count, timestamp)
        )
        await db.commit()


async def generate_result_table(user_id, level, correct_count, total_questions):
    user_answers = await get_user_answers(user_id)
    result_lines = [
        "Это был последний вопрос. Квиз завершен!",
        f"Ваш результат: {correct_count}/{total_questions}\n",
        "Вот ваши ответы:",
        "| Вопрос | Результат |",
        "|-------:|:---------:|"
    ]
    for (q_idx, u_ans, correct) in user_answers:
        question_number = f"{q_idx + 1:02d}"
        result_mark = "✅" if correct == 1 else "❌"
        result_lines.append(f"| {question_number} | {result_mark} |")

    result_lines.append("\nНажмите /start чтобы вернуться в меню.")
    return "\n".join(result_lines)


async def clear_user_answers(user_id):
    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute('DELETE FROM quiz_user_answers WHERE user_id = ?', (user_id,))
        await db.commit()


async def create_table():
    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute(
            '''CREATE TABLE IF NOT EXISTS quiz_state (
                user_id INTEGER PRIMARY KEY,
                question_index INTEGER,
                level INTEGER,
                correct_count INTEGER
            )'''
        )
        await db.execute(
            '''CREATE TABLE IF NOT EXISTS quiz_results (
                user_id INTEGER,
                level INTEGER,
                last_score INTEGER,
                last_played TEXT,
                PRIMARY KEY(user_id, level)
            )'''
        )
        await db.execute(
            '''CREATE TABLE IF NOT EXISTS quiz_user_answers (
                user_id INTEGER,
                question_index INTEGER,
                user_answer TEXT,
                correct INTEGER,
                PRIMARY KEY(user_id, question_index)
            )'''
        )
        await db.commit()


async def main():
    await create_table()
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
