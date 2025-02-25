import qrcode
import os

# Ensure "users" folder exists
if not os.path.exists("users"):
    os.makedirs("users")

# Get user registration number
reg_no = input("Enter Registration Number: ")

# Generate QR code
qr = qrcode.make(reg_no)

# Save QR as "users/{reg_no}.png"
qr.save(f"users/{reg_no}.png")

print(f"QR Code Generated and saved as users/{reg_no}.png")
