from datetime import datetime

from yadisk import Client

def upload_and_get_link(client: Client, filename: str, disk_folder: str) -> str:
    """
    Получает клиент Яндекс диска и имя файла, возвращает ссылку на файл.
    """
    save_filename = str(datetime.timestamp(datetime.now())).replace('.', '') + '.jpg'
    with client:
        client.upload(filename, f'/{disk_folder}/{save_filename}')
        file_url = client.get_download_link(f'/{disk_folder}/{save_filename}')

    return file_url
