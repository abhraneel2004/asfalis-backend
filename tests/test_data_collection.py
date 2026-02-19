
import unittest
import json
import os
os.environ['FLASK_TESTING'] = '1'

from unittest.mock import MagicMock, patch
from app import create_app, db
from app.models.sensor_data import SensorTrainingData

class TestDataCollection(unittest.TestCase):
    def setUp(self):
        self.app = create_app()
        self.client = self.app.test_client()
        self.app_context = self.app.app_context()
        self.app_context.push()
        
        # Mock JWT
        self.patcher = patch('flask_jwt_extended.view_decorators.verify_jwt_in_request')
        self.mock_jwt = self.patcher.start()
        
        # Mock JWT
        self.patcher = patch('flask_jwt_extended.view_decorators.verify_jwt_in_request')
        self.mock_jwt = self.patcher.start()
        
        # Patch the function where it is USED
        self.patcher_id = patch('app.routes.protection.get_jwt_identity')
        self.mock_get_jwt_identity = self.patcher_id.start()
        self.mock_get_jwt_identity.return_value = 'user_123'

    def tearDown(self):
        self.patcher.stop()
        self.patcher_id.stop()
        self.app_context.pop()

    @patch('app.services.protection_service.save_training_data')
    def test_collect_data_endpoint(self, mock_save):
        print("DEBUG: Inside test_collect_data_endpoint")
        mock_save.return_value = (True, "Saved 1 records")
        
        payload = {
            "sensor_type": "accelerometer",
            "data": [
                {"x": 0.1, "y": 0.2, "z": 9.8, "timestamp": 1234567890}
            ],
            "label": 0
        }
        
        print("DEBUG: Sending request...")
        response = self.client.post('/api/protection/collect', 
                                    data=json.dumps(payload),
                                    content_type='application/json')
        
        print(f"DEBUG: Response status: {response.status_code}")
        print(f"DEBUG: Response data: {response.data}")
        self.assertEqual(response.status_code, 201)
        self.assertTrue(response.json['success'])
        mock_save.assert_called_once()

if __name__ == '__main__':
    print("DEBUG: Running main")
    unittest.main()
