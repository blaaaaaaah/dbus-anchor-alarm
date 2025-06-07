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


from utils import exit_on_error

import logging

from abstract_gps_provider import AbstractGPSProvider
from abstract_gps_provider import GPSPosition

logger = logging.getLogger(__name__)

class NMEAGPSProvider(AbstractGPSProvider):
    def __init__(self, timer_provider, nmea_bridge):
        super().__init__(timer_provider)

        self._timer_ids = {
            'invalidate': None
        }

        self._gps_positions = {}

        self._current_gps_src = None

        self._bridge = nmea_bridge

        # we do not rely on 129025 because they might keep sending the last known position
        # even if source lost the GPS fix
        self._bridge.add_pgn_handler(129029, self._on_gnss_position_data)

        
        

    def _on_gnss_position_data(self, nmea_message):
        if "fields" not in nmea_message:
            return

        if "src" not in nmea_message:
            return
        
        # {'canId': 234358019, 'prio': 3, 'src': 3,  'dst': 255, 'pgn': 129029, 'timestamp': '2025-06-06T17:35:03.931Z', 'input': [], 'fields': {'SID': 167, 'Date': '2025.06.06', 'Time': '17:27:06', 'Latitude': 14.084799002033536, 'Longitude': -60.960235248733056, 'Altitude': -29.651882, 'GNSS type': 'GPS+SBAS/WAAS+GLONASS', 'Method': 'no GNSS', 'Integrity': 'No integrity checking', 'Number of SVs': 0, 'HDOP': 0.51, 'PDOP': 1.08, 'Reference Stations': 0, 'list': []}, 'description': 'GNSS Position Data'}
        # {'canId': 234358059, 'prio': 3, 'src': 43, 'dst': 255, 'pgn': 129029, 'timestamp': '2025-06-06T17:35:03.991Z', 'input': [], 'fields': {'Date': '2025.06.06', 'Time': '17:35:04', 'Latitude': 14.084805799339621, 'Longitude': -60.96023005073244, 'GNSS type': 'GPS', 'Method': 'GNSS fix', 'Integrity': 'No integrity checking', 'Geoidal Separation': 0, 'Reference Stations': 0, 'list': []}, 'description': 'GNSS Position Data'}

        
        if "Method" not in nmea_message["fields"]:
            return  # should not happen
        
        if "Latitude" not in nmea_message["fields"]:
            return  # should not happen
        
        if "Longitude" not in nmea_message["fields"]:
            return  # should not happen
        

        # https://canboat.github.io/canboat/canboat.html#lookup-GNS_METHOD
        has_fix = nmea_message["fields"]["Method"] != "no GNSS"


        if has_fix:
            self._gps_positions[nmea_message['src']] = GPSPosition(nmea_message["fields"]["Latitude"], nmea_message["fields"]["Longitude"])
            self._add_timer('invalidate_'+ str(nmea_message['src']), lambda: self._gps_positions.pop(nmea_message['src'], None), 1000)
        else:
            self._gps_positions.pop(nmea_message['src'], None)



    def get_gps_position(self):
        if len(self._gps_positions) == 0:
            return None

        # if we started returning a position from a source, keep this source to avoid bouncing effect
        # between multiple slightly different gps coordinates, eg when antennas are not in the same place
        if self._current_gps_src and self._current_gps_src in self._gps_positions:
            return self._gps_positions[self._current_gps_src]

        self._current_gps_src = next(iter(self._gps_positions))
        return self._gps_positions[self._current_gps_src]







if __name__ == '__main__':

    from nmea_bridge import NMEABridge
    from utils import handle_stdin
    from gi.repository import GLib
    import dbus
    sys.path.insert(1, os.path.join(os.path.dirname(__file__), '../ext/velib_python'))

    from settingsdevice import SettingsDevice
    from unittest.mock import MagicMock
    from dbus.mainloop.glib import DBusGMainLoop

    bridge = NMEABridge('../nmea_bridge.js')
    DBusGMainLoop(set_as_default=True)

    bus = dbus.SessionBus() if 'DBUS_SESSION_BUS_ADDRESS' in os.environ else dbus.SystemBus()
    provider = NMEAGPSProvider(lambda: GLib, bridge)

    def log_gps_position(provider):
        print (str(provider.get_gps_position()))
        return True

    GLib.timeout_add(1000, exit_on_error, log_gps_position, provider)

    print("NMEA GPS Provider test program. Type : exit to exit\n")

    def handle_command(command, text):
        print("Unknown command "+ command)


    handle_stdin(handle_command)