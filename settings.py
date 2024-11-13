import os
import yadisk

from dotenv import load_dotenv

load_dotenv()

YANDEX_CLIENT = yadisk.Client(token=os.getenv('YA_DISK_TOKEN'))
