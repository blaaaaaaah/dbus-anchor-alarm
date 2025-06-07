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


sys.path.insert(1, os.path.join(sys.path[0], '../connectors'))

from dbus_relay_connector import DBusRelayConnector

from mock_dbus_monitor import MockDbusMonitor
from mock_dbus_service import MockDbusService
from mock_settings_device import MockSettingsDevice

from glib_timer_mock import GLibTimerMock
          
from abstract_gps_provider import GPSPosition

class MockDBusRelayConnector(DBusRelayConnector):
    def _create_dbus_monitor(self, *args, **kwargs):
        return MockDbusMonitor(*args, **kwargs)
    
    def _create_dbus_service(self, *args, **kwargs):
        return MockDbusService(args[0])

    def mock_monitor(self):
        return self._alarm_monitor
    
    def mock_service(self):
        return self._dbus_service
    


timer_provider = GLibTimerMock()

class TestDBusRelayConnector(unittest.TestCase):

    def setUp(self):
        self.maxDiff = None

        



    def test_service_available(self):
        controller = MagicMock()
        controller.trigger_anchor_down  = MagicMock()
        controller.trigger_anchor_up    = MagicMock()
        controller.trigger_chain_out    = MagicMock()
        controller.trigger_mute_alarm   = MagicMock()

        connector = MockDBusRelayConnector(lambda: timer_provider, lambda settings, cb: MockSettingsDevice(settings, cb))
        connector._settings['Enabled'] = 1
        connector.set_controller(controller)
        monitor = connector.mock_monitor()
        monitor.add_service('com.victronenergy.system',
			values={
				'/Relay/1/State': 0,
			})
        
        monitor.add_service('com.victronenergy.settings',
			values={
                '/Settings/Relay/1/Function': 2,
			})
    

        
        # make sure relay state is disabled
        def test_states(is_inverted):
            connector._settings['Inverted'] = is_inverted

            state_disabled = AnchorAlarmState('DISABLED', 'Anchor alarm disabled', "short message",'info', False, {})
            connector.on_state_changed(state_disabled)

            self.assertEqual(monitor.get_value("com.victronenergy.system", '/Relay/1/State'), is_inverted)

            state = AnchorAlarmState('IN_RADIUS', 'boat in radius', "short in radius message", 'info', False, {'drop_point': GPSPosition(10, 11), 'radius': 12})
            connector.on_state_changed(state)

            self.assertEqual(monitor.get_value("com.victronenergy.system", '/Relay/1/State'), is_inverted)


            state_dragging = AnchorAlarmState('ALARM_DRAGGING', 'boat outside radius', "short message",'emergency', False, {'drop_point': GPSPosition(10, 11), 'radius': 12})
            connector.on_state_changed(state_dragging)

            self.assertEqual(monitor.get_value("com.victronenergy.system", '/Relay/1/State'), 0 if is_inverted else 1)


            state_muted = AnchorAlarmState('ALARM_DRAGGING_MUTED', 'boat outside radius', "short message",'emergency', True, {'drop_point': GPSPosition(10, 11), 'radius': 12})
            connector.on_state_changed(state_muted)

            self.assertEqual(monitor.get_value("com.victronenergy.system", '/Relay/1/State'), is_inverted)



            state_no_gps = AnchorAlarmState('ALARM_NO_GPS', 'boat outside radius', "short message",'emergency', False, {'drop_point': GPSPosition(10, 11), 'radius': 12})
            connector.on_state_changed(state_no_gps)

            self.assertEqual(monitor.get_value("com.victronenergy.system", '/Relay/1/State'), 0 if is_inverted else 1)


            state_no_gps_muted = AnchorAlarmState('ALARM_NO_GPS_MUTED', 'boat outside radius', "short message",'emergency', True, {'drop_point': GPSPosition(10, 11), 'radius': 12})
            connector.on_state_changed(state_no_gps_muted)

            self.assertEqual(monitor.get_value("com.victronenergy.system", '/Relay/1/State'), is_inverted)


        test_states(0)

        # test inverted state
        test_states(1)


    def test_not_function_equals_2(self):
        controller = MagicMock()
        controller.trigger_anchor_down  = MagicMock()
        controller.trigger_anchor_up    = MagicMock()
        controller.trigger_chain_out    = MagicMock()
        controller.trigger_mute_alarm   = MagicMock()

        connector = MockDBusRelayConnector(lambda: timer_provider, lambda settings, cb: MockSettingsDevice(settings, cb))
        connector.set_controller(controller)
        monitor = connector.mock_monitor()
        monitor.add_service('com.victronenergy.system',
			values={
				'/Relay/1/State': 0,
			})
        
        monitor.add_service('com.victronenergy.settings',
			values={
                '/Settings/Relay/1/Function': 1,
			})
    
     
        self.assertEqual(monitor.get_value("com.victronenergy.system", '/Relay/1/State'), 0)

        state = AnchorAlarmState('IN_RADIUS', 'boat in radius', "short in radius message", 'info', False, {'drop_point': GPSPosition(10, 11), 'radius': 12})
        connector.on_state_changed(state)

        self.assertEqual(monitor.get_value("com.victronenergy.system", '/Relay/1/State'), 0)


        state_dragging = AnchorAlarmState('ALARM_DRAGGING', 'boat outside radius', "short message",'emergency', False, {'drop_point': GPSPosition(10, 11), 'radius': 12})
        connector.on_state_changed(state_dragging)

        self.assertEqual(monitor.get_value("com.victronenergy.system", '/Relay/1/State'), 0)


        state_muted = AnchorAlarmState('ALARM_DRAGGING_MUTED', 'boat outside radius', "short message",'emergency', True, {'drop_point': GPSPosition(10, 11), 'radius': 12})
        connector.on_state_changed(state_muted)

        self.assertEqual(monitor.get_value("com.victronenergy.system", '/Relay/1/State'), 0)



        state_no_gps = AnchorAlarmState('ALARM_NO_GPS', 'boat outside radius', "short message",'emergency', False, {'drop_point': GPSPosition(10, 11), 'radius': 12})
        connector.on_state_changed(state_no_gps)

        self.assertEqual(monitor.get_value("com.victronenergy.system", '/Relay/1/State'), 0)


        state_no_gps_muted = AnchorAlarmState('ALARM_NO_GPS_MUTED', 'boat outside radius', "short message",'emergency', True, {'drop_point': GPSPosition(10, 11), 'radius': 12})
        connector.on_state_changed(state_no_gps_muted)

        self.assertEqual(monitor.get_value("com.victronenergy.system", '/Relay/1/State'), 0)


def test_not_enabled(self):
        controller = MagicMock()
        controller.trigger_anchor_down  = MagicMock()
        controller.trigger_anchor_up    = MagicMock()
        controller.trigger_chain_out    = MagicMock()
        controller.trigger_mute_alarm   = MagicMock()

        connector = MockDBusRelayConnector(lambda: timer_provider, lambda settings, cb: MockSettingsDevice(settings, cb))
        connector._settings['Enabled'] = 0

        connector.set_controller(controller)
        monitor = connector.mock_monitor()
        monitor.add_service('com.victronenergy.system',
			values={
				'/Relay/1/State': 0,
			})
        
        monitor.add_service('com.victronenergy.settings',
			values={
                '/Settings/Relay/1/Function': 2,
			})
    
     
        self.assertEqual(monitor.get_value("com.victronenergy.system", '/Relay/1/State'), 0)

        state = AnchorAlarmState('IN_RADIUS', 'boat in radius', "short in radius message", 'info', False, {'drop_point': GPSPosition(10, 11), 'radius': 12})
        connector.on_state_changed(state)

        self.assertEqual(monitor.get_value("com.victronenergy.system", '/Relay/1/State'), 0)


        state_dragging = AnchorAlarmState('ALARM_DRAGGING', 'boat outside radius', "short message",'emergency', False, {'drop_point': GPSPosition(10, 11), 'radius': 12})
        connector.on_state_changed(state_dragging)

        self.assertEqual(monitor.get_value("com.victronenergy.system", '/Relay/1/State'), 0)


        state_muted = AnchorAlarmState('ALARM_DRAGGING_MUTED', 'boat outside radius', "short message",'emergency', True, {'drop_point': GPSPosition(10, 11), 'radius': 12})
        connector.on_state_changed(state_muted)

        self.assertEqual(monitor.get_value("com.victronenergy.system", '/Relay/1/State'), 0)



        state_no_gps = AnchorAlarmState('ALARM_NO_GPS', 'boat outside radius', "short message",'emergency', False, {'drop_point': GPSPosition(10, 11), 'radius': 12})
        connector.on_state_changed(state_no_gps)

        self.assertEqual(monitor.get_value("com.victronenergy.system", '/Relay/1/State'), 0)


        state_no_gps_muted = AnchorAlarmState('ALARM_NO_GPS_MUTED', 'boat outside radius', "short message",'emergency', True, {'drop_point': GPSPosition(10, 11), 'radius': 12})
        connector.on_state_changed(state_no_gps_muted)

        self.assertEqual(monitor.get_value("com.victronenergy.system", '/Relay/1/State'), 0)

if __name__ == '__main__':
    unittest.main()