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

import logging
logger = logging.getLogger(__name__)

class NMEASOGRPMConnector(AbstractConnector):
    def __init__(self, timer_provider, settings_provider, nmea_bridge):
        super().__init__(timer_provider, settings_provider)
        
        self._init_settings()

        self._timer_ids = {
            'conditions_met': None,
        }

        self._should_watch  = False

        self._last_sog      = None
        self._last_rpm_port = None
        self._last_rpm_stb  = None

        self._bridge = nmea_bridge
        self._bridge.add_pgn_handler(129026, self._on_sog)
        self._bridge.add_pgn_handler(127488, self._on_rpm)


    def _init_settings(self):
        # create the setting that are needed
        settingsList = {
            # Speed Over Ground to be considered as a non moving position. In windy conditions, boat will always move a bit side to side
            # and it will be very hard to get a 0.0 SOG for 3 seconds. 0.3knots seems to be a good value
            "SOG":                 ["/Settings/AnchorAlarm/NMEA/SOGRPM/SOG", 0.3, 0, 1],

            # Number of engines to watch RPM for
            "NumberOfEngines":     ["/Settings/AnchorAlarm/NMEA/SOGRPM/NumberOfEngines", 2, 1, 2],

            # RPM that needs to be reached to enable the anchor alarm
            "RPM":                 ["/Settings/AnchorAlarm/NMEA/SOGRPM/RPM", 1700, 1000, 2200],

            # Duration for which both SOG and RPM conditions need to be met to activate anchor alarm
            "Duration":            ["/Settings/AnchorAlarm/NMEA/SOGRPM/Duration", 3, 0, 10],
        }

        # we don't care about getting notified if settings are updated
        self._settings = self._settings_provider(settingsList, None)

        # TODO XXX add some code to only watch if in DROP_POINT_SET state

        

    def _on_sog(self, nmea_message):
        # {'canId': 167248387, 'prio': 2, 'src': 3, 'dst': 255, 'pgn': 129026, 'timestamp': '2025-05-16T13:51:59.279Z', 'fields': {'SID': 208, 'COG Reference': 'True', 'COG': 0.2787, 'SOG': 0.07}, 'description': 'COG & SOG, Rapid Update'}
        if "fields" not in nmea_message:
            return
        
        if "SOG" not in nmea_message["fields"]:
            return  # should not happen
        
        self._last_sog = nmea_message["fields"]["SOG"]

        self._check_conditions_met()

    def _on_rpm(self, nmea_message):
        # {'canId': 166854714, 'prio': 2, 'src': 58, 'dst': 255, 'pgn': 127488, 'timestamp': '2025-05-16T13:57:08.889Z', 'fields': {'Instance': 'Single Engine or Dual Engine Port', 'Speed': 0, 'Boost Pressure': 0}, 'description': 'Engine Parameters, Rapid Update'}
        # {'canId': 166854712, 'prio': 2, 'src': 56, 'dst': 255, 'pgn': 127488, 'timestamp': '2025-05-16T13:57:41.254Z', 'fields': {'Instance': 'Dual Engine Starboard', 'Speed': 0, 'Boost Pressure': 0}, 'description': 'Engine Parameters, Rapid Update'}
        if "fields" not in nmea_message:
            return
        
        instance_field = "Engine Instance" if "Engine Instance" in nmea_message["fields"] else "Instance"
        engine_id = nmea_message["fields"][instance_field]

        speed_field    = "Engine Speed" if "Engine Speed" in nmea_message["fields"] else "Speed"
        speed = int(nmea_message["fields"][speed_field])

        if engine_id == "Single Engine or Dual Engine Port":
            self._last_rpm_port = speed
        else:
            self._last_rpm_stb = speed

        self._check_conditions_met()

    def _check_conditions_met(self):
        if self._conditions_met():
            if self._timer_ids['conditions_met'] is None:
                logger.info("Conditions are met, arming timer")
                self._add_timer('conditions_met', self._on_conditions_met, self._settings['Duration']*1000)
        else:
            if self._timer_ids['conditions_met'] is not None:
                logger.info("Conditions are not met anymore, removing timer")
            self._remove_timer('conditions_met')

    def _conditions_met(self):
        if not self._should_watch:
            return False
        
        if self._last_sog is None or self._last_sog is not None and self._last_sog > self._settings['SOG']:
            return False
        
        if self._last_rpm_port is None or self._last_rpm_port is not None and self._last_rpm_port <= self._settings['RPM']:
            return False
        
        if self._settings['NumberOfEngines'] == 2 and (self._last_rpm_stb is None or self._last_rpm_stb is not None and self._last_rpm_stb <= self._settings['RPM']):
            return False
        
        return True
    
    def _on_conditions_met(self):
        if self.controller is None:
            return
        
        logger.info("Conditions met for enough time, calling trigger_chain_out")
        self.controller.trigger_chain_out()

    # called when a state changes
    def on_state_changed(self, current_state:AnchorAlarmState):
        self._should_watch = current_state.state == "DROP_POINT_SET"
        self._check_conditions_met()


    # called every second to update state
    def update_state(self, current_state:AnchorAlarmState):
        """Called by controller every second with updated state"""
        # we don't really care
        pass




if __name__ == '__main__':

    from nmea_bridge import NMEABridge
    from utils import handle_stdin, find_n2k_can
    from gi.repository import GLib
    import dbus
    sys.path.insert(1, os.path.join(os.path.dirname(__file__), '../ext/velib_python'))

    from settingsdevice import SettingsDevice
    from unittest.mock import MagicMock
    from dbus.mainloop.glib import DBusGMainLoop
    
    DBusGMainLoop(set_as_default=True)

    bus = dbus.SessionBus() if 'DBUS_SESSION_BUS_ADDRESS' in os.environ else dbus.SystemBus()
    can_id = find_n2k_can(bus)
    bridge = NMEABridge(can_id)    

    nmea_alert_connector = NMEASOGRPMConnector(lambda: GLib, lambda settings, cb: SettingsDevice(bus, settings, cb), bridge)

    controller = MagicMock()
    controller.trigger_chain_out   = MagicMock(side_effect=lambda: print("\n\n\n\n\n\n\ntrigger chain out\n\n\n\n\n\n\n"))
    nmea_alert_connector.set_controller(controller)


    print("NMEA SOG RPM test program. Type : exit to exit\nWhen the SOG is < 0.3 and RPM of both engines is > 1700 for 3 seconds, will print 'trigger chain out'. You can change these settings with dbus-spy")

    def handle_command(command, text):
        print("Unknown command "+ command)


    handle_stdin(handle_command)