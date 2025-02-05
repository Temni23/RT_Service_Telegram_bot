"""

В модуле собраны функция формирующие клавиатуры для работы бота.

Также функция для отправки почты.

"""

import os
import smtplib
from datetime import datetime
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from dotenv import load_dotenv

load_dotenv()


async def download_photo(file_id: str, bot) -> bytes:
    """Получает file_id возвращает от телеграмма файл в bytes."""
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
