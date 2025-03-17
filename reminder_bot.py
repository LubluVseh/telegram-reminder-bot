from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from aiogram.types import Message
from aiogram.enums import ParseMode
from aiogram.client.default import DefaultBotProperties
from aiogram.utils.keyboard import ReplyKeyboardBuilder
from datetime import datetime, timedelta
import asyncio

# Укажи сюда токен своего бота
API_TOKEN = '7525745616:AAGOXdmThvJTWQmmK30skNLeLse6ImbbUh4'

# Инициализация бота с использованием DefaultBotProperties
bot = Bot(token=API_TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
dp = Dispatcher()

# Хранилище для напоминаний (временное, в памяти)
reminders = {}  # Ключ: user_id, значение: список напоминаний
user_states = {}  # Ключ: user_id, значение: текущее состояние

# Создаем клавиатуру с кнопками
def get_main_keyboard():
    builder = ReplyKeyboardBuilder()
    builder.button(text="Добавить напоминание")
    builder.button(text="Показать напоминания")
    builder.button(text="Удалить напоминание")
    builder.adjust(2)  # Располагаем кнопки в 2 столбца
    return builder.as_markup(resize_keyboard=True)  # Автоматически изменяем размер кнопок

# Команда /start
@dp.message(Command("start"))
async def cmd_start(message: Message):
    await message.answer(
        "Привет! Я бот для напоминаний. Выбери действие:",
        reply_markup=get_main_keyboard()  # Отправляем клавиатуру
    )

# Обработка кнопки "Добавить напоминание"
@dp.message(lambda message: message.text == "Добавить напоминание")
async def add_reminder_button(message: Message):
    await message.answer(
        "Напиши текст напоминания:",
        reply_markup=get_main_keyboard()
    )
    user_states[message.from_user.id] = {"step": "waiting_for_text"}

# Обработка текста напоминания
@dp.message(lambda message: message.from_user.id in user_states and user_states[message.from_user.id]["step"] == "waiting_for_text")
async def process_reminder_text(message: Message):
    user_id = message.from_user.id
    user_states[user_id]["text"] = message.text
    user_states[user_id]["step"] = "waiting_for_time"

    await message.answer(
        "Теперь укажи время напоминания в формате ЧЧ:ММ (например, 14:30):",
        reply_markup=get_main_keyboard()
    )

# Обработка времени напоминания
@dp.message(lambda message: message.from_user.id in user_states and user_states[message.from_user.id]["step"] == "waiting_for_time")
async def process_reminder_time(message: Message):
    user_id = message.from_user.id
    time_str = message.text

    try:
        # Парсим время
        reminder_time = datetime.strptime(time_str, "%H:%M").time()
        now = datetime.now()

        # Вычисляем datetime для напоминания
        reminder_datetime = datetime.combine(now.date(), reminder_time)
        if reminder_datetime < now:
            reminder_datetime += timedelta(days=1)  # Если время уже прошло, переносим на завтра

        # Создаем новое напоминание
        new_reminder = {
            "text": user_states[user_id]["text"],
            "time": reminder_datetime
        }

        # Добавляем напоминание в список
        if user_id not in reminders:
            reminders[user_id] = []
        reminders[user_id].append(new_reminder)

        await message.answer(
            f"✅ Напоминание добавлено: {new_reminder['text']} в {reminder_time.strftime('%H:%M')}.",
            reply_markup=get_main_keyboard()
        )

        # Запускаем задачу для отправки напоминания
        asyncio.create_task(send_reminder(user_id, new_reminder["text"], reminder_datetime))

        # Очищаем состояние пользователя
        del user_states[user_id]

    except ValueError:
        await message.answer(
            "❌ Неверный формат времени. Пожалуйста, укажи время в формате ЧЧ:ММ (например, 14:30).",
            reply_markup=get_main_keyboard()
        )

# Обработка кнопки "Показать напоминания"
@dp.message(lambda message: message.text == "Показать напоминания")
async def show_reminders_button(message: Message):
    user_id = message.from_user.id

    if user_id in reminders and reminders[user_id]:
        reminders_list = "\n".join(
            f"{i + 1}. {reminder['text']} в {reminder['time'].strftime('%H:%M')}"
            for i, reminder in enumerate(reminders[user_id])
        )
        await message.answer(
            f"Твои напоминания:\n{reminders_list}",
            reply_markup=get_main_keyboard()
        )
    else:
        await message.answer(
            "У тебя пока нет активных напоминаний.",
            reply_markup=get_main_keyboard()
        )

# Обработка кнопки "Удалить напоминание"
@dp.message(lambda message: message.text == "Удалить напоминание")
async def delete_reminder_button(message: Message):
    user_id = message.from_user.id

    if user_id in reminders and reminders[user_id]:
        await message.answer(
            "Введи номер напоминания, которое хочешь удалить:",
            reply_markup=get_main_keyboard()
        )
        user_states[user_id] = {"step": "waiting_for_reminder_index"}
    else:
        await message.answer(
            "❌ У тебя нет активных напоминаний для удаления.",
            reply_markup=get_main_keyboard()
        )

# Обработка номера напоминания для удаления
@dp.message(lambda message: message.from_user.id in user_states and user_states[message.from_user.id].get("step") == "waiting_for_reminder_index")
async def process_reminder_index(message: Message):
    user_id = message.from_user.id
    try:
        index = int(message.text) - 1  # Преобразуем в индекс (начинается с 0)
        if 0 <= index < len(reminders[user_id]):
            deleted_reminder = reminders[user_id].pop(index)
            await message.answer(
                f"✅ Напоминание удалено: {deleted_reminder['text']} в {deleted_reminder['time'].strftime('%H:%M')}.",
                reply_markup=get_main_keyboard()
            )
        else:
            await message.answer(
                "❌ Неверный номер напоминания.",
                reply_markup=get_main_keyboard()
            )
    except ValueError:
        await message.answer(
            "❌ Пожалуйста, введи номер напоминания.",
            reply_markup=get_main_keyboard()
        )

# Функция для отправки напоминания
async def send_reminder(user_id: int, text: str, reminder_datetime: datetime):
    now = datetime.now()
    delay = (reminder_datetime - now).total_seconds()

    if delay > 0:
        await asyncio.sleep(delay)  # Ждем до времени напоминания
        await bot.send_message(
            user_id,
            f"🔔 Напоминание: {text}",
            reply_markup=get_main_keyboard()
        )

    # Удаляем отправленное напоминание
    if user_id in reminders:
        reminders[user_id] = [
            reminder for reminder in reminders[user_id]
            if reminder["time"] != reminder_datetime
        ]

# Запуск бота
async def main():
    await dp.start_polling(bot)

if __name__ == '__main__':
    asyncio.run(main())