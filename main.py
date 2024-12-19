"""

Основной файл с запуском бота, обработчиками команд и колбэков.

"""

import asyncio
import logging
import json
from aiogram import Bot, Dispatcher, types
from aiogram.filters.command import Command
from aiogram import F

from db import (create_table, get_user_state, update_user_state, save_user_answer, get_user_answers,
                clear_user_answers, save_result)
from quiz import (generate_stats_text, get_question, new_quiz, generate_result_table)

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
        await get_question(callback.message, user_id, quiz_data, get_user_state)
    else:
        total_questions = len(quiz_data[str(current_level)])
        await save_result(user_id, correct_count, current_level, total_questions)
        result_text = await generate_result_table(user_id, current_level, correct_count, total_questions,
                                                  get_user_answers)
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
        await new_quiz(callback.message, user_id, quiz_data, get_user_state)
    except ValueError:
        await callback.message.answer("Произошла ошибка при выборе уровня сложности.")


@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    from aiogram.utils.keyboard import InlineKeyboardBuilder
    builder = InlineKeyboardBuilder()
    builder.add(types.InlineKeyboardButton(text="♟ Начать игру", callback_data="start_game"))
    builder.add(types.InlineKeyboardButton(text="📊 Статистика", callback_data="show_stats"))
    builder.adjust(1)
    await message.answer("Добро пожаловать в квиз!", reply_markup=builder.as_markup())


@dp.callback_query(F.data == "start_game")
async def start_game(callback: types.CallbackQuery):
    from aiogram.utils.keyboard import InlineKeyboardBuilder
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

    async def get_db_results(uid):
        import aiosqlite
        from db import DB_NAME
        async with aiosqlite.connect(DB_NAME) as db:
            async with db.execute('SELECT level, last_score, last_played FROM quiz_results WHERE user_id = ?',
                                  (uid,)) as cursor:
                return await cursor.fetchall()

    result_text = await generate_stats_text(user_id, quiz_data, get_db_results)
    await callback.message.answer(result_text)


@dp.message(Command("stats"))
async def cmd_stats(message: types.Message):
    user_id = message.from_user.id

    async def get_db_results(uid):
        import aiosqlite
        from db import DB_NAME
        async with aiosqlite.connect(DB_NAME) as db:
            async with db.execute('SELECT level, last_score, last_played FROM quiz_results WHERE user_id = ?',
                                  (uid,)) as cursor:
                return await cursor.fetchall()

    result_text = await generate_stats_text(user_id, quiz_data, get_db_results)
    await message.answer(result_text)


async def main():
    await create_table()
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
