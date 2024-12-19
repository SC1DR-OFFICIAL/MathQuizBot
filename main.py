import aiosqlite
import asyncio
import logging
from aiogram import Bot, Dispatcher, types
from aiogram.filters.command import Command
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram import F
import json

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
    # Вместо "right_answer"/"wrong_answer" теперь укажем индекс варианта: answer_{index}
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
    # Возвращает текущий индекс вопроса и уровень сложности для пользователя
    async with aiosqlite.connect(DB_NAME) as db:
        async with db.execute('SELECT question_index, level FROM quiz_state WHERE user_id = ?', (user_id,)) as cursor:
            result = await cursor.fetchone()
            if result:
                return result[0], result[1]
            return 0, None


async def update_user_state(user_id, question_index=None, level=None):
    # Обновляем или устанавливаем индекс вопроса и/или уровень для пользователя
    current_question_index, current_level = await get_user_state(user_id)
    if question_index is None:
        question_index = current_question_index
    if level is None:
        level = current_level
    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute('INSERT OR REPLACE INTO quiz_state (user_id, question_index, level) VALUES (?, ?, ?)',
                         (user_id, question_index, level))
        await db.commit()


@dp.callback_query(F.data.startswith("answer_"))
async def handle_answer(callback: types.CallbackQuery):
    user_id = callback.from_user.id
    current_question_index, current_level = await get_user_state(user_id)
    if current_level is None or current_question_index >= len(quiz_data[current_level]):
        await callback.message.answer("Квиз уже завершен или состояние некорректно.")
        return

    # Извлекаем индекс выбранного варианта из callback_data
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

    if chosen_index == correct_option:
        await callback.message.answer(f"Верно! Ваш ответ: {user_answer}")
    else:
        await callback.message.answer(f"Неверно! Ваш ответ: {user_answer}\nПравильный ответ: {correct_answer}")

    current_question_index += 1
    await update_user_state(user_id, question_index=current_question_index)

    if current_question_index < len(quiz_data[current_level]):
        await get_question(callback.message, user_id)
    else:
        await callback.message.answer("Это был последний вопрос. Квиз завершен!")


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
        await callback.message.answer(f"Вы выбрали уровень сложности {chosen_level}. Начнем игру!")
        await update_user_state(user_id, question_index=0, level=chosen_level)
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
    current_question_index, current_level = await get_user_state(user_id)
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
    # Начинаем квиз с нулевого вопроса (уже установлено в choose_level)
    await get_question(message, user_id)


async def create_table():
    async with aiosqlite.connect(DB_NAME) as db:
        # Создаем таблицу, если ее нет
        await db.execute(
            '''CREATE TABLE IF NOT EXISTS quiz_state (
                user_id INTEGER PRIMARY KEY,
                question_index INTEGER,
                level INTEGER
            )'''
        )
        await db.commit()


async def main():
    await create_table()
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
