import logging
import sqlite3
from aiogram import Bot, Dispatcher, types
from aiogram.contrib.middlewares.logging import LoggingMiddleware
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
import logging.handlers
from aiogram.utils import executor
import keyboards
from aiogram.dispatcher.filters.state import StatesGroup, State
from aiogram.dispatcher import FSMContext
from aiogram.types import Message, CallbackQuery
from aiogram.contrib.fsm_storage.memory import MemoryStorage
import asyncio

# Логирование.
logger = logging.getLogger(__name__)

# Cоздаёт все промежуточные каталоги, если они не существуют.
logging.basicConfig(  # Чтобы бот работал успешно, создаём конфиг с базовыми данными для бота
    level=logging.INFO,
    format="[%(levelname)-8s %(asctime)s at           %(funcName)s]: %(message)s",
    datefmt="%d.%d.%Y %H:%M:%S",
    handlers=[logging.handlers.RotatingFileHandler("Logs/     TGBot.log", maxBytes=10485760, backupCount=0), logging.StreamHandler()])

# Инициализация бота и диспетчера
bot = Bot('5366109022:AAH_PzE6TcAUse11roxNQvgPmLgbFKLm2Us')
dp = Dispatcher(bot, storage=MemoryStorage())
logging.basicConfig(level=logging.INFO)
dp.middleware.setup(LoggingMiddleware())

# Инициализация базы данных SQLite3
conn = sqlite3.connect('predloshka.db') 
cursor = conn.cursor()

cursor.execute('''
    CREATE TABLE IF NOT EXISTS users (
        user_id INT,
        can_post BOOL
    )
''')

cursor.execute('''
    CREATE TABLE IF NOT EXISTS channels (
        channel_id INT,
        channel_name TEXT,
        referrer_link TEXT,
        admin_id INT
    )
''')
conn.commit()

admins = []

# Проверка на то, что юзер - админ канала.
async def channel_admin_check(message: types.Message):
        member = await bot.get_chat_member(message.chat.id, message.from_user.id)
        return member.is_chat_admin()

# Создаём состояния
class UserState(StatesGroup):
    write_post = State()
    write_nameUrl_for_post = State()
    write_url_for_post = State()
    write_channel_name = State()
    write_channel_id = State()

# Обработка команды /start
@dp.message_handler(commands=['start'], state="*")
async def start(message: types.Message, state: FSMContext):
    user_id = message.from_user.id

    if len(message.text) > 7: # Если пользователь перешёл по реф.ссылке
        await state.finish()
        channel_id = message.text[7:]
        channel_name = cursor.execute(f"SELECT channel_name FROM channels WHERE channel_id={channel_id}").fetchone()[0]
        
        if int(channel_id) in cursor.execute(f"SELECT channel_id FROM channels").fetchall()[0]:
            if cursor.execute(f"SELECT can_post FROM users WHERE user_id={user_id}").fetchone()[0] == True: # Если пользователь может предлагать идею
                await state.update_data(channel_id=channel_id)
                await state.update_data(channel_name=channel_name)
                await message.answer(f'Напиши пост, который ты хотел бы опубликовать в канале "{channel_name}"')
                await UserState.write_post.set()
            else: # Если он уже предлагал сегодня идею
                await message.answer(f'Ты можешь предложить только один пост в день для канала "{channel_name}"❗️')
        else:
            await message.answer("Ты перешёл по неправильной реферальной ссылке ❗️")
    else:
        if user_id not in admins:
            if cursor.execute(f"SELECT user_id FROM users WHERE user_id='{message.from_user.id}'").fetchone() is None:
                cursor.execute(f"INSERT INTO users ('user_id', 'can_post') VALUES(?, ?)", (message.from_user.id, True))
                conn.commit()

            keyboards.post_url_keyboard = InlineKeyboardMarkup(row_width=1)
            keyboards.post_url_keyboard.add(*[InlineKeyboardButton(
                text="Добавить ссылку к посту",
                callback_data="write_post__add_button"),
                InlineKeyboardButton(
                text="Отправить пост на модерацию", 
                callback_data="send_to_moderation")])
            await message.answer("Добро пожаловать в бота!", reply_markup=keyboards.user_keyboard)
        else:
            keyboard = InlineKeyboardMarkup()
            keyboard.add(InlineKeyboardButton(text="Админ меню", callback_data="admin_menu"))
            await message.answer("Добро пожаловать в бота!", reply_markup=keyboards.keyboard)

# Обработка команды /admin
@dp.message_handler(commands=['admin'])
async def admin_menu(message: types.Message):
    # Здесь вы можете предоставить доступ к администраторскому меню
    if message.from_user.id in admins:  # Замените на ID вашего администратора
        await message.answer("Администраторское меню:", reply_markup=keyboards.admin_keyboard)
    else:
        await message.answer("У вас нет доступа к администраторскому меню.")

# Функция для прикрепления для начала оформления поста
@dp.message_handler(state=UserState.write_post, content_types=types.ContentType.ANY)
async def get_post(message: Message, state: FSMContext):
    data = await state.get_data()
    print(3)
    if message.video:
        if "videos" not in data:
            videos = [message.media_group_id, message.video]
            await state.update_data(videos=videos)
        else:
            data = await state.get_data()
            videos = data["videos"]
            if videos[0] == message.media_group_id:
                videos.append(message.video)
                await state.update_data(videos=videos)

    elif message.photo:
        if "photos" not in data:
            photos = [message.media_group_id, message.photo[-1]]
            await state.update_data(photos=photos)
        else:
            data = await state.get_data()
            photos = data["photos"]
            if photos[0] == message.media_group_id:
                photos.append(message.photo[-1])
                await state.update_data(photos=photos)
                
    if "post_text" not in data:
        await state.update_data(post_text=message.text)
        await message.answer("Отлично, теперь ты можешь добавить ссылки к своему посту или сразу отправить его на модерацию")

    if "post_text" not in data and (message.photo or message.video): # Если пользователь отправил пост с фоткой
        await state.update_data(post_text=message.caption)
        await message.answer("Загружаю информацию... 🔄")
        # Получаем список фотографий в сообщении
        data = await state.get_data()

        await asyncio.sleep(1)
        if "post_text" not in data:
            await state.update_data(post_text=message.text)
        data = await state.get_data()

        if "media_flag" not in data:
            await state.update_data(media_flag=False)
            if message.photo:
                media = types.MediaGroup()
                photos = data["photos"]
                # Перебираем фотографии и обрабатываем их
                photos = photos[1:]
                print(photos)
                for photo in photos:
                    media.attach_photo(photo.file_id)

                if message.video:
                    videos = data["videos"]
                    videos = videos[1:]
                    for video in videos:
                        if video == videos[-1]:
                            if len(videos) > 1:
                                await message.answer_media_group(media=media)
                            await bot.send_video(message.from_user.id, video=message.video.file_id, caption=data["post_text"], reply_markup=keyboards.post_url_keyboard)   
                        else:
                            media.attach_video(video.file_id)
                else:
                    print(2)
                    if len(photos) > 1:
                        await message.answer_media_group(media=media)
                    await bot.send_photo(message.from_user.id, photo=photo.file_id, caption=data["post_text"], reply_markup=keyboards.post_url_keyboard)

            elif message.video:
                media = types.MediaGroup()
                data = await state.get_data()
                videos = data["videos"]
                videos = videos[1:]
                for video in videos:
                    if video == videos[-1]:
                        if len(videos) > 1:
                            await message.answer_media_group(media=media)
                        await bot.send_video(message.from_user.id, video=message.video.file_id, caption=data["post_text"], reply_markup=keyboards.post_url_keyboard)   
                    else:
                        media.attach_video(video.file_id)
                    
    if not message.video and not message.photo:
        await message.answer(message.text, reply_markup=keyboards.post_url_keyboard)

    await state.reset_state(with_data=False)


# Функция для записи имени ссылки
@dp.message_handler(state=UserState.write_nameUrl_for_post)
async def get_nameUrl_for_post(message: Message, state: FSMContext):
    await state.update_data(url_name=message.text)
    await message.answer("Отлично✅ \nТеперь отправь мне саму ссылку")
    await UserState.write_url_for_post.set()
    

# Функция для прикрепления ссылок к посту
@dp.message_handler(state=UserState.write_url_for_post)
async def get_url_for_post(message: Message, state: FSMContext):
    data = await state.get_data()
    try:
        keyboards.post_url_keyboard.add(InlineKeyboardButton(
            text=data["url_name"],
            url=message.text))
        await message.answer("Ссылка добавлена ✅ \nТы бы хотел добавить ещё?")

        if "photos" in data: # Если пользователь отправил пост с фоткой
            media = types.MediaGroup()
            data["photos"] = data["photos"][1:]
            for photo in data["photos"]:
                if photo == data["photos"][-1]:
                    if len(data["photos"]) > 1:
                        await message.answer_media_group(media=media)
                    await bot.send_photo(message.from_user.id, photo=photo.file_id, caption=data["post_text"], reply_markup=keyboards.post_url_keyboard)
                else:
                    media.attach_photo(photo.file_id)
    except:
        await message.answer("Произошла ошибка, попробуй ещё раз ❗️")


# Функция для получения имени канала
@dp.message_handler(state=UserState.write_channel_name)
async def get_channel_name(message: Message, state: FSMContext):
    await state.update_data(channel_name=message.text)
    await message.answer("Теперь тебе нужно отправить id своего канала")
    await UserState.write_channel_id.set()


# Функция для получения id канала
@dp.message_handler(state=UserState.write_channel_id)
async def get_channel_id(message: Message, state: FSMContext):
    await state.update_data(channel_id=message.text)
    data = await state.get_data()
    refferer_link = "https://t.me/teeeeeeestttttttttiinnngBot?start=" + message.text
    cursor.execute(f"INSERT INTO channels ('channel_id', 'channel_name', 'referrer_link', 'admin_id') VALUES(?, ?, ?, ?)", (data["channel_id"], data["channel_name"], refferer_link, message.from_user.id))
    conn.commit()
    await message.answer(f"Отлично ✅ Теперь, если я есть в твоём канале, то его пользователи смогут по реферальной ссылке предлагать свои идеи для постов. \nИндивидуальная реферальная ссылка твоего канала - {refferer_link}")
    await UserState.write_channel_id.set()


@dp.message_handler()
async def admin_menu_actions(message: types.Message):
    # Обработка кнопок администраторского меню
    if message.from_user.id in admins:  # Замените на ID вашего администратора
        if message.text == "Просмотр статистики":
            # Здесь реализуйте логику для просмотра статистики
            await message.answer("Статистика:")
        elif message.text == "Удаление/блокировка пользователя":
            # Здесь реализуйте логику для удаления/блокировки пользователя
            await message.answer("Введите username пользователя, которого хотите удалить/заблокировать:")
        elif message.text == "Выдача баланса":
            # Здесь реализуйте логику для выдачи баланса пользователю
            await message.answer("Введите username пользователя, которому хотите выдать баланс:")
        elif message.text == "Создание промокода":
            # Здесь реализуйте логику для создания промокода
            await message.answer("Промокод успешно создан.")
        elif message.text == "Отправка рассылки":
            # Здесь реализуйте логику для отправки рассылки
            await message.answer("Введите текст для рассылки.")

    elif await channel_admin_check(message): # Если юзер - админ канала
        await message.answer("Ты админ канала!")


# Когда пользователь нажимает на кнопку
@dp.callback_query_handler(state="*")
async def callback_worker(call: CallbackQuery, state: FSMContext):
    if call.data == "write_post__add_button":
        await call.message.answer("Отправь мне название ссылки, которую хочешь прикрепить к посту")
        await UserState.write_nameUrl_for_post.set()

    elif call.data == "add_channel":
        await call.message.edit_text("Напиши название своего канала")
        await UserState.write_channel_name.set()

    elif call.data == "send_to_moderation":
        data = await state.get_data()
        admin_id = cursor.execute(f'SELECT admin_id FROM channels WHERE channel_id={data["channel_id"]}').fetchone()[0]
        await bot.send_message(admin_id, f"Пользователь {call.from_user.username} прислал идею поста для канала {data['channel_name']}! \nТекст поста: \n{data['post_text']}")
        cursor.execute("UPDATE users SET can_post = ? WHERE user_id = ?",
                    (False, call.from_user.id))
        conn.commit()
        await call.message.delete()
        await call.message.answer("Пост отправлен на модерацию ✅ \nВам придёт уведомление, если пост будет одобрен или отклонён")
        await asyncio.sleep(86400) # Ждём день и разрешаем юзеру снова отправлять посты
        cursor.execute("UPDATE users SET can_post = ? WHERE user_id = ?",
            (True, call.from_user.id))
        conn.commit()
        await bot.send_message(call.from_user.id, f'Вы снова можете предложить идею для поста для канала "{data["channel_name"]}"✅')
        await state.finish()


if __name__ == "__main__":  # Если файл запускается как самостоятельный, а не как модуль
    # В консоле будет отоброжён процесс запуска бота
    logger.info("Запускаю бота...")
    executor.start_polling(  # Бот начинает работать
        dispatcher=dp,  # Передаем в функцию диспетчер
        # (диспетчер отвечает за то, чтобы сообщения пользователя доходили до бота)
        on_startup=logger.info("Загрузился успешно!"), skip_updates=True)
    # Если бот успешно загрузился, то в консоль выведется сообщение
