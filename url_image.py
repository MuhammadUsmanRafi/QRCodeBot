import requests
import cv2
from pyzbar.pyzbar import decode

# Replace 'your_image_url' with the actual URL of the image
image_url = 'https://www.kpmindustries.com/KingConstructionProducts/wp-content/uploads/sites/13/2014/03/3.1.4x-Press-Release-QR-Code-on-Packaging-for-5...-Image.png'

# Download the image from the URL
response = requests.get(image_url)

# Check if the request was successful
if response.status_code == 200:
    # Save the downloaded image to a file
    with open('downloaded_image.jpg', 'wb') as f:
        f.write(response.content)
else:
    print("Failed to download the image.")

# Load the downloaded image
image = cv2.imread('downloaded_image.jpg')

# Convert the image to grayscale
gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)

# Detect QR codes in the grayscale image
decoded_objects = decode(image)

# Iterate through the detected objects and print the data
for obj in decoded_objects:
    print(f"Data: {obj.data.decode('utf-8')}")
