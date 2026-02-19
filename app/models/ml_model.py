
from app.extensions import db
from datetime import datetime
import uuid

class MLModel(db.Model):
    __tablename__ = 'ml_models'

    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    version = db.Column(db.String(20), nullable=False) # e.g. "v1.0", "v1.1"
    is_active = db.Column(db.Boolean, default=False)
    data = db.Column(db.LargeBinary, nullable=False) # Pickled model data
    accuracy = db.Column(db.Float, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def to_dict(self):
        return {
            'id': self.id,
            'version': self.version,
            'is_active': self.is_active,
            'accuracy': self.accuracy,
            'created_at': self.created_at.isoformat()
        }
