import firebase_admin
from firebase_admin import credentials, db
import os
from dotenv import load_dotenv
from datetime import datetime, timedelta

load_dotenv()
# Initialize Firebase

cert_url = os.getenv('CERT_URL')
print(cert_url)
cred = credentials.Certificate(cert_url)  # Replace with your JSON file path
firebase_admin.initialize_app(cred, {
    'databaseURL': 'https://bookiftar2025-default-rtdb.firebaseio.com/'  # Replace with your database URL
})

# RAFAY - need to add all the calendar for Ramadan 26 02/28- 03/29
#ASK CHATGPT we need to get rid of all dates, only dates between feb 28 - mar 29 2025 should be avail.
# Define the structure for masjids, years, and dates

# Initialize dates from 2025-02-28 to 2025-03-29 (Friday - Sunday)
start_date = datetime(2025, 2, 28)
end_date = datetime(2025, 3, 29)

'''Per Masjid, select which days out of the week they will be allowing iftar'''
def get_weekend_dates(start_date, end_date):
    dates = []
    current_date = start_date
    while current_date <= end_date:
        if current_date.weekday() in [0,1,2,3,4, 5, 6]:  # Friday (4), Saturday (5), Sunday (6)
            dates.append(current_date.strftime('%Y-%m-%d'))
        current_date += timedelta(days=1)
    return dates

# Masjid-specific data
masjids = {
    "MasjidNoor": {
        "2025": get_weekend_dates(start_date, end_date)
    }
}

# Initialize Firebase data for slots, depending on how many slots they have
def initialize_slots():
    return {str(i): None for i in range(1, 9)}  # 8 slots initialized as empty

for masjid_name, years in masjids.items():
    for year, dates in years.items():
        for date in dates:
            ref = db.reference(f'bookings/{masjid_name}/{year}/{date}')
            ref.set({
                "slots": initialize_slots(),
                "slots_filled": 0,
                "slots_remaining": 8 # change slot num here
            })

print("Firebase Masjid Noor initialized successfully!")
