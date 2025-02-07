import asyncio
import re
from aiogram import Bot, Dispatcher, types
from aiogram.contrib.fsm_storage.memory import MemoryStorage
from aiogram.dispatcher import FSMContext
from datetime import datetime, timedelta
import pytz
from sqlalchemy import select, and_
from sqlalchemy.orm import sessionmaker
from tg_bot.models import engine, Message
from yandex_cloud_ml_sdk import YCloudML
import time
import requests
import os

TOKEN = os.getenv("TOKEN")
YANDEX_FOLDER_ID = os.getenv("YANDEX_FOLDER_ID")
YANDEX_API_KEY = os.getenv("YANDEX_API_KEY")

sdk = YCloudML(folder_id=YANDEX_FOLDER_ID, auth=YANDEX_API_KEY)


async def get_chat_history(chat_id: int) -> list:
    """Получение истории сообщений из базы данных"""
    messages = []
    try:
        Session = sessionmaker()
        session = Session(bind=engine)

        # Выполняем запрос
        result = (
            session.query(Message)
            .filter(Message.chat_id == chat_id)
            .filter(Message.timestamp)
            .all()
        )
        messages = [{"text": msg.message_text, "date": msg.timestamp} for msg in result]

    except Exception as e:
        print(f"Ошибка получения истории: {e}")
    finally:
        session.close()

    return messages


async def yandex_gpt_summarize(text: str, type_text: str, type2_text: str) -> str:
    folder_id = YANDEX_FOLDER_ID
    api_key = YANDEX_API_KEY
    gpt_model = "yandexgpt-lite"

    system_prompt = f"Ты — помощник, который занимается распределением задач и извлечением важной информации из сообщений. Твоя задача — получить из следующего списка сообщений все точные {type2_text}, указав в ответе дату и время каждого из них. ВАЖНО!: ЕСЛИ ДАТА НЕ СОВПАДАЕТ С ПРОМЕЖУТКОМ, ЕЁ УКАЗЫВАТЬ НЕ НУЖНО, ЕСЛИ НИЧЕГО НЕТ, ТО ОТВЕТЬ ПУСТЫМ ОТВЕТОМ {type2_text} должны быть в пределах следующего временного интервала: с сегодняшнего дня (07.02.2025) в течение 1 {type_text}.Формат вывода:\nДата: [дата]\nОписание: [описание задачи]\nТочное время (если указано): [время]\nТеперь я отправлю тебе список сообщений. Извлеки из них точные {type2_text} с датами и временем (если они указаны), соответствующие указанному временному промежутку."
    user_prompt = text
    print(user_prompt)
    body = {
        "modelUri": f"gpt://{folder_id}/{gpt_model}",
        "completionOptions": {"stream": False, "temperature": 0.3, "maxTokens": 2000},
        "messages": [
            {"role": "system", "text": system_prompt},
            {"role": "user", "text": user_prompt},
        ],
    }
    url = "https://llm.api.cloud.yandex.net/foundationModels/v1/completionAsync"
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Api-Key {api_key}",
    }

    response = requests.post(url, headers=headers, json=body)
    operation_id = response.json().get("id")

    url = f"https://llm.api.cloud.yandex.net:443/operations/{operation_id}"
    headers = {"Authorization": f"Api-Key {api_key}"}

    while True:
        response = requests.get(url, headers=headers)
        print(response.json())
        done = response.json()["done"]
        if done:
            break
        time.sleep(2)

    data = response.json()
    answer = data["response"]["alternatives"][0]["message"]["text"]
    print(answer, "ANSWERRR")
    return answer


async def summarize_messages(
    messages: list, type_text: str, type2_text: str, batch_size: int = 50
) -> str:
    summaries = []
    for i in range(0, len(messages), batch_size):
        batch = messages[i : i + batch_size]
        batch_text = "\n".join([msg["text"] for msg in batch])
        summary = await yandex_gpt_summarize(batch_text, type_text, type2_text)
        summaries.append(summary)
        await asyncio.sleep(1)

    final_text = "\n".join(summaries)
    return await yandex_gpt_summarize(final_text, type_text, type2_text)


async def process_chat_summary(
    chat_id: int, user_id: int, days: str, type: str, bot: Bot
):
    try:
        type_text = ""
        if days == "period_month":
            type_text = "Месяца"
        if days == "period_week":
            type_text = "Недели"
        if days == "period_day":
            type_text = "Дня"

        type2_text = "Всё"
        if type == "deadlines":
            type2_text = "ДЕДЛАЙНЫ"
        if type == "dosug":
            type2_text = "ПРОВЕДЕНИЕ ДОСУГА"
        if type == "networking":
            type2_text = "НЕТВОРКИНГИ"
        print('\n\n\n', type2_text, type, '\n\n\n')
        message = await bot.send_message(
            user_id, f"⏳ Обработка сообщений за {type_text}..."
        )

        messages = await get_chat_history(chat_id)
        if not messages:
            await bot.send_message(
                user_id, "⚠️ Сообщений за выбранный период не найдено"
            )
            return
        summary = await summarize_messages(messages, type_text, type2_text)

        print(summary)
        await bot.send_message(user_id, f"📊 Итоговая выжимка:\n\n{summary[:4080]}")
    except Exception as e:
        print(f"Ошибка обработки: {e}")
