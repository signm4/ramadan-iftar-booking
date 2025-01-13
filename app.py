from flask import Flask, request, render_template, jsonify, redirect, url_for
import sqlite3
from datetime import datetime
import os

app = Flask(__name__)

# Configure upload folder
UPLOAD_FOLDER = 'static/uploads'
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# Initialize the database
def init_db():
    conn = sqlite3.connect('bookings.db')
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS bookings (
        id INTEGER PRIMARY KEY,
        date TEXT,
        quantity INTEGER,
        name TEXT,
        phone TEXT,
        email TEXT,
        payment_method TEXT,
        payment_proof TEXT
    )''')
    conn.commit()
    conn.close()

# Check slots booked for a specific date
def slots_booked(date):
    conn = sqlite3.connect('bookings.db')
    c = conn.cursor()
    c.execute("SELECT SUM(quantity) FROM bookings WHERE date = ?", (date,))
    total = c.fetchone()[0]
    conn.close()
    return total if total else 0

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/available-slots', methods=['GET'])
def available_slots():
    date = request.args.get('date')
    if not date:
        return jsonify({"status": "error", "message": "Date is required."})

    try:
        # Validate date
        booking_date = datetime.strptime(date, "%Y-%m-%d")
        if not (datetime(2025, 2, 28) <= booking_date <= datetime(2025, 3, 29)) or booking_date.weekday() not in [4, 5, 6]:
            return jsonify({"status": "error", "message": "Invalid date. Only Fridays, Saturdays, and Sundays are allowed."})
    except ValueError:
        return jsonify({"status": "error", "message": "Invalid date format."})

    booked = slots_booked(date)
    available = max(0, 8 - booked)
    return jsonify({"status": "success", "available": available})


@app.route('/book', methods=['POST'])
def book():
    date = request.form['date']
    quantity = int(request.form['quantity'])
    name = request.form['name']
    phone = request.form['phone']
    email = request.form['email']
    payment_method = request.form['payment_method']
    payment_proof = request.files.get('payment-proof')

    # Validate date
    try:
        booking_date = datetime.strptime(date, "%Y-%m-%d")
        if not (datetime(2025, 2, 28) <= booking_date <= datetime(2025, 3, 29)) or booking_date.weekday() not in [4, 5, 6]:
            return jsonify({"status": "error", "message": "Invalid date. Only Fridays, Saturdays, and Sundays are allowed."})
    except ValueError:
        return jsonify({"status": "error", "message": "Invalid date format."})

    # Check availability
    booked = slots_booked(date)
    if booked + quantity > 8:
        return jsonify({"status": "error", "message": f"Not enough slots available. Only {8 - booked} slots remain for {date}."})

    # Save payment proof
    if payment_proof:
        filename = f"{name}_{datetime.now().strftime('%Y%m%d%H%M%S')}_{payment_proof.filename}"
        payment_proof.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
    else:
        return jsonify({"status": "error", "message": "Payment confirmation is required."})

    # Save booking
    conn = sqlite3.connect('bookings.db')
    c = conn.cursor()
    c.execute("INSERT INTO bookings (date, quantity, name, phone, email, payment_method, payment_proof) VALUES (?, ?, ?, ?, ?, ?, ?)",
              (date, quantity, name, phone, email, payment_method, filename))
    conn.commit()
    conn.close()

    # Redirect to thank you page
    return redirect(url_for('thank_you'))

@app.route('/thank-you')
def thank_you():
    return render_template('thank_you.html')

if __name__ == '__main__':
    init_db()
    app.run(debug=True)
