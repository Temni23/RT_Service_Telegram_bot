import os
import yadisk

from oauth2client.service_account import ServiceAccountCredentials
from dotenv import load_dotenv
from gspread import authorize

from database_functions import init_db

load_dotenv()

# Настройка логирования
log_folder = 'logs'
log_file = os.path.join(log_folder, 'bot.log')

database_path = init_db('database', 'users.db')

# Создаем клиент яндекса
YANDEX_CLIENT = yadisk.Client(token=os.getenv('YA_DISK_TOKEN'))
YA_DISK_FOLDER = os.getenv('YA_DISK_FOLDER')
YA_DISK_FOLDER_COMPLAINTS=os.getenv('YA_DISK_FOLDER_COMPLAINTS')

# Устанавливаем соединение с API Google
scope = ['https://spreadsheets.google.com/feeds',
         'https://www.googleapis.com/auth/drive']
credentials = ServiceAccountCredentials.from_json_keyfile_name(
    os.getenv('GSHEETS_KEY'), scope)
GOOGLE_CLIENT = authorize(credentials)
GOOGLE_SHEET_NAME_LEFT = os.getenv('GOOGLE_SHEET_NAME_LEFT')
GOOGLE_SHEET_NAME_RIGHT = os.getenv('GOOGLE_SHEET_NAME_RIGHT')
GOOGLE_SHEET_NAME = {'left': GOOGLE_SHEET_NAME_LEFT,
                     'right': GOOGLE_SHEET_NAME_RIGHT}
GOOGLE_SHEET_COMPLAINT_NAME = os.getenv('GOOGLE_SHEET_COMPLAINT_NAME')

DEV_TG_ID = os.getenv('DEV_TG_ID')
TIMEDELTA = int(os.getenv('TIMEDELTA'))

text_message_answers = [
    'Я могу отвечать только на вопросы выбранные из меню. Воспользуйтесь им пожалуйста.',
    'Я не наделен искусственным интеллектом. Воспользуйтесь меню пожалуйста.',
    'Попробуйте найти Ваш вопрос в меню, оно закреплено под этим сообщением.',
    'Я был бы рад поболтать, но могу отвечать только на вопросы из меню. Воспользуйтесь меню пожалуйста.',
]

district_names = ['Ленинский', 'Кировский', 'Свердловский', 'Советский',
                  'Центральный', 'Железнодорожный', 'Октябрьский']
waste_types = ['РСО', 'КГМ', 'Листва в мешках', 'Ветки 0,7м']

districts_tz = {'Ленинский': 'right', 'Кировский': 'right',
                'Свердловский': 'right', 'Советский': 'left',
                'Центральный': 'left', 'Железнодорожный': 'left',
                'Октябрьский': 'left'}
