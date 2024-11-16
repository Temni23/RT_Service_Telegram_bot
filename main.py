import logging
import os
from random import choice

from aiogram import Bot, Dispatcher, types
from aiogram.types import (InlineKeyboardButton, InlineKeyboardMarkup)
from aiogram.utils import executor
from aiogram.contrib.middlewares.logging import LoggingMiddleware
from aiogram.dispatcher import FSMContext
from aiogram.dispatcher.filters import Text, Command
from aiogram.contrib.fsm_storage.memory import MemoryStorage
from dotenv import load_dotenv
from datetime import datetime

from FSM_Classes import RegistrationStates, KGMPickupStates
from api_functions import upload_and_get_link, upload_information_to_gsheets
from bots_func import (get_main_menu, get_cancel, get_waste_type_keyboard,
                       download_photo)
from database_functions import is_user_registered, register_user, \
    save_kgm_request
from settings import (text_message_answers, YANDEX_CLIENT, YA_DISK_FOLDER,
                      DEV_TG_ID, GOOGLE_CLIENT, GOOGLE_SHEET_NAME,
                      database_path)

load_dotenv()

API_TOKEN = os.getenv('TELEGRAM_TOKEN')

logging.basicConfig(level=logging.INFO)

bot = Bot(token=API_TOKEN)
storage = MemoryStorage()
dp = Dispatcher(bot, storage=storage)

dp.middleware.setup(LoggingMiddleware())


###############################################################################
################# Обработка команд ############################################
###############################################################################

@dp.message_handler(commands=['start'])
async def send_welcome(message: types.Message):
    """
    Отрабатывает команду start.
    """
    user_id = message.from_user.id
    if is_user_registered(database_path, user_id):
        await message.reply("Добро пожаловать!, я приму вашу заявку",
                            reply_markup=get_main_menu())
    else:
        keyboard = InlineKeyboardMarkup().add(
            InlineKeyboardButton("Зарегистрироваться",
                                 callback_data="register")
        )
        await message.reply(
            "Добро пожаловать! Похоже, вы новый пользователь. Нажмите кнопку ниже для регистрации.",
            reply_markup=keyboard
        )


@dp.callback_query_handler(lambda callback: callback.data == 'cancel',
                           state="*")
async def cmd_cancel(callback: types.CallbackQuery, state: FSMContext) -> None:
    """
    Отрабатывает команду cancel и завершает текущее состояние.
    """
    current_state = await state.get_state()

    if current_state is not None:
        await state.finish()
        await callback.message.answer("Вы отменили текущую операцию.",
                                      reply_markup=get_main_menu())
    else:
        await callback.message.answer(
            "Сейчас нечего отменять. Попробуйте использовать главное меню.",
            reply_markup=get_main_menu())

    # Удаляем уведомление о нажатии кнопки, чтобы оно не оставалось висеть
    await callback.answer()


###############################################################################
################# Машина состояний регистрация ################################
###############################################################################

@dp.callback_query_handler(Text(equals="register"))
@dp.message_handler(Command("reg"))
async def start_registration(event: types.CallbackQuery | types.Message):
    if isinstance(event, types.CallbackQuery):
        user_id = event.from_user.id
        message = event.message
    elif isinstance(event, types.Message):
        user_id = event.from_user.id
        message = event
    else:
        # Если `event` не является `CallbackQuery` или `Message`
        logging.warning("Unknown event type")
        return

    if is_user_registered(database_path, user_id):
        await message.answer("Вы уже зарегистрированы! Я приму вашу заявку",
                             reply_markup=get_main_menu())
    else:
        await message.answer(
            "Пожалуйста, введите ваше полное имя (Фамилия Имя Отчество):",
            reply_markup=get_cancel()
        )
    await RegistrationStates.waiting_for_full_name.set()


@dp.message_handler(state=RegistrationStates.waiting_for_full_name)
async def get_full_name(message: types.Message, state: FSMContext):
    await state.update_data(full_name=message.text)
    await message.answer("Теперь введите ваш номер телефона:",
                         reply_markup=get_cancel())
    await RegistrationStates.waiting_for_phone_number.set()


@dp.message_handler(state=RegistrationStates.waiting_for_phone_number)
async def get_phone_number(message: types.Message, state: FSMContext):
    await state.update_data(phone_number=message.text)
    await message.answer("Теперь укажите ваше место работы:",
                         reply_markup=get_cancel())
    await RegistrationStates.waiting_for_workplace.set()


@dp.message_handler(state=RegistrationStates.waiting_for_workplace)
async def get_workplace(message: types.Message, state: FSMContext):
    await state.update_data(workplace=message.text)
    user_data = await state.get_data()
    full_name = user_data['full_name']
    phone_number = user_data['phone_number']
    workplace = user_data['workplace']

    # Подтверждение данных перед регистрацией
    keyboad = get_cancel()
    keyboad.add(InlineKeyboardButton(text='ВСЕ ВЕРНО!', callback_data='Верно'))
    await message.answer(
        f"Проверьте ваши данные:\n"
        f"ФИО: {full_name}\n"
        f"Номер телефона: {phone_number}\n"
        f"Место работы: {workplace}\n\n"
        f"Если все верно, нажмите 'ВСЕ ВЕРНО!'.", reply_markup=keyboad
    )
    await RegistrationStates.next()


@dp.callback_query_handler(lambda callback: callback.data == 'Верно',
                           state=RegistrationStates.confirmation_application)
async def confirm_registration(callback_query: types.CallbackQuery,
                               state: FSMContext):
    user_id = callback_query.from_user.id
    user_data = await state.get_data()
    full_name = user_data['full_name']
    phone_number = user_data['phone_number']
    workplace = user_data['workplace']
    username = callback_query.from_user.username

    try:
        register_user(database_path, user_id, full_name, phone_number, workplace,
                      username)
    except Exception as e:
        logging.error(
            e)  # TODO: Можно отправить сообщение об ошибке разработчику

    await callback_query.message.answer(
        "Вы успешно зарегистрированы и теперь можете пользоваться ботом!",
        reply_markup=get_main_menu()
    )
    await state.finish()
    await callback_query.answer("Регистрация завершена!")


##############################################################################
####################### Машина состояний заявка ##############################
##############################################################################

@dp.message_handler(commands=['kgm_request'])
@dp.callback_query_handler(lambda callback: callback.data == "kgm_request")
async def start_kgm_request(message: types.Message | types.CallbackQuery):
    """Начало процесса подачи заявки на вывоз отходов."""
    # Определяем источник (сообщение или callback)
    if isinstance(message, types.Message):
        # Обработчик для команды /kgm_request
        user_id = message.from_user.id
        if is_user_registered(database_path, user_id):
            await message.answer("Введите ваше Фамилию Имя Отчество:",
                                 reply_markup=get_cancel())
        else:
            keyboard = InlineKeyboardMarkup().add(
                InlineKeyboardButton("Зарегистрироваться",
                                     callback_data="register")
            )
            await message.reply(
                "Добро пожаловать! Похоже, вы новый пользователь. "
                "Нажмите кнопку ниже для регистрации.",
                reply_markup=keyboard
            )
            return

    elif isinstance(message, types.CallbackQuery):
        # Обработчик для callback
        user_id = message.from_user.id
        if is_user_registered(database_path, user_id):
            await message.message.answer("Введите ваше Фамилию Имя Отчество:",
                                         reply_markup=get_cancel())
        else:
            keyboard = InlineKeyboardMarkup().add(
                InlineKeyboardButton("Зарегистрироваться",
                                     callback_data="register")
            )
            await message.message.answer(
                "Добро пожаловать! Похоже, вы новый пользователь. "
                "Нажмите кнопку ниже для регистрации.",
                reply_markup=keyboard
            )
            return

    # Переход в состояние ожидания ФИО
    await KGMPickupStates.waiting_for_full_name.set()
    if isinstance(message, types.CallbackQuery):
        await message.answer()


@dp.message_handler(state=KGMPickupStates.waiting_for_full_name)
async def get_full_name(message: types.Message, state: FSMContext):
    await state.update_data(full_name=message.text)
    await message.answer("Теперь введите ваш номер телефона:",
                         reply_markup=get_cancel())
    await KGMPickupStates.waiting_for_phone_number.set()


@dp.message_handler(state=KGMPickupStates.waiting_for_phone_number)
async def get_phone(message: types.Message, state: FSMContext):
    await state.update_data(phone=message.text)
    await message.answer("Введите название вашей управляющей компании:",
                         reply_markup=get_cancel())
    await KGMPickupStates.waiting_for_management_company.set()


@dp.message_handler(state=KGMPickupStates.waiting_for_management_company)
async def get_management_company(message: types.Message, state: FSMContext):
    await state.update_data(management_company=message.text)
    await message.answer("Введите адрес вашего дома:",
                         reply_markup=get_cancel())
    await KGMPickupStates.waiting_for_address.set()


@dp.message_handler(state=KGMPickupStates.waiting_for_address)
async def get_address(message: types.Message, state: FSMContext):
    await state.update_data(address=message.text)
    await message.answer("Выберите тип отходов:",
                         reply_markup=get_waste_type_keyboard())
    await KGMPickupStates.waiting_for_waste_type.set()


@dp.callback_query_handler(
    lambda callback: callback.data.startswith("waste_type:"),
    state=KGMPickupStates.waiting_for_waste_type)
async def get_waste_type(callback_query: types.CallbackQuery,
                         state: FSMContext):
    waste_type = callback_query.data.split(":")[1]
    await state.update_data(waste_type=waste_type)
    await callback_query.message.answer(
        'При необходимости добавьте комментарий. Например: '
        '"Мебель у третьего подъезда МКД". '
        'Если в комментарии нет необходимости отправьте "Нет"',
        reply_markup=get_cancel())
    await KGMPickupStates.waiting_for_comment.set()


@dp.message_handler(state=KGMPickupStates.waiting_for_comment)
async def get_comment(message: types.Message, state: FSMContext):
    await state.update_data(comment=message.text)
    await message.answer(
        "Отправьте фото отходов. В данный момент я могу сохранить одну фотографию.",
        reply_markup=get_cancel())
    await KGMPickupStates.waiting_for_photo.set()


@dp.message_handler(content_types=['photo'],
                    state=KGMPickupStates.waiting_for_photo)
async def get_photo(message: types.Message, state: FSMContext):
    photo_file_id = message.photo[
        -1].file_id  # Получаем file_id для сохранения в БД
    await state.update_data(photo=photo_file_id)
    await state.update_data(username=message.from_user.username)

    # Получаем все данные, которые собрали, для подтверждения
    user_data = await state.get_data()
    confirmation_text = (
        f"Проверьте введенные данные:\n"
        f"ФИО: {user_data['full_name']}\n"
        f"Телефон: {user_data['phone']}\n"
        f"Управляющая компания: {user_data['management_company']}\n"
        f"Адрес дома: {user_data['address']}\n"
        f"Тип отходов: {user_data['waste_type']}\n\n"
        f"Комментарий: {user_data['comment']}\n\n"
        "Если все верно, нажмите 'Подтвердить'."
    )
    confirmation_keyboard = InlineKeyboardMarkup()
    confirmation_keyboard.add(
        InlineKeyboardButton(text="Подтвердить",
                             callback_data="confirm_data")).add(
        InlineKeyboardButton(text="Отмена", callback_data="cancel"))
    await message.answer_photo(photo=photo_file_id, caption=confirmation_text,
                               reply_markup=confirmation_keyboard)
    await KGMPickupStates.waiting_for_confirmation.set()



@dp.callback_query_handler(lambda callback: callback.data == "confirm_data",
                           state=KGMPickupStates.waiting_for_confirmation)
async def confirm_data(callback_query: types.CallbackQuery, state: FSMContext):
    user_data = await state.get_data()
    # Логика сохранения заявки в базу данных здесь
    await callback_query.message.answer(
        "Спасибо! Ваша заявка принята.",
        reply_markup=get_main_menu())
    await state.finish()
    await callback_query.answer()
    # Сохраняем фото на ЯДиск
    link_ya_disk = False
    try:
        downloaded_file = await download_photo(user_data['photo'], bot)
        link_ya_disk = upload_and_get_link(YANDEX_CLIENT, downloaded_file,
                                           YA_DISK_FOLDER)
    except Exception as e:
        logging.error(f"Ошибка при загрузке файла на Яндекс.Диск: {e}")
        await bot.send_message(DEV_TG_ID,
                               "Произошла ошибка при загрузке фото. Смотри логи.")
    # Сохраняем заявку в ГТаблицу
    g_data = [
        datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        'Телеграмм БОТ',
        user_data['full_name'],
        user_data['phone'],
        user_data['management_company'],
        user_data['address'],
        user_data['waste_type'],
        user_data['comment']
    ]
    if link_ya_disk:
        g_data.append(link_ya_disk)
    g_data.append(user_data['username'])
    # Сохраняем в базу данных заявку
    try:
        save_kgm_request(database_path, *g_data[2:])
    except Exception as e:
        logging.error(f"Ошибка при сохранении заявки в БД: {e}")
        lost_data = ' '.join(g_data)
        await bot.send_message(DEV_TG_ID,
                               "Произошла ошибка при сохранении заявки в БД. "
                               "Смотри логи." + lost_data)
    try:
        upload_information_to_gsheets(GOOGLE_CLIENT, GOOGLE_SHEET_NAME, g_data)
    except Exception as e:
        logging.error(f"Ошибка при загрузке файла на Гугл.Диск: {e}")
        lost_data = ' '.join(g_data)
        await bot.send_message(DEV_TG_ID,
                               "Произошла ошибка при загрузке на GD. "
                               "Смотри логи." + lost_data)


##############################################################################
##################### Работа с сообщениями####################################
##############################################################################

@dp.message_handler()
async def random_text_message_answer(message: types.Message) -> None:
    """
    Функция отправляет случайный ответ из предустановленного списка.

    На текстовое сообщение пользователя.
    """
    text = choice(text_message_answers)
    await message.reply(text=text, reply_markup=get_main_menu())


if __name__ == '__main__':
    executor.start_polling(dp, skip_updates=True)
