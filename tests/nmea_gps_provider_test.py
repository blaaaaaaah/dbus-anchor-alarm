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
from unittest import mock


sys.path.insert(1, os.path.join(sys.path[0], '..'))
sys.path.insert(1, os.path.join(os.path.dirname(__file__), '../ext/velib_python/test'))


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

from nmea_gps_provider import NMEAGPSProvider
          
timer_provider = GLibTimerMock()




class TestNMEAGPSProvider(unittest.TestCase):

    def setUp(self):
        self.maxDiff = None


    def test_provider(self):
        mock_bridge = MagicMock()
        
        handler = None
        def _set_handler(pgn, the_handler):
            nonlocal handler
            handler = the_handler

        mock_bridge.add_pgn_handler = MagicMock(side_effect=_set_handler)              


        provider = NMEAGPSProvider(lambda: timer_provider, mock_bridge)

        self.assertIsNone(provider.get_gps_position())

        def get_nofix_message(src):
            return {'canId': 234358019, 'prio': 3, 'src': src,  'dst': 255, 'pgn': 129029, 'timestamp': '2025-06-06T17:35:03.931Z', 'input': [], 
                    'fields': {'SID': 167, 'Date': '2025.06.06', 'Time': '17:27:06', 'Latitude': 14.084799002033536, 'Longitude': -60.960235248733056, 
                               'Altitude': -29.651882, 'GNSS type': 'GPS+SBAS/WAAS+GLONASS', 'Method': 'no GNSS', 'Integrity': 'No integrity checking', 
                               'Number of SVs': 0, 'HDOP': 0.51, 'PDOP': 1.08, 'Reference Stations': 0, 'list': []}, 'description': 'GNSS Position Data'}


        def get_fix_message(src, lat, lon):
            return {'canId': 234358059, 'prio': 3, 'src': src, 'dst': 255, 'pgn': 129029, 'timestamp': '2025-06-06T17:35:03.991Z', 'input': [], 
                    'fields': {'Date': '2025.06.06', 'Time': '17:35:04', 'Latitude': lat, 'Longitude': lon, 'GNSS type': 'GPS', 'Method': 'GNSS fix', 
                               'Integrity': 'No integrity checking', 'Geoidal Separation': 0, 'Reference Stations': 0, 'list': []}, 'description': 'GNSS Position Data'}

        handler(get_nofix_message(1))
        self.assertIsNone(provider.get_gps_position())

        handler(get_fix_message(1, 1, 1))
        self.assertEqual(provider.get_gps_position(), GPSPosition(1, 1))

        timer_provider.tick()
        timer_provider.tick()
        self.assertIsNone(provider.get_gps_position())

        handler(get_fix_message(1, 2, 2))
        self.assertEqual(provider.get_gps_position(), GPSPosition(2, 2))
        handler(get_nofix_message(1))
        self.assertIsNone(provider.get_gps_position())

        handler(get_fix_message(1, 3, 3))
        handler(get_nofix_message(2))
        self.assertEqual(provider.get_gps_position(), GPSPosition(3, 3))
        handler(get_fix_message(20, 20, 20))
        self.assertEqual(provider.get_gps_position(), GPSPosition(3, 3))


        handler(get_nofix_message(1))
        self.assertEqual(provider.get_gps_position(), GPSPosition(20, 20))

        handler(get_nofix_message(20))
        self.assertIsNone(provider.get_gps_position())


        handler(get_fix_message(20, 20, 20))
        self.assertEqual(provider.get_gps_position(), GPSPosition(20, 20))

        timer_provider.tick()
        timer_provider.tick()
        self.assertIsNone(provider.get_gps_position())


if __name__ == '__main__':
    unittest.main()