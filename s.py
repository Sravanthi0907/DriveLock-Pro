import cv2
import json
import time
import os

DATA_FILE = "data.json"

# Load existing data or create new
if os.path.exists(DATA_FILE):
    with open(DATA_FILE, "r") as f:
        stand_data = json.load(f)
else:
    stand_data = {"stand1": "opened", "stand2": "opened", "locked_by": {}}

# Initialize webcam
cap = cv2.VideoCapture(0)
detector = cv2.QRCodeDetector()

print("Scanning for QR Code...")

while True:
    _, frame = cap.read()
    data, _, _ = detector.detectAndDecode(frame)

    if data:
        reg_no = data.strip()
        print(f"Detected QR Code: {reg_no}")
        break

    cv2.imshow("QR Scanner", frame)
    if cv2.waitKey(1) & 0xFF == ord("q"):
        break

cap.release()
cv2.destroyAllWindows()

# Ask user to select stand
while True:
    stand_choice = input("Select Stand (1 or 2): ").strip()

    if stand_choice not in ["1", "2"]:
        print("Invalid choice! Select Stand 1 or 2.")
        continue

    stand_key = f"stand{stand_choice}"

    # If stand is locked, allow only the locker to unlock
    if stand_data[stand_key] == "locked":
        locked_by = stand_data["locked_by"].get(stand_key, "Unknown")

        if locked_by == reg_no:
            stand_data[stand_key] = "opened"
            del stand_data["locked_by"][stand_key]
            print(f"✅ Stand {stand_choice} unlocked by {reg_no}")
        else:
            print(f"❌ Stand {stand_choice} is already taken by {locked_by}")
            break
    else:
        stand_data[stand_key] = "locked"
        stand_data["locked_by"][stand_key] = reg_no
        print(f"🔒 Stand {stand_choice} locked by {reg_no}")

    # Save updated data
    with open(DATA_FILE, "w") as f:
        json.dump(stand_data, f, indent=4)

    break
