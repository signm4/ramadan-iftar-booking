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
cert_url = os.getenv('CERT_URL')
cred = credentials.Certificate(cert_url)  # Replace with your JSON file path
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
    try:
        # Debugging log
        print(f"Masjid: {masjid}")
        
        # Render the form.html template, passing the masjid variable
        return render_template('form.html', masjid=masjid)
    except Exception as e:
        # Log the error and return a generic error message
        print(f"Error rendering form.html for masjid: {masjid}. Error: {e}")
        return "An error occurred while rendering the form.", 500



from datetime import datetime

@app.route('/available-slots/<masjid>', methods=['GET'])
def available_slots(masjid):
    date = request.args.get('date')
    if not date:
        return jsonify({"status": "error", "message": "Date is required."})

    try:
        # Validate the date
        booking_date = datetime.strptime(date, "%Y-%m-%d")
        start_date = datetime(2025, 2, 28)
        end_date = datetime(2025, 3, 29)
        valid_days = [4, 5, 6]  # Friday, Saturday, Sunday

        if not (start_date <= booking_date <= end_date) or booking_date.weekday() not in valid_days:
            return jsonify({"status": "error", "message": "Selected date is not valid for this masjid."})
    except ValueError:
        return jsonify({"status": "error", "message": "Invalid date format."})

    # Fetch data from Firebase
    year = date.split('-')[0]
    ref = db.reference(f'bookings/{masjid}/{year}/{date}')
    data = ref.get()

    # If the date doesn't exist, default to 8 available slots
    available_slots = 8
    if data:
        available_slots = data.get('slots_remaining', 8)

    return jsonify({"status": "success", "available_slots": available_slots})



# 
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

    # Validate date (ensure it's within the allowed range and days)
    start_date = datetime(2025, 2, 28)
    end_date = datetime(2025, 3, 29)
    valid_days = [4, 5, 6]  # Friday, Saturday, Sunday

    try:
        booking_date = datetime.strptime(date, "%Y-%m-%d")
        if not (start_date <= booking_date <= end_date) or booking_date.weekday() not in valid_days:
            return jsonify({"status": "error", "message": "Selected date is not valid for this masjid."})
    except ValueError:
        return jsonify({"status": "error", "message": "Invalid date format."})

    # Save payment proof
    proof_url = None
    if payment_proof:
        proof_filename = f"{name}_{datetime.now().strftime('%Y%m%d%H%M%S')}_{payment_proof.filename}"
        proof_path = os.path.join(app.config['UPLOAD_FOLDER'], proof_filename)
        payment_proof.save(proof_path)
        proof_url = f"/static/uploads/{proof_filename}"

    # Firebase reference for the selected date
    ref = db.reference(f'bookings/{masjid}/{year}/{date}')
    data = ref.get()

    # Ensure data is initialized correctly
    if not data:
        return jsonify({"status": "error", "message": "Invalid date or masjid data not initialized."})

    # Initialize missing or malformed slots structure
    if "slots" not in data or not isinstance(data["slots"], dict):
        data["slots"] = {str(i): None for i in range(1, 9)}  # Default to 8 slots
        data["slots_filled"] = data.get("slots_filled", 0)
        data["slots_remaining"] = data.get("slots_remaining", 8)

    # Check slot availability
    available_slots = [int(slot) for slot, details in data["slots"].items() if details is None]
    if len(available_slots) < quantity:
        return jsonify({"status": "error", "message": f"Only {len(available_slots)} slots are available."})

    # Fill slots with donor details
    for i in range(quantity):
        slot_index = available_slots[i]
        data["slots"][str(slot_index)] = {
            "name": name,
            "phone": phone,
            "email": email,
            "payment_method": payment_method,
            "payment_proof": proof_url
        }

    # Update slots filled and remaining
    data["slots_filled"] += quantity
    data["slots_remaining"] -= quantity

    # Save updated data back to Firebase
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

    # Get the date from query parameters
    date = request.args.get('date')
    if not date:
        return redirect(f'/admin-dashboard/{masjid}')

    # Fetch data from Firebase
    ref = db.reference(f'bookings/{masjid}/2025/{date}')
    data = ref.get()

    if not data or "slots" not in data:
        return render_template('date_details.html', masjid=masjid, date=date, donors=[])

    # Extract donor details and calculate the amount
    donors = []
    for slot, details in data["slots"].items():
        if details:  # Only process booked slots
            details["amount"] = 250  # $250 per slot
            donors.append(details)

    return render_template('date_details.html', masjid=masjid, date=date, donors=donors)

@app.route('/allowed-dates/<masjid>', methods=['GET'])
def allowed_dates(masjid):
    # Define the allowed date range and days
    start_date = datetime(2025, 2, 28)
    end_date = datetime(2025, 3, 29)
    valid_days = [4, 5, 6]  # Friday, Saturday, Sunday

    # Generate valid dates
    dates = []
    current_date = start_date
    while current_date <= end_date:
        if current_date.weekday() in valid_days:
            dates.append(current_date.strftime('%Y-%m-%d'))
        current_date += timedelta(days=1)

    return jsonify({"status": "success", "dates": dates})


if __name__ == '__main__':
    app.run(debug=True)
