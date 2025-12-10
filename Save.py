import sqlite3
import aiohttp
import re
import logging
from aiogram import Bot, Dispatcher, F
from aiogram.types import Message, BufferedInputFile
from aiogram.filters import CommandStart
import asyncio
import os

# Получаем токен из переменных окружения Railway
API_TOKEN = os.environ.get("API_TOKEN", "8393566752:AAEBV_v7S4PLWMOuu3HRcbvqAXyxSUma7ug")

bot = Bot(token=API_TOKEN)
dp = Dispatcher()

# Настройка логирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# --- Инициализация базы данных ---
def init_db():
    try:
        conn = sqlite3.connect("users.db")
        cursor = conn.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY,
                user_id INTEGER UNIQUE,
                username TEXT
            )
        """)
        conn.commit()
        conn.close()
        logger.info("База данных инициализирована")
    except Exception as e:
        logger.error(f"Ошибка инициализации БД: {e}")

def add_user(user_id: int, username: str):
    try:
        conn = sqlite3.connect("users.db")
        cursor = conn.cursor()
        cursor.execute("INSERT OR IGNORE INTO users (user_id, username) VALUES (?, ?)", (user_id, username))
        conn.commit()
        conn.close()
    except Exception as e:
        logger.error(f"Ошибка добавления пользователя: {e}")

# --- Обработчики ---
@dp.message(CommandStart())
async def start_cmd(message: Message):
    add_user(message.from_user.id, message.from_user.username or "NoUsername")
    await message.answer(
        "👋 Привет!\n\n"
        "📎 Я могу скачать фото/видео с Pinterest без водяных знаков.\n"
        "📤 Просто отправьте ссылку на пост!"
    )

@dp.message(F.text.regexp(r"https?://(www\.)?pin\.it/.*"))
async def handle_pinterest(message: Message):
    url = message.text.strip()
    logger.info(f"Получена ссылка: {url}")

    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url) as resp:
                if resp.status == 200:
                    content = await resp.text()

                    # Проверяем наличие видео
                    video_url = re.search(r'<video.*?src="(.*?)"', content)
                    if video_url:
                        async with session.get(video_url.group(1)) as vresp:
                            if vresp.status == 200:
                                video_data = await vresp.read()
                                video = BufferedInputFile(video_data, filename="pinterest.mp4")
                                await bot.send_video(message.chat.id, video)
                                return

                    # Проверяем наличие картинки
                    img_url = re.search(r'<img.*?src="(.*?)"', content)
                    if img_url:
                        async with session.get(img_url.group(1)) as iresp:
                            if iresp.status == 200:
                                img_data = await iresp.read()
                                photo = BufferedInputFile(img_data, filename="pinterest.jpg")
                                await bot.send_photo(message.chat.id, photo, caption='Спасибо, что пользуетесь ботом!')
                                await bot.send_document(message.chat.id, photo, caption='Для ценителей качества - изображение документом!')
                                return

                    await message.answer("❌ Не удалось найти медиа в этой ссылке.")
                else:
                    await message.answer("❌ Ошибка при получении данных с Pinterest.")
    except Exception as e:
        logger.error(f"Ошибка обработки Pinterest: {e}")
        await message.answer(f"⚠️ Ошибка: {e}")

async def main():
    logger.info("Запуск бота...")
    init_db()
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
