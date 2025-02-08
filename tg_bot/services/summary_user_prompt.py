import re
import time
from datetime import datetime, timedelta

import pytz
import requests
from aiogram import Bot, types
from sqlalchemy.orm import sessionmaker
from yandex_cloud_ml_sdk import YCloudML

from tg_bot.config import load_config
from tg_bot.models import Message, engine

config = load_config(".env")
YANDEX_FOLDER_ID = config.yandex_api.folder_id
YANDEX_API_KEY = config.yandex_api.api_key

sdk = YCloudML(folder_id=YANDEX_FOLDER_ID, auth=YANDEX_API_KEY)


def check_data(item: str, today_date: str, days: int) -> str:
    date_match = re.search(r"\*\*Дата\*\*: (\d{2}\.\d{2}\.\d{4})", item)
    if not date_match:
        return item

    try:
        event_date = datetime.strptime(date_match.group(1), "%d.%m.%Y")
        today = datetime.strptime(today_date, "%d.%m.%Y")
        max_date = today + timedelta(days=days)
    except ValueError as e:
        raise ValueError(f"Ошибка парсинга даты: {e}") from e

    return item if today <= event_date <= max_date else ""


def remove_first_line(text: str) -> str:
    return "\n".join(text.split("\n")[1:]) if "\n" in text else text


async def get_chat_history(chat_id: int) -> list[dict]:
    try:
        with sessionmaker(bind=engine)() as session:
            messages = session.query(Message).filter(Message.chat_id == chat_id).all()
            return [
                {"text": msg.message_text, "date": msg.timestamp, "link": msg.link}
                for msg in messages
            ]
    except Exception as e:
        return []


async def yandex_gpt_summarize(
    text: str, user_prompt: str, message: types.Message = None, percent: int = None
) -> str:
    today_date = datetime.now(pytz.timezone("Europe/Moscow")).strftime("%d.%m.%Y")

    system_prompt = (
        "ВСЁ ЧТО ТЕБЕ НЕ ПОДХОДИТ ЗАМЕНИ НЕ **** пройдись по всем сообщениям "
        "и проработай их. ВЫПОЛНИВ ЗАПРОС ПОЛЬЗОВАТЕЛЯ!\n"
        "запрос отправляется в формате: [text]-[data]-[link]"
    )

    user_prompt = (
        "Запрос пользователя:\n"
        f"{user_prompt}\n"
        "Cообщения в формате [text] - [date] - [link]\n"
        f"{text}"
    )

    body = {
        "modelUri": f"gpt://{YANDEX_FOLDER_ID}/yandexgpt-32k/rc",
        "completionOptions": {
            "stream": False,
            "temperature": 0.44,
            "maxTokens": 2000000,
        },
        "messages": [
            {"role": "system", "text": system_prompt},
            {"role": "user", "text": user_prompt},
        ],
    }

    url = "https://llm.api.cloud.yandex.net/foundationModels/v1/completionAsync"
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Api-Key {YANDEX_API_KEY}",
    }

    try:
        response = requests.post(url, headers=headers, json=body)
        response.raise_for_status()
        operation_id = response.json().get("id")

        if message and percent:
            await message.edit_text(f"⏳ Обработка сообщений: {percent}%")

        while True:
            response = requests.get(
                f"https://llm.api.cloud.yandex.net:443/operations/{operation_id}",
                headers=headers,
            )
            response.raise_for_status()

            if response.json().get("done"):
                break
            time.sleep(0.5)

        result = response.json()["response"]["alternatives"][0]["message"]["text"]
        return result.replace("**Ссылка**: None", "") + "\n\n"

    except requests.exceptions.RequestException as e:
        return f"Ошибка API: {str(e)}"


async def summarize_messages(
    messages: list[dict],
    user_prompt: str,
    max_percent: int,
    percent_now: int,
    message: types.Message,
    batch_size: int = 50,
) -> str:
    unique_messages = []
    seen_texts = set()

    for msg in messages:
        if msg["text"] not in seen_texts:
            unique_messages.append(msg)
            seen_texts.add(msg["text"])

    summary_all = []
    for i in range(0, len(unique_messages), batch_size):
        batch = unique_messages[i : i + batch_size]
        batch_text = "\n".join(
            f'[{msg["text"]}] - [{msg["date"]}] - [{msg["link"]}]' for msg in batch
        )

        progress = (max_percent + percent_now * 2) // 3
        await _update_message(message, f"⏳ Обработка сообщений: {progress}%")

        summary = await yandex_gpt_summarize(batch_text, user_prompt, message, progress)
        summary_all.append(summary)

    final_summary = await yandex_gpt_summarize(
        "\n".join(summary_all), user_prompt, message, progress
    )
    return final_summary


async def process_chat_summary_user_prompt(
    chats: list[int], user_prompt: str, bot: Bot, message: types.Message
) -> None:
    status_message = await message.answer("⏳ Обработка сообщений...")
    summaries = []

    for index, chat_id in enumerate(chats, start=1):
        messages = await get_chat_history(chat_id)
        if not messages:
            continue

        max_percent = (index / len(chats)) * 100
        percent_now = ((index - 1) / len(chats)) * 100

        summary = await summarize_messages(
            messages, user_prompt, max_percent, percent_now, status_message
        )

        if summary.strip():
            summaries.append(summary)

    await _send_final_summary(status_message, summaries)


async def _update_message(message: types.Message, text: str) -> None:
    try:
        await message.edit_text(text)
    except Exception as e:
        pass


async def _send_final_summary(message: types.Message, summaries: list[str]) -> None:
    if not summaries:
        await message.edit_text("📊 Нет релевантных данных за выбранный период.")
        return

    final_summary = "\n------------------------------\n".join(summaries)
    try:
        await message.edit_text(f"📊 Итоговая выжимка:\n\n{final_summary}")
    except Exception:
        await message.answer(f"📊 Итоговая выжимка:\n\n{final_summary}")
