import logging
import os
from random import choice

from aiogram import Bot, Dispatcher, types
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.utils import executor
from aiogram.contrib.middlewares.logging import LoggingMiddleware
from aiogram.dispatcher import FSMContext
from aiogram.dispatcher.filters import Text
from aiogram.contrib.fsm_storage.memory import MemoryStorage
from dotenv import load_dotenv

from FSM_Classes import RegistrationStates
from bots_func import get_main_menu, get_cancel
from database_functions import is_user_registered, register_user
from settings import text_message_ansers

load_dotenv()

API_TOKEN = os.getenv('TELEGRAM_TOKEN')

logging.basicConfig(level=logging.DEBUG)

bot = Bot(token=API_TOKEN)
storage = MemoryStorage()
dp = Dispatcher(bot, storage=storage)

dp.middleware.setup(LoggingMiddleware())


@dp.message_handler(commands=['start'])
async def send_welcome(message: types.Message):
    user_id = message.from_user.id
    if is_user_registered('users.db', user_id):
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

@dp.callback_query_handler(lambda callback: callback.data == 'cancel', state="*")
async def cmd_cancel(callback: types.CallbackQuery, state: FSMContext) -> None:
    """
    Отрабатывает команду cancel и завершает текущее состояние.
    """
    # Получаем текущее состояние
    current_state = await state.get_state()

    # Проверяем, если есть активное состояние, завершаем его
    if current_state is not None:
        await state.finish()
        await callback.message.answer("Вы отменили текущую операцию.", reply_markup=get_main_menu())
    else:
        # Если нет активного состояния, выводим сообщение
        await callback.message.answer("Сейчас нечего отменять. Попробуйте использовать главное меню.", reply_markup=get_main_menu())

    # Удаляем уведомление о нажатии кнопки, чтобы оно не оставалось висеть
    await callback.answer()



###############################################################################
################# Машина состояний регистрация ################################
###############################################################################

@dp.callback_query_handler(Text(equals="register"))
async def start_registration(callback_query: types.CallbackQuery):
    user_id = callback_query.from_user.id
    if is_user_registered('users.db', user_id):
        await callback_query.message.answer("Вы уже зарегистрированы! "
                                            "Я приму вашу заявку",
                            reply_markup=get_main_menu())
    else:
        await callback_query.message.answer(
            "Пожалуйста, введите ваше полное имя (Фамилия Имя Отчество):",
            reply_markup=get_cancel()
        )
    await RegistrationStates.waiting_for_full_name.set()


@dp.message_handler(state=RegistrationStates.waiting_for_full_name)
async def get_full_name(message: types.Message, state: FSMContext):
    await state.update_data(full_name=message.text)
    await message.answer("Теперь введите ваш номер телефона:", reply_markup=get_cancel())
    await RegistrationStates.waiting_for_phone_number.set()


@dp.message_handler(state=RegistrationStates.waiting_for_phone_number)
async def get_phone_number(message: types.Message, state: FSMContext):
    await state.update_data(phone_number=message.text)
    await message.answer("Теперь укажите ваше место работы:", reply_markup=get_cancel())
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
async def confirm_registration(message: types.Message, state: FSMContext):
    user_id = message.from_user.id
    user_data = await state.get_data()
    full_name = user_data['full_name']
    phone_number = user_data['phone_number']
    workplace = user_data['workplace']
    username = message.from_user.username

    # Сохраняем данные в базе
    try:
        register_user('users.db', user_id, full_name, phone_number, workplace, username)
    except Exception as e:
        logging.error(e) # TODO Переделать на отправку ошибки разработчику
    await bot.send_message(message.from_user.id,
        "Вы успешно зарегистрированы и теперь можете пользоваться ботом!",
                           reply_markup=get_main_menu())
    await state.finish()

##############################################################################
##################### Работа с сообщениями

@dp.message_handler()
async def random_text_message_answer(message: types.Message) -> None:
    """
    Функция отправляет случайный ответ из предустановленного списка.

    На текстовое сообщение пользователя.
    """
    text = choice(text_message_ansers)
    await message.reply(text=text, reply_markup=get_main_menu())


if __name__ == '__main__':
    executor.start_polling(dp, skip_updates=True)
