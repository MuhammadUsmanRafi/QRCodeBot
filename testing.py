import os
from telebot import TeleBot
from telebot.types import Message
from pyzbar.pyzbar import decode
import cv2
import tempfile
import threading
import sched
import time

BOT_TOKEN = os.environ.get("BOT_TOKEN", "6536565219:AAF8XErOqDpKa88tfgtryYP5_m0_sMgMVh4")

bot = TeleBot(token=BOT_TOKEN, num_threads=4)

message_ids = {}

lock = threading.Lock()

scheduler = sched.scheduler(time.time, time.sleep)

def delete_message(chat_id, message_id):
    time.sleep(20)
    try:
        bot.delete_message(chat_id, message_id)
        with lock:
            if chat_id in message_ids:
                del message_ids[chat_id]
    except KeyError:
        pass

@bot.message_handler(commands=["start"])
def start(message: Message):
    start_message = (
        "👋 Hello! I am your *QR code bot*.\n"
        "Send me a photo with a QR code."
    )
    bot.send_message(message.chat.id, start_message, parse_mode="Markdown")

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
                qr_data_message = f"🔍 Decoded QR code data:\n*{', '.join(qr_data)}*"
                reply_bot = bot.reply_to(message, qr_data_message, parse_mode="Markdown")

                with lock:
                    message_ids[message.chat.id] = message.message_id
                    message_ids[reply_bot.chat.id] = reply_bot.message_id
                    threading.Thread(target=delete_message, args=(message.chat.id, message.message_id)).start()
                    threading.Thread(target=delete_message, args=(reply_bot.chat.id, reply_bot.message_id)).start()
            else:
                bot.reply_to(message, "❌ No QR code found in the image.")
        else:
            bot.reply_to(message, "❌ Error processing the image. Please make sure the image is valid.")
    else:
        bot.reply_to(message, "❌ Please send only images with QR codes.")

if __name__ == '__main__':
    bot.polling(none_stop=True)
