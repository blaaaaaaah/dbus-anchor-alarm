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
import logging
import time

sys.path.insert(1, os.path.join(sys.path[0], '..'))
sys.path.insert(1, os.path.join(sys.path[0], '../ext'))

from abstract_connector import AbstractConnector
from anchor_alarm_model import AnchorAlarmState

# Web Push imports
try:
    from pywebpush import webpush, WebPushException
    from cryptography.hazmat.primitives import serialization
    from cryptography.hazmat.primitives.asymmetric import ec
    from cryptography.hazmat.backends import default_backend
    import base64
    WEBPUSH_AVAILABLE = True
except ImportError as e:
    WEBPUSH_AVAILABLE = False
    webpush = None
    logging.warning(f"Web push dependencies not available: {e}")

logger = logging.getLogger(__name__)

class DBusDWPConnector(AbstractConnector):
    """
    Declarative Web Push (DWP) Connector for sending push notifications to iOS and other devices.
    Handles VAPID key generation, subscription management, and notification delivery.
    Integrates with D-Bus service for trigger handling.
    """
    
    def __init__(self, timer_provider, settings_provider, dbus_service):
        super().__init__(timer_provider, settings_provider)
        
        self._dbus_service = dbus_service
        self._vapid_keys_file = os.path.join(os.path.dirname(__file__), '..', 'vapid_keys.json')
        self._subscriptions = {}
        self._vapid_keys = None
        
        if not WEBPUSH_AVAILABLE:
            logger.error("Web push dependencies not available. Push notifications will not work.")
            return
        
        # Log versions for debugging
        try:
            import pywebpush
            import cryptography
            logger.info(f"pywebpush version: {pywebpush.__version__ if hasattr(pywebpush, '__version__') else 'unknown'}")
            logger.info(f"cryptography version: {cryptography.__version__}")
        except Exception as e:
            logger.warning(f"Could not get library versions: {e}")
            
        self._init_settings()
        self._load_or_generate_vapid_keys()
        self._load_subscriptions()
        self._init_dbus_paths()
        
    def _init_settings(self):
        """Initialize settings for push notifications"""
        settingsList = {
            # VAPID public key for frontend access (path from MQTTParser) - readonly
            "DWPPublicKey": ["/Settings/AnchorAlarm/PushNotifications/DWP/PublicKey", "", 0, 0, False],
            
            # Contact email for VAPID (required by web push spec)
            "VapidContactEmail": ["/Settings/AnchorAlarm/PushNotifications/VapidContactEmail", "admin@localhost", 0, 0],
            
            # JSON string containing push subscriptions (managed automatically) - readonly
            "Subscriptions": ["/Settings/AnchorAlarm/PushNotifications/DWP/Subscriptions", "{}", 0, 0, False],
        }
        
        self._settings = self._settings_provider(settingsList, self._on_setting_changed)
        
    def _on_setting_changed(self, key, old_value, new_value):
        """Handle settings changes"""
        if key == "Subscriptions":
            self._load_subscriptions()
            
    def _load_or_generate_vapid_keys(self):
        """Load existing VAPID keys or generate new ones"""
        try:
            if os.path.exists(self._vapid_keys_file):
                with open(self._vapid_keys_file, 'r') as f:
                    self._vapid_keys = json.load(f)
                logger.info("Loaded existing VAPID keys")
            else:
                self._generate_vapid_keys()
                logger.info("Generated new VAPID keys")
                
            # Publish public key to settings for frontend access
            self._publish_vapid_public_key()
            
        except Exception as e:
            logger.error(f"Failed to load/generate VAPID keys: {e}")
            
    def _generate_vapid_keys(self):
        """Generate new VAPID key pair"""
        try:
            # Generate private key
            private_key = ec.generate_private_key(ec.SECP256R1(), default_backend())
            
            # Get private key in PEM format
            private_pem = private_key.private_bytes(
                encoding=serialization.Encoding.PEM,
                format=serialization.PrivateFormat.PKCS8,
                encryption_algorithm=serialization.NoEncryption()
            ).decode('utf-8')
            
            # Get public key in uncompressed format for web push
            public_key = private_key.public_key()
            public_numbers = public_key.public_numbers()
            
            # Convert to uncompressed format (0x04 + x + y coordinates)
            x_bytes = public_numbers.x.to_bytes(32, 'big')
            y_bytes = public_numbers.y.to_bytes(32, 'big')
            uncompressed_key = b'\x04' + x_bytes + y_bytes
            
            # Base64 URL-safe encode for web push
            public_key_b64 = base64.urlsafe_b64encode(uncompressed_key).decode('utf-8').rstrip('=')
            
            self._vapid_keys = {
                'private_key': private_pem,
                'public_key': public_key_b64
            }
            
            # Save to file
            os.makedirs(os.path.dirname(self._vapid_keys_file), exist_ok=True)
            with open(self._vapid_keys_file, 'w') as f:
                json.dump(self._vapid_keys, f, indent=2)
                
            logger.info("Generated and saved new VAPID keys")
            
        except Exception as e:
            logger.error(f"Failed to generate VAPID keys: {e}")
            raise
            
    def _publish_vapid_public_key(self):
        """Publish VAPID public key to settings for frontend access"""
        if self._vapid_keys and 'public_key' in self._vapid_keys:
            self._settings["DWPPublicKey"] = self._vapid_keys['public_key']
            logger.info(f"Published VAPID public key to settings")
            
    def _load_subscriptions(self):
        """Load push subscriptions from settings"""
        try:
            subscriptions_json = self._settings["Subscriptions"] or "{}"
            self._subscriptions = json.loads(subscriptions_json)
            logger.info(f"Loaded {len(self._subscriptions)} push subscriptions")
        except (json.JSONDecodeError, Exception) as e:
            logger.error(f"Failed to load subscriptions: {e}")
            self._subscriptions = {}
            
    def _save_subscriptions(self):
        """Save push subscriptions to settings"""
        try:
            subscriptions_json = json.dumps(self._subscriptions)
            self._settings["Subscriptions"] = subscriptions_json
            logger.debug(f"Saved {len(self._subscriptions)} push subscriptions")
        except Exception as e:
            logger.error(f"Failed to save subscriptions: {e}")
            
    def add_subscription(self, subscription_id, subscription_info):
        """Add a new push subscription"""
        try:
            # Validate subscription info
            required_fields = ['endpoint', 'keys']
            if not all(field in subscription_info for field in required_fields):
                logger.error(f"Invalid subscription info: missing required fields")
                return False
                
            # Validate keys
            if not all(key in subscription_info['keys'] for key in ['p256dh', 'auth']):
                logger.error(f"Invalid subscription keys: missing p256dh or auth")
                return False
                
            self._subscriptions[subscription_id] = subscription_info
            self._save_subscriptions()
            
            logger.info(f"Added push subscription: {subscription_id}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to add subscription {subscription_id}: {e}")
            return False
            
    def remove_subscription(self, subscription_id):
        """Remove a push subscription"""
        try:
            if subscription_id in self._subscriptions:
                del self._subscriptions[subscription_id]
                self._save_subscriptions()
                logger.info(f"Removed push subscription: {subscription_id}")
                return True
            else:
                logger.warning(f"Subscription not found: {subscription_id}")
                return False
                
        except Exception as e:
            logger.error(f"Failed to remove subscription {subscription_id}: {e}")
            return False
            
    def send_push_notification(self, title, body, data=None):
        """Send push notification to all subscribed devices"""
        if not WEBPUSH_AVAILABLE:
            logger.warning("Web push not available, skipping notification")
            return
            
        if not self._subscriptions:
            logger.debug("No push subscriptions, skipping notification")
            return
            
        if not self._vapid_keys:
            logger.error("VAPID keys not available, cannot send push notification")
            return
            
        notification_payload = {
            'title': title,
            'body': body,
            'data': data or {}
        }
        
        payload_json = json.dumps(notification_payload)
        logger.info(f"Notification payload: {payload_json}")
        
        # Send to all subscriptions
        failed_subscriptions = []
        
        for subscription_id, subscription_info in self._subscriptions.items():
            try:
                # Prepare VAPID claims
                endpoint = subscription_info.get('endpoint', '')
                
                if 'web.push.apple.com' in endpoint:
                    # Apple Push specific claims
                    vapid_claims = {
                        "sub": f"mailto:{self._settings['VapidContactEmail'] or 'admin@localhost'}",
                        "aud": "https://web.push.apple.com",
                        "exp": int(time.time()) + 12 * 3600  # 12 hours from now
                    }
                    logger.debug(f"Apple VAPID claims: {vapid_claims}")
                else:
                    # Standard VAPID claims for other services
                    vapid_claims = {
                        "sub": f"mailto:{self._settings['VapidContactEmail'] or 'admin@localhost'}"
                    }
                    logger.debug(f"Standard VAPID claims: {vapid_claims}")
                
                logger.debug(f"Sending to {subscription_id}: endpoint={subscription_info.get('endpoint', '')[:50]}...")
                logger.debug(f"Private key type: {type(self._vapid_keys['private_key'])}, length: {len(self._vapid_keys['private_key']) if self._vapid_keys['private_key'] else 0}")
                
                # Convert PEM to DER format for pywebpush
                pem_key = self._vapid_keys['private_key']
                # Remove PEM headers and decode to DER
                key_lines = pem_key.strip().split('\n')
                key_data = ''.join(line for line in key_lines if not line.startswith('-----'))
                
                # Send push notification
                webpush(
                    subscription_info=subscription_info,
                    data=payload_json,
                    vapid_private_key=key_data,
                    vapid_claims=vapid_claims
                )
                
                logger.info(f"Successfully sent push notification to {subscription_id}")
                
            except WebPushException as e:
                logger.warning(f"Failed to send push to {subscription_id}: {e}")
                if e.response and e.response.status_code in [410, 413]:
                    # Subscription expired or invalid
                    failed_subscriptions.append(subscription_id)
                    
            except Exception as e:
                logger.error(f"Error sending push to {subscription_id}: {e}")
                
        # Remove failed subscriptions
        for subscription_id in failed_subscriptions:
            logger.info(f"Removing invalid subscription: {subscription_id}")
            self.remove_subscription(subscription_id)
            
        logger.info(f"Sent push notification '{title}' to {len(self._subscriptions) - len(failed_subscriptions)} devices")
        
    def on_state_changed(self, current_state):
        """Handle anchor alarm state changes and send push notifications"""
        if not WEBPUSH_AVAILABLE:
            return
            
        # Only send notifications for dangerous states that are not muted
        dangerous_states = [AnchorAlarmState.ALARM_DRAGGING, AnchorAlarmState.ALARM_NO_GPS]
        
        # Send notification for dangerous states (if not muted)
        if current_state.state in dangerous_states and not current_state.alarm_muted:
            if current_state.state == "ALARM_DRAGGING":
                self.send_push_notification(
                    title="Anchor Alarm - DRAGGING",
                    body="Your anchor is dragging! Check your position immediately.",
                    data={
                        "state": "ALARM_DRAGGING",
                        "url": "/",
                        "timestamp": int(time.time())
                    }
                )
            elif current_state.state == "ALARM_NO_GPS":
                self.send_push_notification(
                    title="Anchor Alarm - NO GPS",
                    body="GPS signal lost. Cannot monitor anchor position.",
                    data={
                        "state": "ALARM_NO_GPS", 
                        "url": "/",
                        "timestamp": int(time.time())
                    }
                )
                
    def get_vapid_public_key(self):
        """Get the VAPID public key for frontend use"""
        if self._vapid_keys and 'public_key' in self._vapid_keys:
            return self._vapid_keys['public_key']
        return None
        
    def trigger_register_dwp_device(self, subscription_data):
        """Handle DWP device registration trigger from MQTT"""
        try:
            # Parse subscription data JSON
            data = json.loads(subscription_data) if isinstance(subscription_data, str) else subscription_data
            
            subscription_id = data.get('subscriptionId')
            subscription_info = data.get('subscription')
            
            if not subscription_id or not subscription_info:
                logger.error("Invalid DWP registration data: missing subscriptionId or subscription")
                return False
                
            success = self.add_subscription(subscription_id, subscription_info)
            if success:
                logger.info(f"Successfully registered DWP device: {subscription_id}")
            return success
            
        except Exception as e:
            logger.error(f"Failed to register DWP device: {e}")
            return False
            
    def trigger_unregister_dwp_device(self, subscription_id):
        """Handle DWP device unregistration trigger from MQTT"""
        try:
            success = self.remove_subscription(subscription_id)
            if success:
                logger.info(f"Successfully unregistered DWP device: {subscription_id}")
            return success
            
        except Exception as e:
            logger.error(f"Failed to unregister DWP device: {e}")
            return False
            
    def _init_dbus_paths(self):
        """Initialize D-Bus paths for DWP triggers"""
        if not self._dbus_service:
            return
            
        # Add DWP trigger paths
        self._dbus_service.add_path('/Triggers/RegisterDWPDevice', "", "JSON data to register DWP push notification device", writeable=True, onchangecallback=self._on_dbus_changed)
        self._dbus_service.add_path('/Triggers/UnregisterDWPDevice', "", "Subscription ID to unregister DWP device", writeable=True, onchangecallback=self._on_dbus_changed)
        
    def _on_dbus_changed(self, path, newvalue):
        """Handle D-Bus trigger changes for DWP"""
        if path == '/Triggers/RegisterDWPDevice':
            if newvalue:
                self.trigger_register_dwp_device(newvalue)
            return False  # Reset trigger
            
        if path == '/Triggers/UnregisterDWPDevice':
            if newvalue:
                self.trigger_unregister_dwp_device(newvalue)
            return False  # Reset trigger


if __name__ == "__main__":
    import sys
    import os
    
    sys.path.insert(1, os.path.join(os.path.dirname(__file__), '..'))
    sys.path.insert(1, os.path.join(os.path.dirname(__file__), '../ext/velib_python'))
    
    from utils import handle_stdin
    from gi.repository import GLib
    from dbus.mainloop.glib import DBusGMainLoop
    import dbus
    from settingsdevice import SettingsDevice
    
    # Setup logging
    import logging
    logging.basicConfig(level=logging.INFO)
    logger = logging.getLogger(__name__)
    
    if not WEBPUSH_AVAILABLE:
        print("❌ Web push dependencies not available. Install with: pip install pywebpush cryptography")
        sys.exit(1)
    
    def create_dbus_service():
        """Create a test D-Bus service"""
        from vedbus import VeDbusService
        dbus_service = VeDbusService("com.victronenergy.anchoralarm.dwp-test", register=False)
        dbus_service.add_mandatory_paths(sys.argv[0], "test-version", None, 0, 0, 'DWP Test', 0, 0, 1)
        return dbus_service
    
    # Setup D-Bus
    DBusGMainLoop(set_as_default=True)
    bus = dbus.SessionBus() if 'DBUS_SESSION_BUS_ADDRESS' in os.environ else dbus.SystemBus()
    
    # Create test D-Bus service
    dbus_service = create_dbus_service()
    
    # Create DWP connector
    dwp_connector = DBusDWPConnector(
        lambda: GLib, 
        lambda settings, cb: SettingsDevice(bus, settings, cb),
        dbus_service
    )
    
    # Register D-Bus service after connector adds its paths
    dbus_service.register()
    
    print("🚀 DWP Connector Test Tool")
    print(f"📋 VAPID Public Key: {dwp_connector.get_vapid_public_key()}")
    print("\nCommands:")
    print("  add:{json subscription data}")
    print("  remove:{subscription id}")
    print("  send:{notification text}")
    print("  list")
    print("  key")
    print("  exit")
    print("\nExamples:")
    print('  add:{"subscriptionId":"test123","subscription":{"endpoint":"https://example.com","keys":{"p256dh":"key1","auth":"key2"}}}')
    print("  remove:test123")
    print("  send:Test notification message")
    print()
    
    def handle_command(command, text):
        """Handle commands from stdin"""
        if command == "add":
            if not text:
                print("❌ Error: JSON subscription data required")
                return
            try:
                subscription_data = json.loads(text)
                success = dwp_connector.trigger_register_dwp_device(subscription_data)
                if success:
                    print(f"✅ Subscription added: {subscription_data.get('subscriptionId', 'unknown')}")
                else:
                    print("❌ Failed to add subscription")
            except json.JSONDecodeError as e:
                print(f"❌ Invalid JSON: {e}")
            except Exception as e:
                print(f"❌ Error: {e}")
                
        elif command == "remove":
            if not text:
                print("❌ Error: Subscription ID required")
                return
            success = dwp_connector.trigger_unregister_dwp_device(text)
            if success:
                print(f"✅ Subscription removed: {text}")
            else:
                print(f"❌ Failed to remove subscription: {text}")
                
        elif command == "send":
            if not text:
                print("❌ Error: Notification text required")
                return
            if not dwp_connector._subscriptions:
                print("❌ No subscriptions available. Add a subscription first.")
                return
            dwp_connector.send_push_notification(
                title="Test Notification",
                body=text,
                data={"test": True, "timestamp": int(time.time())}
            )
            print(f"✅ Notification sent: '{text}'")
            
        elif command == "list":
            subscriptions = dwp_connector._subscriptions
            if subscriptions:
                print(f"📋 Current subscriptions ({len(subscriptions)}):")
                for sub_id, sub_info in subscriptions.items():
                    endpoint = sub_info.get('endpoint', 'unknown')
                    print(f"  - {sub_id}: {endpoint}")
            else:
                print("📋 No subscriptions found")
                
        elif command == "key":
            public_key = dwp_connector.get_vapid_public_key()
            if public_key:
                print(f"📋 VAPID Public Key: {public_key}")
            else:
                print("❌ No VAPID public key available")
                
        else:
            print(f"❌ Unknown command: {command}")
    
    # Start handling stdin commands
    handle_stdin(handle_command)