
import os
import time
import numpy as np
import joblib
from flask import current_app

from app.services.sos_service import trigger_sos

# ---------------------------------------------------------------------------
# Model loading (once at import time)
# ---------------------------------------------------------------------------
_MODEL_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..', 'model.pkl')
_model = None


def _get_model():
    """Lazy-load the ML model so it works inside the Flask app context."""
    global _model
    if _model is None:
        try:
            _model = joblib.load(_MODEL_PATH)
            print(f"✅ Danger-detection model loaded from {_MODEL_PATH}")
        except Exception as e:
            print(f"❌ Failed to load model: {e}")
    return _model


# ---------------------------------------------------------------------------
# In-memory stores
# ---------------------------------------------------------------------------
# Active protection toggle per user
active_protection_users = {}

# SOS cooldown tracker: user_id -> last SOS trigger timestamp
_sos_cooldown = {}
SOS_COOLDOWN_SECONDS = 20


def _is_on_cooldown(user_id):
    """Return True if the user has triggered an SOS within the last 20 seconds."""
    last_trigger = _sos_cooldown.get(user_id)
    if last_trigger is None:
        return False
    return (time.time() - last_trigger) < SOS_COOLDOWN_SECONDS


def _mark_sos_triggered(user_id):
    """Record that an SOS was just triggered for cooldown tracking."""
    _sos_cooldown[user_id] = time.time()


# ---------------------------------------------------------------------------
# Feature extraction (mirrors data_train.py exactly)
# ---------------------------------------------------------------------------
def extract_features(window):
    """Extract 15 statistical features from a sensor window.

    Args:
        window: np.ndarray of shape (N, 3) — N readings of [x, y, z].

    Returns:
        np.ndarray of shape (1, 15) ready for model.predict().
    """
    window = np.array(window, dtype=float)
    feats = []
    for i in range(3):
        axis = window[:, i]
        feats += [axis.mean(), axis.std(), axis.max(), axis.min(), np.sum(axis ** 2)]
    return np.array(feats).reshape(1, -1)


def predict_danger(window_data):
    """Run the ML model on a sensor window.

    Args:
        window_data: list of [x, y, z] lists.

    Returns:
        (prediction, confidence) — prediction is 0 (safe) or 1 (danger).
    """
    model = _get_model()
    if model is None:
        return 0, 0.0

    features = extract_features(window_data)
    prediction = int(model.predict(features)[0])

    # Get probability if the model supports it
    confidence = 0.0
    if hasattr(model, 'predict_proba'):
        proba = model.predict_proba(features)[0]
        confidence = float(proba[prediction])

    return prediction, confidence


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------
def toggle_protection(user_id, is_active):
    if is_active:
        active_protection_users[user_id] = True
        return True, "Protection activated"
    else:
        active_protection_users.pop(user_id, None)
        return True, "Protection deactivated"


def get_protection_status(user_id):
    is_active = active_protection_users.get(user_id, False)
    return {
        "is_active": is_active,
        "bracelet_connected": False  # Mock
    }


def analyze_sensor_data(user_id, sensor_type, readings, sensitivity):
    """Analyze incoming sensor readings using the ML model.

    This replaces the old threshold-based mock logic. The readings list
    of {x, y, z, timestamp} dicts is converted into a window and fed to
    the RandomForest model.
    """
    if not active_protection_users.get(user_id):
        return {"alert_triggered": False, "confidence": 0.0}

    # Convert [{x, y, z, timestamp}, ...] into [[x, y, z], ...]
    window_data = [[r['x'], r['y'], r['z']] for r in readings]

    prediction, confidence = predict_danger(window_data)

    if prediction == 1:
        # Check cooldown before triggering SOS
        if _is_on_cooldown(user_id):
            return {
                "alert_triggered": False,
                "confidence": confidence,
                "message": "SOS on cooldown, please wait before triggering again."
            }

        # Trigger SOS
        from app.services.location_service import get_last_location
        last_loc = get_last_location(user_id)
        lat = last_loc.latitude if last_loc else 0.0
        lng = last_loc.longitude if last_loc else 0.0

        alert, msg = trigger_sos(user_id, lat, lng, trigger_type=f"auto_{sensor_type}")
        _mark_sos_triggered(user_id)

        # Send WhatsApp alert
        try:
            from app.services.whatsapp_service import send_whatsapp_alert
            from app.models.trusted_contact import TrustedContact
            contacts = TrustedContact.query.filter_by(user_id=user_id).all()
            maps_link = f"https://maps.google.com/?q={lat},{lng}"
            whatsapp_msg = f"⚠ SOS ALERT!\nDanger detected via {sensor_type}!\n📍 Location: {maps_link}"
            for contact in contacts:
                send_whatsapp_alert(contact.phone, whatsapp_msg)
        except Exception as e:
            current_app.logger.error(f"WhatsApp alert failed: {e}")

        return {
            "alert_triggered": True,
            "alert_id": alert.id if alert else None,
            "confidence": confidence
        }

    return {"alert_triggered": False, "confidence": confidence}


def predict_from_window(user_id, window_data, location="Unknown"):
    """Direct window-based prediction (mirrors dummy_server.py /predict).

    Args:
        user_id: The authenticated user's ID.
        window_data: list of [x, y, z] lists.
        location: Optional location string.

    Returns:
        dict with prediction result.
    """
    prediction, confidence = predict_danger(window_data)

    response = {"prediction": prediction, "confidence": confidence}

    if prediction == 1:
        # Check cooldown
        if _is_on_cooldown(user_id):
            response["sos_sent"] = False
            response["message"] = "SOS on cooldown, please wait before triggering again."
            return response

        # Trigger SOS
        from app.services.location_service import get_last_location
        last_loc = get_last_location(user_id)
        lat = last_loc.latitude if last_loc else 0.0
        lng = last_loc.longitude if last_loc else 0.0

        alert, msg = trigger_sos(user_id, lat, lng, trigger_type="auto_sensor_window")
        _mark_sos_triggered(user_id)

        # Send WhatsApp alert
        try:
            from app.services.whatsapp_service import send_whatsapp_alert
            from app.models.trusted_contact import TrustedContact
            contacts = TrustedContact.query.filter_by(user_id=user_id).all()
            maps_link = f"https://maps.google.com/?q={lat},{lng}"
            whatsapp_msg = f"⚠ SOS ALERT!\nDanger detected!\n📍 Location: {location}\n🗺 Map: {maps_link}"
            for contact in contacts:
                send_whatsapp_alert(contact.phone, whatsapp_msg)
        except Exception as e:
            current_app.logger.error(f"WhatsApp alert failed: {e}")

        response["sos_sent"] = True
        response["alert_id"] = alert.id if alert else None

    return response
