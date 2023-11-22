import os
from telebot import TeleBot
from telebot.types import Message
from pyzbar.pyzbar import decode
import cv2
import tempfile

BOT_TOKEN = os.environ.get("BOT_TOKEN", "6536565219:AAF8XErOqDpKa88tfgtryYP5_m0_sMgMVh4")
AUTHORIZED_USERS = {5113829891}
group_chat_id = -4036315855

bot = TeleBot(BOT_TOKEN)


@bot.message_handler(commands=["start"])
def start(message: Message):
    bot.send_message(message.chat.id, "Hello! I am your QR code bot. Send me an image with a QR code.")


@bot.message_handler(content_types=["photo", "text"])
def process_message(message: Message):
    # Check if the user is authorized to use the bot in the group
    if message.chat.id == group_chat_id and message.from_user.id not in AUTHORIZED_USERS:
        bot.send_message(message.chat.id, "You are not authorized to use this bot in the group.")
        return

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
                bot.reply_to(message, f"Decoded QR code data: {', '.join(qr_data)}")
            else:
                bot.reply_to(message, "No QR code found in the image.")
        else:
            bot.reply_to(message, "Error processing the image. Please make sure the image is valid.")
    else:
        bot.reply_to(message, "Please send only images with QR codes.")


if __name__ == '__main__':
    bot.polling(none_stop=True)
