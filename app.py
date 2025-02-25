from flask import Flask, render_template, request, jsonify, flash
import cv2
import json
import os
import base64
import numpy as np
import time
from datetime import datetime
from data_handlers import DataHandler
import subprocess

app = Flask(__name__)
data_handler = DataHandler()

# File paths
DATA_FILE = "data.json"
HISTORY_FILE = "history.json"
QR_HISTORY_FILE = "qr_history.json"

# Mock database for stand status
stands = {str(i): "available" for i in range(1, 11)}

# Load stand data
def load_data():
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, "r") as f:
            return json.load(f)
    return {"stand1": "opened", "stand2": "opened", "locked_by": {}}

# Save stand data
def save_data(data):
    with open(DATA_FILE, "w") as f:
        json.dump(data, f, indent=4)

# Load QR scan history
def load_qr_history():
    if os.path.exists(QR_HISTORY_FILE):
        with open(QR_HISTORY_FILE, "r") as f:
            return json.load(f)
    return []

# Save QR scan history
def save_qr_history(history):
    with open(QR_HISTORY_FILE, "w") as f:
        json.dump(history, f, indent=4)

# Add an entry to QR history
def add_qr_history_entry(stand, action, user, status):
    history = load_qr_history()
    entry = {
        "timestamp": datetime.now().isoformat(),
        "stand": stand,
        "action": action,
        "user": user,
        "status": status
    }
    history.append(entry)
    save_qr_history(history)

# Decode QR Code from image
def decode_qr(image_data):
    try:
        image_data = image_data.split(",")[1]
        image_bytes = base64.b64decode(image_data)
        np_arr = np.frombuffer(image_bytes, np.uint8)
        image = cv2.imdecode(np_arr, cv2.IMREAD_COLOR)
        detector = cv2.QRCodeDetector()
        data, _, _ = detector.detectAndDecode(image)
        return data.strip() if data else None
    except Exception:
        return None

# Routes
@app.route("/")
def home():
    return render_template("home.html")

@app.route("/index")
def index():
    return render_template("index.html")

@app.route("/about")
def about():
    try:
        # Run hack.py and capture output
        result = subprocess.run(['python', 'hack.py'], capture_output=True, text=True)

        if result.returncode == 0:
            return render_template("about.html", script_output=result.stdout)
        else:
            flash("An error occurred while running hack.py", "error")
            return render_template("about.html")  # Redirect to home.html on failure
    except Exception as e:
        flash(f"Exception occurred: {str(e)}", "error")
        return render_template("about.html")  # Redirect on exception


@app.route("/booking")
def booking():
    return render_template("booking.html")

@app.route("/history")
def history():
    return render_template("history.html")

@app.route("/new")
def new():
    return render_template("new.html")

# API Routes
@app.route("/get_history", methods=["GET"])
def get_history():
    # Get user_id from session (using mock user for now)
    user_id = "user123"
    bookings = data_handler.get_user_bookings(user_id)
    return jsonify(bookings)

@app.route("/get_qr_history", methods=["GET"])
def get_qr_history():
    history = load_qr_history()
    return jsonify(history)

@app.route("/get_status", methods=["GET"])
def get_status():
    data = load_data()
    response = {
        "stand1": data.get("stand1", "opened"),
        "stand2": data.get("stand2", "opened"),
        "locked_by": data.get("locked_by", {}),
        **stands
    }
    return jsonify(response)

@app.route("/scan_qr", methods=["POST"])
def scan_qr_and_lock():
    request_data = request.get_json()
    stand = request.args.get("stand")
    image_data = request_data.get("image")

    if not stand or not image_data:
        return jsonify({"success": False, "message": "Invalid scan attempt!"})

    reg_no = decode_qr(image_data)
    if not reg_no:
        return jsonify({"success": False, "message": "No QR code detected!"})

    stand_key = f"stand{stand}"
    data = load_data()

    if stand_key not in data:
        return jsonify({"success": False, "message": f"Invalid stand: {stand}"})

    if data[stand_key] == "locked":
        locked_by = data["locked_by"].get(stand_key, "Unknown")
        if locked_by == reg_no:
            data[stand_key] = "opened"
            data["locked_by"].pop(stand_key, None)
            add_qr_history_entry(stand, "unlock", reg_no, "opened")
            message = f"✅ Stand {stand} unlocked by {reg_no}"
        else:
            message = f"❌ Stand {stand} is locked by {locked_by}."
            return jsonify({"success": False, "message": message})
    else:
        data[stand_key] = "locked"
        data["locked_by"][stand_key] = reg_no
        add_qr_history_entry(stand, "lock", reg_no, "locked")
        message = f"🔒 Stand {stand} locked by {reg_no}"

    save_data(data)
    return jsonify({"success": True, "message": message})

@app.route("/save_booking", methods=['POST'])
def save_booking():
    booking_data = request.json
    # Add user_id to booking data (in real app, get from session)
    booking_data['userId'] = "user123"
    new_booking = data_handler.create_booking(booking_data)
    
    # Update stands status
    stands[str(booking_data['standNumber'])] = "booked"
    
    # Add to QR history for tracking
    add_qr_history_entry(
        booking_data['standNumber'],
        "book",
        booking_data['userId'],
        "booked"
    )
    
    return jsonify(new_booking)

@app.route("/update_payment_status", methods=['POST'])
def update_payment_status():
    data = request.json
    data_handler.update_payment_status(data['bookingId'], data['status'])
    
    # Simulate payment processing delay
    time.sleep(2)
    
    # Add payment record to QR history
    booking = data_handler.get_booking_by_id(data['bookingId'])
    if booking:
        add_qr_history_entry(
            booking['standNumber'],
            "payment",
            booking['userId'],
            data['status']
        )
    
    return jsonify({"success": True})

@app.route("/cancel_booking", methods=['POST'])
def cancel_booking():
    data = request.json
    booking = data_handler.get_booking_by_id(data['bookingId'])
    
    if booking:
        # Update stands status
        stands[str(booking['standNumber'])] = "available"
        
        # Add cancellation to QR history
        add_qr_history_entry(
            booking['standNumber'],
            "cancel",
            booking['userId'],
            "cancelled"
        )
        
        # Cancel the booking
        data_handler.cancel_booking(data['bookingId'])
    
    return jsonify({"success": True})

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)