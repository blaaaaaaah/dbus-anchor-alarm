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

sys.path.insert(1, os.path.join(sys.path[0], '..'))
sys.path.insert(1, os.path.join(os.path.dirname(__file__), '../ext/velib_python/test'))

from anchor_alarm_model import AnchorAlarmState

import unittest
from unittest.mock import ANY
from unittest.mock import MagicMock
from unittest.mock import Mock
from unittest.mock import patch

sys.modules['dbus'] = Mock()


sys.path.insert(1, os.path.join(sys.path[0], '../gps_providers'))

from dbus_gps_provider import DBusGPSProvider

from mock_dbus_monitor import MockDbusMonitor
from mock_dbus_service import MockDbusService
from mock_settings_device import MockSettingsDevice

from glib_timer_mock import GLibTimerMock
          
from abstract_gps_provider import GPSPosition

class MockDBusGPSProvider(DBusGPSProvider):
    def _create_dbus_monitor(self, *args, **kwargs):
        return MockDbusMonitor(*args, **kwargs)

    def mock_monitor(self):
        return self._dbusmonitor
    
    


timer_provider = GLibTimerMock()

class TestDBusGPSProvider(unittest.TestCase):

    def setUp(self):
        self.maxDiff = None

        



    def test_service_available(self):
        

        provider = MockDBusGPSProvider(lambda: timer_provider)
        monitor = provider.mock_monitor()


        self.assertIsNone(provider.get_gps_position())
        monitor.add_service('com.victronenergy.gps.qwe1',
			values={
                '/DeviceInstance': 0,
				'/Fix': 0,
				'/Position/Latitude': 1,
				'/Position/Longitude': 1
                })
        self.assertIsNone(provider.get_gps_position())
        
        monitor.set_value('com.victronenergy.gps.qwe1', '/Fix', 1)
    
        self.assertEqual(provider.get_gps_position(), GPSPosition(1, 1))

        monitor.set_value('com.victronenergy.gps.qwe1', '/Position/Latitude', 2)
        monitor.set_value('com.victronenergy.gps.qwe1', '/Position/Longitude', 2)

        self.assertEqual(provider.get_gps_position(), GPSPosition(2, 2))

        monitor.set_value('com.victronenergy.gps.qwe1', '/Fix', 0)
        self.assertIsNone(provider.get_gps_position())

        monitor.set_value('com.victronenergy.gps.qwe1', '/Fix', 1)
        self.assertEqual(provider.get_gps_position(), GPSPosition(2, 2))

        monitor.add_service('com.victronenergy.gps.qwe2',
			values={
                '/DeviceInstance': 0,
				'/Fix': 1,
				'/Position/Latitude': 10,
				'/Position/Longitude': 10
                })
        
        self.assertEqual(provider.get_gps_position(), GPSPosition(2, 2))
        monitor.set_value('com.victronenergy.gps.qwe1', '/Fix', 0)

        self.assertEqual(provider.get_gps_position(), GPSPosition(10, 10))

        monitor.set_value('com.victronenergy.gps.qwe1', '/Fix', 1)
        self.assertEqual(provider.get_gps_position(), GPSPosition(2, 2))

        monitor.remove_service('com.victronenergy.gps.qwe1')

        self.assertEqual(provider.get_gps_position(), GPSPosition(10, 10))

        monitor.remove_service('com.victronenergy.gps.qwe2')
        self.assertIsNone(provider.get_gps_position())


if __name__ == '__main__':
    unittest.main()