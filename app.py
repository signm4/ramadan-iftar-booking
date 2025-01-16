from flask import Flask, request, render_template, jsonify, redirect, url_for, session, make_response
import sqlite3
from datetime import datetime, timedelta
import os, csv, io
import zipfile

app = Flask(__name__, static_folder='static')

# app.secret_key = os.urandom(24)

app.secret_key = "secretkey"


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

# # Initialize the database
# def init_db():
#     conn = sqlite3.connect('bookings.db')
#     c = conn.cursor()
#     c.execute('''CREATE TABLE IF NOT EXISTS bookings (
#         id INTEGER PRIMARY KEY,
#         date TEXT,
#         quantity INTEGER,
#         name TEXT,
#         phone TEXT,
#         email TEXT,
#         payment_method TEXT,
#         payment_proof TEXT
#     )''')
#     conn.commit()
#     conn.close()

# Check slots booked for a specific date
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

@app.route('/admin-login/<masjid>', methods=['GET', 'POST'])
def admin_login(masjid):
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')

        # Check credentials
        if ADMIN_CREDENTIALS.get(masjid) and \
           username == ADMIN_CREDENTIALS[masjid]['username'] and \
           password == ADMIN_CREDENTIALS[masjid]['password']:
            # Set session for the admin
            session['masjid'] = masjid
            session['admin_logged_in'] = True
            return redirect(f'/admin-dashboard/{masjid}')
        else:
            return render_template('admin_login.html', masjid=masjid, error="Invalid credentials")

    return render_template('admin_login.html', masjid=masjid)

@app.route('/admin-dashboard/<masjid>', methods=['GET'])
def admin_dashboard(masjid):
    # Ensure admin is logged in
    if not session.get('admin_logged_in') or session.get('masjid') != masjid:
        return redirect('/')

    # Fetch data: slots filled for each date
    conn = sqlite3.connect("bookings.db")
    cursor = conn.cursor()
    cursor.execute('''
        SELECT date, SUM(quantity) AS slots_filled
        FROM bookings
        WHERE masjid = ?
        GROUP BY date
    ''', (masjid,))
    dates_data = cursor.fetchall()
    conn.close()

    # Format the data for the template
    dates = [{"date": row[0], "slots_filled": row[1]} for row in dates_data]

    return render_template('admin_dashboard.html', masjid=masjid, dates=dates)


@app.route('/admin-dashboard/<masjid>/details', methods=['GET'])
def date_details(masjid):
    # Ensure admin is logged in
    if not session.get('admin_logged_in') or session.get('masjid') != masjid:
        return redirect('/')

    # Get the selected date and search query from the request
    date = request.args.get('date')
    search_query = request.args.get('search', '').strip().lower()  # Search query

    if not date:
        return redirect(f'/admin-dashboard/{masjid}')

    # Fetch donor details for the selected date
    conn = sqlite3.connect("bookings.db")
    cursor = conn.cursor()
    if search_query:
        # Search by name or email
        cursor.execute('''
            SELECT name, phone, email, quantity, payment_method, payment_proof
            FROM bookings
            WHERE masjid = ? AND date = ? AND (LOWER(name) LIKE ? OR LOWER(email) LIKE ?)
        ''', (masjid, date, f"%{search_query}%", f"%{search_query}%"))
    else:
        # Fetch all donors for the date
        cursor.execute('''
            SELECT name, phone, email, quantity, payment_method, payment_proof
            FROM bookings
            WHERE masjid = ? AND date = ?
        ''', (masjid, date))
    donors_data = cursor.fetchall()
    conn.close()

    # Format the data for the template
    donors = [
        {
            "name": row[0],
            "phone": row[1],
            "email": row[2],
            "quantity": row[3],
            "payment_method": row[4],
            "payment_proof": row[5]
        }
        for row in donors_data
    ]

    return render_template('date_details.html', masjid=masjid, date=date, donors=donors, search_query=search_query)

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


# Below code works, However does not display image of payment confirmation.
# @app.route('/admin-dashboard/<masjid>', methods=['GET'])
# def admin_dashboard(masjid):
#     # Ensure the admin is logged in
#     if not session.get('admin_logged_in') or session.get('masjid') != masjid:
#         return redirect('/')

#     # Fetch slot data for the masjid
#     conn = sqlite3.connect("bookings.db")
#     cursor = conn.cursor()
#     cursor.execute("SELECT date, SUM(quantity), 8 - SUM(quantity) AS slots_left FROM bookings WHERE masjid = ? GROUP BY date", (masjid,))
#     slots_data = cursor.fetchall()
#     conn.close()

#     # Format data for the template
#     slots = [{"date": row[0], "slots_filled": row[1], "slots_left": row[2]} for row in slots_data]

#     return render_template('admin_dashboard.html', masjid=masjid, slots=slots)

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


@app.route('/book', methods=['POST'])
def book():
    date = request.form['date']
    quantity = int(request.form['quantity'])
    name = request.form['name']
    phone = request.form['phone']
    email = request.form['email']
    masjid = request.form.get('masjid')  # Ensure this is retrieved from the form
    payment_method = request.form['payment_method']
    payment_proof = request.files.get('payment-proof')

    # Validate date
    try:
        booking_date = datetime.strptime(date, "%Y-%m-%d")
        if not (datetime(2025, 2, 28) <= booking_date <= datetime(2025, 3, 29)) or booking_date.weekday() not in [4, 5, 6]:
            return jsonify({"status": "error", "message": "Invalid date. Only Fridays, Saturdays, and Sundays are allowed."})
    except ValueError:
        return jsonify({"status": "error", "message": "Invalid date format."})

    # Ensure masjid is provided
    if not masjid:
        return jsonify({"status": "error", "message": "Masjid information is missing."})

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
    c.execute("""
        INSERT INTO bookings (date, quantity, name, phone, email, masjid, payment_method, payment_proof) 
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    """, (date, quantity, name, phone, email, masjid, payment_method, filename))
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
