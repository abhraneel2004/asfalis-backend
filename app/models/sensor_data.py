
from app.extensions import db
from datetime import datetime
import uuid

class SensorTrainingData(db.Model):
    __tablename__ = 'sensor_training_data'

    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = db.Column(db.String(36), db.ForeignKey('users.id'), nullable=False)
    timestamp = db.Column(db.BigInteger, nullable=False) # Unix timestamp (ms)
    
    # Sensor readings
    x = db.Column(db.Float, nullable=False)
    y = db.Column(db.Float, nullable=False)
    z = db.Column(db.Float, nullable=False)
    
    sensor_type = db.Column(db.String(20), nullable=False) # 'accelerometer', 'gyroscope'
    
    # Labels for RL/Training
    # 0 = Safe/False Positive, 1 = Danger/True Positive
    label = db.Column(db.Integer, nullable=False) 
    
    is_verified = db.Column(db.Boolean, default=False) # True if manually provided/corrected by user
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def to_dict(self):
        return {
            'id': self.id,
            'user_id': self.user_id,
            'timestamp': self.timestamp,
            'x': self.x,
            'y': self.y,
            'z': self.z,
            'sensor_type': self.sensor_type,
            'label': self.label,
            'is_verified': self.is_verified,
            'created_at': self.created_at.isoformat()
        }
