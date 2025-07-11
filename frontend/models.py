from datetime import datetime
from database import db
from flask_login import UserMixin

class User(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True)
    role = db.Column(db.String(50), default="clinician")  # or 'admin'
    name = db.Column(db.String(150), nullable=False)
    email = db.Column(db.String(150), unique=True, nullable=False)
    password = db.Column(db.String(200), nullable=False)

    # New clinician fields
    institution = db.Column(db.String(200))
    license_number = db.Column(db.String(100))
    is_verified = db.Column(db.Boolean, default=False)

    predictions = db.relationship("Prediction", backref="user", lazy=True)
    feedbacks = db.relationship("Feedback", backref="user", lazy=True)  # <-- NEW


class Prediction(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    image_path = db.Column(db.String(300), nullable=False)
    gradcam_path = db.Column(db.String(300), nullable=True)
    label = db.Column(db.String(50), nullable=False)
    confidence = db.Column(db.Float, nullable=False)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    feedbacks = db.relationship("Feedback", backref="prediction", lazy=True)  # <-- NEW


# NEW MODEL
class Feedback(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    prediction_id = db.Column(db.Integer, db.ForeignKey("prediction.id"), nullable=False)

    is_correct = db.Column(db.Boolean, nullable=False)
    true_label = db.Column(db.String(50), nullable=True)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)



class Notification(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True)  # null = global
    message = db.Column(db.String(500), nullable=False)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    is_read = db.Column(db.Boolean, default=False)

    user = db.relationship('User', backref='notifications')

