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


# Функция для загрузки конфигурации из config.json
def load_config():
    try:
        with open("config.json", "r") as file:
            return json.load(file)
    except (FileNotFoundError, json.JSONDecodeError) as e:
        logging.error("Ошибка загрузки config.json: %s", e)
        raise


# Загрузка конфигурации
config = load_config()

# Объект бота
bot = Bot(token=config["API_TOKEN"])
dp = Dispatcher()

# Имя базы данных
DB_NAME = 'quiz_bot.db'

# Структура квиза
quiz_data = {
    1: [
        {'question': 'Сколько будет 2 + 2?', 'options': ['3', '4', '5', '6'], 'correct_option': 1},
        {'question': 'Чему равен корень из 9?', 'options': ['1', '2', '3', '4'], 'correct_option': 2},
        {'question': 'Сколько градусов в прямом угле?', 'options': ['45', '90', '180', '360'], 'correct_option': 1},
        {'question': 'Чему равен 5 * 5?', 'options': ['10', '20', '25', '30'], 'correct_option': 2},
        {'question': 'Сколько будет 10 - 3?', 'options': ['5', '6', '7', '8'], 'correct_option': 2},
        {'question': 'Чему равна сумма углов треугольника?', 'options': ['90', '180', '270', '360'],
         'correct_option': 1},
        {'question': 'Сколько будет 15 / 3?', 'options': ['3', '5', '7', '9'], 'correct_option': 1},
        {'question': 'Чему равен квадрат числа 4?', 'options': ['8', '12', '16', '20'], 'correct_option': 2},
        {'question': 'Как называется отрезок, соединяющий две точки окружности?',
         'options': ['Радиус', 'Диаметр', 'Хорда', 'Касательная'], 'correct_option': 2},
        {'question': 'Сколько будет 7 + 6?', 'options': ['11', '12', '13', '14'], 'correct_option': 2}
    ],
    2: [
        {'question': 'Чему равен 2^5?', 'options': ['16', '32', '64', '128'], 'correct_option': 1},
        {'question': 'Сколько граней у куба?', 'options': ['4', '6', '8', '12'], 'correct_option': 1},
        {'question': 'Чему равен факториал числа 4?', 'options': ['24', '12', '6', '4'], 'correct_option': 0},
        {'question': 'Чему равен логарифм 100 по основанию 10?', 'options': ['1', '2', '10', '100'],
         'correct_option': 1},
        {'question': 'Решите уравнение: x + 5 = 12. Чему равен x?', 'options': ['5', '7', '10', '12'],
         'correct_option': 1},
        {'question': 'Сколько будет 3 * 3 * 3?', 'options': ['9', '18', '27', '81'], 'correct_option': 2},
        {'question': 'Какое число делится на 2, 3 и 5 одновременно?', 'options': ['10', '15', '30', '60'],
         'correct_option': 2},
        {'question': 'Чему равен синус 90 градусов?', 'options': ['0', '1', '0.5', '-1'], 'correct_option': 1},
        {'question': 'Сколько будет корень из 81?', 'options': ['9', '8', '7', '6'], 'correct_option': 0},
        {'question': 'Чему равна сумма всех углов квадрата?', 'options': ['180', '360', '540', '720'],
         'correct_option': 1}
    ],
    3: [
        {'question': 'Чему равна производная функции f(x) = x^2?', 'options': ['x', '2x', 'x^2', '2'],
         'correct_option': 1},
        {'question': 'Интеграл от x dx равен:', 'options': ['x^2/2 + C', 'x^2 + C', '2x + C', 'x + C'],
         'correct_option': 0},
        {'question': 'Решите уравнение: 2x = 8. Чему равен x?', 'options': ['2', '3', '4', '8'], 'correct_option': 2},
        {'question': 'Чему равна длина окружности радиуса R?', 'options': ['pi*R^2', '2*pi*R', 'pi*R', 'R^2'],
         'correct_option': 1},
        {'question': 'Чему равна сумма ряда 1 + 2 + 3 + ... + 100?', 'options': ['5050', '5000', '505', '1000'],
         'correct_option': 0},
        {'question': 'Чему равна производная sin(x)?', 'options': ['cos(x)', '-sin(x)', 'sin(x)', '-cos(x)'],
         'correct_option': 0},
        {'question': 'Чему равен интеграл от 1/x dx?', 'options': ['ln(x) + C', '1/x + C', 'x + C', 'ln|x| + C'],
         'correct_option': 3},
        {'question': 'Чему равен корень уравнения x^2 - 9 = 0?', 'options': ['3', '-3', '3 и -3', '0'],
         'correct_option': 2},
        {'question': 'Чему равен предел функции 1/x при x стремящемся к бесконечности?',
         'options': ['0', '1', 'бесконечность', '-1'], 'correct_option': 0},
        {'question': 'Какой интеграл называют определённым?',
         'options': ['Интеграл с верхним и нижним пределом', 'Интеграл без пределов', 'Интеграл с переменной',
                     'Интеграл с одной границы'], 'correct_option': 0}
    ]
}


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
            (user_id, question_index, level, correct_count))
        await db.commit()


async def save_user_answer(user_id, question_index, user_answer, correct):
    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute(
            'INSERT OR REPLACE INTO quiz_user_answers (user_id, question_index, user_answer, correct) VALUES (?, ?, ?, ?)',
            (user_id, question_index, user_answer, 1 if correct else 0))
        await db.commit()


async def get_user_answers(user_id):
    async with aiosqlite.connect(DB_NAME) as db:
        async with db.execute(
                'SELECT question_index, user_answer, correct FROM quiz_user_answers WHERE user_id = ? ORDER BY question_index',
                (user_id,)) as cursor:
            return await cursor.fetchall()


@dp.callback_query(F.data.startswith("answer_"))
async def handle_answer(callback: types.CallbackQuery):
    user_id = callback.from_user.id
    current_question_index, current_level, correct_count = await get_user_state(user_id)
    if current_level is None or current_question_index >= len(quiz_data[current_level]):
        await callback.message.answer("Квиз уже завершен или состояние некорректно.")
        return

    chosen_str = callback.data.split("_")[1]
    chosen_index = int(chosen_str)

    await callback.bot.edit_message_reply_markup(
        chat_id=user_id,
        message_id=callback.message.message_id,
        reply_markup=None
    )

    question_data = quiz_data[current_level][current_question_index]
    correct_option = question_data['correct_option']
    user_answer = question_data['options'][chosen_index]
    correct_answer = question_data['options'][correct_option]

    is_correct = (chosen_index == correct_option)
    if is_correct:
        correct_count += 1
        await callback.message.answer(f"✅ Верно! Ваш ответ: {user_answer}")
    else:
        await callback.message.answer(f"❌ Неверно! Ваш ответ: {user_answer}\n✅ Правильный ответ: {correct_answer}")

    # Сохраняем ответ пользователя
    await save_user_answer(user_id, current_question_index, user_answer, is_correct)

    current_question_index += 1
    await update_user_state(user_id, question_index=current_question_index, correct_count=correct_count)

    if current_question_index < len(quiz_data[current_level]):
        await get_question(callback.message, user_id)
    else:
        total_questions = len(quiz_data[current_level])
        await save_result(user_id, correct_count, current_level)
        # Формируем таблицу результатов
        result_text = await generate_result_table(user_id, current_level, correct_count, total_questions)
        await callback.message.answer(result_text)


@dp.callback_query(F.data.startswith("level_"))
async def choose_level(callback: types.CallbackQuery):
    user_id = callback.from_user.id
    try:
        chosen_level = int(callback.data.split("_")[1])
        if chosen_level not in quiz_data:
            await callback.message.answer("Указанный уровень сложности недоступен.")
            return
        await callback.bot.edit_message_reply_markup(
            chat_id=user_id,
            message_id=callback.message.message_id,
            reply_markup=None
        )
        # Сбрасываем состояние квиза и счетчик правильных ответов
        await update_user_state(user_id, question_index=0, level=chosen_level, correct_count=0)
        # Очищаем ответы пользователя из предыдущих попыток (опционально)
        await clear_user_answers(user_id)
        await callback.message.answer(f"Вы выбрали уровень сложности {chosen_level}. Начнем игру!")
        await new_quiz(callback.message, user_id)
    except ValueError:
        await callback.message.answer("Произошла ошибка при выборе уровня сложности.")


@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    builder = InlineKeyboardBuilder()
    builder.add(
        types.InlineKeyboardButton(
            text="\ud83c\udfae Начать игру",
            callback_data="start_game"
        )
    )
    await message.answer("Добро пожаловать в квиз!", reply_markup=builder.as_markup())


@dp.callback_query(F.data == "start_game")
async def start_game(callback: types.CallbackQuery):
    user_id = callback.from_user.id
    # Предложим выбрать уровень сложности
    builder = InlineKeyboardBuilder()
    builder.add(
        types.InlineKeyboardButton(
            text="\u2b50 Легкий",
            callback_data="level_1"
        ),
        types.InlineKeyboardButton(
            text="\ud83d\udd25 Средний",
            callback_data="level_2"
        ),
        types.InlineKeyboardButton(
            text="\ud83c\udf0c Сложный",
            callback_data="level_3"
        )
    )
    await callback.bot.edit_message_reply_markup(
        chat_id=user_id,
        message_id=callback.message.message_id,
        reply_markup=None
    )
    await callback.message.answer("Выберите уровень сложности:", reply_markup=builder.as_markup())


async def get_question(message, user_id):
    current_question_index, current_level, correct_count = await get_user_state(user_id)
    if current_level is None:
        await message.answer("Невозможно получить вопрос: уровень не выбран.")
        return
    if current_question_index >= len(quiz_data[current_level]):
        await message.answer("Это был последний вопрос. Квиз завершен!")
        return

    question_data = quiz_data[current_level][current_question_index]
    correct_index = question_data['correct_option']
    opts = question_data['options']
    kb = generate_options_keyboard(opts, correct_index)
    await message.answer(question_data['question'], reply_markup=kb)


async def new_quiz(message, user_id):
    await get_question(message, user_id)


async def save_result(user_id, correct_count, level):
    # Сохраняем результат в таблицу quiz_results
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute(
            'INSERT OR REPLACE INTO quiz_results (user_id, last_score, last_level, last_played) VALUES (?, ?, ?, ?)',
            (user_id, correct_count, level, timestamp))
        await db.commit()


@dp.message(Command("stats"))
async def cmd_stats(message: types.Message):
    user_id = message.from_user.id
    async with aiosqlite.connect(DB_NAME) as db:
        async with db.execute('SELECT last_score, last_level, last_played FROM quiz_results WHERE user_id = ?',
                              (user_id,)) as cursor:
            result = await cursor.fetchone()
            if result:
                last_score, last_level, last_played = result
                total_questions = len(quiz_data.get(last_level, []))
                await message.answer(f"Ваш последний результат:\n"
                                     f"Уровень: {last_level}\n"
                                     f"Счет: {last_score}/{total_questions}\n"
                                     f"Пройдено: {last_played}")
            else:
                await message.answer("У вас еще нет статистики, пройдите квиз!")


async def generate_result_table(user_id, level, correct_count, total_questions):
    user_answers = await get_user_answers(user_id)
    # user_answers: [(question_index, user_answer, correct), ...]

    result_lines = [
        "Это был последний вопрос. Квиз завершен!",
        f"Ваш результат: {correct_count}/{total_questions}\n",
        "Вот ваши ответы:",
        "| Вопрос | Результат |",
        "|-------:|:---------:|"
    ]

    for (q_idx, u_ans, correct) in user_answers:
        question_number = f"{q_idx+1:02d}"  # форматируем с ведущими нулями
        result_mark = "✅" if correct == 1 else "❌"
        result_lines.append(f"| {question_number} | {result_mark} |")

    # Добавляем финальное сообщение
    result_lines.append("\nНажмите /start чтобы вернуться в меню.")

    return "\n".join(result_lines)


async def clear_user_answers(user_id):
    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute('DELETE FROM quiz_user_answers WHERE user_id = ?', (user_id,))
        await db.commit()


async def create_table():
    async with aiosqlite.connect(DB_NAME) as db:
        # Создаем таблицу состояния квиза
        await db.execute(
            '''CREATE TABLE IF NOT EXISTS quiz_state (
                user_id INTEGER PRIMARY KEY,
                question_index INTEGER,
                level INTEGER,
                correct_count INTEGER
            )'''
        )
        # Создаем таблицу результатов
        await db.execute(
            '''CREATE TABLE IF NOT EXISTS quiz_results (
                user_id INTEGER PRIMARY KEY,
                last_score INTEGER,
                last_level INTEGER,
                last_played TEXT
            )'''
        )
        # Создаем таблицу для сохранения ответов на каждый вопрос
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
