"""
Функции для работы с БД: создание таблиц, получение и обновление состояния пользователя, 
сохранение ответов, результатов.
"""

import aiosqlite
from datetime import datetime

DB_NAME = 'quiz_bot.db'


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


async def clear_user_answers(user_id):
    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute('DELETE FROM quiz_user_answers WHERE user_id = ?', (user_id,))
        await db.commit()


async def save_result(user_id, correct_count, level, total_questions):
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute(
            'INSERT OR REPLACE INTO quiz_results (user_id, level, last_score, last_played) VALUES (?, ?, ?, ?)',
            (user_id, level, correct_count, timestamp)
        )
        await db.commit()
