import sqlite3

conn = sqlite3.connect('bookings.db')
c = conn.cursor()

# Add the payment_method column to the table
c.execute("ALTER TABLE bookings ADD COLUMN payment_method TEXT")

conn.commit()
conn.close()

print("Database updated with payment_method column!")
