"""
Функции для работы с базой данных.
"""
import sqlite3


def init_db(db_name: str):
    """
    Инициализирует базу данных.
    """
    conn = sqlite3.connect(db_name)
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY,
            full_name TEXT,
            phone_number TEXT,
            workplace TEXT,
            username TEXT
        )
    ''')
    conn.commit()
    conn.close()


def is_user_registered(db_name: str, user_id: int):
    """
    Проверка пользователя на наличие в базе данных.
    """
    conn = sqlite3.connect(db_name)
    cursor = conn.cursor()
    cursor.execute("SELECT id FROM users WHERE id = ?", (user_id,))
    result = cursor.fetchone()
    conn.close()
    return result is not None


def register_user(db_name: str, user_id: int, full_name: str, phone_number:str, workplace: str, username: str):
    """
    Сохранение пользователя в базе данных.
    """
    conn = sqlite3.connect(db_name)
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO users (id, full_name, phone_number, workplace, username) VALUES (?, ?, ?, ?, ?)",
        (user_id, full_name, phone_number, workplace, username))
    conn.commit()
    conn.close()
