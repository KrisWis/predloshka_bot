from aiogram.types import ReplyKeyboardMarkup, InlineKeyboardButton, InlineKeyboardMarkup
admin_keyboard = ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
admin_keyboard.add("Просмотр статистики", "Удаление/блокировка пользователя")
admin_keyboard.add("Выдача баланса", "Создание промокода")
admin_keyboard.add("Отправка рассылки")

user_keyboard = InlineKeyboardMarkup(row_width=1)
user_keyboard.add(*[InlineKeyboardButton(
    text="Добавить канал",
    callback_data="add_channel"),
    InlineKeyboardButton(
    text="Посмотреть статистику канала", 
    callback_data="stats")])

channel_admin_keyboard = InlineKeyboardMarkup(row_width=1)
channel_admin_keyboard.add(*[InlineKeyboardButton(
    text="Принять",
    callback_data="channel_admin_accept"),
    InlineKeyboardButton(
    text="Отклонить", 
    callback_data="channel_admin_reject"),
    InlineKeyboardButton(
    text="Заблокировать", 
    callback_data="channel_admin_block")])