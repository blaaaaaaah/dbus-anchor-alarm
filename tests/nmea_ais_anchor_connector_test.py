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

sys.path.insert(1, os.path.join(sys.path[0], '..'))
sys.path.insert(1, os.path.join(os.path.dirname(__file__), '../ext/velib_python/test'))

from anchor_alarm_model import AnchorAlarmState

import unittest
from unittest.mock import ANY
from unittest.mock import MagicMock
from unittest.mock import Mock
from unittest.mock import patch
from unittest.mock import call

from mock_settings_device import MockSettingsDevice
from glib_timer_mock import GLibTimerMock

sys.path.insert(1, os.path.join(sys.path[0], '../gps_providers'))
from abstract_gps_provider import GPSPosition

sys.path.insert(1, os.path.join(sys.path[0], '../connectors'))

from nmea_ais_anchor_connector import NMEAAISAnchorConnector
          
timer_provider = GLibTimerMock()






class TestNMEAAISAnchorConnector(unittest.TestCase):

    def setUp(self):
        self.maxDiff = None

        



    def test_nmea_messages(self):
        mock_bridge = MagicMock()
        mock_bridge.add_pgn_handler = MagicMock()
        mock_bridge.send_nmea = MagicMock()


        connector = NMEAAISAnchorConnector(lambda: timer_provider, MockSettingsDevice,  mock_bridge)
        connector._settings['AdvertiseInterval'] = 2

        controller = MagicMock()
        controller.trigger_mute_alarm   = MagicMock()
        connector.set_controller(controller)

        # AnchorAlarmState = namedtuple('AnchorAlarmState', ['state', 'message', 'level', 'muted', 'params'])
        state_drop_point_set = AnchorAlarmState('DROP_POINT_SET', 'Drop point set, please do blablala',"short message", 'info', False, {'drop_point': GPSPosition(10, 11)})
        state_in_radius = AnchorAlarmState('IN_RADIUS', 'boat in radius',"short message", 'info', False, {'drop_point': GPSPosition(10, 11), 'radius': 12})
        state_in_radius2 = AnchorAlarmState('IN_RADIUS', 'boat in radius 2',"short message", 'info', False, {'drop_point': GPSPosition(10, 11), 'radius': 12})
        state_in_radius3 = AnchorAlarmState('IN_RADIUS', 'boat in radius 3',"short message", 'info', False, {'drop_point': GPSPosition(10, 11), 'radius': 12})
        state_dragging = AnchorAlarmState('ALARM_DRAGGING', 'Anchor dragging !',"short message", 'emergency', False, {'drop_point': GPSPosition(10, 11), 'radius': 12})
        state_dragging_muted = AnchorAlarmState('ALARM_DRAGGING_MUTED', 'Anchor dragging ! (muted)',"short message", 'emergency', True, {'drop_point': GPSPosition(10, 11), 'radius': 12})
        state_disabled = AnchorAlarmState('DISABLED', 'Anchor alarm disabled',"short message", 'info', False, {})

        

        position_nmea_message = { 
            "pgn": 129039, 
            "fields": {
                "Message ID": "Standard Class B position report", 
                "Repeat Indicator": "Initial", 
                "User ID": connector._MMSI, 
                "Longitude": 11, 
                "Latitude": 10, 
                "Position Accuracy": "Low", 
                "RAIM": "not in use", 
                "Time Stamp": "45", 
                "COG": 0, 
                "SOG": 0, 
                "AIS Transceiver information": "Channel B VDL reception", 
                "Heading": 0, 
                "Regional Application B": 0, 
                "Unit type": "SOTDMA", 
                "Integrated Display": "No", 
                "DSC": "No", 
                "Band": "Top 525 kHz of marine band", 
                "Can handle Msg 22": "No", 
                "AIS mode": "Autonomous", 
                "AIS communication state": "SOTDMA"
            }, 
            "description": "AIS Class B Position Report"
        }

        position_disabled_nmea_message = { 
            "pgn": 129039, 
            "fields": {
                "Message ID": "Standard Class B position report", 
                "Repeat Indicator": "Initial", 
                "User ID": connector._MMSI, 
                "Longitude": connector._DISABLED_POSITION.longitude, 
                "Latitude": connector._DISABLED_POSITION.latitude, 
                "Position Accuracy": "Low", 
                "RAIM": "not in use", 
                "Time Stamp": "45", 
                "COG": 0, 
                "SOG": 0, 
                "AIS Transceiver information": "Channel B VDL reception", 
                "Heading": 0, 
                "Regional Application B": 0, 
                "Unit type": "SOTDMA", 
                "Integrated Display": "No", 
                "DSC": "No", 
                "Band": "Top 525 kHz of marine band", 
                "Can handle Msg 22": "No", 
                "AIS mode": "Autonomous", 
                "AIS communication state": "SOTDMA"
            }, 
            "description": "AIS Class B Position Report"
        }

        name_nmea_message = { 
            'pgn': 129809, 
            'fields': {
                'Message ID': 'Static data report', 
                'Repeat Indicator': 'Initial', 
                'User ID': connector._MMSI, 
                'Name': 'Anchor', 
                'AIS Transceiver information': 'Channel B VDL reception'
            }, 
            'description': 'AIS Class B static data (msg 24 Part A)'
        }

        connector.on_state_changed(state_disabled)
        mock_bridge.send_nmea.assert_has_calls([call(position_disabled_nmea_message), call(name_nmea_message)])
        timer_provider.tick()
        timer_provider.tick()
        mock_bridge.send_nmea.assert_has_calls([call(position_disabled_nmea_message), call(name_nmea_message),
                                                call(position_disabled_nmea_message), call(name_nmea_message)])

        connector.on_state_changed(state_drop_point_set)
        mock_bridge.send_nmea.assert_has_calls([call(position_disabled_nmea_message), call(name_nmea_message),
                                                call(position_disabled_nmea_message), call(name_nmea_message),
                                                call(position_nmea_message), call(name_nmea_message)])
        timer_provider.tick()
        timer_provider.tick()
        mock_bridge.send_nmea.assert_has_calls([call(position_disabled_nmea_message), call(name_nmea_message),
                                                call(position_disabled_nmea_message), call(name_nmea_message),
                                                call(position_nmea_message), call(name_nmea_message),
                                                call(position_nmea_message), call(name_nmea_message)])

        connector.on_state_changed(state_in_radius)
        mock_bridge.send_nmea.assert_has_calls([call(position_disabled_nmea_message), call(name_nmea_message),
                                                call(position_disabled_nmea_message), call(name_nmea_message),
                                                call(position_nmea_message), call(name_nmea_message),
                                                call(position_nmea_message), call(name_nmea_message),
                                                call(position_nmea_message), call(name_nmea_message)])

        timer_provider.tick()
        timer_provider.tick()
        mock_bridge.send_nmea.assert_has_calls([call(position_disabled_nmea_message), call(name_nmea_message),
                                                call(position_disabled_nmea_message), call(name_nmea_message),
                                                call(position_nmea_message), call(name_nmea_message),
                                                call(position_nmea_message), call(name_nmea_message),
                                                call(position_nmea_message), call(name_nmea_message),
                                                call(position_nmea_message), call(name_nmea_message)])


        connector.on_state_changed(state_dragging)
        mock_bridge.send_nmea.assert_has_calls([call(position_disabled_nmea_message), call(name_nmea_message),
                                                call(position_disabled_nmea_message), call(name_nmea_message),
                                                call(position_nmea_message), call(name_nmea_message),
                                                call(position_nmea_message), call(name_nmea_message),
                                                call(position_nmea_message), call(name_nmea_message),
                                                call(position_nmea_message), call(name_nmea_message),
                                                call(position_nmea_message), call(name_nmea_message)])
        
        connector.on_state_changed(state_dragging_muted)
        mock_bridge.send_nmea.assert_has_calls([call(position_disabled_nmea_message), call(name_nmea_message),
                                                call(position_disabled_nmea_message), call(name_nmea_message),
                                                call(position_nmea_message), call(name_nmea_message),
                                                call(position_nmea_message), call(name_nmea_message),
                                                call(position_nmea_message), call(name_nmea_message),
                                                call(position_nmea_message), call(name_nmea_message),
                                                call(position_nmea_message), call(name_nmea_message),
                                                call(position_nmea_message), call(name_nmea_message)])
        
        connector.on_state_changed(state_disabled)
        mock_bridge.send_nmea.assert_has_calls([call(position_disabled_nmea_message), call(name_nmea_message),
                                                call(position_disabled_nmea_message), call(name_nmea_message),
                                                call(position_nmea_message), call(name_nmea_message),
                                                call(position_nmea_message), call(name_nmea_message),
                                                call(position_nmea_message), call(name_nmea_message),
                                                call(position_nmea_message), call(name_nmea_message),
                                                call(position_nmea_message), call(name_nmea_message),
                                                call(position_nmea_message), call(name_nmea_message),
                                                call(position_disabled_nmea_message), call(name_nmea_message),])
        
        timer_provider.tick()
        timer_provider.tick()

        mock_bridge.send_nmea.assert_has_calls([call(position_disabled_nmea_message), call(name_nmea_message),
                                                call(position_disabled_nmea_message), call(name_nmea_message),
                                                call(position_nmea_message), call(name_nmea_message),
                                                call(position_nmea_message), call(name_nmea_message),
                                                call(position_nmea_message), call(name_nmea_message),
                                                call(position_nmea_message), call(name_nmea_message),
                                                call(position_nmea_message), call(name_nmea_message),
                                                call(position_nmea_message), call(name_nmea_message),
                                                call(position_disabled_nmea_message), call(name_nmea_message),
                                                call(position_disabled_nmea_message), call(name_nmea_message),])


    def test_anchor_name(self):
        mock_bridge = MagicMock()
        mock_bridge.add_pgn_handler = MagicMock()
        mock_bridge.send_nmea = MagicMock()


        connector = NMEAAISAnchorConnector(lambda: timer_provider, MockSettingsDevice,  mock_bridge)
        connector._settings['AdvertiseInterval'] = 2
        connector._settings['Name'] = "qwe"

        controller = MagicMock()
        controller.trigger_mute_alarm   = MagicMock()
        connector.set_controller(controller)

    
        state_disabled = AnchorAlarmState('DISABLED', 'Anchor alarm disabled',"short message", 'info', False, {})

    
        position_disabled_nmea_message = { 
            "pgn": 129039, 
            "fields": {
                "Message ID": "Standard Class B position report", 
                "Repeat Indicator": "Initial", 
                "User ID": connector._MMSI, 
                "Longitude": connector._DISABLED_POSITION.longitude, 
                "Latitude": connector._DISABLED_POSITION.latitude, 
                "Position Accuracy": "Low", 
                "RAIM": "not in use", 
                "Time Stamp": "45", 
                "COG": 0, 
                "SOG": 0, 
                "AIS Transceiver information": "Channel B VDL reception", 
                "Heading": 0, 
                "Regional Application B": 0, 
                "Unit type": "SOTDMA", 
                "Integrated Display": "No", 
                "DSC": "No", 
                "Band": "Top 525 kHz of marine band", 
                "Can handle Msg 22": "No", 
                "AIS mode": "Autonomous", 
                "AIS communication state": "SOTDMA"
            }, 
            "description": "AIS Class B Position Report"
        }

        name_nmea_message = { 
            'pgn': 129809, 
            'fields': {
                'Message ID': 'Static data report', 
                'Repeat Indicator': 'Initial', 
                'User ID': connector._MMSI, 
                'Name': 'qwe', 
                'AIS Transceiver information': 'Channel B VDL reception'
            }, 
            'description': 'AIS Class B static data (msg 24 Part A)'
        }

        connector.on_state_changed(state_disabled)
        mock_bridge.send_nmea.assert_has_calls([call(position_disabled_nmea_message), call(name_nmea_message)])


    def test_heading(self):
        handler = None
        def _set_handler(pgn, the_handler):
            nonlocal handler
            handler = the_handler

        mock_bridge = MagicMock()
        mock_bridge.add_pgn_handler = MagicMock(side_effect=_set_handler)
        mock_bridge.send_nmea = MagicMock()


        connector = NMEAAISAnchorConnector(lambda: timer_provider, MockSettingsDevice,  mock_bridge)
        connector._settings['AdvertiseInterval'] = 2

        controller = MagicMock()
        controller.trigger_mute_alarm   = MagicMock()
        connector.set_controller(controller)

        # AnchorAlarmState = namedtuple('AnchorAlarmState', ['state', 'message', 'level', 'muted', 'params'])
        state_drop_point_set = AnchorAlarmState('DROP_POINT_SET', 'Drop point set, please do blablala',"short message", 'info', False, {'drop_point': GPSPosition(10, 11)})
        state_disabled = AnchorAlarmState('DISABLED', 'Anchor alarm disabled',"short message", 'info', False, {})

        

        position_disabled_nmea_message = { 
            "pgn": 129039, 
            "fields": {
                "Message ID": "Standard Class B position report", 
                "Repeat Indicator": "Initial", 
                "User ID": connector._MMSI, 
                "Longitude": connector._DISABLED_POSITION.longitude, 
                "Latitude": connector._DISABLED_POSITION.latitude, 
                "Position Accuracy": "Low", 
                "RAIM": "not in use", 
                "Time Stamp": "45", 
                "COG": 0, 
                "SOG": 0, 
                "AIS Transceiver information": "Channel B VDL reception", 
                "Heading": 0, 
                "Regional Application B": 0, 
                "Unit type": "SOTDMA", 
                "Integrated Display": "No", 
                "DSC": "No", 
                "Band": "Top 525 kHz of marine band", 
                "Can handle Msg 22": "No", 
                "AIS mode": "Autonomous", 
                "AIS communication state": "SOTDMA"
            }, 
            "description": "AIS Class B Position Report"
        }

        name_nmea_message = { 
            'pgn': 129809, 
            'fields': {
                'Message ID': 'Static data report', 
                'Repeat Indicator': 'Initial', 
                'User ID': connector._MMSI, 
                'Name': 'Anchor', 
                'AIS Transceiver information': 'Channel B VDL reception'
            }, 
            'description': 'AIS Class B static data (msg 24 Part A)'
        }

        connector.on_state_changed(state_disabled)
        mock_bridge.send_nmea.assert_has_calls([call(position_disabled_nmea_message), call(name_nmea_message)])
        timer_provider.tick()

        HEADING = 1.3892

        position_disabled_nmea_message2 = { 
            "pgn": 129039, 
            "fields": {
                "Message ID": "Standard Class B position report", 
                "Repeat Indicator": "Initial", 
                "User ID": connector._MMSI, 
                "Longitude": connector._DISABLED_POSITION.longitude, 
                "Latitude": connector._DISABLED_POSITION.latitude, 
                "Position Accuracy": "Low", 
                "RAIM": "not in use", 
                "Time Stamp": "45", 
                "COG": HEADING, 
                "SOG": 0, 
                "AIS Transceiver information": "Channel B VDL reception", 
                "Heading": HEADING, 
                "Regional Application B": 0, 
                "Unit type": "SOTDMA", 
                "Integrated Display": "No", 
                "DSC": "No", 
                "Band": "Top 525 kHz of marine band", 
                "Can handle Msg 22": "No", 
                "AIS mode": "Autonomous", 
                "AIS communication state": "SOTDMA"
            }, 
            "description": "AIS Class B Position Report"
        }

        handler({"canId":166793731,"prio":2,"src":3,"dst":255,"pgn":127250,"timestamp":"2025-06-10T18:04:39.871Z","fields":{"SID":163,"Heading":HEADING,"Deviation":0,"Variation":-0.2655,"Reference":"True"},"description":"Vessel Heading"})

        timer_provider.tick()
        mock_bridge.send_nmea.assert_has_calls([call(position_disabled_nmea_message), call(name_nmea_message),
                                                call(position_disabled_nmea_message2), call(name_nmea_message)])

    

if __name__ == '__main__':
    unittest.main()