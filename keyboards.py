from aiogram.types import ReplyKeyboardMarkup, KeyboardButton


start_kb = ReplyKeyboardMarkup(resize_keyboard=True)
start_kb.add(KeyboardButton('add new task'))
start_kb.add(KeyboardButton('show current tasks'))
start_kb.add(KeyboardButton('show finished tasks'))

cancel_kb = ReplyKeyboardMarkup(resize_keyboard=True,one_time_keyboard=False)
cancel_kb.add(KeyboardButton('/cancel'))