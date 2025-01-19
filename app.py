from flask import Flask, request, render_template, jsonify, redirect, url_for, session, make_response
from datetime import datetime, timedelta
import os, csv, io
import zipfile
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
from dotenv import load_dotenv

import firebase_admin
from firebase_admin import credentials, db

# Load environment variables
load_dotenv()

# Initialize Firebase
cred = credentials.Certificate("/Users/sulemanm/Documents/Python/Book_Iftar/ramadan-iftar-booking/secrets_bookiftar.json")  # Replace with your JSON file path
firebase_admin.initialize_app(cred, {
    'databaseURL': 'https://bookiftar2025-default-rtdb.firebaseio.com/'  # Replace with your database URL
})

# Flask app setup
app = Flask(__name__, static_folder='static')
app.secret_key = os.getenv('SECRET_KEY', 'default_secret_key')
app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv('DATABASE_URL', 'sqlite:///bookings.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db_sql = SQLAlchemy(app)

# Admin credentials
ADMIN_USERNAME = 'admin'
ADMIN_PASSWORD_HASH = generate_password_hash('password123', method="pbkdf2:sha256")  # Replace with your actual password

# Ensure upload directory exists
UPLOAD_FOLDER = 'static/uploads'
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# Slots calculation helper
def slots_booked(date):
    ref = db.reference('bookings')
    bookings = ref.order_by_child('date').equal_to(date).get()
    total_slots = sum(booking['quantity'] for booking in bookings.values())
    return total_slots if total_slots else 0

# Routes
@app.route('/')
def home():
    return render_template('home.html')

@app.route('/select-masjid', methods=['GET'])
def select_masjid():
    masjid = request.args.get('masjid')
    if not masjid:
        return redirect(url_for('home'))
    return redirect(url_for('masjid_form', masjid=masjid))

@app.route('/masjid/<masjid>')
def masjid_form(masjid):
    return render_template('form.html', masjid=masjid)

# @app.route('/available-slots', methods=['GET'])
# def available_slots():
#     date = request.args.get('date')
#     if not date:
#         return jsonify({"status": "error", "message": "Date is required."})

#     try:
#         booking_date = datetime.strptime(date, "%Y-%m-%d")
#         if not (datetime(2025, 2, 28) <= booking_date <= datetime(2025, 3, 29)) or booking_date.weekday() not in [4, 5, 6]:
#             return jsonify({"status": "error", "message": "Invalid date. Only Fridays, Saturdays, and Sundays are allowed."})
#     except ValueError:
#         return jsonify({"status": "error", "message": "Invalid date format."})

#     booked = slots_booked(date)
#     available = max(0, 8 - booked)
#     return jsonify({"status": "success", "available": available})

@app.route('/available-slots/<masjid>', methods=['GET'])
def available_slots(masjid):
    date = request.args.get('date')
    if not date:
        return jsonify({"status": "error", "message": "Date is required."})

    year = date.split('-')[0]
    available_slots = get_slot_availability(masjid, year, date)

    return jsonify({"status": "success", "available_slots": available_slots})


# @app.route('/book', methods=['POST'])
# def book():
#     date = request.form['date']
#     quantity = int(request.form['quantity'])
#     name = request.form['name']
#     phone = request.form['phone']
#     email = request.form['email']
#     payment_method = request.form['payment_method']
#     payment_proof = request.files.get('payment-proof')

#     # Save payment proof
#     proof_url = None
#     if payment_proof:
#         proof_filename = f"{name}_{datetime.now().strftime('%Y%m%d%H%M%S')}_{payment_proof.filename}"
#         proof_path = os.path.join(app.config['UPLOAD_FOLDER'], proof_filename)
#         payment_proof.save(proof_path)
#         proof_url = f"/static/uploads/{proof_filename}"

#     # Save booking in Firebase
#     ref = db.reference('bookings')
#     ref.push({
#         'date': date,
#         'quantity': quantity,
#         'name': name,
#         'phone': phone,
#         'email': email,
#         'payment_method': payment_method,
#         'payment_proof': proof_url
#     })

#     return redirect('/thank-you')

@app.route('/book/<masjid>', methods=['POST'])
def book(masjid):
    date = request.form['date']
    year = date.split('-')[0]
    quantity = int(request.form['quantity'])
    name = request.form['name']
    phone = request.form['phone']
    email = request.form['email']
    payment_method = request.form['payment_method']
    payment_proof = request.files.get('payment-proof')

    # Save payment proof
    proof_url = None
    if payment_proof:
        proof_filename = f"{name}_{datetime.now().strftime('%Y%m%d%H%M%S')}_{payment_proof.filename}"
        proof_path = os.path.join(app.config['UPLOAD_FOLDER'], proof_filename)
        payment_proof.save(proof_path)
        proof_url = f"/static/uploads/{proof_filename}"

    # Get reference for the date
    ref = db.reference(f'bookings/{masjid}/{year}/{date}')
    data = ref.get()

    # Initialize data if date doesn't exist
    if not data:
        data = {
            "slots": {},
            "slots_filled": 0,
            "slots_remaining": 8
        }

    # Check slot availability
    if data["slots_remaining"] < quantity:
        return jsonify({"status": "error", "message": f"Only {data['slots_remaining']} slots are available."})

    # Update slot details
    next_slot = data["slots_filled"] + 1
    for i in range(next_slot, next_slot + quantity):
        data["slots"][str(i)] = {
            "name": name,
            "phone": phone,
            "email": email,
            "payment_method": payment_method,
            "payment_proof": proof_url
        }

    # Update slots filled and remaining
    data["slots_filled"] += quantity
    data["slots_remaining"] -= quantity

    # Save back to Firebase
    ref.set(data)

    return redirect('/thank-you')


@app.route('/thank-you')
def thank_you():
    return render_template('thank_you.html')

@app.route('/admin-login/<masjid>', methods=['GET', 'POST'])
def admin_login(masjid):
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        if username == ADMIN_USERNAME and check_password_hash(ADMIN_PASSWORD_HASH, password):
            session['admin_logged_in'] = True
            session['masjid'] = masjid
            return redirect(f'/admin-dashboard/{masjid}')
        else:
            return render_template('admin_login.html', masjid=masjid, error="Invalid credentials")
    return render_template('admin_login.html', masjid=masjid)

@app.route('/admin-logout')
def admin_logout():
    session.clear()
    return redirect('/')

@app.route('/admin-dashboard/<masjid>', methods=['GET'])
def admin_dashboard(masjid):
    if not session.get('admin_logged_in') or session.get('masjid') != masjid:
        return redirect(f'/admin-login/{masjid}')

    year = "2025"  # Update dynamically if needed
    ref = db.reference(f'bookings/{masjid}/{year}')
    dates_data = ref.get()

    date_summary = []
    if dates_data:
        for date, data in dates_data.items():
            date_summary.append({
                "date": date,
                "slots_filled": data["slots_filled"],
                "slots_remaining": data["slots_remaining"],
                "total_donated": data["slots_filled"] * 250
            })

    return render_template('admin_dashboard.html', masjid=masjid, date_summary=date_summary)


@app.route('/admin-dashboard/<masjid>/details', methods=['GET'])
def date_details(masjid):
    if not session.get('admin_logged_in') or session.get('masjid') != masjid:
        return redirect(f'/admin-login/{masjid}')

    date = request.args.get('date')
    if not date:
        return redirect(f'/admin-dashboard/{masjid}')

    ref = db.reference('bookings')
    bookings = ref.order_by_child('date').equal_to(date).get()

    donors = [
        {
            'name': data['name'],
            'phone': data['phone'],
            'email': data['email'],
            'quantity': data['quantity'],
            'payment_method': data['payment_method'],
            'payment_proof': data['payment_proof']
        }
        for key, data in bookings.items()
    ]

    return render_template('date_details.html', masjid=masjid, date=date, donors=donors)

if __name__ == '__main__':
    app.run(debug=True)
