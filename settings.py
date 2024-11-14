import os
import yadisk

from oauth2client.service_account import ServiceAccountCredentials
from dotenv import load_dotenv
from gspread import authorize

from database_functions import init_db

load_dotenv()

init_db()

#Создаем клиент яндекса
YANDEX_CLIENT = yadisk.Client(token=os.getenv('YA_DISK_TOKEN'))

# Устанавливаем соединение с API Google
scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
credentials = ServiceAccountCredentials.from_json_keyfile_name('test-sheets-441605-f353fc7f5f8c.json', scope)
GOOGLE_CLIENT = authorize(credentials)