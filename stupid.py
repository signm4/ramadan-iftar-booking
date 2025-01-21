import os
from dotenv import load_dotenv

from firebase_admin import storage
import uuid
from flask import Flask, request, render_template, jsonify, redirect, url_for, session, make_response
from datetime import datetime, timedelta
import os, csv, io
import zipfile
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
from dotenv import load_dotenv

import firebase_admin
from firebase_admin import credentials, db

PRICE_PER_SLOT = 250
def book(masjid):
    # Retrieve form data
    date = input(['date'])
    year = date.split('-')[0]
    quantity = int(input(['quantity']))
    name = input(['name'])
    phone = input(['phone'])
    email = request.form['email']
    payment_method = request.form['payment_method']
    # payment_proof = request.files.get('payment-proof')

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

    # Upload payment proof to Firebase Storage
    proof_url = None
    if payment_proof:
        try:
            unique_filename = f"{masjid}/{year}/{date}/{uuid.uuid4()}_{payment_proof.filename}"
            bucket = storage.bucket()
            blob = bucket.blob(unique_filename)
            blob.upload_from_file(payment_proof, content_type=payment_proof.content_type)
            blob.make_public()  # Make the file publicly accessible (if needed)
            proof_url = blob.public_url
        except Exception as e:
            return jsonify({"status": "error", "message": f"Failed to upload payment proof: {str(e)}"})

    # Firebase reference for the selected date
    ref = db.reference(f'bookings/{masjid}/{year}/{date}')
    data = ref.get()

    # Initialize data if not present or malformed
    if not data:
        data = {"slots": {str(i): None for i in range(1, 9)}, "slots_filled": 0, "slots_remaining": 8}

    # Ensure the "slots" structure is valid
    if "slots" not in data or not isinstance(data["slots"], dict):
        data["slots"] = {str(i): None for i in range(1, 9)}
    data["slots_filled"] = data.get("slots_filled", 0)
    data["slots_remaining"] = data.get("slots_remaining", 8)

    # Find the next available slot
    current_slots = data["slots"]
    available_slots = [slot for slot, details in current_slots.items() if details is None]

    # Handle overbooking
    if len(available_slots) < quantity:
        return jsonify({"status": "error", "message": f"Only {len(available_slots)} slots are available."})

    # Assign slots to the new donor
    for i in range(quantity):
        next_slot = available_slots[i]
        current_slots[next_slot] = {
            "name": name,
            "phone": phone,
            "email": email,
            "payment_method": payment_method,
            "payment_proof": proof_url
        }

    # Update slots filled and remaining
    data["slots_filled"] += quantity
    data["slots_remaining"] = 8 - data["slots_filled"]

    # Save updated data back to Firebase
    ref.update({
        "slots": current_slots,
        "slots_filled": data["slots_filled"],
        "slots_remaining": data["slots_remaining"]
    })

    # Render thank you page
    return render_template('thank_you.html', masjid=masjid)
