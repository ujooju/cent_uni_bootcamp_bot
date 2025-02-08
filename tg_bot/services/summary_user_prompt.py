import asyncio
import re
from aiogram import Bot, Dispatcher, types
from aiogram.contrib.fsm_storage.memory import MemoryStorage
from aiogram.dispatcher import FSMContext
from datetime import datetime, timedelta
import pytz
from sqlalchemy import select
from sqlalchemy.orm import sessionmaker
from tg_bot.models import engine, Message
from yandex_cloud_ml_sdk import YCloudML
import time
import requests
import os

TOKEN = os.getenv("TOKEN")
# YANDEX_FOLDER_ID = os.getenv("YANDEX_FOLDER_ID")
# YANDEX_API_KEY = os.getenv("YANDEX_API_KEY")
YANDEX_FOLDER_ID = "b1gug7c74crq38i2spt2"
YANDEX_API_KEY = "AQVN2VdnEpiYARjmZXK4bO4GYyeeIdPqcNba3pGY"
# print(YANDEX_FOLDER_ID, YANDEX_API_KEY)
sdk = YCloudML(folder_id=YANDEX_FOLDER_ID, auth=YANDEX_API_KEY)
def check_data(i, today_date, type_text):

    days = int(type_text)
    
    date_match = re.search(r'\*\*Дата\*\*: (\d{2}\.\d{2}\.\d{4})', i)
    if not date_match:
        return i
    event_date = datetime.strptime(date_match.group(1), "%d.%m.%Y")
    today = datetime.strptime(today_date, "%d.%m.%Y")
    min_date = today
    max_date = today + timedelta(days=days) 
    if min_date <= event_date <= max_date:
        return i
    else:
        return ""
    
def remove_first_line(i):
    lines = i.split("\n")
    if len(lines) > 1:
        return "\n".join(lines[1:])
    else:
        return i
    


async def get_chat_history(chat_id: int) -> list:
    try:
        session = sessionmaker(bind=engine)()
        result = session.query(Message).filter(Message.chat_id == chat_id).all()
        return [
            {"text": msg.message_text, "date": msg.timestamp, "link": msg.link}
            for msg in result
        ]
    except Exception as e:
        print(f"Ошибка получения истории: {e}")
        return []
    finally:
        session.close()

async def yandex_gpt_summarize(text: str, user_prompt: str, message: types.Message=None, percent=None) -> str:
    today_date = datetime.now(pytz.timezone("Europe/Moscow")).strftime("%d.%m.%Y")
    system_prompt = ( 
        "!ЗАМЕНИ ВСЕ МАТНЫЕ И НЕЦЕНЗУРНЫЕ СЛОВА НА ********"
        "!ЗАМЕНИ ВСЕ РЕАЛЬНЫЕ ИМЕНА, НАЦИОНАЛЬНОСТИ И СТРАНЫ НА ******"
        "!ЕСЛИ ЧТО-ТО НЕ УСТРАИВАЕТ В ЗАПРОСЕ, ЗАМЕНИ НА *****"
        "Ты — интеллектуальный ассистент, анализирующий весь контекст чата. "
        "Ваша задача — выполнить запрос пользователя, учитывая все доступные сообщения. "
        "Чат представлен в формате списка, где каждое сообщение включает текст, дату и ссылку на оригинал.\n\n"
        "**Твой процесс работы:**\n"
        "1. Проанализируй все предоставленные сообщения.\n"
        "2. Определи ключевые темы, упоминания, аргументы или другие значимые детали.\n"
        "3. Выполни запрос пользователя с учетом всей доступной информации.\n"
        "4. Если запрос требует вывода данных, сформируй его на основе сообщений из чата.\n\n"
    )
    user_prompt = (
        "Запрос пользователя:"
        f"{user_prompt}\n"
        "Cообщения в формате [text] - [date] - [link]"
        f"{text}"
    )

    body = {
        "modelUri": f"gpt://{YANDEX_FOLDER_ID}/yandexgpt-32k/rc",
        "completionOptions": {"stream": False, "temperature": 0.1, "maxTokens": 2000000},
        "messages": [
            {"role": "system", "text": system_prompt},
            {"role": "user", "text": user_prompt},
        ],
    }
    
    url = "https://llm.api.cloud.yandex.net/foundationModels/v1/completionAsync"
    headers = {"Content-Type": "application/json", "Authorization": f"Api-Key {YANDEX_API_KEY}"}
    response = requests.post(url, headers=headers, json=body)
    print(response)
    operation_id = response.json().get("id")
    if message:
        await message.edit_text(f"⏳ Обработка сообщений: {percent}%")
    
    while True:
        response = requests.get(f"https://llm.api.cloud.yandex.net:443/operations/{operation_id}", headers=headers)
        if response.json().get("done"):
            break
        time.sleep(0.5)
    data = response.json()["response"]["alternatives"][0]["message"]["text"].split("\n\n")
    text = ""
    for i in data:
        l = False
        if "**Ссылка**: None" in i:
            l = True
            text += i.replace("**Ссылка**: None", "") + "\n\n"
        else:
            text += str(i) + "\n\n"
    return text

async def summarize_messages(messages: list, user_prompt: str, max_percent: int, percent_now:int, message: types.Message, batch_size: int = 50) -> str:
    unique_messages = []
    seen_texts = set() 

    for msg in messages:
        if msg["text"] not in seen_texts:
            unique_messages.append(msg)
            seen_texts.add(msg["text"])
    all_text = "\n".join([f'[{msg["text"]}] - [{msg["date"]}] - [{msg["link"]}]' for msg in unique_messages])
    progress = (max_percent + percent_now*2)//3
    await message.edit_text(f"⏳ Обработка сообщений: {progress}%")
    progress = (max_percent*2 + percent_now)//3
    summary = await yandex_gpt_summarize(all_text, user_prompt, message, progress)
    
    return summary

async def process_chat_summary_user_prompt(chats: list[int], user_prompt: str, bot: Bot, message: types.Message):


    # await message.edit_reply_markup()
    message = await message.answer(f"⏳ Обработка сообщений ...")
    summaries = []
    total_chats = len(chats)
    
    for index, chat_id in enumerate(chats, start=1):
        messages = await get_chat_history(chat_id)
        if messages:
            max_percent = (index / total_chats) * 100
            percent_now = ((index-1) / total_chats) * 100
            summary = await summarize_messages(messages, user_prompt, max_percent, percent_now, message)
            if summary.strip():
                summaries.append(summary)
        progress = round((index / total_chats) * 100)
        await message.edit_text(f"⏳ Обработка сообщений: {progress}%")
    
    if summaries:
        final_summary = "\n------------------------------\n".join(summaries)
        await message.edit_text(f"📊 Итоговая выжимка:\n\n{final_summary}")
    else:
        await message.edit_text("📊 Нет релевантных данных за выбранный период.")

