from aiogram.dispatcher.filters.state import StatesGroup, State

class TaskState(StatesGroup):
    header = State()
    description = State()
    date = State()
    time = State()
    is_periodic = State()
    attachments = State()
    interval = State()
    is_finished = State()

class PreEditState(StatesGroup):
    check = State()

class EditState(StatesGroup):
    check = State()
    description = State()
    date = State()
    time = State()
    attachments = State()

