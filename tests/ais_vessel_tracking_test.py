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
import time
import math

sys.path.insert(1, os.path.join(sys.path[0], '..'))
sys.path.insert(1, os.path.join(os.path.dirname(__file__), '../ext/velib_python/test'))

import unittest
from unittest.mock import ANY
from unittest.mock import MagicMock
from unittest.mock import Mock
from unittest.mock import patch

sys.modules['dbus'] = Mock()

sys.path.insert(1, os.path.join(sys.path[0], '../connectors'))
sys.path.insert(1, os.path.join(sys.path[0], '../gps_providers'))

from dbus_connector import DBusConnector
from abstract_gps_provider import GPSPosition

from mock_dbus_monitor import MockDbusMonitor
from mock_dbus_service import MockDbusService
from mock_settings_device import MockSettingsDevice
from glib_timer_mock import GLibTimerMock

class MockAISDBusConnector(DBusConnector):
    def _create_dbus_monitor(self, *args, **kwargs):
        return MockDbusMonitor(*args, **kwargs)
    
    def _create_dbus_service(self, *args, **kwargs):
        return MockDbusService(args[0])

    def mock_monitor(self):
        return self._alarm_monitor
    
    def mock_service(self):
        return self._dbus_service

timer_provider = GLibTimerMock()

class TestAISVesselTracking(unittest.TestCase):

    def setUp(self):
        self.maxDiff = None
        
        # Create mock controller with GPS position
        self.mock_controller = MagicMock()
        self.mock_controller.get_gps_position = MagicMock(return_value=GPSPosition(14.0829979, -60.9595577))
        
        # Create mock bridge
        self.mock_bridge = MagicMock()
        self.mock_bridge.add_pgn_handler = MagicMock()
        self.mock_bridge.send_nmea = MagicMock()
        
        # Create connector
        self.connector = MockAISDBusConnector(
            lambda: timer_provider, 
            lambda settings, cb: MockSettingsDevice(settings, cb), 
            self.mock_bridge
        )
        self.connector.set_controller(self.mock_controller)
        
        # Sample AIS messages for testing
        self.valid_ais_message = {
            "canId": 301469618,
            "prio": 4,
            "src": 178,
            "dst": 255,
            "pgn": 129039,
            "timestamp": "2025-07-01T16:48:46.066Z",
            "fields": {
                "Message ID": "Standard Class B position report",
                "User ID": 368081510,
                "Longitude": -60.9494,
                "Latitude": 14.0756,
                "COG": 1.7698,
                "SOG": 5.2,
                "Heading": 1.4312
            }
        }
        
        self.far_ais_message = {
            "canId": 301469618,
            "prio": 4,
            "src": 178,
            "dst": 255,
            "pgn": 129039,
            "timestamp": "2025-07-01T16:48:46.066Z",
            "fields": {
                "Message ID": "Standard Class B position report",
                "User ID": 999999999,
                "Longitude": -58.0000,  # Far away position
                "Latitude": 16.0000,
                "COG": 0.0,
                "SOG": 0.0
            }
        }

    def test_ais_message_processing_valid(self):
        """Test processing of valid AIS messages"""
        
        # Increase distance limit to allow test vessel (distance ~1369m)
        self.connector._settings['DistanceToVessel'] = 2000
        
        # Process AIS message
        self.connector._on_ais_message(self.valid_ais_message)
        
        # Verify vessel was created (excluding 'self' vessel)
        mmsi = str(self.valid_ais_message["fields"]["User ID"])
        vessels_without_self = {k: v for k, v in self.connector._vessels.items() if k != 'self'}
        self.assertIn(mmsi, vessels_without_self)
        
        # Verify vessel data
        vessel = self.connector._vessels[mmsi]
        self.assertEqual(vessel['mmsi'], mmsi)
        self.assertEqual(vessel['latitude'], 14.0756)
        self.assertEqual(vessel['longitude'], -60.9494)
        self.assertEqual(vessel['sog'], 5.2)
        self.assertAlmostEqual(vessel['cog'], 1.7698 * (180.0 / math.pi), places=2)
        self.assertGreater(vessel['distance'], 0)
        
        # Call update_state to update DBus paths (this is normally called by timer)
        from anchor_alarm_model import AnchorAlarmState
        from abstract_gps_provider import GPSPosition
        mock_state = AnchorAlarmState('IN_RADIUS', 'boat in radius', "short in radius message", 'info', False, {'drop_point': GPSPosition(10, 11), 'radius': 12, 'current_radius':5, 'radius_tolerance': 15, 'alarm_muted_count': 0, 'no_gps_count': 0, 'out_of_radius_count': 0})
        self.connector.update_state(mock_state)
        
        # Verify DBus paths were created
        service = self.connector.mock_service()
        self.assertEqual(service[f'/Vessels/{mmsi}/Latitude'], 14.0756)
        self.assertEqual(service[f'/Vessels/{mmsi}/Longitude'], -60.9494)
        self.assertEqual(service[f'/Vessels/{mmsi}/SOG'], 5.2)

    def test_ais_message_processing_invalid_messages(self):
        """Test handling of invalid AIS messages"""
        
        # Count vessels excluding 'self'
        def count_vessels():
            return len([k for k in self.connector._vessels.keys() if k != 'self'])
        
        # Test message without fields
        invalid_msg1 = {"canId": 123}
        self.connector._on_ais_message(invalid_msg1)
        self.assertEqual(count_vessels(), 0)
        
        # Test message without User ID
        invalid_msg2 = {"fields": {"Longitude": -60.0, "Latitude": 14.0}}
        self.connector._on_ais_message(invalid_msg2)
        self.assertEqual(count_vessels(), 0)
        
        # Test message without coordinates
        invalid_msg3 = {"fields": {"User ID": 123456}}
        self.connector._on_ais_message(invalid_msg3)
        self.assertEqual(count_vessels(), 0)
        
        # Test message without COG/SOG
        invalid_msg4 = {
            "fields": {
                "User ID": 123456,
                "Longitude": -60.0,
                "Latitude": 14.0
            }
        }
        self.connector._on_ais_message(invalid_msg4)
        self.assertEqual(count_vessels(), 0)

    def test_vessel_creation_and_updates(self):
        """Test vessel creation and updating"""
        
        mmsi = "368081510"
        
        # Create vessel
        vessel = self.connector._create_vessel(mmsi)
        self.assertEqual(vessel['mmsi'], mmsi)
        self.assertEqual(vessel['latitude'], "")
        self.assertEqual(vessel['longitude'], "")
        self.assertEqual(len(vessel['tracks']), 0)
        
        # Verify it's stored
        self.assertIn(mmsi, self.connector._vessels)
        
        # Verify calling again returns same vessel
        vessel2 = self.connector._create_vessel(mmsi)
        self.assertIs(vessel, vessel2)
        
        # Verify DBus paths exist
        service = self.connector.mock_service()
        self.assertTrue(f'/Vessels/{mmsi}/Latitude' in service)
        self.assertTrue(f'/Vessels/{mmsi}/Longitude' in service)
        self.assertTrue(f'/Vessels/{mmsi}/SOG' in service)
        self.assertTrue(f'/Vessels/{mmsi}/COG' in service)
        self.assertTrue(f'/Vessels/{mmsi}/Heading' in service)
        self.assertTrue(f'/Vessels/{mmsi}/Tracks' in service)

    def test_vessel_removal(self):
        """Test vessel removal and cleanup"""
        
        mmsi = "368081510"
        
        # Create vessel
        self.connector._create_vessel(mmsi)
        self.assertIn(mmsi, self.connector._vessels)
        
        # Remove vessel
        self.connector._remove_vessel(mmsi)
        self.assertNotIn(mmsi, self.connector._vessels)
        
        # Verify DBus paths were removed
        service = self.connector.mock_service()
        self.assertFalse(f'/Vessels/{mmsi}/Latitude' in service)
        self.assertFalse(f'/Vessels/{mmsi}/Longitude' in service)
        
        # Test removing non-existent vessel (should not crash)
        self.connector._remove_vessel("999999999")

    def test_vessel_distance_filtering(self):
        """Test filtering vessels by distance"""
        
        # Configure distance limit
        self.connector._settings['DistanceToVessel'] = 100  # 100 meters
        
        # Process close vessel (should be accepted)
        close_msg = self.valid_ais_message.copy()
        close_msg["fields"]["User ID"] = 111111111
        close_msg["fields"]["Latitude"] = 14.0830  # Very close to our position
        close_msg["fields"]["Longitude"] = -60.9596
        
        self.connector._on_ais_message(close_msg)
        self.assertIn("111111111", self.connector._vessels)
        
        # Process far vessel (should be rejected)
        self.connector._on_ais_message(self.far_ais_message)
        self.assertNotIn("999999999", self.connector._vessels)

    def test_max_vessels_limit_enforcement(self):
        """Test maximum vessel limit enforcement"""
        
        # Set max vessels to 2
        self.connector._settings['MaxVessels'] = 2
        self.connector._settings['DistanceToVessel'] = 10000  # Large distance to allow all
        
        # Add first vessel (close)
        msg1 = self.valid_ais_message.copy()
        msg1["fields"]["User ID"] = 111111111
        msg1["fields"]["Latitude"] = 14.0830
        msg1["fields"]["Longitude"] = -60.9596
        self.connector._on_ais_message(msg1)
        
        # Add second vessel (medium distance)
        msg2 = self.valid_ais_message.copy()
        msg2["fields"]["User ID"] = 222222222
        msg2["fields"]["Latitude"] = 14.0850
        msg2["fields"]["Longitude"] = -60.9600
        self.connector._on_ais_message(msg2)
        
        self.assertEqual(len(self.connector._vessels), 3)
        
        # Add third vessel that's closer than one of the existing ones
        msg3 = self.valid_ais_message.copy()
        msg3["fields"]["User ID"] = 333333333
        msg3["fields"]["Latitude"] = 14.0829  # Very close
        msg3["fields"]["Longitude"] = -60.9595
        self.connector._on_ais_message(msg3)
        
        # Should still have 2 (+self) vessels, but the farthest should be removed
        self.assertEqual(len(self.connector._vessels), 3)
        self.assertIn("333333333", self.connector._vessels)  # New close vessel should be kept

    def test_vessel_replacement_by_distance(self):
        """Test vessel replacement logic when at max capacity"""
        
        self.connector._settings['MaxVessels'] = 1
        self.connector._settings['DistanceToVessel'] = 10000
        
        # Add first vessel (far)
        msg1 = self.valid_ais_message.copy()
        msg1["fields"]["User ID"] = 111111111
        msg1["fields"]["Latitude"] = 14.1000  # Far
        msg1["fields"]["Longitude"] = -60.9000
        self.connector._on_ais_message(msg1)
        
        # Try to add closer vessel (should replace)
        msg2 = self.valid_ais_message.copy()
        msg2["fields"]["User ID"] = 222222222
        msg2["fields"]["Latitude"] = 14.0830  # Close
        msg2["fields"]["Longitude"] = -60.9596
        self.connector._on_ais_message(msg2)
        
        self.assertEqual(len(self.connector._vessels), 2)
        self.assertNotIn("111111111", self.connector._vessels)
        self.assertIn("222222222", self.connector._vessels)
        
        # Try to add farther vessel (should be rejected)
        msg3 = self.far_ais_message.copy()
        msg3["fields"]["User ID"] = 333333333
        self.connector._on_ais_message(msg3)
        
        self.assertEqual(len(self.connector._vessels), 2)
        self.assertIn("222222222", self.connector._vessels)  # Original close vessel remains

    def test_vessel_pruning_by_distance(self):
        """Test pruning vessels that become too far"""
        
        # Set up vessel with distance limit that allows test vessel
        self.connector._settings['DistanceToVessel'] = 2000
        self.connector._on_ais_message(self.valid_ais_message)
        mmsi = str(self.valid_ais_message["fields"]["User ID"])
        vessels_without_self = {k: v for k, v in self.connector._vessels.items() if k != 'self'}
        self.assertIn(mmsi, vessels_without_self)
        
        # Change distance limit to be smaller than vessel distance
        self.connector._vessels[mmsi]['distance'] = 2000  # Simulate vessel being far
        self.connector._settings['DistanceToVessel'] = 500
        
        # Run pruning
        self.connector._prune_vessels()
        
        # Vessel should be removed
        self.assertNotIn(mmsi, self.connector._vessels)

    @patch('time.time')
    def test_vessel_pruning_by_time(self, mock_time):
        """Test pruning vessels based on age"""
        
        mock_time.return_value = 1000
        
        # Create vessel with track
        mmsi = "368081510"
        vessel = self.connector._create_vessel(mmsi)
        vessel['tracks'].append({
            'latitude': 14.0756,
            'longitude': -60.9494,
            'timestamp': 800  # Old timestamp
        })
        vessel['distance'] = 100  # Within distance limit
        
        # Set prune interval 
        self.connector._settings['PruneInterval'] = 150
        
        # Run pruning - vessel should be removed due to age
        self.connector._prune_vessels()
        self.assertNotIn(mmsi, self.connector._vessels)

    def test_prune_vessels_without_gps(self):
        """Test pruning when GPS is not available"""
        
        # Set controller to return no GPS
        self.mock_controller.get_gps_position.return_value = None
        
        # Create vessel
        mmsi = "368081510"
        self.connector._create_vessel(mmsi)
        
        # Pruning should not crash and should not remove vessels
        self.connector._prune_vessels()
        self.assertIn(mmsi, self.connector._vessels)

    @patch('time.time')
    def test_vessel_track_recording(self, mock_time):
        """Test vessel track recording with time intervals"""
        
        mock_time.return_value = 1000
        
        # Create vessel
        mmsi = "368081510"
        vessel = self.connector._create_vessel(mmsi)
        vessel['latitude'] = 14.0756
        vessel['longitude'] = -60.9494
        
        # Write vessel info (should add track)
        self.connector._write_vessel_info(mmsi)
        
        self.assertEqual(len(vessel['tracks']), 1)
        track = vessel['tracks'][0]
        self.assertEqual(track['latitude'], 14.0756)
        self.assertEqual(track['longitude'], -60.9494)
        self.assertEqual(track['timestamp'], 1000)
        
        # Try to add another track immediately (should not add due to interval)
        vessel['latitude'] = 14.0757
        self.connector._write_vessel_info(mmsi)
        self.assertEqual(len(vessel['tracks']), 1)  # Still only one track
        
        # Advance time past interval
        mock_time.return_value = 1050  # 50 seconds later (> 30 second default interval)
        self.connector._write_vessel_info(mmsi)
        
        self.assertEqual(len(vessel['tracks']), 2)
        self.assertEqual(vessel['tracks'][1]['timestamp'], 1050)

    def test_track_interval_enforcement(self):
        """Test track interval setting"""
        
        # Set custom track interval
        self.connector._settings['TracksInterval'] = 60  # 60 seconds
        
        mmsi = "368081510"
        vessel = self.connector._create_vessel(mmsi)
        vessel['latitude'] = 14.0756
        vessel['longitude'] = -60.9494
        
        with patch('time.time') as mock_time:
            mock_time.return_value = 1000
            self.connector._write_vessel_info(mmsi)
            self.assertEqual(len(vessel['tracks']), 1)
            
            # 30 seconds later (less than 60) - should not add
            mock_time.return_value = 1030
            self.connector._write_vessel_info(mmsi)
            self.assertEqual(len(vessel['tracks']), 1)
            
            # 60 seconds later - should add
            mock_time.return_value = 1060
            self.connector._write_vessel_info(mmsi)
            self.assertEqual(len(vessel['tracks']), 2)

    def test_track_maxlen_enforcement(self):
        """Test track deque maximum length"""
        
        # Set small track limit
        self.connector._settings['NumberOfTracks'] = 3
        
        mmsi = "368081510"
        vessel = self.connector._create_vessel(mmsi)
        
        # Add tracks beyond limit
        with patch('time.time') as mock_time:
            for i in range(5):
                mock_time.return_value = 1000 + (i * 60)  # 60 second intervals
                vessel['latitude'] = 14.0756 + i * 0.001
                vessel['longitude'] = -60.9494 + i * 0.001
                self.connector._write_vessel_info(mmsi)
        
        # Should only keep last 3 tracks
        self.assertEqual(len(vessel['tracks']), 3)
        self.assertEqual(vessel['tracks'][0]['timestamp'], 1120)  # Should be the 3rd track
        self.assertEqual(vessel['tracks'][-1]['timestamp'], 1240)  # Should be the 5th track

    def test_ais_without_controller(self):
        """Test AIS processing without controller"""
        
        # Remove controller
        self.connector.controller = None
        
        # Should not crash and should not create vessels (except 'self')
        self.connector._on_ais_message(self.valid_ais_message)
        vessels_without_self = {k: v for k, v in self.connector._vessels.items() if k != 'self'}
        self.assertEqual(len(vessels_without_self), 0)

    def test_ais_without_gps_position(self):
        """Test AIS processing when GPS position is unavailable"""
        
        # Set controller to return no GPS
        self.mock_controller.get_gps_position.return_value = None
        
        # Should not crash and should not create vessels (except 'self')
        self.connector._on_ais_message(self.valid_ais_message)
        vessels_without_self = {k: v for k, v in self.connector._vessels.items() if k != 'self'}
        self.assertEqual(len(vessels_without_self), 0)

    def test_invalid_coordinates(self):
        """Test handling of invalid coordinates"""
        
        # Test with invalid latitude
        invalid_msg = self.valid_ais_message.copy()
        invalid_msg["fields"]["Latitude"] = 91.0  # Invalid latitude
        
        # Should not crash (geodesic calculation will handle it)
        self.connector._on_ais_message(invalid_msg)

    def test_vessel_json_serialization(self):
        """Test vessel track JSON serialization"""
        
        mmsi = "368081510"
        vessel = self.connector._create_vessel(mmsi)
        
        # Add some tracks
        vessel['tracks'].append({
            'latitude': 14.0756,
            'longitude': -60.9494,
            'timestamp': time.time() - 50
        })

        latest_time = time.time() - 20
        vessel['tracks'].append({
            'latitude': 14.0757,
            'longitude': -60.9495,
            'timestamp': latest_time
        })
        
        # Write to service
        self.connector._write_vessel_info(mmsi)
        
        # Verify JSON serialization
        service = self.connector.mock_service()
        tracks_json = service[f'/Vessels/{mmsi}/Tracks']
        tracks_data = json.loads(tracks_json)
        
        self.assertEqual(len(tracks_data), 2)
        self.assertEqual(tracks_data[0]['latitude'], 14.0756)
        self.assertEqual(tracks_data[1]['timestamp'], latest_time)

    def test_write_vessel_info_nonexistent(self):
        """Test writing vessel info for non-existent vessel"""
        
        # Should not crash
        self.connector._write_vessel_info("999999999")

    def test_settings_configuration(self):
        """Test vessel tracking settings"""
        
        # Verify default settings exist and have correct values
        self.assertEqual(self.connector._settings['NumberOfTracks'], 100)
        self.assertEqual(self.connector._settings['TracksInterval'], 30)
        self.assertEqual(self.connector._settings['PruneInterval'], 180)
        self.assertEqual(self.connector._settings['DistanceToVessel'], 400)
        self.assertEqual(self.connector._settings['MaxVessels'], 10)


if __name__ == '__main__':
    unittest.main()