import os

import gspread
import qrcode
from oauth2client.service_account import ServiceAccountCredentials

# Determine the full path to the JSON credentials file
credentials_file = os.path.join(os.getcwd(), "credentials.json")

# Set up Google Sheets API credentials
scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive", ]
creds = ServiceAccountCredentials.from_json_keyfile_name(credentials_file, scope)
client = gspread.authorize(creds)

# Connect to the Google Sheet by its title
sheet_title = "Participants data"
spreadsheet = client.open(sheet_title)
worksheet = spreadsheet.get_worksheet(0)  # assuming the data is in the first worksheet

# Get all the data from the Google Sheet
data = worksheet.get_all_records()

# Create a directory for storing QR codes if it doesn't exist
qr_code_directory = "qr_codes"
if not os.path.exists(qr_code_directory):
    os.mkdir(qr_code_directory)

# Generate QR codes for each row's data
for row in data:
    if row["_id"] == "":
        break
    # Create a formatted string for the data
    formatted_data = ""
    for key, value in row.items():
        if key == "image_url" or key == "mobile_number" or key == "email":
            continue
        formatted_data += f"{key}: {value}\n"

    # Generate a QR code for the formatted data
    qr = qrcode.QRCode(version=1, error_correction=qrcode.constants.ERROR_CORRECT_L, box_size=10, border=4, )
    qr.add_data(formatted_data)
    qr.make(fit=True)
    img = qr.make_image(fill_color="black", back_color="white")

    # Save the QR code image with a unique filename
    qr_code_filename = os.path.join(qr_code_directory, f"{row['_id']}.png")
    img.save(qr_code_filename)

print("The QR code has been generated successfully.")
