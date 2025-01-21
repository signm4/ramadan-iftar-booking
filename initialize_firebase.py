import firebase_admin
from firebase_admin import credentials, db

# Initialize Firebase
cred = credentials.Certificate('/Users/sulemanm/Documents/Python/Book_Iftar/ramadan-iftar-booking/secrets_bookiftar.json')  # Replace with your JSON file path
firebase_admin.initialize_app(cred, {
    'databaseURL': 'https://bookiftar2025-default-rtdb.firebaseio.com/'  # Replace with your database URL
})

# RAFAY - need to add all the calendar for Ramadan 26 02/28- 03/29
#ASK CHATGPT we need to get rid of all dates, only dates between feb 28 - mar 29 2025 should be avail.
# Define the structure for masjids, years, and dates
masjids = {
    "MasjidBilal": {
        "2025": [
            "2025-02-28",
            "2025-02-29",
            "2025-03-01",
            "2025-03-02",
            "2025-03-03"
        ]
    },
    "MasjidNoor": {
        "2025": [
            "2025-02-28",
            "2025-03-01",
            "2025-03-03"
        ]
    }
}

#RAFAY - plz add a init slot for each date , remember we are adding one slot extra, make it where it displays one slot less

# Create the slots structure for all dates
def initialize_slots(filled_slot=None):
    slots = {}
    for i in range(1, 9):  # Initialize 8 slots
        if filled_slot and i == filled_slot:
            slots[str(i)] = {  # Pre-fill slot 1 for demonstration
                "name": "John Doe",
                "phone": "1234567890",
                "email": "john.doe@example.com",
                "payment_method": "Zelle",
                "payment_proof": "/static/uploads/john_doe_proof.jpg"
            }
        else:
            slots[str(i)] = None  # Empty slot
    return slots

# Initialize database with the correct structure
for masjid_name, years in masjids.items():
    for year, dates in years.items():
        for date in dates:
            ref = db.reference(f'bookings/{masjid_name}/{year}/{date}')
            if date == "2025-02-28" and masjid_name == "MasjidBilal":
                # Initialize February 28 with one slot filled
                ref.set({
                    "slots": initialize_slots(filled_slot=1),
                    "slots_filled": 1,
                    "slots_remaining": 7
                })
            else:
                # Default initialization for other dates
                ref.set({
                    "slots": initialize_slots(),  # Pre-fill all slots as empty
                    "slots_filled": 0,
                    "slots_remaining": 8
                })

print("Firebase database initialized successfully!")
