import json
from datetime import datetime
import os

class DataHandler:
    def __init__(self):
        self.bookings_file = 'bookings.json'
        self.users_file = 'users.json'
        self.stands_file = 'stands.json'
        self.initialize_files()

    def initialize_files(self):
        # Create files if they don't exist
        for file_name in [self.bookings_file, self.users_file, self.stands_file]:
            if not os.path.exists(file_name):
                with open(file_name, 'w') as f:
                    if file_name == self.bookings_file:
                        json.dump({"bookings": []}, f)
                    elif file_name == self.users_file:
                        json.dump({"users": []}, f)
                    else:
                        json.dump({"stands": [{"id": i, "status": "available", "current_booking_id": None} for i in range(1, 11)]}, f)

    def read_json_file(self, file_name):
        with open(file_name, 'r') as f:
            return json.load(f)

    def write_json_file(self, file_name, data):
        with open(file_name, 'w') as f:
            json.dump(data, f, indent=2)

    def get_user_bookings(self, user_id):
        data = self.read_json_file(self.bookings_file)
        return [booking for booking in data['bookings'] if booking['userId'] == user_id]

    def create_booking(self, booking_data):
        data = self.read_json_file(self.bookings_file)
        booking_id = int(datetime.now().timestamp() * 1000)
        
        new_booking = {
            "id": booking_id,
            "standNumber": booking_data['standNumber'],
            "startTime": booking_data['startTime'],
            "endTime": booking_data['endTime'],
            "amountPaid": booking_data.get('amountPaid', 0),
            "paymentStatus": booking_data.get('paymentStatus', 'Pending'),
            "userId": booking_data['userId']
        }
        
        data['bookings'].append(new_booking)
        self.write_json_file(self.bookings_file, data)
        
        # Update stand status
        self.update_stand_status(booking_data['standNumber'], "occupied", booking_id)
        
        # Update user's active bookings
        self.update_user_bookings(booking_data['userId'], booking_id)
        
        return new_booking

    def update_stand_status(self, stand_number, status, booking_id=None):
        data = self.read_json_file(self.stands_file)
        for stand in data['stands']:
            if stand['id'] == stand_number:
                stand['status'] = status
                stand['current_booking_id'] = booking_id
                break
        self.write_json_file(self.stands_file, data)

    def update_user_bookings(self, user_id, booking_id):
        data = self.read_json_file(self.users_file)
        for user in data['users']:
            if user['id'] == user_id:
                if 'active_bookings' not in user:
                    user['active_bookings'] = []
                user['active_bookings'].append(booking_id)
                break
        self.write_json_file(self.users_file, data)

    def update_payment_status(self, booking_id, status):
        data = self.read_json_file(self.bookings_file)
        for booking in data['bookings']:
            if booking['id'] == booking_id:
                booking['paymentStatus'] = status
                break
        self.write_json_file(self.bookings_file, data)

    def cancel_booking(self, booking_id):
        # Get booking data
        data = self.read_json_file(self.bookings_file)
        booking = None
        for b in data['bookings']:
            if b['id'] == booking_id:
                booking = b
                data['bookings'].remove(b)
                break
                
        if booking:
            # Update stand status
            self.update_stand_status(booking['standNumber'], "available", None)
            
            # Update user's active bookings
            user_data = self.read_json_file(self.users_file)
            for user in user_data['users']:
                if user['id'] == booking['userId']:
                    if booking_id in user['active_bookings']:
                        user['active_bookings'].remove(booking_id)
                    break
            self.write_json_file(self.users_file, user_data)
            
        self.write_json_file(self.bookings_file, data)

    def get_booking_by_id(self, booking_id):
        data = self.read_json_file(self.bookings_file)
        for booking in data['bookings']:
            if booking['id'] == booking_id:
                return booking
        return None