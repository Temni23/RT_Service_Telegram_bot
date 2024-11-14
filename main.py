import logging
import os
from aiogram import Bot, Dispatcher, types
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.utils import executor
from aiogram.contrib.middlewares.logging import LoggingMiddleware
from aiogram.dispatcher import FSMContext
from aiogram.dispatcher.filters import Text
from aiogram.contrib.fsm_storage.memory import MemoryStorage
from dotenv import load_dotenv

from FSM_Classes import RegistrationStates
from database_functions import is_user_registered, register_user

load_dotenv()

API_TOKEN = os.getenv('TELEGRAM_TOKEN')

# Configure logging
logging.basicConfig(level=logging.INFO)

# Initialize bot, storage, and dispatcher
bot = Bot(token=API_TOKEN)
storage = MemoryStorage()  # Инициализируем MemoryStorage
dp = Dispatcher(bot, storage=storage)  # Передаем storage в Dispatcher

# Optional: Add logging middleware
dp.middleware.setup(LoggingMiddleware())  # Логирование для отладки


@dp.message_handler(commands=['start'])
async def send_welcome(message: types.Message):
    user_id = message.from_user.id
    if is_user_registered('users.db', user_id):
        await message.reply("Вы уже зарегистрированы! Добро пожаловать!")
    else:
        keyboard = InlineKeyboardMarkup().add(
            InlineKeyboardButton("Зарегистрироваться",
                                 callback_data="register")
        )
        await message.reply(
            "Добро пожаловать! Похоже, вы новый пользователь. Нажмите кнопку ниже для регистрации.",
            reply_markup=keyboard
        )


@dp.callback_query_handler(Text(equals="register"))
async def start_registration(callback_query: types.CallbackQuery):
    await callback_query.message.answer(
        "Пожалуйста, введите ваше полное имя (Фамилия Имя Отчество):"
    )
    await RegistrationStates.waiting_for_full_name.set()


@dp.message_handler(state=RegistrationStates.waiting_for_full_name)
async def get_full_name(message: types.Message, state: FSMContext):
    await state.update_data(full_name=message.text)
    await message.answer("Теперь введите ваш номер телефона:")
    await RegistrationStates.waiting_for_phone_number.set()


@dp.message_handler(state=RegistrationStates.waiting_for_phone_number)
async def get_phone_number(message: types.Message, state: FSMContext):
    await state.update_data(phone_number=message.text)
    await message.answer("Теперь укажите ваше место работы:")
    await RegistrationStates.waiting_for_workplace.set()


@dp.message_handler(state=RegistrationStates.waiting_for_workplace)
async def get_workplace(message: types.Message, state: FSMContext):
    await state.update_data(workplace=message.text)
    user_data = await state.get_data()
    full_name = user_data['full_name']
    phone_number = user_data['phone_number']
    workplace = user_data['workplace']

    # Подтверждение данных перед регистрацией
    await message.answer(
        f"Проверьте ваши данные:\n"
        f"ФИО: {full_name}\n"
        f"Номер телефона: {phone_number}\n"
        f"Место работы: {workplace}\n\n"
        f"Если все верно, отправьте 'Подтверждаю'."
    )
    await RegistrationStates.next()


@dp.message_handler(lambda message: message.text.lower() == 'подтверждаю',
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
    await message.answer(
        "Вы успешно зарегистрированы и теперь можете пользоваться ботом!")
    await state.finish()


if __name__ == '__main__':
    executor.start_polling(dp, skip_updates=True)
