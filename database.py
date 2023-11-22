import pymongo
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import os

# Determine the full path to the JSON credentials file
credentials_file = os.path.join(os.getcwd(), "credentials.json")

# Connect to MongoDB
mongo_client = pymongo.MongoClient("mongodb://localhost:27017/")
db = mongo_client["CUI_SAHIWAL"]
collection = db["Participants_collection"]

# Set up Google Sheets API credentials
scope = [
    "https://spreadsheets.google.com/feeds",
    "https://www.googleapis.com/auth/drive",
]
creds = ServiceAccountCredentials.from_json_keyfile_name(credentials_file, scope)
client = gspread.authorize(creds)

# Connect to the Google Sheet by its title
sheet_title = "Participants data"
spreadsheet = client.open(sheet_title)
worksheet = spreadsheet.get_worksheet(0)  # assuming the data is in the first worksheet

# Get all the data from the Google Sheet
data = worksheet.get_all_records()

# Remove leading or extra spaces from each cell's values
for row in data:
    for key, value in row.items():
        if isinstance(value, str):
            row[key] = value.strip()

# Insert data into MongoDB
collection.insert_many(data)

# Close MongoDB connection
mongo_client.close()
