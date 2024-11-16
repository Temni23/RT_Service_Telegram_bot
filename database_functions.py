"""
Функции для работы с базой данных.
"""
import sqlite3
import time


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
    cursor.execute('''
            CREATE TABLE IF NOT EXISTS kgm_requests (
                id INTEGER PRIMARY KEY,
                timestamp INTEGER,
                full_name TEXT,
                phone_number TEXT,
                management_company TEXT,
                adress TEXT,
                waste_type TEXT,
                photo_link TEXT,
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

def save_kgm_request(db_name: str, full_name: str, phone_number: str,
                     management_company: str, address: str, waste_type: str,
                     photo_link: str, username: str):
    """
    Сохраняет заявку на вывоз КГМ в базу данных.

    Args:
        db_name (str): Имя файла базы данных.
        full_name (str): ФИО пользователя.
        phone_number (str): Номер телефона пользователя.
        management_company (str): Название управляющей компании.
        address (str): Адрес дома.
        waste_type (str): Тип отходов.
        photo_link (str): Ссылка на фото отходов.
        username (str): Username пользователя в Telegram.
    """
    conn = sqlite3.connect(db_name)
    cursor = conn.cursor()
    try:
        timestamp = int(time.time())  # Текущее время в формате UNIX
        cursor.execute('''
            INSERT INTO kgm_requests (
                timestamp, full_name, phone_number, management_company, 
                adress, waste_type, photo_link, username
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ''', (timestamp, full_name, phone_number, management_company,
              address, waste_type, photo_link, username))
        conn.commit()
    except sqlite3.Error as e:
        print(f"Ошибка при сохранении заявки: {e}")
    finally:
        conn.close()