import concurrent.futures
import os
import smtplib
from email.mime.image import MIMEImage
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

import pymongo

# Connect to MongoDB
mongo_client = pymongo.MongoClient("mongodb://localhost:27017/")
db = mongo_client["CUI_SAHIWAL"]
collection = db["Participants_collection"]

# Email settings
sender_email = "musmanrajputt490@gmail.com"
subject = "Invitation to Unforgettable Welcome and Farewell Party - Follow these Exclusive Instructions"
body_template_path = "email_script.txt"

# Load email body template
with open(body_template_path, "r") as file:
    body_template = file.read()


def send_email(document):
    recipient_email = document["email"]
    recipient_name = document["name"]
    recipient_id = str(document["_id"])

    body = body_template.replace("[Name]", recipient_name)

    message = MIMEMultipart()
    message["From"] = sender_email
    message["To"] = recipient_email
    message["Subject"] = subject
    message.attach(MIMEText(body, "plain"))

    image_path = os.path.join("qr_codes", f"{recipient_id}.png")
    with open(image_path, "rb") as image_file:
        image = MIMEImage(image_file.read(), name=os.path.basename(image_path))
        message.attach(image)

    try:
        with smtplib.SMTP("smtp.gmail.com", 587) as server:
            server.starttls()
            server.login(sender_email, "iuox lzmd wzlr awrb")
            server.sendmail(sender_email, recipient_email, message.as_string())
        print(f"Email sent to {recipient_email} for {recipient_name}")
    except smtplib.SMTPRecipientsRefused as e:
        print(f"Error sending email to {recipient_email}: {e}")


if __name__ == "__main__":
    # Retrieve data from MongoDB
    data = collection.find()

    with concurrent.futures.ThreadPoolExecutor() as executor:
        future_to_document = {executor.submit(send_email, document): document for document in data}

        concurrent.futures.wait(future_to_document)

    print("All emails have been sent.")

mongo_client.close()
