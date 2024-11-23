"""
Функции для работы с базой данных.
"""
import os
import sqlite3
import time


def init_db(database_folder: str, database_name: str) -> str:
    """
    Инициализирует базу данных.

    Args:
        database_folder (str): Путь к папке, где будет размещена база данных.
        database_name (str): Имя файла базы данных.

    Returns:
        str: Полный путь к базе данных.
    """
    try:
        # Создаём папку для базы данных, если её нет
        os.makedirs(database_folder, exist_ok=True)

        # Формируем полный путь к базе данных
        db_path = os.path.join(database_folder, database_name)

        # Подключаемся к базе и создаём таблицы
        conn = sqlite3.connect(db_path)
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
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS kgm_requests (
                id INTEGER PRIMARY KEY,
                timestamp INTEGER,
                full_name TEXT,
                phone_number TEXT,
                management_company TEXT,
                adress TEXT,
                district TEXT,
                waste_type TEXT,
                comment TEXT,
                photo_link TEXT,
                username TEXT
            )
        ''')
        conn.commit()
        conn.close()
        return db_path
    except Exception as e:
        print(f"Ошибка при инициализации базы данных: {e}")
        raise


def is_user_registered(db_path: str, user_id: int):
    """
    Проверка пользователя на наличие в базе данных.
    """
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute("SELECT id FROM users WHERE id = ?", (user_id,))
    result = cursor.fetchone()
    conn.close()
    return result is not None


def register_user(db_path: str, user_id: int, full_name: str,
                  phone_number: str, workplace: str, username: str):
    """
    Сохранение пользователя в базе данных.
    """
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO users (id, full_name, phone_number, workplace, username) VALUES (?, ?, ?, ?, ?)",
        (user_id, full_name, phone_number, workplace, username))
    conn.commit()
    conn.close()


def save_kgm_request(db_path: str, full_name: str, phone_number: str,
                     management_company: str, address: str, district: str,
                     waste_type: str, comment: str, photo_link: str,
                     username: str):
    """
    Сохраняет заявку на вывоз КГМ в базу данных.

    Args:
        db_path (str): Имя файла базы данных.
        full_name (str): ФИО пользователя.
        phone_number (str): Номер телефона пользователя.
        management_company (str): Название управляющей компании.
        address (str): Адрес дома.
        district (str): Адрес дома.
        waste_type (str): Тип отходов.
        comment: (str): Комментарий пользователя.
        photo_link (str): Ссылка на фото отходов.
        username (str): Username пользователя в Telegram.
    """
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    try:
        timestamp = int(time.time())  # Текущее время в формате UNIX
        cursor.execute('''
            INSERT INTO kgm_requests (
                timestamp, full_name, phone_number, management_company, 
                adress, district, waste_type, comment, photo_link, username
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (timestamp, full_name, phone_number, management_company,
              address, district, waste_type, comment, photo_link, username))
        conn.commit()
    except sqlite3.Error as e:
        print(f"Ошибка при сохранении заявки: {e}")
    finally:
        conn.close()


import sqlite3


def get_user_by_id(user_id: int, db_path: str) -> dict:
    """
    Получает информацию о пользователе из базы данных по user_id.

    Args:
        user_id (int): Идентификатор пользователя.
        db_path (str): Путь к базе данных SQLite.

    Returns:
        dict: Словарь с информацией о пользователе. Если пользователь не найден, возвращается пустой словарь.
    """
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    try:
        cursor.execute(
            'SELECT id, full_name, phone_number, workplace, username FROM users WHERE id = ?',
            (user_id,))
        row = cursor.fetchone()

        if row:
            user_data = {
                "id": row[0],
                "full_name": row[1],
                "phone_number": row[2],
                "workplace": row[3],
                "username": row[4],
            }
        else:
            user_data = {}  # Возвращаем пустой словарь, если пользователь не найден

    finally:
        conn.close()

    return user_data
