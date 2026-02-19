
import os
import sys
import joblib
import pandas as pd
import numpy as np
from sqlalchemy import create_engine
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import train_test_split
from sklearn.metrics import accuracy_score, classification_report
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Add project root to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.config import Config
from app.services.protection_service import extract_features

def train():
    print("🔄 Connecting to database...")
    db_url = Config.SQLALCHEMY_DATABASE_URI
    engine = create_engine(db_url)
    
    # Fetch labeled training data
    query = "SELECT * FROM sensor_training_data WHERE label IS NOT NULL"
    df = pd.read_sql(query, engine)
    
    if df.empty:
        print("⚠️ No training data found in 'sensor_training_data'. Aborting.")
        return

    print(f"✅ Loaded {len(df)} records.")
    
    # Prepare features
    # We need to reconstruct windows from the raw data stream.
    # storage format: one row per reading.
    # Logic: Group by user_id + sensor_type, sort by timestamp, then chunk into windows of size N=40.
    
    FEATURE_WINDOW_SIZE = 40
    X_features = []
    y_labels = []
    
    # Group by user and sensor type
    grouped = df.groupby(['user_id', 'sensor_type'])
    
    for (uid, stype), group in grouped:
        # Sort by timestamp
        group = group.sort_values('timestamp')
        
        # Create windows
        # Use numpy for efficiency
        raw_x = group['x'].values
        raw_y = group['y'].values
        raw_z = group['z'].values
        labels = group['label'].values # Should be consistent within a window ideally
        
        num_readings = len(group)
        # We need at least one window
        if num_readings < FEATURE_WINDOW_SIZE:
            continue
            
        # Slide or Chunk? Let's Chunk for simplicity
        num_windows = num_readings // FEATURE_WINDOW_SIZE
        
        for i in range(num_windows):
            start = i * FEATURE_WINDOW_SIZE
            end = start + FEATURE_WINDOW_SIZE
            
            # Extract statistical features (Mean, Std, Max, Min, SumSq) for X, Y, Z
            # Total 15 features
            w_x = raw_x[start:end]
            w_y = raw_y[start:end]
            w_z = raw_z[start:end]
            
            # Label: use the majority vote or the first label of the window
            # Since we auto-label the whole batch, they are likely same.
            w_label = labels[start] 
            
            feats = []
            for axis in [w_x, w_y, w_z]:
                feats += [axis.mean(), axis.std(), axis.max(), axis.min(), np.sum(axis ** 2)]
            
            # 2. Add Sensor Type One-Hot Encoding
            if stype == 'accelerometer':
                feats += [1, 0]
            elif stype == 'gyroscope':
                feats += [0, 1]
            else:
                feats += [0, 0]
                
            X_features.append(feats)
            y_labels.append(w_label)
            
    if not X_features:
        print("⚠️  Not enough data to form complete windows (need 40 readings). Aborting.")
        return

    X = np.array(X_features)
    y = np.array(y_labels)
    
    print(f"✅ Created {len(X)} training windows (Features: {X.shape[1]}).")
    
    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)
    
    model = RandomForestClassifier(n_estimators=100)
    model.fit(X_train, y_train)
    
    preds = model.predict(X_test)
    print(f"🎯 Accuracy: {accuracy_score(y_test, preds)}")
    print(classification_report(y_test, preds))
    
    # Serialize model
    import io
    model_bytes = io.BytesIO()
    joblib.dump(model, model_bytes)
    model_data = model_bytes.getvalue()
    
    # Save to DB
    from app import create_app
    from app.models.ml_model import MLModel
    from app.extensions import db
    from datetime import datetime

    app = create_app()
    with app.app_context():
        # Deactivate old models
        db.session.query(MLModel).update({MLModel.is_active: False})
        
        # Save new model
        version = f"v{datetime.now().strftime('%Y%m%d%H%M')}"
        new_model = MLModel(
            version=version,
            is_active=True,
            data=model_data,
            accuracy=float(accuracy_score(y_test, preds))
        )
        db.session.add(new_model)
        db.session.commit()
        print(f"💾 Model {version} saved to database with accuracy {new_model.accuracy}")

if __name__ == "__main__":
    train()
