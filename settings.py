import os
import yadisk

from oauth2client.service_account import ServiceAccountCredentials
from dotenv import load_dotenv
from gspread import authorize

from database_functions import init_db

load_dotenv()

init_db('users.db')

#Создаем клиент яндекса
YANDEX_CLIENT = yadisk.Client(token=os.getenv('YA_DISK_TOKEN'))

# Устанавливаем соединение с API Google
scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
credentials = ServiceAccountCredentials.from_json_keyfile_name('test-sheets-441605-f353fc7f5f8c.json', scope)
GOOGLE_CLIENT = authorize(credentials)


text_message_ansers = [
    "Я могу отвечать только на вопросы выбранные из меню. Воспользуйтесь им пожалуйста.",
    "Я не наделен искусственным интеллектом. Воспользуйтесь меню пожалуйста.",
    "Злой программист разрешает мне отвечать только на вопросы выбранные из меню.",
    "Попробуйте найти Ваш вопрос в меню, оно закреплено под этим сообщением.",
    "Я был бы рад поболтать, но могу отвечать только на вопросы о ТКО. Воспользуйтесь меню пожалуйста.",
]