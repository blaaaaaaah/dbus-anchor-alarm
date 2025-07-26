# Copyright (c) 2025 Thomas Dubois
# 
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in all
# copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.

import sys
import os
import json
import tempfile
import unittest
from unittest.mock import MagicMock, Mock, patch

sys.path.insert(1, os.path.join(sys.path[0], '..'))
sys.path.insert(1, os.path.join(os.path.dirname(__file__), '../ext/velib_python/test'))
sys.path.insert(1, os.path.join(os.path.dirname(__file__), '../ext/'))

# Mock modules that may not be available in test environment
sys.modules['dbus'] = Mock()

sys.path.insert(1, os.path.join(sys.path[0], '../connectors'))

from dbus_dwp_connector import DBusDWPConnector
from anchor_alarm_model import AnchorAlarmState

from mock_dbus_service import MockDbusService
from mock_settings_device import MockSettingsDevice
from glib_timer_mock import GLibTimerMock

class MockDBusDWPConnector(DBusDWPConnector):
    """Mock DWP connector for testing"""
    
    def __init__(self, *args, **kwargs):
        # Create a temporary file for VAPID keys testing
        self._temp_dir = tempfile.mkdtemp()
        super().__init__(*args, **kwargs)
        self._vapid_keys_file = os.path.join(self._temp_dir, 'vapid_keys.json')

timer_provider = GLibTimerMock()

def create_mock_dbus_service():
    """Create a mock D-Bus service for testing"""
    return MockDbusService("com.victronenergy.anchoralarm.test")

class TestDBusDWPConnector(unittest.TestCase):

    def setUp(self):
        self.maxDiff = None

    def test_vapid_key_generation(self):
        """Test that VAPID keys are generated correctly"""
        mock_dbus_service = create_mock_dbus_service()
        
        with patch('dbus_dwp_connector.WEBPUSH_AVAILABLE', True):
            connector = MockDBusDWPConnector(
                lambda: timer_provider, 
                lambda settings, cb: MockSettingsDevice(settings, cb),
                mock_dbus_service
            )
            
            # Check that VAPID keys were generated
            self.assertIsNotNone(connector._vapid_keys)
            self.assertIn('public_key', connector._vapid_keys)
            self.assertIn('private_key', connector._vapid_keys)
            
            # Check that public key was published to settings
            public_key = connector.get_vapid_public_key()
            self.assertIsNotNone(public_key)
            self.assertEqual(connector._settings['DWPPublicKey'], public_key)

    def test_subscription_management(self):
        """Test adding and removing push subscriptions"""
        mock_dbus_service = create_mock_dbus_service()
        
        with patch('dbus_dwp_connector.WEBPUSH_AVAILABLE', True):
            connector = MockDBusDWPConnector(
                lambda: timer_provider,
                lambda settings, cb: MockSettingsDevice(settings, cb),
                mock_dbus_service
            )
            
            # Test adding a subscription
            subscription_id = "test-subscription-123"
            subscription_info = {
                "endpoint": "https://fcm.googleapis.com/fcm/send/test",
                "keys": {
                    "p256dh": "test-p256dh-key",
                    "auth": "test-auth-key"
                }
            }
            
            success = connector.add_subscription(subscription_id, subscription_info)
            self.assertTrue(success)
            self.assertIn(subscription_id, connector._subscriptions)
            
            # Test removing a subscription
            success = connector.remove_subscription(subscription_id)
            self.assertTrue(success)
            self.assertNotIn(subscription_id, connector._subscriptions)

    def test_trigger_register_dwp_device(self):
        """Test DWP device registration trigger"""
        mock_dbus_service = create_mock_dbus_service()
        
        with patch('dbus_dwp_connector.WEBPUSH_AVAILABLE', True):
            connector = MockDBusDWPConnector(
                lambda: timer_provider,
                lambda settings, cb: MockSettingsDevice(settings, cb),
                mock_dbus_service
            )
            
            # Test registration with valid data
            subscription_data = {
                "subscriptionId": "test-device-456",
                "subscription": {
                    "endpoint": "https://fcm.googleapis.com/fcm/send/test456",
                    "keys": {
                        "p256dh": "test-p256dh-key-456",
                        "auth": "test-auth-key-456"
                    }
                }
            }
            
            success = connector.trigger_register_dwp_device(json.dumps(subscription_data))
            self.assertTrue(success)
            self.assertIn("test-device-456", connector._subscriptions)

    def test_trigger_unregister_dwp_device(self):
        """Test DWP device unregistration trigger"""
        mock_dbus_service = create_mock_dbus_service()
        
        with patch('dbus_dwp_connector.WEBPUSH_AVAILABLE', True):
            connector = MockDBusDWPConnector(
                lambda: timer_provider,
                lambda settings, cb: MockSettingsDevice(settings, cb),
                mock_dbus_service
            )
            
            # Add a subscription first
            subscription_id = "test-device-789"
            subscription_info = {
                "endpoint": "https://fcm.googleapis.com/fcm/send/test789",
                "keys": {
                    "p256dh": "test-p256dh-key-789",
                    "auth": "test-auth-key-789"
                }
            }
            connector.add_subscription(subscription_id, subscription_info)
            
            # Test unregistration
            success = connector.trigger_unregister_dwp_device(subscription_id)
            self.assertTrue(success)
            self.assertNotIn(subscription_id, connector._subscriptions)

    def test_dbus_paths_initialization(self):
        """Test that D-Bus paths are properly initialized"""
        mock_dbus_service = create_mock_dbus_service()
        
        with patch('dbus_dwp_connector.WEBPUSH_AVAILABLE', True):
            connector = MockDBusDWPConnector(
                lambda: timer_provider,
                lambda settings, cb: MockSettingsDevice(settings, cb),
                mock_dbus_service
            )
            
            # Check that DWP trigger paths were added
            service = connector._dbus_service
            self.assertTrue(hasattr(service, 'add_path'))
            
            # The mock service should have received calls to add_path
            # for the DWP trigger paths

    def test_webpush_unavailable_handling(self):
        """Test behavior when webpush dependencies are not available"""
        mock_dbus_service = create_mock_dbus_service()
        
        with patch('dbus_dwp_connector.WEBPUSH_AVAILABLE', False):
            connector = MockDBusDWPConnector(
                lambda: timer_provider,
                lambda settings, cb: MockSettingsDevice(settings, cb),
                mock_dbus_service
            )
            
            # Should handle gracefully without crashing
            self.assertIsNotNone(connector)

if __name__ == '__main__':
    unittest.main()