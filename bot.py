import logging
import asyncio
from datetime import datetime
import hashlib
import aiopg
from aiogram import Bot, Dispatcher, Router, types, exceptions
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.filters import Command, and_f, or_f
from aiogram.filters.state import StateFilter
from aiogram import F
from environs import Env
from datetime import datetime
from zoneinfo import ZoneInfo   

# Конфигурация бота
env = Env()
env.read_env()
logging.basicConfig(level=logging.INFO, 
                    format='[{asctime}] - {name} - {levelname} - {filename}:{lineno} - // {message}', 
                    style='{')
logger = logging.getLogger(__name__)

TOKEN = env('TOKEN')
DSN = env('DATABASE_DSN')
FERNET_KEY = env('FERNET_KEY').encode()

bot = Bot(token=TOKEN)
storage = MemoryStorage()
dp = Dispatcher(storage=storage)
router = Router()
dp.include_router(router)

class ComplaintForm(StatesGroup):
    title = State()
    location = State()
    department = State()
    incident_date = State()  
    description = State()
    amount = State()

# Подключениеи к базе данных
async def create_db_pool():
    return await aiopg.create_pool(DSN)

# Команда /start
@router.message(Command(commands=['start']))
async def start(message: types.Message, state: FSMContext):
    await state.clear()
    await message.reply("Приветствуем Вас!\nПожалуйста, введите краткое название вашей жалобы на взятку.\nНе волнуйтесь, мы не храним вашу личную информацию: она полностью зашифрована и анонимизирована.\nЕсли Вы не хотите отвечать на какой-либо вопрос, просто отправьте '-'.")
    await message.reply("Придумайте краткий заголовок вашей жалобе")
    await state.set_state(ComplaintForm.title)

@router.message(StateFilter(ComplaintForm.title))
async def process_title(message: types.Message, state: FSMContext):
    await state.update_data(title=message.text) 
    await message.reply("Где произошел инцидент?")
    await state.set_state(ComplaintForm.location)

@router.message(StateFilter(ComplaintForm.location))
async def process_location(message: types.Message, state: FSMContext):
    await state.update_data(location=message.text)
    await message.reply("Какой орган власти был замешан в инциденте? Используйте официальные названия.")
    await state.set_state(ComplaintForm.department)

@router.message(StateFilter(ComplaintForm.department))
async def process_department(message: types.Message, state: FSMContext):
    await state.update_data(department=message.text)
    await message.reply("Когда произошел инцидент? Ответ нужно дать в формате: ГГГГ-ММ-ДД ЧЧ:ММ)")
    await state.set_state(ComplaintForm.incident_date)

@router.message(StateFilter(ComplaintForm.incident_date))
async def process_incident_date(message: types.Message, state: FSMContext):
    incident_datetime_str = message.text
    try:
        incident_datetime = datetime.strptime(incident_datetime_str, "%Y-%m-%d %H:%M")
        await state.update_data(incident_date=incident_datetime.strftime("%Y-%m-%d %H:%M"))
        await message.reply("""
                        Пожалуйста, опишите ситуацию в деталях.\nОбратите внимание на следующие подробности:\n- что привело к ситуации взяточничества\n- по чьей инициативе возникла ситуация\n- способ взяточничества (прямое требование или подсказка/намек)\n- последствия инцидента (что вы получили / чего избежали)\n- другие подробности на ваше усмотрение\n
                        """)
        await state.set_state(ComplaintForm.description)
    except ValueError:
        await message.reply("Формат даты и времени неверен. Пожалуйста, дайте ответ в виде ГГГГ-ММ-ДД ЧЧ:ММ")
        await state.set_state(ComplaintForm.incident_date)

@router.message(StateFilter(ComplaintForm.description))
async def process_description(message: types.Message, state: FSMContext):
    await state.update_data(description=message.text)
    await message.reply("Какова была сумма взятки?")
    await state.set_state(ComplaintForm.amount)

# Финальный шаг
@router.message(and_f(StateFilter(ComplaintForm.amount), lambda message: message.text.replace('.', '', 1).isdigit()))
async def process_amount(message: types.Message, state: FSMContext):
    utc_now = datetime.now(ZoneInfo("UTC")).strftime("%Y-%m-%d %H:%M:%S %Z%z")
    await state.update_data(amount=message.text, date=utc_now)  
    data = await state.get_data()

    # Здесь происходит зашифрока user_id
    user_id_str = str(message.from_user.id).encode('utf-8')
    hashed_user_id = hashlib.sha256(user_id_str).hexdigest()
    data['hashed_user_id'] = hashed_user_id

    await store_complaint(data)
    await state.clear()
    await message.reply("Мы ценим Вашу помощь в борьбе с коррупцией. Ваша жалоба была зарегистрирована в анонимном формате.")

async def store_complaint(complaint):
    async with db_pool.acquire() as conn:
        async with conn.cursor() as cur:
            await cur.execute('''
                INSERT INTO complaints(encrypted_user_id, title, date, location, department, description, amount)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
            ''', (complaint['hashed_user_id'], complaint['title'], complaint['date'], complaint['location'], complaint['department'], complaint['description'], complaint['amount']))

async def main():
    global db_pool   
    db_pool = await create_db_pool()   
    try:
        await dp.start_polling(bot)
    finally:
        db_pool.close()
        await db_pool.wait_closed()

if __name__ == '__main__':
    asyncio.run(main())
