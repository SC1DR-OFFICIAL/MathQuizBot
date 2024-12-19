"""

Вспомогательные функции для логики квиза (генерация вопросов, клавиатур, результатов и статистики).

"""

from aiogram import types
from aiogram.utils.keyboard import InlineKeyboardBuilder


async def generate_stats_text(user_id, quiz_data, get_db_results):
    results = await get_db_results(user_id)
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


async def get_question(message, user_id, quiz_data, get_user_state):
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


async def new_quiz(message, user_id, quiz_data, get_user_state):
    await get_question(message, user_id, quiz_data, get_user_state)


async def generate_result_table(user_id, level, correct_count, total_questions, get_user_answers):
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
