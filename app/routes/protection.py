
from flask import Blueprint, jsonify, request
from flask_jwt_extended import jwt_required, get_jwt_identity
from app.schemas.protection_schema import ToggleProtectionSchema, SensorDataSchema, SensorWindowSchema
from app.services.protection_service import (
    toggle_protection, get_protection_status, analyze_sensor_data, predict_from_window
)
from marshmallow import ValidationError

protection_bp = Blueprint('protection', __name__)

@protection_bp.route('/toggle', methods=['POST'])
@jwt_required()
def toggle():
    current_user_id = get_jwt_identity()
    schema = ToggleProtectionSchema()
    try:
        data = schema.load(request.json)
    except ValidationError as err:
        return jsonify(success=False, error={"code": "VALIDATION_ERROR", "message": "Invalid request", "details": err.messages}), 400

    success, msg = toggle_protection(current_user_id, data['is_active'])
    
    status = get_protection_status(current_user_id)
    return jsonify(success=True, data=status, message=msg), 200

@protection_bp.route('/status', methods=['GET'])
@jwt_required()
def status():
    current_user_id = get_jwt_identity()
    status = get_protection_status(current_user_id)
    return jsonify(success=True, data=status), 200

@protection_bp.route('/sensor-data', methods=['POST'])
@jwt_required()
def sensor_data():
    current_user_id = get_jwt_identity()
    schema = SensorDataSchema()
    try:
        data = schema.load(request.json)
    except ValidationError as err:
        return jsonify(success=False, error={"code": "VALIDATION_ERROR", "message": "Invalid request", "details": err.messages}), 400

    result = analyze_sensor_data(
        current_user_id, 
        data['sensor_type'], 
        data['data'], 
        data['sensitivity']
    )
    
    return jsonify(success=True, data=result), 200

@protection_bp.route('/predict', methods=['POST'])
@jwt_required()
def predict():
    """ML-based danger prediction from a raw sensor window.

    Accepts: {"window": [[x,y,z], ...], "location": "optional string"}
    Returns: {"prediction": 0|1, "confidence": float, "sos_sent": bool}
    """
    current_user_id = get_jwt_identity()
    schema = SensorWindowSchema()
    try:
        data = schema.load(request.json)
    except ValidationError as err:
        return jsonify(success=False, error={"code": "VALIDATION_ERROR", "message": "Invalid request", "details": err.messages}), 400

    result = predict_from_window(
        current_user_id,
        data['window'],
        data.get('location', 'Unknown')
    )

    return jsonify(success=True, data=result), 200

@protection_bp.route('/collect', methods=['POST'])
@jwt_required()
def collect_data():
    """Endpoint to ingest labeled sensor data for training."""
    current_user_id = get_jwt_identity()
    from app.schemas.protection_schema import SensorTrainingSchema
    from app.services.protection_service import save_training_data

    schema = SensorTrainingSchema()
    try:
        data = schema.load(request.json)
    except ValidationError as err:
        return jsonify(success=False, error={"code": "VALIDATION_ERROR", "message": "Invalid request", "details": err.messages}), 400

    success, msg = save_training_data(
        current_user_id,
        data['sensor_type'],
        data['data'],
        data['label'],
        is_verified=True # Direct collection implies user knows the label
    )

    if success:
        return jsonify(success=True, message=msg), 201
    else:
        return jsonify(success=False, error={"code": "DB_ERROR", "message": msg}), 500
