from datetime import datetime

from yadisk import Client
from gspread import Client as GClient


def upload_and_get_link(client: Client, filename: bytes, disk_folder: str) -> str:
    """
    Получает клиент Яндекс диска и имя файла, возвращает ссылку на файл.
    """
    save_filename = str(datetime.timestamp(datetime.now())).replace('.', '') + '.jpg'
    with client:
        client.upload(filename, f'/{disk_folder}/{save_filename}')
        file_url = client.get_download_link(f'/{disk_folder}/{save_filename}')

    return file_url




def upload_information_to_gsheets(client: GClient, sheet_name: str, data: list) -> None:
    # Открываем таблицу
    spreadsheet = client.open(sheet_name)

    # Открываем первый лист
    worksheet = spreadsheet.sheet1

    # Добавляем строку с данными
    #worksheet.append_row([str(datetime.timestamp(datetime.now())).replace('.', ''), "Имя", "+1234567890"])
    worksheet.append_row(data)