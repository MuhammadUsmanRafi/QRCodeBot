import base64
import os

import gdown
import gspread
import pymongo
from oauth2client.service_account import ServiceAccountCredentials

# Determine the full path to the JSON credentials file
credentials_file = os.path.join(os.getcwd(), "credentials.json")

# Connect to MongoDB
mongo_client = pymongo.MongoClient("mongodb://localhost:27017/")
db = mongo_client["CUI_SAHIWAL"]
collection = db["Participants_collection"]

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

# Ensure the "images" directory exists
images_directory = os.path.join(os.getcwd(), "images")
os.makedirs(images_directory, exist_ok=True)

# Remove leading or extra spaces from each cell's values
for row in data:
    if 'image_url' in row:
        image_url = row['image_url']
        if image_url:
            try:
                # Extract the file ID from the Google Drive link
                file_id = image_url.split("/")[5]

                # Construct the direct download link
                direct_download_link = f"https://drive.google.com/uc?id={file_id}"

                # Ensure the "images" directory exists
                os.makedirs(images_directory, exist_ok=True)

                # Construct the image file path with the _id as the filename
                image_filename = f"{row['_id']}.jpg"
                image_path = os.path.join(images_directory, image_filename)

                # Download the image from Google Drive and save it with the _id as the filename
                gdown.download(direct_download_link, image_path, quiet=False)

                # Read the image file
                with open(image_path, "rb") as image_file:
                    # Encode the image to base64
                    base64_encoded = base64.b64encode(image_file.read()).decode("utf-8")
                    # Store the base64-encoded string in the row
                    row['image'] = base64_encoded

            except Exception as e:
                print(f"Error processing image: {e}")

            # Remove the 'image_url' key from the row
            del row['image_url']

    # Strip leading and trailing spaces from string values
    for key, value in row.items():
        if isinstance(value, str):
            row[key] = value.strip()

    if row["_id"] == "":
        break
    print(f"{row['_id']}, {row['name']}")
    # Insert the row into MongoDB
    collection.insert_one(row)

# Close MongoDB connection
mongo_client.close()

print("The Database has been successfully created")
