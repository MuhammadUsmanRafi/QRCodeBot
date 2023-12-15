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


# Function to process QR code data
def process_qr_data(qr_data, message):
    # Extracted QR data
    qr_data_message = f"ℹ️ Processed QR code data: {qr_data}"

    # Use bot.reply_to to send the reply message
    reply_bot = bot.reply_to(message, qr_data_message, parse_mode="Markdown")

    # Delete the original message and the reply after a delay
    with lock:
        # Store message IDs for deletion
        message_ids[message.chat.id] = message.message_id
        message_ids[reply_bot.chat.id] = reply_bot.message_id

        # Use threading to delete messages after a delay
        threading.Thread(target=delete_message, args=(message.chat.id, message.message_id)).start()
        threading.Thread(target=delete_message, args=(reply_bot.chat.id, reply_bot.message_id)).start()


# Handle incoming messages (photos or text)
@bot.message_handler(content_types=["photo", "text"])
def process_message(message: Message):
    # Check if the message contains a photo
    if message.content_type == "photo":
        # Get the file ID of the last photo in the message
        photo_file = message.photo[-1].file_id

        # Get file information for the photo
        file_info = bot.get_file(photo_file)
        file_path = file_info.file_path

        # Download the photo
        downloaded_image = bot.download_file(file_path)

        # Use a temporary file to store the downloaded image
        with tempfile.NamedTemporaryFile(delete=False) as temp_image:
            temp_image.write(downloaded_image)
            temp_image.seek(0)
            image = cv2.imread(temp_image.name)

        # Check if the image is valid
        if image is not None:
            # Decode QR codes from the image
            decoded_objects = decode(image)

            # Extract QR data from the decoded objects
            qr_data = [obj.data.decode('utf-8') for obj in decoded_objects]

            # Check if QR data is found in the image
            if qr_data:
                # Extract the first QR code data (assuming there is only one)
                qr_data = qr_data[0]

                # Format and process the QR data
                qr_data_formatted = convert_to_desired_format(qr_data)
                matching_entry = collection.find_one(qr_data_formatted)

                if matching_entry is not None and "_id" in matching_entry and "_id" in qr_data_formatted:
                    if matching_entry["_id"] == qr_data_formatted["_id"]:
                        qr_data_message = f"QR code data matched to\n{qr_data}\n\n*✅ You can enter!*"

                        # Retrieve and convert base64 image to send along with the reply
                        image_base64 = matching_entry.get("image", "")
                        image_data = base64.b64decode(image_base64)
                        image_file = BytesIO(image_data)

                        # Send the image along with the reply message
                        reply_bot = bot.send_photo(message.chat.id, image_file, caption=qr_data_message,
                                                   parse_mode="Markdown")
                        collection.delete_one(qr_data_formatted)
                    else:
                        qr_data_message = f"QR code data does not match.\n{qr_data}\n\n*❌ You can't enter.*"
                        reply_bot = bot.reply_to(message, qr_data_message, parse_mode="Markdown")
                else:
                    qr_data_message = f"QR code data not found in our database.\n{qr_data}\n\n*❌ You can't enter.*"
                    reply_bot = bot.reply_to(message, qr_data_message, parse_mode="Markdown")

                # Delete the original and reply messages after a delay
                with lock:
                    message_ids[message.chat.id] = message.message_id
                    message_ids[reply_bot.chat.id] = reply_bot.message_id
                    threading.Thread(target=delete_message, args=(message.chat.id, message.message_id)).start()
                    threading.Thread(target=delete_message, args=(reply_bot.chat.id, reply_bot.message_id)).start()
            else:
                # If no QR code is found in the image
                reply_bot = bot.reply_to(message, "❌ No QR code found in the image.")

                # Delete the original and reply messages after a delay
                with lock:
                    message_ids[message.chat.id] = message.message_id
                    message_ids[reply_bot.chat.id] = reply_bot.message_id
                    threading.Thread(target=delete_message, args=(message.chat.id, message.message_id)).start()
                    threading.Thread(target=delete_message, args=(reply_bot.chat.id, reply_bot.message_id)).start()
        else:
            # If there is an error processing the image
            bot.reply_to(message, "❌ Error processing the image. Please make sure the image is valid.")
    else:
        # If the message is not a photo
        bot.reply_to(message, "❌ Please send only images with QR codes.")


def delete_message(chat_id, message_id):
    time.sleep(30)
    try:
        bot.delete_message(chat_id, message_id)
        with lock:
            if chat_id in message_ids:
                del message_ids[chat_id]
    except KeyError:
        pass


if __name__ == '__main__':
    bot.polling(none_stop=True)
