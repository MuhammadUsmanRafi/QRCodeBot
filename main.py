import os
from telebot import TeleBot
from pymongo import MongoClient
from pyzbar.pyzbar import decode
import cv2
import tempfile
import numpy as np

# Replace with your bot token and MongoDB connection details
BOT_TOKEN = os.environ.get("BOT_TOKEN", "YOUR_BOT_TOKEN")
MONGO_URI = "YOUR_MONGODB_URI"

# Initialize the Telegram Bot
bot = TeleBot(BOT_TOKEN)

# Connect to the MongoDB database
client = MongoClient(MONGO_URI)
db = client["party_db"]
participants_collection = db["participants"]


# Telegram message handler for processing QR code images
@bot.message_handler(content_types=["photo"])
def process_image(message):
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
        if decoded_objects:
            qr_data = decoded_objects[0].data.decode('utf-8')

            # Check if the scanned QR code exists in the database
            participant = participants_collection.find_one({"qr_code": qr_data})

            if participant:
                registration_number = participant.get("registration_number", "N/A")
                department = participant.get("department", "N/A")
                cell_number = participant.get("cell_number", "N/A")
                email_address = participant.get("email_address", "N/A")

                response_message = (
                    f"Welcome to , {participant['name']}!\n"
                    f"Registration number: {registration_number}\n"
                    f"Department: {department}\n"
                    f"Cell number: {cell_number}\n"
                    f"Email address: {email_address}\n"
                    "He/She allow to enter."
                )
                bot.reply_to(message, response_message)

                participants_collection.delete_one({"_id": participant["_id"]})  # Remove from the database
            else:
                bot.reply_to(message, "Sorry, your QR code doesn't match our records. You can't enter.")
        else:
            bot.reply_to(message, "No valid QR code found in the image.")
    else:
        bot.reply_to(message, "Error processing the image. Please make sure the image is valid.")


# Start the bot
if __name__ == '__main__':
    bot.polling(none_stop=True)
