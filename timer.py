import os
import time
from telebot import TeleBot
from telebot.types import Message
from pyzbar.pyzbar import decode
import cv2
import tempfile

BOT_TOKEN = os.environ.get("BOT_TOKEN", "6536565219:AAF8XErOqDpKa88tfgtryYP5_m0_sMgMVh4")

bot = TeleBot(BOT_TOKEN)
message_ids_to_delete = {}


@bot.message_handler(commands=["delete"])
def delete_messages(message: Message):
    chat_id = message.chat.id
    if chat_id in message_ids_to_delete:
        for message_id in message_ids_to_delete[chat_id]:
            bot.delete_message(chat_id, message_id)
        message_ids_to_delete[chat_id].clear()
        bot.reply_to(message, "Deleted QR code data messages.")


@bot.message_handler(commands=["start"])
def start(message: Message):
    chat_id = message.chat.id
    if chat_id not in message_ids_to_delete:
        message_ids_to_delete[chat_id] = []
    message_ids_to_delete[chat_id].append(message.message_id)
    reply_message = bot.send_message(chat_id, "Hello! I am your QR code bot. Send me an image with a QR code.")
    message_ids_to_delete[chat_id].append(reply_message.message_id)


@bot.message_handler(content_types=["photo", "text"])
def process_message(message: Message):
    chat_id = message.chat.id
    if chat_id not in message_ids_to_delete:
        message_ids_to_delete[chat_id] = []

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
                message_ids_to_delete[chat_id].append(message.message_id)

                reply_message = bot.reply_to(message, f"Decoded QR code data: {', '.join(qr_data)}")
                message_ids_to_delete[chat_id].append(reply_message.message_id)
            else:
                bot.reply_to(message, "No QR code found in the image.")
        else:
            bot.reply_to(message, "Error processing the image. Please make sure the image is valid.")
    else:
        message_ids_to_delete[chat_id].append(message.message_id)
        reply_message = bot.reply_to(message, "Please send only images with QR codes.")
        message_ids_to_delete[chat_id].append(reply_message.message_id)


if __name__ == '__main__':
    bot.polling(none_stop=True)
