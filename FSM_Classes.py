"""Классы для машины состояний."""
from aiogram.dispatcher.filters.state import StatesGroup, State


class MessageStatesGroup(StatesGroup):
    """Класс для приема заявок от пользователя."""

    address = State()
    name = State()
    phone = State()
    consumer_email = State()
    question = State()
    feedback = State()
    confirmation = State()


class RegistrationStates(StatesGroup):
    """Класс для регистрации пользователя."""
    waiting_for_full_name = State()
    waiting_for_phone_number = State()
    waiting_for_workplace = State()
    confirmation_application = State()
