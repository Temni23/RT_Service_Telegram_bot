# RT_Service_Telegram_bot

Этот бот осуществляет прием заявок от зарегистрированных пользователей. Заявки сохраняются в Excel файл, опционально пересылаются на электронную почту или в Телеграмм чат. Ведет логирование.

## Описание:

Проект RT_Service_Telegram_bot выполнен Климовым А.В. Распространится в
ознакомительных целях. Коммерческое использование возможно только с согласия
автора.

Контакт автора temni23@yandex.ru

## Установка на windows:

Клонировать репозиторий и перейти в него в командной строке:

```

```

```
cd RT_Service_Telegram_bot
```

Создать и активировать виртуальное окружение:

```
python -m venv venv
```

```
source venv/Scripts/activate
```

Установить зависимости из файла requirements.txt:

```
python -m pip install --upgrade pip
```

```
pip install -r requirements.txt
```

## Работа с проектом

Создайте файл .env В этом файле добавьте переменную TELEGRAM_TOKEN в которую
стоокой сохраните токен вашего бота

Также создайте в этом файле переменные присвоив им СВОИ значения

```
EMAIL=your_text   #Используется для входа в почту с которой пересылается обращение пользователя
PASSWORD_EMAIL=your_text #Используется для входа в почту с которой пересылается обращение пользователя
TARGET_EMAIL=your_text   #Используется для отправки обращения пользователя на указанную почту
TARGET_TG=your_text  #Используется для отправки обращения пользователя в телеграмм ответственному лицу
```

# Работа с ботом через Докер

Бот может быть запущен с использованием Docker

Скопируйте файл docker-compose.yml на сервер с установленным docker и docker compose

Создайте файл constants.py в папке с файлом docker-compose.yml

Также создайте в этом файле переменные присвоив им СВОИ значения

```
EMAIL=django-your_text   #Используется для входа в почту с которой пересылается обращение пользователя
PASSWORD_EMAIL=your_text #Используется для входа в почту с которой пересылается обращение пользователя
TARGET_EMAIL=your_text   #Используется для отправки обращения пользователя на указанную почту
TARGET_TG=your_text  #Используется для отправки обращения пользователя в телеграмм ответственному лицу

Выполните команду

```
sudo docker compose up
```

Бот запустится в Docker контейнере.

Логи бота будут сохранены в volume logs
Контакты в volume contacts
