"""

В модуле собраны функция формирующие клавиатуры для работы бота.

Также функция для отправки почты.

"""

import os
import re
import smtplib
from datetime import datetime
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from dotenv import load_dotenv

load_dotenv()


async def download_photo(file_id: str, bot) -> bytes:
    """Получает file_id, возвращает от телеграмм файл в bytes."""
    file = await bot.get_file(file_id)
    file_path = file.file_path
    # Загружаем файл в bytes
    photo_bytes = await bot.download_file(file_path)
    return photo_bytes


def get_cancel() -> InlineKeyboardMarkup:
    """Формирует и возвращает Inline клавиатуру с одной кнопкой Отмена."""
    keyboard = InlineKeyboardMarkup()
    button = InlineKeyboardButton(text='Отмена', callback_data='cancel')
    keyboard.add(button)
    return keyboard


def get_main_menu() -> InlineKeyboardMarkup:
    """Формирует и возвращает Inline клавиатуру, главное меню.

    Направить обращение
    """
    keyboard = InlineKeyboardMarkup()
    keyboard.add(InlineKeyboardButton("Заявка на вывоз КГМ",
                                      callback_data="kgm_request"))
    keyboard.add(InlineKeyboardButton("Обращение по качеству услуг",
                                      callback_data="quality_complaint"))
    return keyboard


def get_waste_type_keyboard(waste_types: list) -> InlineKeyboardMarkup:
    """Формирует и возвращает Inline клавиатуру с типами отходов."""
    keyboard = InlineKeyboardMarkup()
    for waste_type in waste_types:
        keyboard.add(InlineKeyboardButton(text=waste_type,
                                          callback_data=f"waste_type:{waste_type}"))
    return keyboard


def get_district_name(district_names: list) -> InlineKeyboardMarkup:
    """Формирует и возвращает Inline клавиатуру с именами районов."""
    keyboard = InlineKeyboardMarkup()
    for district in district_names:
        keyboard.add(InlineKeyboardButton(text=district,
                                          callback_data=f"district:{district}"))
    return keyboard


def get_coast_name(districts: dict[str: str], district_name) -> str:
    return districts.get(district_name)


async def send_email(message_text, target_email):
    """Отправляет письмо на заданную почту."""
    email = os.getenv("EMAIL")
    password = os.getenv("PASSWORD_EMAIL")
    time = datetime.now()

    msg = MIMEMultipart()
    msg['From'] = email
    msg['To'] = target_email
    msg[
        'Subject'] = (f"Новое обращение принято ботом "
                      f"{time.strftime('%Y-%m-%d %H:%M')}")
    msg.attach(MIMEText(message_text))
    try:
        mailserver = smtplib.SMTP('smtp.yandex.ru', 587)

        mailserver.ehlo()
        # Защищаем соединение с помощью шифрования tls
        mailserver.starttls()
        # Повторно идентифицируем себя как зашифрованное соединение
        # перед аутентификацией.
        mailserver.ehlo()
        mailserver.login(email, password)

        mailserver.sendmail(email, target_email, msg.as_string())

        mailserver.quit()
    except smtplib.SMTPException:
        print("Ошибка: Невозможно отправить сообщение")


# Клавиатуры для FSM этапов
async def get_quality_complaint_keyboard():
    keyboard = InlineKeyboardMarkup()
    keyboard.add(InlineKeyboardButton("Сообщить о невывозе",
                                      callback_data="Невывоз"))
    keyboard.add(InlineKeyboardButton("Замечания по качеству услуг",
                                      callback_data="Замечания"))
    keyboard.add(InlineKeyboardButton("Отмена", callback_data="cancel"))
    return keyboard


async def get_no_collection_days_keyboard():
    keyboard = InlineKeyboardMarkup()
    keyboard.add(InlineKeyboardButton("Сегодня", callback_data="today"))
    keyboard.add(InlineKeyboardButton("Вчера", callback_data="1 день"))
    keyboard.add(InlineKeyboardButton("Позавчера",
                                      callback_data="2 дня"))
    keyboard.add(
        InlineKeyboardButton("Более 2 дней", callback_data="Больше 2 дней"))
    keyboard.add(InlineKeyboardButton("Отмена", callback_data="cancel"))
    return keyboard


async def get_quality_issue_keyboard():
    keyboard = InlineKeyboardMarkup()
    keyboard.add(InlineKeyboardButton("Не вернули бак на место",
                                      callback_data="Не вернули бак"))
    keyboard.add(
        InlineKeyboardButton("Повредили бак", callback_data="Повредили бак"))
    keyboard.add(InlineKeyboardButton("Не подобрали россыпь",
                                      callback_data="Россыпь"))
    keyboard.add(InlineKeyboardButton("Неполная отгрузка",
                                      callback_data="Неполная отгрузка"))
    keyboard.add(InlineKeyboardButton("Отмена", callback_data="cancel"))
    return keyboard


async def get_cancel_keyboard():
    keyboard = InlineKeyboardMarkup()
    keyboard.add(InlineKeyboardButton("Отмена", callback_data="cancel"))
    return keyboard


async def get_confirmation_keyboard():
    keyboard = InlineKeyboardMarkup()
    keyboard.add(
        InlineKeyboardButton("Подтвердить", callback_data="confirm_data"))
    keyboard.add(InlineKeyboardButton("Отмена", callback_data="cancel"))
    return keyboard


async def get_contact_method_keyboard():
    keyboard = InlineKeyboardMarkup()
    keyboard.add(InlineKeyboardButton("Обратная связь не нужна",
                                      callback_data="Не нужна"))
    keyboard.add(InlineKeyboardButton("Телефон", callback_data="Телефон"))
    keyboard.add(
        InlineKeyboardButton("Электронная почта", callback_data="email"))
    keyboard.add(InlineKeyboardButton("Отмена", callback_data="cancel"))
    return keyboard


async def get_no_comment_keyboard():
    keyboard = InlineKeyboardMarkup()
    keyboard.add(
        InlineKeyboardButton("Нет комментария", callback_data="Нет комментария"))
    keyboard.add(InlineKeyboardButton("Отмена", callback_data="cancel"))
    return keyboard


async def get_registration_keyboard():
    keyboard = InlineKeyboardMarkup().add(
        InlineKeyboardButton("Зарегистрироваться", callback_data="register"))
    return keyboard


# Функция для валидации email
def is_valid_email(email: str) -> bool:
    return re.match(r"^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$",
                    email) is not None
