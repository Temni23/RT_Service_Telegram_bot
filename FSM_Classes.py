"""Классы для машины состояний."""
from aiogram.dispatcher.filters.state import StatesGroup, State


class KGMPickupStates(StatesGroup):
    """Класс для приема заявок от пользователя."""
    waiting_for_management_company = State()
    waiting_for_district = State()
    waiting_for_address = State()
    waiting_for_waste_type = State()
    waiting_for_comment = State()
    waiting_for_photo = State()
    waiting_for_confirmation = State()


class RegistrationStates(StatesGroup):
    """Класс для регистрации пользователя."""
    waiting_for_full_name = State()
    waiting_for_phone_number = State()
    waiting_for_workplace = State()
    confirmation_application = State()

class ComplaintFSM(StatesGroup):
    """Класс для приема жалоб."""
    choosing_complaint_type = State()
    choosing_no_collection_days = State()
    choosing_quality_issue = State()
    entering_address = State()
    uploading_photo = State()
    adding_comment = State()
    choosing_contact_method = State()
    entering_email = State()
    confirming_data = State()