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

ag = input("age: ")
name_input = input("name: ")
project_input = input("Masjid: ")

# Optional: Write some data to test
ref.set({
    'name': name_input,
    'project': project_input,
    'age': ag
})

# After update
data = ref.get()
print("Data from Firebase after edit:", data)
