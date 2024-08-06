from flask import Flask, request, jsonify
from flask_sqlalchemy import SQLAlchemy
from flask_cors import CORS
from datetime import datetime, timedelta
from geopy.distance import geodesic

app = Flask(__name__)
CORS(app)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///attendance.db'
db = SQLAlchemy(app)

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(80), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    attendances = db.relationship('Attendance', backref='user', lazy=True)

class Attendance(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    device_id = db.Column(db.String(120), nullable=False)  # New field for device ID

@app.route('/register', methods=['POST'])
def register():
    data = request.json
    name = data.get('name')
    email = data.get('email')

    if not name or not email:
        return jsonify({'message': 'Name and email are required'}), 400

    existing_user = User.query.filter_by(email=email).first()
    if existing_user:
        return jsonify({'message': 'User with this email already exists'}), 400

    user = User(name=name, email=email)
    db.session.add(user)
    db.session.commit()
    
    return jsonify({'message': 'User registered successfully'}), 201

@app.route('/mark_attendance', methods=['POST'])
def mark_attendance():
    data = request.json
    email = data.get('email')
    user_lat = data.get('latitude')
    user_lon = data.get('longitude')
    device_id = data.get('device_id')  # Device ID from request

    if not email or not user_lat or not user_lon or not device_id:
        return jsonify({'message': 'Email, latitude, longitude, and device ID are required'}), 400

    user = User.query.filter_by(email=email).first()
    if not user:
        return jsonify({'message': 'User not found'}), 404

    # Define the center point and a 500-meter allowed range
    center = (26.4732, 73.1140)  # Coordinates of the specified location
    range_m = 500  # 500 meters for the geofence

    user_location = (user_lat, user_lon)
    distance = geodesic(center, user_location).meters

    if distance > range_m:
        return jsonify({'message': 'User is out of range'}), 403

    # Check if the device has already marked attendance in the last hour
    last_attendance = Attendance.query.filter_by(device_id=device_id).order_by(Attendance.timestamp.desc()).first()
    if last_attendance and datetime.utcnow() - last_attendance.timestamp < timedelta(hours=1):
        return jsonify({'message': 'You can only mark attendance once per hour from the same device'}), 403

    attendance = Attendance(user_id=user.id, device_id=device_id)
    db.session.add(attendance)
    db.session.commit()

    return jsonify({'message': 'Attendance marked successfully'}), 201

@app.route('/attendance', methods=['GET'])
def get_attendance():
    attendances = Attendance.query.all()
    attendance_list = [{
        'id': attendance.id,
        'user_id': attendance.user_id,
        'timestamp': attendance.timestamp,
        'device_id': attendance.device_id  # Include device ID in response
    } for attendance in attendances]
    return jsonify(attendance_list)

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(debug=True)
