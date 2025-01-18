import firebase_admin
from firebase_admin import credentials
from firebase_admin import db
from dotenv import load_dotenv
import os

# Load environment variables from .env file
load_dotenv()

# Fetch the credentials and database URL from environment variables
cred_path = os.getenv('GOOGLE_APPLICATION_CREDENTIALS')
database_url = os.getenv('FIREBASE_DATABASE_URL')

# Initialize the Firebase app
cred = credentials.Certificate(cred_path)
firebase_admin.initialize_app(cred, {
    'databaseURL': database_url
})

# Test connection by reading the database
ref = db.reference('/')
data = ref.get()
print("Data from Firebase:", data)

# User input
ag = input("age: ")
name_input = input("name: ")
project_input = input("Masjid: ")

# Reference to the masjids node
masjids_ref = db.reference('masjids')

# Add a masjid
masjid_name = "MasjidBilal"
masjid_ref = masjids_ref.child(masjid_name)

# Add a year
year = "2025"
year_ref = masjid_ref.child('years').child(year)

# Add a date
date = "01-17"
date_ref = year_ref.child('dates').child(date)

# Add a slot
slot_id = "slot1"
slot_data = {
    "donorName": name_input,
    "phone": "1234567890",  # Replace with a dynamic input if needed
    "email": "johndoe@example.com",  # Replace with a dynamic input if needed
    "quantity": ag,
    "paymentMethod": "Credit Card",  # Replace with a dynamic input if needed
    "paymentProof": "proof_image_url"
}

# Retrieve all masjids
all_masjids = masjids_ref.get()
print("All Masjids:", all_masjids)

# Retrieve specific masjid data
masjid_data = masjids_ref.child(masjid_name).get()
print(f"Data for {masjid_name}:", masjid_data)

# Write the slot data
date_ref.child('slots').child(slot_id).set(slot_data)
print(f"Slot {slot_id} added successfully!")

# After update
data = ref.get()
print("Data from Firebase after edit:", data)
