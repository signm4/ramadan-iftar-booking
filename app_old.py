from flask import Flask, request, render_template, jsonify, redirect, url_for, session, make_response
import sqlite3
from datetime import datetime, timedelta
import os, csv, io
import zipfile
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
from dotenv import load_dotenv

import firebase_admin
from firebase_admin import credentials, db

# Initialize Firebase
cred = credentials.Certificate('/Users/sulemanm/Documents/Python/Book_Iftar/ramadan-iftar-booking/secrets_bookiftar.json')  # Replace with your JSON file path
firebase_admin.initialize_app(cred, {
    'databaseURL': 'https://bookiftar2025-default-rtdb.firebaseio.com/'  # Replace with your database URL
})

load_dotenv()
app = Flask(__name__, static_folder='static')

# app.secret_key = os.urandom(24)

app.secret_key = os.getenv('SECRET_KEY', 'default_secret_key')
app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv('DATABASE_URL', 'sqlite:///bookings.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)

ADMIN_USERNAME = 'admin'
ADMIN_PASSWORD_HASH = generate_password_hash('password123', method="pbkdf2:sha256")  # Replace with your actual password


def init_db():
    conn = sqlite3.connect("bookings.db")
    cursor = conn.cursor()

    # Create the bookings table with all required columns
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS bookings (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            date TEXT NOT NULL,
            quantity INTEGER NOT NULL,
            name TEXT NOT NULL,
            phone TEXT NOT NULL,
            email TEXT NOT NULL,
            masjid TEXT NOT NULL,
            payment_method TEXT NOT NULL,
            payment_proof TEXT NOT NULL
        )
    ''')
    conn.commit()
    conn.close()

# Call init_db() when the app starts
# init_db()


# Configure upload folder
UPLOAD_FOLDER = 'static/uploads'
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

def slots_booked(date):
    conn = sqlite3.connect('bookings.db')
    c = conn.cursor()
    c.execute("SELECT SUM(quantity) FROM bookings WHERE date = ?", (date,))
    total = c.fetchone()[0]
    conn.close()
    return total if total else 0

@app.route('/')
def home():
    return render_template('home.html')

# Dummy credentials (replace with database or secure method)
ADMIN_CREDENTIALS = {
    "MasjidBilal": {"username": "admin", "password": "password123"}
}
# Login route
@app.route('/admin-login/<masjid>', methods=['GET', 'POST'])
def admin_login(masjid):
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        # Validate username and password (replace with dynamic validation if needed)
        if username == ADMIN_USERNAME and check_password_hash(ADMIN_PASSWORD_HASH, password):
            session['admin_logged_in'] = True
            session['masjid'] = masjid  # Store the masjid in the session
            return redirect(f'/admin-dashboard/{masjid}')
        else:
            return render_template('admin_login.html', masjid=masjid, error="Invalid credentials")

    return render_template('admin_login.html', masjid=masjid)



# Admin logout route
@app.route('/admin-logout')
def admin_logout():
    session.clear()
    return redirect('/')


from datetime import datetime, timedelta


@app.route('/admin-dashboard/<masjid>', methods=['GET'])
def admin_dashboard(masjid):
    if not session.get('admin_logged_in') or session.get('masjid') != masjid:
        return redirect(f'/admin-login/{masjid}')

    # Fetch data from Firebase
    ref = db.reference('bookings')
    bookings = ref.order_by_child('date').get()

    # Summarize data by date
    summary = {}
    for key, data in bookings.items():
        if data['date'] not in summary:
            summary[data['date']] = {'slots_filled': 0, 'total_donated': 0}
        summary[data['date']]['slots_filled'] += data['quantity']
        summary[data['date']]['total_donated'] += data['quantity'] * 250

    # Format for the template
    date_summary = [
        {
            'date': date,
            'slots_filled': summary[date]['slots_filled'],
            'slots_remaining': 8 - summary[date]['slots_filled'],
            'total_donated': summary[date]['total_donated']
        }
        for date in sorted(summary.keys())
    ]

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
    ref = db.reference('bookings')
    bookings = ref.order_by_child('date').equal_to(date).get()

    # Format donor details
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



@app.route('/admin-dashboard/<masjid>/export', methods=['GET'])
def export_data(masjid):
    # Ensure admin is logged in
    if not session.get('admin_logged_in') or session.get('masjid') != masjid:
        return redirect('/')

    # Get the selected date from the request
    date = request.args.get('date')
    if not date:
        return redirect(f'/admin-dashboard/{masjid}')

    # Fetch donor details for the selected date
    conn = sqlite3.connect("bookings.db")
    cursor = conn.cursor()
    cursor.execute('''
        SELECT name, phone, email, quantity, payment_method, payment_proof
        FROM bookings
        WHERE masjid = ? AND date = ?
    ''', (masjid, date))
    donors_data = cursor.fetchall()
    conn.close()

    # Generate CSV
    output = []
    output.append(['Name', 'Phone', 'Email', 'Slots Booked', 'Payment Method', 'Payment Proof'])
    for row in donors_data:
        output.append(list(row))

    # Create CSV response
    si = io.StringIO()
    cw = csv.writer(si)
    cw.writerows(output)
    response = make_response(si.getvalue())
    response.headers['Content-Disposition'] = f'attachment; filename=donors_{date}.csv'
    response.headers['Content-Type'] = 'text/csv'
    return response

@app.route('/admin-dashboard/<masjid>/export-all', methods=['GET'])
def export_all_data(masjid):
    # Ensure admin is logged in
    if not session.get('admin_logged_in') or session.get('masjid') != masjid:
        return redirect('/')

    # Initialize date range
    start_date = datetime(2025, 2, 28)
    end_date = datetime(2025, 3, 29)
    date_range = [(start_date + timedelta(days=i)).strftime('%Y-%m-%d') for i in range((end_date - start_date).days + 1)]
    
    conn = sqlite3.connect("bookings.db")
    cursor = conn.cursor()

    # Fetch all booking data
    cursor.execute('''
        SELECT date, SUM(quantity) AS slots_filled, SUM(quantity * 250) AS total_donated
        FROM bookings
        WHERE masjid = ?
        GROUP BY date
    ''', (masjid,))
    summary_data = cursor.fetchall()

    # Fetch all donor details
    cursor.execute('''
        SELECT date, name, phone, email, quantity, (quantity * 250) AS amount_donated
        FROM bookings
        WHERE masjid = ?
    ''', (masjid,))
    detailed_data = cursor.fetchall()

    conn.close()

    # Prepare summary data (fill missing dates)
    summary = []
    for date in date_range:
        filled_data = next((row for row in summary_data if row[0] == date), None)
        slots_filled = filled_data[1] if filled_data else 0
        total_donated = filled_data[2] if filled_data else 0
        slots_left = 8 - slots_filled
        summary.append([date, slots_filled, slots_left, total_donated])

    # Prepare detailed data
    detailed = [['Date', 'Name', 'Phone', 'Email', 'Slots Booked', 'Amount Donated']]
    detailed.extend(detailed_data)

    # Generate CSV for summary
    summary_file = io.StringIO()
    summary_writer = csv.writer(summary_file)
    summary_writer.writerow(['Date', 'Slots Filled', 'Slots Left', 'Total Donated'])
    summary_writer.writerows(summary)

    # Generate CSV for detailed data
    detailed_file = io.StringIO()
    detailed_writer = csv.writer(detailed_file)
    detailed_writer.writerows(detailed)

    # Create a response with both files as attachments
    response = make_response()
    response.headers['Content-Type'] = 'application/zip'
    response.headers['Content-Disposition'] = 'attachment; filename=exported_data.zip'

    # Create a zip file with both CSVs
    with io.BytesIO() as zip_buffer:
        with zipfile.ZipFile(zip_buffer, 'w') as zf:
            zf.writestr('summary.csv', summary_file.getvalue())
            zf.writestr('detailed.csv', detailed_file.getvalue())
        zip_buffer.seek(0)
        response.data = zip_buffer.read()

    return response



@app.route('/slot-details/<masjid>', methods=['GET'])
def slot_details(masjid):
    # Ensure the admin is logged in
    if not session.get('admin_logged_in') or session.get('masjid') != masjid:
        return redirect('/')

    date = request.args.get('date')
    if not date:
        return redirect(f'/admin-dashboard/{masjid}')

    # Fetch donor details for the selected date
    conn = sqlite3.connect("bookings.db")
    cursor = conn.cursor()
    cursor.execute("SELECT name, phone, email, quantity FROM bookings WHERE masjid = ? AND date = ?", (masjid, date))
    donor_data = cursor.fetchall()
    conn.close()

    # Format data for the template
    donors = [{"name": row[0], "phone": row[1], "email": row[2], "quantity": row[3]} for row in donor_data]

    return render_template('slot_details.html', masjid=masjid, date=date, donors=donors)


@app.route('/select-masjid', methods=['GET'])
def select_masjid():
    masjid = request.args.get('masjid')
    if not masjid:
        return redirect(url_for('home'))
    # Redirect to the specific masjid's form page
    return redirect(url_for('masjid_form', masjid=masjid))

@app.route('/masjid/<masjid>')
def masjid_form(masjid):
    # Check for specific masjid and render the corresponding form
    # if masjid == "MasjidBilal":
    #     return render_template('form.html', masjid_name="Masjid Bilal (Kyle, TX)")
    # else:
    #     return render_template('404.html'), 404
    return render_template('form.html', masjid=masjid)


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

    # Calculate available slots
    booked = slots_booked(date)  # Assume slots_booked(date) returns the number of slots already booked
    available = max(0, 8 - booked)
    return jsonify({"status": "success", "available": available})

#OLD CODE BEFORE DB MIGRATION TO FIREBASE
# @app.route('/book', methods=['POST'])
# def book():
#     date = request.form['date']
#     quantity = int(request.form['quantity'])
#     name = request.form['name']
#     phone = request.form['phone']
#     email = request.form['email']
#     masjid = request.form.get('masjid')  # Ensure this is retrieved from the form
#     payment_method = request.form['payment_method']
#     payment_proof = request.files.get('payment-proof')

#     # Validate date
#     try:
#         booking_date = datetime.strptime(date, "%Y-%m-%d")
#         if not (datetime(2025, 2, 28) <= booking_date <= datetime(2025, 3, 29)) or booking_date.weekday() not in [4, 5, 6]:
#             return jsonify({"status": "error", "message": "Invalid date. Only Fridays, Saturdays, and Sundays are allowed."})
#     except ValueError:
#         return jsonify({"status": "error", "message": "Invalid date format."})

#     # Ensure masjid is provided
#     if not masjid:
#         return jsonify({"status": "error", "message": "Masjid information is missing."})

#     # Check availability
#     booked = slots_booked(date)
#     if booked + quantity > 8:
#         return jsonify({"status": "error", "message": f"Not enough slots available. Only {8 - booked} slots remain for {date}."})

#     # Save payment proof
#     if payment_proof:
#         filename = f"{name}_{datetime.now().strftime('%Y%m%d%H%M%S')}_{payment_proof.filename}"
#         payment_proof.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
#     else:
#         return jsonify({"status": "error", "message": "Payment confirmation is required."})

#     # Save booking
#     conn = sqlite3.connect('bookings.db')
#     c = conn.cursor()
#     c.execute("""
#         INSERT INTO bookings (date, quantity, name, phone, email, masjid, payment_method, payment_proof) 
#         VALUES (?, ?, ?, ?, ?, ?, ?, ?)
#     """, (date, quantity, name, phone, email, masjid, payment_method, filename))
#     conn.commit()
#     conn.close()

#     # Redirect to thank you page
#     return redirect(url_for('thank_you'))

@app.route('/book', methods=['POST'])
def book():
    # Retrieve data from the form
    date = request.form['date']
    quantity = int(request.form['quantity'])
    name = request.form['name']
    phone = request.form['phone']
    email = request.form['email']
    payment_method = request.form['payment_method']
    payment_proof = request.files.get('payment-proof')

    # Save payment proof (if uploaded)
    proof_url = None
    if payment_proof:
        proof_filename = f"{name}_{datetime.now().strftime('%Y%m%d%H%M%S')}_{payment_proof.filename}"
        proof_path = os.path.join('static/uploads', proof_filename)
        payment_proof.save(proof_path)
        proof_url = f"/static/uploads/{proof_filename}"

    # Save booking in Firebase Realtime Database
    ref = db.reference('bookings')
    new_booking = {
        'date': date,
        'quantity': quantity,
        'name': name,
        'phone': phone,
        'email': email,
        'payment_method': payment_method,
        'payment_proof': proof_url
    }
    ref.push(new_booking)

    return redirect('/thank-you')



@app.route('/thank-you')
def thank_you():
    return render_template('thank_you.html')

if __name__ == '__main__':
    init_db()
    app.run(debug=True)
