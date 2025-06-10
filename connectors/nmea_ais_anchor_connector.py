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

from abstract_connector import AbstractConnector
from anchor_alarm_model import AnchorAlarmState
from abstract_gps_provider import GPSPosition


import logging
logger = logging.getLogger(__name__)

class NMEAAISAnchorConnector(AbstractConnector):
    def __init__(self, timer_provider, settings_provider, nmea_bridge):
        super().__init__(timer_provider, settings_provider)

        self._timer_ids = {
            'advertise_timer': None
        }

        self._init_settings()

        self._MMSI = 0

        # There's no way to remove an AIS target, so put it far away in Groenland somewhere
        self._DISABLED_POSITION = GPSPosition(77.0494219, -43.4613829)

        self._anchor_position = self._DISABLED_POSITION
        self._anchor_heading = 0

        self._bridge = nmea_bridge

        self._bridge.add_pgn_handler(127250, self._on_heading_change)

    
    def _init_settings(self):
        # create the setting that are needed
        # store that to iterate over it in _on_settings_updated
        self._settingsList = {
            # How often, in seconds, the anchor position should be advertised on AIS. Set to 0 to disable anchor position on AIS
            "AdvertiseInterval":                ["/Settings/AnchorAlarm/NMEA/AISAnchor/AdvertiseInterval", 5, 0, 60],
            
            # Name of the AIS target that should be displayed
            "Name":                             ["/Settings/AnchorAlarm/NMEA/AISAnchor/TargetName", "Anchor", 0, 60],
        }


        self._settings = self._settings_provider(self._settingsList, self._on_setting_changed)
        self._on_setting_changed(None, None, None)        


    def _on_setting_changed(self, key, old_value, new_value):
        self._remove_timer('advertise_timer')
        logger.debug("adding timer")
        if self._settings['AdvertiseInterval'] != 0:
            self._add_timer('advertise_timer', self._advertise_ais_target, self._settings['AdvertiseInterval']*1000, False)


    # called when a state changes
    def on_state_changed(self, current_state:AnchorAlarmState):
        """Called by controller when state changed"""
        logger.info("On state changed "+ current_state.state)

        if current_state.state == "DISABLED": 
            self._anchor_position = self._DISABLED_POSITION
        elif "drop_point" in current_state.params:
            self._anchor_position = current_state.params["drop_point"]

        self.update_state(current_state)

        # advertise the state change
        self._advertise_ais_target()


    def _advertise_ais_target(self):
        if self._settings['AdvertiseInterval'] == 0:
            # do not advertise at all, stop timer
            return False

        
        # { "pgn": 129039, "fields": {"Message ID": "Standard Class B position report", "Repeat Indicator": "Initial", "User ID": 368299999, "Longitude": -60.9595577, "Latitude": 14.0829979, "Position Accuracy": "Low", "RAIM": "not in use", "Time Stamp": "45", "COG": 0, "SOG": 0, "AIS Transceiver information": "Channel B VDL reception", "Heading": 0, "Regional Application B": 0, "Unit type": "SOTDMA", "Integrated Display": "No", "DSC": "No", "Band": "Top 525 kHz of marine band", "Can handle Msg 22": "No", "AIS mode": "Autonomous", "AIS communication state": "SOTDMA"}, "description": "AIS Class B Position Report"}
        # { 'pgn': 129809, 'fields': {'Message ID': 'Static data report', 'Repeat Indicator': 'Initial', 'User ID': 244024607, 'Name': 'COSI', 'AIS Transceiver information': 'Channel B VDL reception'}, 'description': 'AIS Class B static data (msg 24 Part A)'}

        
        position_nmea_message = { 
            "pgn": 129039, 
            "fields": {
                "Message ID": "Standard Class B position report", 
                "Repeat Indicator": "Initial", 
                "User ID": self._MMSI, 
                "Longitude": self._anchor_position.longitude, 
                "Latitude": self._anchor_position.latitude, 
                "Position Accuracy": "Low", 
                "RAIM": "not in use", 
                "Time Stamp": "45", 
                "COG": self._anchor_heading, 
                "SOG": 0, 
                "AIS Transceiver information": "Channel B VDL reception", 
                "Heading": self._anchor_heading, 
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

    
        logger.debug("advertising anchor position", position_nmea_message)
        self._bridge.send_nmea(position_nmea_message)

        name_nmea_message = { 
            'pgn': 129809, 
            'fields': {
                'Message ID': 'Static data report', 
                'Repeat Indicator': 'Initial', 
                'User ID': self._MMSI, 
                'Name': self._settings['Name'], 
                'AIS Transceiver information': 'Channel B VDL reception'
            }, 
            'description': 'AIS Class B static data (msg 24 Part A)'
        }
        
        logger.debug("advertising anchor name", name_nmea_message)
        self._bridge.send_nmea(name_nmea_message)

        return True # we want to repeat that


    # called every second to update state
    def update_state(self, current_state:AnchorAlarmState):
        """Called by controller every second with updated state"""
        pass
        # not sure we need that. Maybe to update heading ?


    def _on_heading_change(self, nmea_message):
        # {"canId":166793731,"prio":2,"src":3,"dst":255,"pgn":127250,"timestamp":"2025-06-10T18:04:39.871Z","fields":{"SID":163,"Heading":1.3892,"Deviation":0,"Variation":-0.2655,"Reference":"True"},"description":"Vessel Heading"}}
        if "fields" not in nmea_message:
            return
        
        if "Heading" not in nmea_message["fields"]:
            return  # should not happen
        
        self._anchor_heading = nmea_message["fields"]["Heading"]



if __name__ == '__main__':

    from nmea_bridge import NMEABridge
    from utils import handle_stdin, find_n2k_can
    from gi.repository import GLib
    import dbus
    sys.path.insert(1, os.path.join(os.path.dirname(__file__), '../ext/velib_python'))

    from settingsdevice import SettingsDevice
    from unittest.mock import MagicMock
    from collections import namedtuple
    from dbus.mainloop.glib import DBusGMainLoop


    logging.basicConfig(level=logging.DEBUG)

    from abstract_gps_provider import GPSPosition
    
    DBusGMainLoop(set_as_default=True)

    bus = dbus.SessionBus() if 'DBUS_SESSION_BUS_ADDRESS' in os.environ else dbus.SystemBus()
    can_id = find_n2k_can(bus)
    bridge = NMEABridge(can_id)    

    nmea_ais_connector = NMEAAISAnchorConnector(lambda: GLib, lambda settings, cb: SettingsDevice(bus, settings, cb), bridge)


    state_drop_point_set = AnchorAlarmState('DROP_POINT_SET', 'Drop point set, please do blablala',"short message", 'info', False, {'drop_point': GPSPosition(10, 11)})
    state_in_radius = AnchorAlarmState('IN_RADIUS', 'boat in radius',"short message", 'info', False, {'drop_point': GPSPosition(10, 11), 'radius': 12})
    state_dragging = AnchorAlarmState('ALARM_DRAGGING', 'Anchor dragging !',"short message", 'emergency', False, {'drop_point': GPSPosition(10, 11), 'radius': 12})
    state_dragging_muted = AnchorAlarmState('ALARM_DRAGGING_MUTED', 'Anchor dragging ! (muted)',"short message", 'emergency', True, {'drop_point': GPSPosition(10, 11), 'radius': 12})
    state_disabled = AnchorAlarmState('DISABLED', 'Anchor alarm disabled',"short message", 'info', False, {})
    state_no_gps = AnchorAlarmState('ALARM_NO_GPS', 'alarm no gps',"short message", 'emergency', False, {})
    state_no_gps_muted = AnchorAlarmState('ALARM_NO_GPS_MUTED', 'alarm no gps',"short message", 'emergency', True, {})

    controller = MagicMock()

    nmea_ais_connector.set_controller(controller)

    print("NMEA DS connector test program.\nType:\ndisabled to simulate DISABLED state\ndrop to simulate DROP_POINT_SET\nradius to simulate IN_RADIUS\ndragging to simulate ALARM_DRAGGING\ndragging_muted to simulate ALARM_DRAGING_MUTED\nnogps to simulate ALARM_NO_GPS\nnogps_muted to simulate ALARM_NO_GPS_MUTED\nexit to exit\n")

    def handle_command(command, text):
        if command == "disabled":
            nmea_ais_connector.on_state_changed(state_disabled)
        elif command == "drop":
            nmea_ais_connector.on_state_changed(state_drop_point_set)
        elif command == "radius":
            nmea_ais_connector.on_state_changed(state_in_radius)
        elif command == "dragging":
            nmea_ais_connector.on_state_changed(state_dragging)
        elif command == "dragging_muted":
            nmea_ais_connector.on_state_changed(state_dragging_muted)
        elif command == "nogps":
            nmea_ais_connector.on_state_changed(state_no_gps)
        elif command == "nogps_muted":
            nmea_ais_connector.on_state_changed(state_no_gps_muted)
        else:
            print("Unknown command "+ command)


    handle_stdin(handle_command)
