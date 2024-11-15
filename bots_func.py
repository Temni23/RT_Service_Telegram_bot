"""

В модуле собраны функция формирующие клавиатуры для работы бота.

Также функция для отправки почты.

"""

import logging
import os
import smtplib
from datetime import datetime
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from logging.handlers import RotatingFileHandler

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

from dotenv import load_dotenv

load_dotenv()

# logger = logging.getLogger(__name__)
# logger.setLevel(logging.INFO)
# handler = RotatingFileHandler("logs/main_logs.log", encoding="UTF-8")
# formatter = logging.Formatter(
#     '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
# )
# handler.setFormatter(formatter)
# logger.addHandler(handler)


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
    button = InlineKeyboardButton(text='Заявка на вывоз КГМ',
                                   callback_data='kgm_request')
    keyboard.add(button)
    return keyboard




def get_waste_type_keyboard() -> InlineKeyboardMarkup:
    """Формирует и возвращает Inline клавиатуру с типами отходов."""
    keyboard = InlineKeyboardMarkup()
    waste_types = ["РСО", "КГМ", "Листва в мешках", "Ветки 0,7м"]
    for waste_type in waste_types:
        keyboard.add(InlineKeyboardButton(text=waste_type, callback_data=f"waste_type:{waste_type}"))
    return keyboard


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
