import os
import sched
import tempfile
import threading
import time

import cv2
import pymongo
from pyzbar.pyzbar import decode
from telebot import TeleBot
from telebot.types import Message

BOT_TOKEN = os.environ.get("BOT_TOKEN", "6536565219:AAF8XErOqDpKa88tfgtryYP5_m0_sMgMVh4")

bot = TeleBot(token=BOT_TOKEN, num_threads=4)

message_ids = {}

lock = threading.Lock()

scheduler = sched.scheduler(time.time, time.sleep)

# Connect to MongoDB
mongo_client = pymongo.MongoClient("mongodb://localhost:27017")
db = mongo_client["CUI_SAHIWAL"]
collection = db["Participants_collection"]


@bot.message_handler(commands=["start"])
def start(message: Message):
    start_message = ("👋 Hello! I am your *QR code bot*.\n"
                     "Send me a photo with a QR code.")
    bot.send_message(message.chat.id, start_message, parse_mode="Markdown")


def convert_to_desired_format(qr_data):
    data = {}
    for line in qr_data.split("\n"):
        line = line.strip()
        if ":" in line:
            key, value = line.split(":", 1)
            key = key.strip()
            value = value.strip()
            if key == "mobile_number" or key == "email" or key == "department":
                continue
            data[key] = value
    return data


@bot.message_handler(content_types=["photo", "text"])
def process_message(message: Message):
    if message.content_type == "photo":
        photo_file = message.photo[-1].file_id
        file_info = bot.get_file(photo_file)
        file_path = file_info.file_path
        downloaded_image = bot.download_file(file_path)

        with tempfile.NamedTemporaryFile(delete=False) as temp_image:
            temp_image.write(downloaded_image)
            temp_image.seek(0)
            image = cv2.imread(temp_image.name)

        if image is not None:
            decoded_objects = decode(image)
            qr_data = [obj.data.decode('utf-8') for obj in decoded_objects]

            if qr_data:
                qr_data = qr_data[0]

                qr_data_formatted = convert_to_desired_format(qr_data)
                print(qr_data_formatted)
                matching_entry = collection.find_one(qr_data_formatted)
                print(matching_entry)

                if matching_entry is not None and "_id" in matching_entry and "_id" in qr_data_formatted:
                    if matching_entry["_id"] == qr_data_formatted["_id"]:
                        qr_data_message = f"✅ QR code data matched to\n{qr_data}\n\n*You can enter!*"
                    else:
                        qr_data_message = f"❌ QR code data does not match.\n{qr_data}\n\n*You can't enter.*"
                else:
                    qr_data_message = f"❌ QR code data not found in our database.\n{qr_data}\n\n*You can't enter.*"

                reply_bot = bot.reply_to(message, qr_data_message, parse_mode="Markdown")

                collection.delete_one(qr_data_formatted)

                with lock:
                    message_ids[message.chat.id] = message.message_id
                    message_ids[reply_bot.chat.id] = reply_bot.message_id
                    threading.Thread(target=delete_message, args=(message.chat.id, message.message_id)).start()
                    threading.Thread(target=delete_message, args=(reply_bot.chat.id, reply_bot.message_id)).start()
            else:
                reply_bot = bot.reply_to(message, "❌ No QR code found in the image.")
                with lock:
                    message_ids[message.chat.id] = message.message_id
                    message_ids[reply_bot.chat.id] = reply_bot.message_id
                    threading.Thread(target=delete_message, args=(message.chat.id, message.message_id)).start()
                    threading.Thread(target=delete_message, args=(reply_bot.chat.id, reply_bot.message_id)).start()
        else:
            bot.reply_to(message, "❌ Error processing the image. Please make sure the image is valid.")
    else:
        bot.reply_to(message, "❌ Please send only images with QR codes.")


def delete_message(chat_id, message_id):
    time.sleep(20)
    try:
        bot.delete_message(chat_id, message_id)
        with lock:
            if chat_id in message_ids:
                del message_ids[chat_id]
    except KeyError:
        pass


if __name__ == '__main__':
    bot.polling(none_stop=True)
