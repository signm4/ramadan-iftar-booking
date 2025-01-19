import firebase_admin
from firebase_admin import credentials, db

# Initialize Firebase
cred = credentials.Certificate('/Users/sulemanm/Documents/Python/Book_Iftar/ramadan-iftar-booking/secrets_bookiftar.json')  # Replace with your JSON file path
firebase_admin.initialize_app(cred, {
    'databaseURL': 'https://bookiftar2025-default-rtdb.firebaseio.com/'  # Replace with your database URL
})

# Masjids to initialize
masjids = {
    "MasjidBilal": {
        "2025": {
            "2025-02-28": {
                "slots": {},
                "slots_filled": 0,
                "slots_remaining": 8
            },
            "2025-03-01": {
                "slots": {},
                "slots_filled": 0,
                "slots_remaining": 8
            },
            "2025-03-02": {
                "slots": {},
                "slots_filled": 0,
                "slots_remaining": 8
            }
        }
    },
    "MasjidNoor": {
        "2025": {
            "2025-02-28": {
                "slots": {},
                "slots_filled": 0,
                "slots_remaining": 8
            },
            "2025-03-01": {
                "slots": {},
                "slots_filled": 0,
                "slots_remaining": 8
            },
            "2025-03-02": {
                "slots": {},
                "slots_filled": 0,
                "slots_remaining": 8
            }
        }
    }
}

# Push the masjid structure to Firebase
ref = db.reference('bookings')

for masjid_name, years in masjids.items():
    for year, dates in years.items():
        for date, data in dates.items():
            ref.child(f"{masjid_name}/{year}/{date}").set(data)

print("Firebase Realtime Database initialized successfully!")
