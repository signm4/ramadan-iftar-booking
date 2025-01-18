import firebase_admin
from firebase_admin import credentials, db
from dotenv import load_dotenv
import os
import bcrypt
import random
import string
import uuid

# Load environment variables from .env file
load_dotenv()

# Fetch the credentials and database URL from environment variables
cred_path = os.getenv('GOOGLE_APPLICATION_CREDENTIALS')
database_url = os.getenv('FIREBASE_DATABASE_URL')

# Initialize Firebase app
cred = credentials.Certificate(cred_path)
firebase_admin.initialize_app(cred, {'databaseURL': database_url})


# Function to hash a password
def hash_password(plain_password):
    salt = bcrypt.gensalt()
    hashed_password = bcrypt.hashpw(plain_password.encode('utf-8'), salt)
    return hashed_password


# Function to verify a password
def verify_password(plain_password, hashed_password):
    return bcrypt.checkpw(plain_password.encode('utf-8'), hashed_password)


# Function to create a random password
def generate_random_password(length=10):
    characters = string.ascii_letters + string.digits
    return ''.join(random.choice(characters) for _ in range(length))


# Main program
is_admin = input("Are you an admin? (yes/no): ").strip().lower()

if is_admin == 'yes':
    admins_ref = db.reference('admins')
    username = input("Enter your admin username: ")
    admin_data = admins_ref.order_by_child('username').equal_to(username).get()

    if not admin_data:
        # New admin setup
        print("Admin not found. Setting up a new admin account.")
        admin_password = generate_random_password()
        print(f"Generated admin password: {admin_password}")

        hashed_password = hash_password(admin_password)
        admins_ref.child(str(uuid.uuid4())).set({
            'username': username,
            'password': hashed_password.decode('utf-8')
        })
        print("Admin credentials stored securely in the database.")
    else:
        # Existing admin login
        admin_key = list(admin_data.keys())[0]
        stored_hashed_password = admin_data[admin_key]['password']
        password_attempt = input("Enter your password: ")

        if verify_password(password_attempt, stored_hashed_password.encode('utf-8')):
            print("Login successful!")
        else:
            print("Incorrect password. Please try again.")

else:
    # Normal user flow
    masjids_ref = db.reference('masjids')
    masjid_name = input("Enter your Masjid name: ")
    masjid_id = str(uuid.uuid4())
    masjid_ref = masjids_ref.child(masjid_id)

    # Add masjid details
    masjid_ref.set({'masjidName': masjid_name, 'years': {}})

    year = input("Enter the year (e.g., 2025): ")
    year_ref = masjid_ref.child('years').child(year)

    date = input("Enter the date (e.g., 01-17): ")
    date_ref = year_ref.child('dates').child(date)

    # Collect slot details
    donor_name = input("Enter donor name: ")
    phone = input("Enter phone number: ")
    email = input("Enter email: ")
    payment_method = input("Enter payment method (e.g., Credit Card): ")
    payment_proof = input("Enter payment proof (URL or text): ")
    quantity = input("Enter quantity: ")

    slot_id = str(uuid.uuid4())
    slot_data = {
        "donorName": donor_name,
        "phone": phone,
        "email": email,
        "paymentMethod": payment_method,
        "paymentProof": payment_proof,
        "quantity": quantity
    }
    date_ref.child('slots').child(slot_id).set(slot_data)

    print(f"Slot {slot_id} added successfully under Masjid {masjid_name}!")

print("Operation complete.")
