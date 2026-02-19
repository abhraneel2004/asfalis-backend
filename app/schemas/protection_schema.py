
from marshmallow import Schema, fields, validate

class ToggleProtectionSchema(Schema):
    is_active = fields.Bool(required=True)

class SensorReadingSchema(Schema):
    x = fields.Float(required=True)
    y = fields.Float(required=True)
    z = fields.Float(required=True)
    timestamp = fields.Int(required=True)

class SensorDataSchema(Schema):
    sensor_type = fields.Str(required=True, validate=validate.OneOf(["accelerometer", "gyroscope"]))
    data = fields.List(fields.Nested(SensorReadingSchema), required=True)
    sensitivity = fields.Str(missing="medium")

class SensorWindowSchema(Schema):
    """Schema for the /predict endpoint — accepts a raw window of [x, y, z] readings."""
    window = fields.List(
        fields.List(fields.Float(), required=True),
        required=True,
        validate=validate.Length(min=3)
    )
    location = fields.Str(missing="Unknown")

class SensorTrainingSchema(Schema):
    sensor_type = fields.Str(required=True, validate=validate.OneOf(["accelerometer", "gyroscope"]))
    data = fields.List(fields.Nested(SensorReadingSchema), required=True)
    label = fields.Int(required=True, validate=validate.OneOf([0, 1])) # 0=Safe, 1=Danger
