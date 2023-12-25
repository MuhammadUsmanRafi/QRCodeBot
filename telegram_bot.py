import base64
import os
import sched
import tempfile
import threading
import time
from io import BytesIO

import cv2
import pymongo
from pyzbar.pyzbar import decode
from telebot import TeleBot
from telebot.types import Message

BOT_TOKEN = os.environ.get("BOT_TOKEN", "YOUR_BOT_TOKEN")

bot = TeleBot(token=BOT_TOKEN, num_threads=4)

message_ids = {}
process_state = {}

lock = threading.Lock()

scheduler = sched.scheduler(time.time, time.sleep)

# Connect to MongoDB
mongo_client = pymongo.MongoClient("mongodb://localhost:27017")
db = mongo_client["CUI_SAHIWAL"]
collection = db["Participants_collection"]
collection_2 = db["Incoming_Participants"]
collection_states = db["states"]


@bot.message_handler(commands=["start"])
def start(message: Message):
    start_message = ("👋 Hey there! I'm your *QR code bot.*\n\n"
                     "Ready for some QR action? 📷 Just send me a photo with a QR code!\n\n"
                     "To get started:\n"
                     "➡️ Type 'in' to enable entrance functionality.\n"
                     "➡️ Type 'out' to activate outgoing functionality.")

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


def save_process_state(chat_id, state):
    state_data = {"chat_id": chat_id, "state": state}
    collection_states.update_one({"chat_id": chat_id}, {"$set": state_data}, upsert=True)


def get_process_state(chat_id):
    state_data = collection_states.find_one({"chat_id": chat_id})
    return state_data.get("state") if state_data else None


def process_qr_data(qr_data, message):
    qr_data_message = f"ℹ️ Processed QR code data: {qr_data}"

    reply_bot = bot.reply_to(message, qr_data_message, parse_mode="Markdown")

    with lock:
        message_ids[message.chat.id] = message.message_id
        message_ids[reply_bot.chat.id] = reply_bot.message_id
        threading.Thread(target=delete_message, args=(message.chat.id, message.message_id)).start()
        threading.Thread(target=delete_message, args=(reply_bot.chat.id, reply_bot.message_id)).start()


@bot.message_handler(content_types=["photo", "text"])
def process_message(message: Message):
    global process_state

    saved_state = get_process_state(message.chat.id)
    if saved_state:
        process_state["state"] = saved_state

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
                if process_state['state'] == 'in':
                    matching_entry = collection.find_one(qr_data_formatted)
                    if matching_entry is not None and "_id" in matching_entry and "_id" in qr_data_formatted:
                        if matching_entry["_id"] == qr_data_formatted["_id"]:
                            qr_data_message = f"QR code data matched to\n{qr_data}\n\n*✅ You can enter!*"
                            image_base64 = matching_entry.get("image", "")
                            image_data = base64.b64decode(image_base64)
                            image_file = BytesIO(image_data)
                            send_data = qr_data_message.replace("_", "")
                            reply_bot = bot.send_photo(message.chat.id, image_file, caption=send_data,
                                                       parse_mode="Markdown")
                            collection.delete_one(qr_data_formatted)
                            updated_data = {"mobile_number": matching_entry.get("mobile_number", ""),
                                            "email": matching_entry.get("email", ""), "image": image_base64}
                            qr_data_formatted.update(updated_data)
                            collection_2.insert_one(qr_data_formatted)
                        else:
                            qr_data_message = f"QR code data does not match.\n{qr_data}\n\n*❌ You can't enter.*"
                            send_data = qr_data_message.replace("_", "")
                            reply_bot = bot.reply_to(message, send_data, parse_mode="Markdown")
                    else:
                        qr_data_message = f"QR code data not found in our database.\n{qr_data}\n\n*❌ You can't enter.*"
                        send_data = qr_data_message.replace("_", "")
                        reply_bot = bot.reply_to(message, send_data, parse_mode="Markdown")

                    with lock:
                        message_ids[message.chat.id] = message.message_id
                        message_ids[reply_bot.chat.id] = reply_bot.message_id
                        threading.Thread(target=delete_message, args=(message.chat.id, message.message_id)).start()
                        threading.Thread(target=delete_message, args=(reply_bot.chat.id, reply_bot.message_id)).start()
                elif process_state['state'] == 'out':
                    matching_entry = collection_2.find_one(qr_data_formatted)
                    if matching_entry:
                        collection.insert_one(matching_entry)
                        collection_2.delete_one(qr_data_formatted)
                        reply_bot = bot.reply_to(message, "✅ This person is authorized to re-enter using the "
                                                          "provided QR code.", parse_mode="Markdown")
                    else:
                        qr_data = qr_data.replace("_", "")
                        reply_bot = bot.reply_to(message, f"This individual does not have entry data or is not "
                                                          f"considered a valid person.\n{qr_data}\n\n*"
                                                          f"❌ You can't enter.*", parse_mode="Markdown")
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
        text = message.text.lower()
        if text == "out":
            save_process_state(message.chat.id, "out")
            bot.reply_to(message,
                         "Sure thing! 🤖🌟 This bot functionality will recognize when the user expresses a desire "
                         "to venture outdoors, and it will capture and document that intention for you. 📝🚀\n\n OUT",
                         parse_mode="Markdown")
        elif text == "in":
            save_process_state(message.chat.id, "in")
            bot.reply_to(message,
                         "Certainly! 🤖✨ This bot state will interpret as the participant expressing a desire to "
                         "enter, and it will efficiently record and document this intention for you. 📝🚪\n\n IN",
                         parse_mode="Markdown")
        else:
            bot.reply_to(message,
                         'Sure thing! 📩🤖 Simply send the text "in" or "out" to switch the bot\'s functionality '
                         'state. 🔄✨', parse_mode="Markdown")


def delete_message(chat_id, message_id):
    time.sleep(10)
    try:
        bot.delete_message(chat_id, message_id)
        with lock:
            if chat_id in message_ids:
                del message_ids[chat_id]
    except KeyError:
        pass


if __name__ == '__main__':
    print("BOT STARTED")
    bot.polling(none_stop=True)
