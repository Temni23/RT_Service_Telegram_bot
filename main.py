import logging
import os
from datetime import datetime, timedelta
from random import choice

from aiogram import Bot, Dispatcher, types
from aiogram.contrib.fsm_storage.memory import MemoryStorage
from aiogram.contrib.middlewares.logging import LoggingMiddleware
from aiogram.dispatcher import FSMContext
from aiogram.dispatcher.filters import Text, Command
from aiogram.types import (InlineKeyboardButton, InlineKeyboardMarkup)
from aiogram.utils import executor
from dotenv import load_dotenv

from FSM_Classes import RegistrationStates, KGMPickupStates, ComplaintFSM
from api_functions import upload_and_get_link, upload_information_to_gsheets
from bots_func import (get_main_menu, get_cancel, get_waste_type_keyboard,
                       download_photo, get_district_name, get_coast_name,
                       is_valid_email, get_quality_complaint_keyboard,
                       get_no_collection_days_keyboard,
                       get_quality_issue_keyboard, get_cancel_keyboard,
                       get_confirmation_keyboard, get_no_comment_keyboard,
                       get_contact_method_keyboard, get_registration_keyboard)
from database_functions import (is_user_registered, register_user,
                                save_kgm_request, get_user_by_id,
                                save_quality_complaint)
from settings import (text_message_answers, YANDEX_CLIENT, YA_DISK_FOLDER,
                      DEV_TG_ID, GOOGLE_CLIENT, GOOGLE_SHEET_NAME,
                      database_path, log_file, waste_types, district_names,
                      districts_tz, TIMEDELTA, GOOGLE_SHEET_COMPLAINT_NAME,
                      YA_DISK_FOLDER_COMPLAINTS, GROUP_ID)

load_dotenv()

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,  # Уровень логирования
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    # Формат записи
    handlers=[
        logging.FileHandler(log_file, mode="a", encoding="utf-8"),
        # Логи в файл
        logging.StreamHandler()  # Логи в консоль
    ]
)

logger = logging.getLogger(__name__)  # Создаём объект логгера
logger.info("Логи будут сохраняться в файл: %s", log_file)

API_TOKEN = os.getenv('TELEGRAM_TOKEN')

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
        await message.reply("Добро пожаловать! "
                            "Я приму вашу заявку на вывоз КГМ \U0001F69B или обращения по качеству оказания услуг \U0001f514",
                            reply_markup=get_main_menu())
    else:
        keyboard = await get_registration_keyboard()
        await message.reply(
            "Добро пожаловать! Похоже, вы новый пользователь. "
            "Нажмите кнопку ниже для регистрации. "
            "Это не займет много времени \U0001F64F\U0001F64F\U0001F64F",
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
        await callback.message.answer("Вы отменили текущую операцию. "
                                      "Давайте начнем заново",
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
        await message.answer("Вы уже зарегистрированы! "
                             "Я приму вашу заявку \U0001F69B",
                             reply_markup=get_main_menu())
        return
    else:
        await message.answer(text="Начнем! \nОтветным сообщением направляйте"
                                  " мне нужную "
                                  "информацию, а я ее обработаю. "
                                  "\nПожалуйста, вводите "
                                  "верные данные, это очень важно для "
                                  "эффективности моей работы. \n\n"
                                  "1/3 Напишите Вашу Фамилию Имя и Отчество",
                             reply_markup=get_cancel())
    await RegistrationStates.waiting_for_full_name.set()


@dp.message_handler(lambda message: len(message.text) < 10,
                    state=RegistrationStates.waiting_for_full_name)
async def check_name(message: types.Message) -> None:
    """Проверяет ФИО на количество символов."""
    await message.answer(
        "Введите реальные ФИО в формате \n \U00002757 Фамилия Имя Отчество "
        "Это чрезвычайно важно.",
        reply_markup=get_cancel())


@dp.message_handler(state=RegistrationStates.waiting_for_full_name)
async def get_full_name(message: types.Message, state: FSMContext):
    await state.update_data(full_name=message.text)
    await message.answer(
        '2/3 \U0000260E Введите номер своего контактного телефона через "8" без '
        'пробелов, тире и прочих лишних знаков. Например "89231234567"',
        reply_markup=get_cancel())
    await RegistrationStates.waiting_for_phone_number.set()


@dp.message_handler(state=RegistrationStates.waiting_for_phone_number,
                    regexp=r'^(8|\+7)[\- ]?\(?\d{3}\)?[\- ]?\d{3}[\- ]?\d{2}[\- ]?\d{2}$')
async def get_phone_number(message: types.Message, state: FSMContext):
    """Функция отрабатывает если пользователь ввел валидный телефон."""
    await state.update_data(phone_number=message.text)
    await message.answer("3/3 Теперь укажите УК, ТСЖ, ТСН "
                         "или иное Ваше место работы:",
                         reply_markup=get_cancel())
    await RegistrationStates.waiting_for_workplace.set()


@dp.message_handler(state=RegistrationStates.waiting_for_phone_number)
async def check_phone(message: types.Message) -> None:
    """Проверяет номер телефона введенный пользователем."""
    await message.answer(
        "Введите корректный номер телефона без пробелов, скобок и тире."
        "Например: 89081234567",
        reply_markup=get_cancel())


@dp.message_handler(lambda message: len(message.text) < 5,
                    state=RegistrationStates.waiting_for_workplace)
async def check_workplace(message: types.Message) -> None:
    """Проверяет адрес введенное пользователем место работы на количество символов."""
    await message.answer(
        'Введите чуть больше информации. Пример: ООО "ЖКХ"',
        reply_markup=get_cancel())


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
        f"Проверьте информацию:\n"
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
        register_user(database_path, user_id, full_name, phone_number,
                      workplace,
                      username)
    except Exception as e:
        logging.error(e)
        await bot.send_message(DEV_TG_ID,
                               f"Произошла ошибка при регистрации пользователя "
                               f"{user_id}, {full_name}, {phone_number}, "
                               f"{workplace}, {username}")

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
            await message.answer(
                text="Начнем! \nОтветным сообщением направляйте"
                     " мне нужную "
                     "информацию, а я ее обработаю. "
                     "\nПожалуйста, вводите "
                     "верные данные, это очень важно для "
                     "эффективность моей работы. \n\n"
                     "1/6 \U00002764 Введите название управляющей "
                     "компании (УК, ТСЖ, ТСН)",
                reply_markup=get_cancel())
        else:
            keyboard = await get_registration_keyboard()
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
            await message.message.answer(
                text="Начнем! \U0001F60E \nОтветным сообщением направляйте"
                     " мне нужную "
                     "информацию, а я ее обработаю. "
                     "\nПожалуйста, вводите "
                     "верные данные, это очень важно для "
                     "эффективность моей работы. \n\n"
                     "1/6 Введите название управляющей компании (УК, ТСЖ, ТСН)",
                reply_markup=get_cancel())
        else:
            keyboard = await get_registration_keyboard()
            await message.message.answer(
                "Добро пожаловать! Похоже, вы новый пользователь. "
                "Нажмите кнопку ниже для регистрации.",
                reply_markup=keyboard
            )
            return

    # Переход в состояние ожидания УК
    await KGMPickupStates.waiting_for_management_company.set()
    if isinstance(message, types.CallbackQuery):
        await message.answer()


@dp.message_handler(lambda message: len(message.text) < 5,
                    state=KGMPickupStates.waiting_for_management_company)
async def kgm_check_management_company(message: types.Message) -> None:
    """Проверяет адрес введенное пользователем место работы на количество символов."""
    await message.answer(
        ' \U00002757 Введите чуть больше информации. Пример: ООО "ЖКХ"',
        reply_markup=get_cancel())


@dp.message_handler(state=KGMPickupStates.waiting_for_management_company)
async def get_management_company(message: types.Message, state: FSMContext):
    await state.update_data(management_company=message.text)
    await message.answer(
        "2/6 Выберете район в котором находятся КГО:",
        reply_markup=get_district_name(district_names))
    await KGMPickupStates.waiting_for_district.set()


@dp.callback_query_handler(
    lambda callback: callback.data.startswith("district:"),
    state=KGMPickupStates.waiting_for_district)
async def get_district(callback_query: types.CallbackQuery, state: FSMContext):
    district = callback_query.data.split(":")[1]
    await state.update_data(district=district)
    await callback_query.message.answer(
        "3/6 Напишите адрес для вывоза в формате \U00002757 Город, Улица,"
        " Дом \U00002757:",
        reply_markup=get_cancel())
    await KGMPickupStates.waiting_for_address.set()
    await callback_query.answer()


@dp.message_handler(lambda message: len(message.text) < 10,
                    state=KGMPickupStates.waiting_for_address)
async def kgm_check_address(message: types.Message) -> None:
    """Проверяет адрес введенный пользователем на количество символов."""
    await message.answer(
        'Введите правильный адрес в формате \n \U00002757 Город, Улица,'
        ' Дом \U00002757 \nЭто чрезвычайно важно для корректной '
        'работы с Вашим вопросом. \n Пример "Красноярск ул. Тельмана д. 1"',
        reply_markup=get_cancel())


@dp.message_handler(state=KGMPickupStates.waiting_for_address)
async def get_address(message: types.Message, state: FSMContext):
    await state.update_data(address=message.text)
    await message.answer("4/6 Выберите тип отходов:",
                         reply_markup=get_waste_type_keyboard(waste_types))
    await KGMPickupStates.waiting_for_waste_type.set()


@dp.callback_query_handler(
    lambda callback: callback.data.startswith("waste_type:"),
    state=KGMPickupStates.waiting_for_waste_type)
async def get_waste_type(callback_query: types.CallbackQuery,
                         state: FSMContext):
    waste_type = callback_query.data.split(":")[1]
    await state.update_data(waste_type=waste_type)
    await callback_query.message.answer(
        '5/6 \U0001F5E8 При необходимости добавьте комментарий. Например: '
        '"Мебель у третьего подъезда МКД". '
        'Если в комментарии нет необходимости отправьте "Нет"',
        reply_markup=get_cancel())
    await KGMPickupStates.waiting_for_comment.set()


@dp.message_handler(state=KGMPickupStates.waiting_for_comment)
async def get_comment(message: types.Message, state: FSMContext):
    await state.update_data(comment=message.text)
    await message.answer(
        "6/6 \U0001F381 Отправьте фото отходов. "
        "Много не нужно, достаточно одну фотографию.",
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
        f"\U000026A0 Район: {user_data['district']}\n"
        f"\U00002764 Управляющая компания: {user_data['management_company']}\n"
        f"\U00002757 Адрес дома: {user_data['address']}\n"
        f"\U0001F5D1 Тип отходов: {user_data['waste_type']}\n\n"
        f"\U0001F5E8 Комментарий: {user_data['comment']}\n\n"
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
    user_id = callback_query.from_user.id
    # Логика сохранения заявки в базу данных здесь
    await callback_query.message.answer(
        "Спасибо! Ваша заявка принята \U0001F9D9",
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
    # Получаем информацию о пользователе из базы данных
    user_info = get_user_by_id(user_id, database_path)
    # Получаем имя тех зоны
    coast = get_coast_name(districts_tz, user_data['district'])
    # Сохраняем заявку в ГТаблицу
    g_data = [
        (datetime.now() + timedelta(hours=TIMEDELTA)).strftime(
            "%Y-%m-%d %H:%M:%S"),
        'Телеграмм БОТ',
        user_info['full_name'],
        user_info['phone_number'],
        user_data['management_company'],
        user_data['address'],
        user_data['district'],
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
        upload_information_to_gsheets(GOOGLE_CLIENT, GOOGLE_SHEET_NAME[coast],
                                      g_data)
    except Exception as e:
        logging.error(f"Ошибка при загрузке файла на Гугл.Диск: {e}")
        lost_data = ' '.join(g_data)
        await bot.send_message(DEV_TG_ID,
                               "Произошла ошибка при загрузке на GD. "
                               "Смотри логи." + lost_data)


##############################################################################
####################### Машина состояний жалоба ##############################
################################################################################

@dp.callback_query_handler(
    lambda callback: callback.data == "quality_complaint", state="*")
async def start_complaint_process(callback: types.CallbackQuery,
                                  state: FSMContext):
    user_id = callback.from_user.id
    if is_user_registered(database_path, user_id):
        await callback.message.answer(
            text="Начнем! \nОтветным сообщением направляйте"
                 " мне нужную "
                 "информацию, а я ее обработаю. "
                 "\nПожалуйста, вводите "
                 "верные данные, это очень важно для "
                 "эффективность моей работы. \n\n"
                 "1/8 \U00002764 Выберите тип обращения:",
            reply_markup=await get_quality_complaint_keyboard())
    else:
        keyboard = await get_registration_keyboard()
        await callback.message.reply(
            "Добро пожаловать! Похоже, вы новый пользователь. "
            "Нажмите кнопку ниже для регистрации.",
            reply_markup=keyboard
        )
        await callback.answer()
        return
    await ComplaintFSM.waiting_complaint_type.set()
    await callback.answer()


@dp.callback_query_handler(state=ComplaintFSM.waiting_complaint_type)
async def complaint_type_chosen(callback: types.CallbackQuery,
                                state: FSMContext):
    await state.update_data(complaint_type=callback.data)
    if callback.data == "Невывоз":
        await callback.message.answer("2/8 Когда не вывезли ТКО?",
                                      reply_markup=await get_no_collection_days_keyboard())
        await ComplaintFSM.waiting_trouble.set()
        await callback.answer()

    elif callback.data == "Замечания":
        await callback.message.answer("2/8 Выберите тему замечания:",
                                      reply_markup=await get_quality_issue_keyboard())
        await ComplaintFSM.waiting_trouble.set()
        await callback.answer()


@dp.callback_query_handler(state=ComplaintFSM.waiting_trouble)
async def trouble_chosen(callback: types.CallbackQuery, state: FSMContext):
    if callback.data == "today":
        await callback.message.answer("Техника работает на линии, ожидайте.",
                                      # TODO Добавить санпин
                                      reply_markup=get_main_menu())
        await state.finish()
        return
    await state.update_data(trouble=callback.data)
    await callback.message.answer("3/8 С каким адресом связано обращение?",
                                  # TODO Привести к одному виду с КГМ
                                  reply_markup=get_cancel())
    await ComplaintFSM.waiting_address.set()
    await callback.answer()


@dp.message_handler(state=ComplaintFSM.waiting_address)
async def trouble_chosen(message: types.Message, state: FSMContext):
    await state.update_data(address=message.text)
    await message.answer(
        "4/8 Введите название управляющей компании (УК, ТСЖ, ТСН)",
        reply_markup=get_cancel())
    await ComplaintFSM.waiting_for_management_company.set()


@dp.message_handler(state=ComplaintFSM.waiting_for_management_company)
async def management_company_chosen(message: types.Message, state: FSMContext):
    await state.update_data(management_company=message.text)
    await message.answer(
        "5/8 Выберете район с которым связано обращение:",
        reply_markup=get_district_name(district_names))
    await ComplaintFSM.waiting_for_district.set()


@dp.callback_query_handler(state=ComplaintFSM.waiting_for_district)
async def address_entered(callback: types.CallbackQuery, state: FSMContext):
    await state.update_data(district=callback.data.split(":")[1])
    await callback.message.answer("6/8 Отправьте фото с фиксацией проблемы",
                                  reply_markup=await get_cancel_keyboard())
    await ComplaintFSM.waiting_photo.set()
    await callback.answer()


@dp.message_handler(content_types=types.ContentType.PHOTO,
                    state=ComplaintFSM.waiting_photo)
async def photo_uploaded(message: types.Message, state: FSMContext):
    await state.update_data(photo=message.photo[-1].file_id)
    await message.answer("7/8 Добавьте комментарий с описанием проблемы",
                         reply_markup=await get_no_comment_keyboard())
    await ComplaintFSM.waiting_comment.set()


# Обработка текстового комментария
@dp.message_handler(state=ComplaintFSM.waiting_comment)
async def comment_entered(message: types.Message, state: FSMContext):
    await state.update_data(comment=message.text)
    await message.answer("8/8 Выберете способ обратной связи",
                         reply_markup=await get_contact_method_keyboard())
    await ComplaintFSM.waiting_contact_method.set()


# Обработка комментария по кнопке
@dp.callback_query_handler(state=ComplaintFSM.waiting_comment)
async def comment_clicked(callback: types.CallbackQuery, state: FSMContext):
    await state.update_data(comment=callback.data)
    await callback.message.answer("8/8 Выберете способ обратной связи",
                                  reply_markup=await get_contact_method_keyboard())
    await ComplaintFSM.waiting_contact_method.set()
    await callback.answer()


@dp.callback_query_handler(state=ComplaintFSM.waiting_contact_method)
async def contact_method_chosen(callback: types.CallbackQuery,
                                state: FSMContext):
    if callback.data == "email":
        await state.update_data(contact_method=callback.data)
        await callback.message.answer("* Введите email для обратной связи:",
                                      reply_markup=await get_cancel_keyboard())
        await ComplaintFSM.waiting_email.set()
    else:
        await state.update_data(contact_method=callback.data)
        user_data = await state.get_data()
        photo_file_id = user_data.get('photo', 'photo missed')
        confirmation_text = (
            f"Проверьте введенные данные:\n"
            f"\U0001F5D1 Тип обращения: {user_data.get('complaint_type', 'Не указано')}\n"
            f"\U00002b50 Суть обращения: {user_data.get('trouble', 'Не указано')}\n"
            f"\U000026A0 Район: {user_data.get('district', 'Не указан')}\n"
            f"\U00002764 Управляющая компания: {user_data.get('management_company', 'Не указана')}\n"
            f"\U00002757 Адрес дома: {user_data.get('address', 'Не указан')}\n"
            f"\U0001F5E8 Комментарий: {user_data.get('comment', 'Отсутствует')}\n"
            f"\U00002712 Способ обратной связи: {user_data.get('contact_method', 'Не выбран')}\n\n"
            "Если все верно, нажмите 'Подтвердить'."
        )
        keyboard = await get_confirmation_keyboard()
        if '@' in callback.from_user.mention:
            keyboard.add(
                InlineKeyboardButton("Телеграм", callback_data="Телеграм"))

        await callback.message.answer_photo(photo=photo_file_id,
                                            caption=confirmation_text,
                                            reply_markup=keyboard)
        await ComplaintFSM.waiting_for_confirmation.set()
        await callback.answer()


@dp.message_handler(state=ComplaintFSM.waiting_email)
async def email_entered(message: types.Message, state: FSMContext):
    email = message.text.strip()
    if is_valid_email(email):
        await state.update_data(email=email)
        user_data = await state.get_data()
        photo_file_id = user_data.get('photo', 'photo missed')
        confirmation_text = (
            f"Проверьте введенные данные:\n"
            f"\U0001F5D1 Тип обращения: {user_data.get('complaint_type', 'Не указано')}\n"
            f"\U00002b50 Суть обращения: {user_data.get('trouble', 'Не указано')}\n"
            f"\U000026A0 Район: {user_data.get('district', 'Не указан')}\n"
            f"\U00002764 Управляющая компания: {user_data.get('management_company', 'Не указана')}\n"
            f"\U00002757 Адрес дома: {user_data.get('address', 'Не указан')}\n"
            f"\U0001F5E8 Комментарий: {user_data.get('comment', 'Отсутствует')}\n"
            f"\U00002712 Способ обратной связи: "
            f"{user_data.get('contact_method', 'Не выбран')}: {user_data.get('email', 'email не выбран')} \n\n"
            "Если все верно, нажмите 'Подтвердить'."
        )
        keyboard = await get_confirmation_keyboard()
        if '@' in message.from_user.mention:
            keyboard.add(
                InlineKeyboardButton("Телеграм", callback_data="Телеграм"))

        await message.answer_photo(photo=photo_file_id,
                                            caption=confirmation_text,
                                            reply_markup=keyboard)
        await ComplaintFSM.waiting_for_confirmation.set()
    else:
        await message.answer(
            "Некорректный email. Пожалуйста, введите корректный адрес электронной почты:",
            reply_markup=await get_cancel_keyboard())


@dp.callback_query_handler(lambda callback: callback.data == "confirm_data",
                           state=ComplaintFSM.waiting_for_confirmation)
async def confirm_data(callback: types.CallbackQuery, state: FSMContext):
    user_data = await state.get_data()
    user_id = callback.from_user.id
    # Логика сохранения заявки в базу данных здесь
    await callback.message.answer(
        "Спасибо! Ваша заявка принята \U0001F9D9",
        reply_markup=get_main_menu())
    await state.finish()
    await callback.answer()

    forward_text = (
        f"Ботом получено обращение:\n"
        f"\U0001F5D1 Тип обращения: {user_data.get('complaint_type', 'Не указано')}\n"
        f"\U00002b50 Суть обращения: {user_data.get('trouble', 'Не указано')}\n"
        f"\U000026A0 Район: {user_data.get('district', 'Не указан')}\n"
        f"\U00002764 Управляющая компания: {user_data.get('management_company', 'Не указана')}\n"
        f"\U00002757 Адрес дома: {user_data.get('address', 'Не указан')}\n"
        f"\U0001F5E8 Комментарий: {user_data.get('comment', 'Отсутствует')}\n"
        f"\U00002712 Способ обратной связи: "
        f"{user_data.get('contact_method', 'Не выбран')}: {user_data.get('email', 'email не выбран')} \n\n"
    )
    # Пересылаем обращение в группу сотрудников
    await bot.send_photo(chat_id=GROUP_ID, photo=user_data['photo'],
                         caption=forward_text)

    # Сохраняем фото на ЯДиск
    link_ya_disk = False
    try:
        downloaded_file = await download_photo(user_data['photo'], bot)
        link_ya_disk = upload_and_get_link(YANDEX_CLIENT, downloaded_file,
                                           YA_DISK_FOLDER_COMPLAINTS)
    except Exception as e:
        logging.error(f"Ошибка при загрузке файла на Яндекс.Диск: {e}")
        await bot.send_message(DEV_TG_ID,
                               "Произошла ошибка при загрузке фото. Смотри логи.")
    # Получаем информацию о пользователе из базы данных
    user_info = get_user_by_id(user_id, database_path)
    # Получаем имя тех зоны
    coast = get_coast_name(districts_tz, user_data['district'])

    # Сохраняем заявку в ГТаблицу
    g_data = [
        (datetime.now() + timedelta(hours=TIMEDELTA)).strftime(
            "%Y-%m-%d %H:%M:%S"),
        coast,
        'Телеграмм БОТ',
        user_info.get('full_name', 'Не указан'),
        user_info.get('phone_number', 'Не указан'),
        user_data.get('management_company', 'Не указана'),
        user_data.get('address', 'Не указан'),
        user_data.get('district', 'Не указан'),
        user_data.get('complaint_type', 'Не указан'),
        user_data.get('trouble', 'Не указано'),
        user_data.get('comment', 'Нет комментария'),
        user_data.get('contact_method', 'Не указан'),
        user_data.get('email', 'Не указан')  # email перед photo_link
    ]

    if link_ya_disk:
        g_data.append(link_ya_disk)  # Добавляем фото, если есть

    g_data.append(user_info.get('username', 'Не указан'))

    # Сохраняем в базу данных жалобу
    try:
        save_quality_complaint(database_path, *g_data[3:])
    except Exception as e:
        logging.error(f"Ошибка при сохранении жалобы в БД: {e}")
        lost_data = ' '.join(g_data)
        await bot.send_message(DEV_TG_ID,
                               "Произошла ошибка при сохранении жалобы в БД. "
                               "Смотри логи." + lost_data)
    try:
        upload_information_to_gsheets(GOOGLE_CLIENT,
                                      GOOGLE_SHEET_COMPLAINT_NAME,
                                      g_data)
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
