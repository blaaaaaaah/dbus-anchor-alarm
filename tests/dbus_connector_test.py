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
from turtle import st

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

from dbus_connector import DBusConnector

from mock_dbus_monitor import MockDbusMonitor
from mock_dbus_service import MockDbusService
from mock_settings_device import MockSettingsDevice

from glib_timer_mock import GLibTimerMock
          
from abstract_gps_provider import GPSPosition

class MockDBusConnector(DBusConnector):
    def _create_dbus_monitor(self, *args, **kwargs):
        return MockDbusMonitor(*args, **kwargs)

    def mock_monitor(self):
        return self._alarm_monitor
    
    def mock_service(self):
        return self._dbus_service
    


timer_provider = GLibTimerMock()

def create_mock_dbus_service():
    """Create a mock D-Bus service for testing"""
    return MockDbusService("com.victronenergy.anchoralarm.test")

class TestDBusConnector(unittest.TestCase):

    def setUp(self):
        self.maxDiff = None

        



    def test_settings_created_and_update_callback(self):
        mock_bridge = MagicMock()
        mock_bridge.add_pgn_handler = MagicMock()
        mock_bridge.send_nmea = MagicMock()

        connector = MockDBusConnector(lambda: timer_provider, lambda settings, cb: MockSettingsDevice(settings, cb), mock_bridge, create_mock_dbus_service())

        self.assertEqual(connector._anchor_up_digital_input, 'com.victronenergy.digitalinput.input01')

        connector._settings['AnchorDownDigitalInputNumber'] = 3
        self.assertEqual(connector._anchor_down_digital_input, 'com.victronenergy.digitalinput.input03')


    def test_service_available(self):
        controller = MagicMock()
        controller.trigger_anchor_down  = MagicMock()
        controller.trigger_anchor_up    = MagicMock()
        controller.trigger_chain_out    = MagicMock()
        controller.trigger_mute_alarm   = MagicMock()
        controller.get_gps_position = MagicMock(return_value=GPSPosition(10, 11))

        mock_bridge = MagicMock()
        mock_bridge.add_pgn_handler = MagicMock()
        mock_bridge.send_nmea = MagicMock()


        connector = MockDBusConnector(lambda: timer_provider, lambda settings, cb: MockSettingsDevice(settings, cb), mock_bridge, create_mock_dbus_service())
        connector.set_controller(controller)
        monitor = connector.mock_monitor()
        monitor.add_service('com.victronenergy.digitalinput.input01',
			values={
				'/ProductName': "qwe",
				'/CustomName': "qwe",
                '/DeviceInstance': 0
			})
        
        monitor.add_service('com.victronenergy.settings',
			values={
                '/Settings/DigitalInput/1/AlarmSetting': 0,
                '/Settings/DigitalInput/1/InvertAlarm': 0,
                '/Settings/SystemSetup/SystemName': 'system name'
			})
        
        monitor.add_service('com.victronenergy.platform',
			values={
                '/Notifications/Alarm': 0
			})


        service = connector.mock_service()
        self.assertEqual(service['/Alarm/State'], 'DISABLED')
        self.assertEqual(service['/Alarm/Message'], '')
        self.assertEqual(service['/Alarm/Level'], '')
        self.assertEqual(service['/Alarm/Muted'], False)
        self.assertEqual(service['/Alarm/Alarm'], False)
        self.assertEqual(service['/Alarm/MutedDuration'], 0)
        self.assertEqual(service['/Alarm/NoGPSDuration'], 0)
        self.assertEqual(service['/Alarm/OutOfRadiusDuration'], 0)

        self.assertEqual(service['/Anchor/Latitude'], "")
        self.assertEqual(service['/Anchor/Longitude'], "")
        self.assertEqual(service['/Anchor/Radius'], "")
        self.assertEqual(service['/Anchor/Distance'], "")
        self.assertEqual(service['/Anchor/Tolerance'], "")

  

        # AnchorAlarmState = namedtuple('AnchorAlarmState', ['state', 'message', 'level', 'muted', 'params'])
        state = AnchorAlarmState('IN_RADIUS', 'boat in radius', "short in radius message", 'info', False, {'drop_point': GPSPosition(10, 11), 'radius': 12, 'current_radius':5, 'radius_tolerance': 15, 'alarm_muted_count': 0, 'no_gps_count': 0, 'out_of_radius_count': 0})
        connector.on_state_changed(state)

        self.assertEqual(service['/Alarm/State'], state.state)
        self.assertEqual(service['/Alarm/Message'], state.message)
        self.assertEqual(service['/Alarm/Level'], state.level)
        self.assertEqual(service['/Alarm/Muted'], state.muted)

        self.assertEqual(service['/Alarm/Alarm'], False)
        self.assertEqual(service['/Alarm/MutedDuration'], 0)
        self.assertEqual(service['/Alarm/NoGPSDuration'], 0)
        self.assertEqual(service['/Alarm/OutOfRadiusDuration'], 0)

        self.assertEqual(service['/Anchor/Latitude'], state.params['drop_point'].latitude)
        self.assertEqual(service['/Anchor/Longitude'], state.params['drop_point'].longitude)
        self.assertEqual(service['/Anchor/Radius'], state.params['radius'])
        self.assertEqual(service['/Anchor/Distance'], state.params['current_radius'])
        self.assertEqual(service['/Anchor/Tolerance'], state.params['radius_tolerance'])

        self.assertEqual(monitor.get_value('com.victronenergy.digitalinput.input01', '/CustomName'), state.message)
        self.assertEqual(monitor.get_value('com.victronenergy.digitalinput.input01', '/ProductName'), state.message)

        self.assertEqual(monitor.get_value("com.victronenergy.settings", '/Settings/DigitalInput/1/AlarmSetting'), False)
        self.assertEqual(monitor.get_value("com.victronenergy.settings", '/Settings/DigitalInput/1/InvertAlarm'), False)

        self.assertEqual(monitor.get_value("com.victronenergy.settings", '/Settings/SystemSetup/SystemName'), 'system name')

        connector._settings['FeedbackUseSystemName'] = 1

        state2 = AnchorAlarmState('IN_RADIUS', 'boat in radius 2',"in radius short message", 'info', False, {'drop_point': GPSPosition(110, 111), 'radius': 112, 'current_radius':12, 'radius_tolerance':15, 'alarm_muted_count': 0, 'no_gps_count': 0, 'out_of_radius_count': 0})
        connector.update_state(state2)

        self.assertEqual(service['/Alarm/State'], state2.state)
        self.assertEqual(service['/Alarm/Message'], state2.message)
        self.assertEqual(service['/Alarm/Level'], state2.level)
        self.assertEqual(service['/Alarm/Muted'], state2.muted)
        
        self.assertEqual(service['/Alarm/Alarm'], False)
        self.assertEqual(service['/Alarm/MutedDuration'], 0)
        self.assertEqual(service['/Alarm/NoGPSDuration'], 0)
        self.assertEqual(service['/Alarm/OutOfRadiusDuration'], 0)

        self.assertEqual(service['/Anchor/Latitude'], state2.params['drop_point'].latitude)
        self.assertEqual(service['/Anchor/Longitude'], state2.params['drop_point'].longitude)
        self.assertEqual(service['/Anchor/Radius'], state2.params['radius'])
        self.assertEqual(service['/Anchor/Distance'], state2.params['current_radius'])
        self.assertEqual(service['/Anchor/Tolerance'], state2.params['radius_tolerance'])

        # make sure alarm feedback didnt change. TODO XXX maybe change that ?
        self.assertEqual(monitor.get_value('com.victronenergy.digitalinput.input01', '/CustomName'), state2.message)
        self.assertEqual(monitor.get_value('com.victronenergy.digitalinput.input01', '/ProductName'), state2.message)
        
        self.assertEqual(monitor.get_value("com.victronenergy.settings", '/Settings/DigitalInput/1/AlarmSetting'), False)
        self.assertEqual(monitor.get_value("com.victronenergy.settings", '/Settings/DigitalInput/1/InvertAlarm'), False)

        self.assertEqual(monitor.get_value("com.victronenergy.settings", '/Settings/SystemSetup/SystemName'), state2.short_message)


        state3 = AnchorAlarmState('ALARM_DRAGGING', 'boat outside radius', "short message",'emergency', False, {'drop_point': GPSPosition(10, 11), 'radius': 12, 'current_radius': 7, 'radius_tolerance': 15, 'alarm_muted_count': 0, 'no_gps_count': 0, 'out_of_radius_count': 1})
        connector.on_state_changed(state3)

        self.assertEqual(service['/Alarm/State'], state3.state)
        self.assertEqual(service['/Alarm/Message'], state3.message)
        self.assertEqual(service['/Alarm/Level'], state3.level)
        self.assertEqual(service['/Alarm/Muted'], state3.muted)

        self.assertEqual(service['/Alarm/Alarm'], True)
        self.assertEqual(service['/Alarm/MutedDuration'], 0)
        self.assertEqual(service['/Alarm/NoGPSDuration'], 0)
        self.assertEqual(service['/Alarm/OutOfRadiusDuration'], 1)

        self.assertEqual(service['/Anchor/Latitude'], state3.params['drop_point'].latitude)
        self.assertEqual(service['/Anchor/Longitude'], state3.params['drop_point'].longitude)
        self.assertEqual(service['/Anchor/Radius'], state3.params['radius'])
        self.assertEqual(service['/Anchor/Distance'], state3.params['current_radius'])
        self.assertEqual(service['/Anchor/Tolerance'], state3.params['radius_tolerance'])

        self.assertEqual(monitor.get_value('com.victronenergy.digitalinput.input01', '/CustomName'), state3.message)
        self.assertEqual(monitor.get_value('com.victronenergy.digitalinput.input01', '/ProductName'), state3.message)
        self.assertEqual(monitor.get_value("com.victronenergy.settings", '/Settings/DigitalInput/1/AlarmSetting'), True)
        self.assertEqual(monitor.get_value("com.victronenergy.settings", '/Settings/DigitalInput/1/InvertAlarm'), True)
        monitor.set_value('com.victronenergy.platform', '/Notifications/Alarm', 1)  # our code doesn't set that to 1 automatically, Cerbo does

        # test mute alarm from cerbo
        monitor.set_value('com.victronenergy.platform', '/Notifications/Alarm', 0)
      
        controller.trigger_mute_alarm.assert_called_once()

        state4 = AnchorAlarmState('ALARM_DRAGGING_MUTED', 'boat outside radius', "short message",'emergency', True, {'drop_point': GPSPosition(10, 11), 'radius': 12, 'current_radius': 7, 'radius_tolerance': 15, 'alarm_muted_count': 1, 'no_gps_count': 0, 'out_of_radius_count': 1})
        connector.on_state_changed(state4)

        self.assertEqual(service['/Alarm/State'], state4.state)
        self.assertEqual(service['/Alarm/Message'], state4.message)
        self.assertEqual(service['/Alarm/Level'], state4.level)
        self.assertEqual(service['/Alarm/Muted'], state4.muted)

        self.assertEqual(service['/Alarm/Alarm'], True)
        self.assertEqual(service['/Alarm/MutedDuration'], 1)
        self.assertEqual(service['/Alarm/NoGPSDuration'], 0)
        self.assertEqual(service['/Alarm/OutOfRadiusDuration'], 1)

        self.assertEqual(service['/Anchor/Latitude'], state4.params['drop_point'].latitude)
        self.assertEqual(service['/Anchor/Longitude'], state4.params['drop_point'].longitude)
        self.assertEqual(service['/Anchor/Radius'], state4.params['radius'])
        self.assertEqual(service['/Anchor/Distance'], state4.params['current_radius'])
        self.assertEqual(service['/Anchor/Tolerance'], state4.params['radius_tolerance'])

        self.assertEqual(monitor.get_value("com.victronenergy.settings", '/Settings/DigitalInput/1/AlarmSetting'), False)
        self.assertEqual(monitor.get_value("com.victronenergy.settings", '/Settings/DigitalInput/1/InvertAlarm'), False)  

    def test_reset_state(self):
        pass



    #@patch.object(GLibMock, 'source_remove')
    def test_anchor_down(self):
        controller = MagicMock()
        controller.trigger_anchor_down  = MagicMock()
        controller.trigger_anchor_up    = MagicMock()
        controller.trigger_chain_out    = MagicMock()
        controller.trigger_mute_alarm   = MagicMock()
        controller.get_gps_position = MagicMock(return_value=GPSPosition(10, 11))


        mock_bridge = MagicMock()
        mock_bridge.add_pgn_handler = MagicMock()
        mock_bridge.send_nmea = MagicMock()


        connector = MockDBusConnector(lambda: timer_provider, lambda settings, cb: MockSettingsDevice(settings, cb), mock_bridge, create_mock_dbus_service())
        connector.set_controller(controller)
        connector._settings['MuteAlarmDigitalInputNumber']=4
        connector._settings['MuteAlarmDigitalInputDuration']=3

        monitor = connector.mock_monitor()
        monitor.add_service('com.victronenergy.digitalinput.input01',
			values={
				'/ProductName': "qwe",
				'/CustomName': "qwe",
                '/State': 1,
                '/DeviceInstance': 0
			})
        
        monitor.add_service('com.victronenergy.digitalinput.input02',
			values={
				'/ProductName': "qwe",
				'/CustomName': "qwe",
                '/State': 1,
                '/DeviceInstance': 1
			})
        monitor.add_service('com.victronenergy.digitalinput.input04',
			values={
				'/ProductName': "qwe",
				'/CustomName': "qwe",
                '/State': 1,
                '/DeviceInstance': 1
			})

        service = connector.mock_service()
        
        ON_STATE = 1        # TODO XXX check values
        OFF_STATE = 0
        
        def _check_all_not_called():
            controller.trigger_anchor_down.assert_not_called()
            controller.trigger_anchor_up.assert_not_called()
            controller.trigger_anchor_chain_out.assert_not_called()
            controller.trigger_mute_alarm.assert_not_called()

        def _4ticks():
            timer_provider.tick()
            timer_provider.tick()
            timer_provider.tick()
            timer_provider.tick()

        # couple of ticks, expect nothing
        _4ticks()
        _check_all_not_called()
        

        def check_sequence(path, called_check):

            # send state off, expect nothing
            monitor.set_value(path, '/State', OFF_STATE)
            _check_all_not_called()
            _4ticks()
            _check_all_not_called()



            # send state on, off, expect nothing, timer cleared
            monitor.set_value(path, '/State', ON_STATE)
            _check_all_not_called()
            timer_provider.tick()
            _check_all_not_called()


            monitor.set_value(path, '/State', OFF_STATE)
            #mock_source_remove.assert_called_once()
            #mock_source_remove.reset_mock()
            _check_all_not_called()
            _4ticks()
            _check_all_not_called()


            # send state on, wait for trigger, off. Expect controller update, timer cleared
            monitor.set_value(path, '/State', ON_STATE)

            timer_provider.tick()
            _check_all_not_called()  

            timer_provider.tick()
            _check_all_not_called()

            called_check()

            _check_all_not_called()
            _4ticks()
            _check_all_not_called()

            # TODO XXX : assert timer cleared


            # send state on, off. expect nothing
            monitor.set_value(path, '/State', ON_STATE)
            monitor.set_value(path, '/State', OFF_STATE)

            _check_all_not_called()
            _4ticks()
            _check_all_not_called()

            # TODO XXX : assert timer cleared



            # send state on, off, on, off. expect nothing
            # send state on, wait for trigger, off. Expect controller update, timer cleared
            monitor.set_value(path, '/State', ON_STATE)
            timer_provider.tick()
            _check_all_not_called()  

            monitor.set_value(path, '/State', OFF_STATE)
            timer_provider.tick()
            _check_all_not_called()  

            monitor.set_value(path, '/State', ON_STATE)
            timer_provider.tick()
            _check_all_not_called()  

            monitor.set_value(path, '/State', OFF_STATE)
            timer_provider.tick()
            _check_all_not_called()  

            _4ticks()
            _check_all_not_called()



            monitor.set_value(path, '/State', ON_STATE)

            timer_provider.tick()
            _check_all_not_called()  

            timer_provider.tick()
            _check_all_not_called()

            called_check()

            _check_all_not_called()
            _4ticks()
            _check_all_not_called()

            # send state on, off, on, wait for trigger, off. Expect controller update, timer cleared


        def _check_input_01():
            timer_provider.tick()
            controller.trigger_anchor_up.assert_called()
            controller.trigger_anchor_up.reset_mock()

        check_sequence('com.victronenergy.digitalinput.input01', _check_input_01)

        def _check_input_02():
            timer_provider.tick()
            controller.trigger_anchor_down.assert_called()
            controller.trigger_anchor_down.reset_mock()

        check_sequence('com.victronenergy.digitalinput.input02', _check_input_02)
        
        def _check_input_04():
            timer_provider.tick()
            controller.trigger_mute_alarm.assert_called()
            controller.trigger_mute_alarm.reset_mock()

        check_sequence('com.victronenergy.digitalinput.input04', _check_input_04)


        def _check_input_mooring():
            timer_provider.tick()
            controller.trigger_mooring_mode.assert_called()
            controller.trigger_mooring_mode.reset_mock()

        connector._settings['MuteAlarmDigitalInputNumber'] = 0
        connector._settings['MooringModeDigitalInputNumber'] = 4

        check_sequence('com.victronenergy.digitalinput.input04', _check_input_mooring)

        # TODO XXX : check mute Alarm
        state3 = AnchorAlarmState('ALARM_DRAGGING', 'boat outside radius', "short message",'emergency', False, {'drop_point': GPSPosition(10, 11), 'radius': 12, 'current_radius': 7, 'radius_tolerance': 15, 'alarm_muted_count': 0, 'no_gps_count': 0, 'out_of_radius_count': 1})
        connector.on_state_changed(state3)

        self.assertEqual(service['/Alarm/State'], state3.state)
        self.assertEqual(service['/Alarm/Message'], state3.message)
        self.assertEqual(service['/Alarm/Level'], state3.level)
        self.assertEqual(service['/Alarm/Muted'], state3.muted)
        self.assertEqual(service['/Alarm/Alarm'], True)
        self.assertEqual(service['/Alarm/MutedDuration'], 0)
        self.assertEqual(service['/Alarm/NoGPSDuration'], 0)
        self.assertEqual(service['/Alarm/OutOfRadiusDuration'], 1)

        self.assertEqual(service['/Anchor/Latitude'], state3.params['drop_point'].latitude)
        self.assertEqual(service['/Anchor/Longitude'], state3.params['drop_point'].longitude)
        self.assertEqual(service['/Anchor/Radius'], state3.params['radius'])
        self.assertEqual(service['/Anchor/Distance'], state3.params['current_radius'])
        self.assertEqual(service['/Anchor/Tolerance'], state3.params['radius_tolerance'])

        state4 = AnchorAlarmState('ALARM_DRAGGING_MUTED', 'boat outside radius', "short message",'emergency', True, {'drop_point': GPSPosition(10, 11), 'radius': 12, 'current_radius': 7, 'radius_tolerance': 15, 'alarm_muted_count': 1, 'no_gps_count': 0, 'out_of_radius_count': 1})
        connector.on_state_changed(state4)

        self.assertEqual(service['/Alarm/State'], state4.state)
        self.assertEqual(service['/Alarm/Message'], state4.message)
        self.assertEqual(service['/Alarm/Level'], state4.level)
        self.assertEqual(service['/Alarm/Muted'], state4.muted)
        
        self.assertEqual(service['/Alarm/Alarm'], True)
        self.assertEqual(service['/Alarm/MutedDuration'], 1)
        self.assertEqual(service['/Alarm/NoGPSDuration'], 0)
        self.assertEqual(service['/Alarm/OutOfRadiusDuration'], 1)

        self.assertEqual(service['/Anchor/Latitude'], state4.params['drop_point'].latitude)
        self.assertEqual(service['/Anchor/Longitude'], state4.params['drop_point'].longitude)
        self.assertEqual(service['/Anchor/Radius'], state4.params['radius'])
        self.assertEqual(service['/Anchor/Distance'], state4.params['current_radius'])
        self.assertEqual(service['/Anchor/Tolerance'], state4.params['radius_tolerance'])



    def test_mingled_up_down_out_calls(self):
        # TODO XXX : should not happen in a normal setup but check anchor_up ON_STATE while anchod_down ON_STATE
        pass


    def test_dbus_triggers(self):
        # set 1 in Triggers/AnchorDown, make sure it's called, etc

        controller = MagicMock()
        controller.trigger_anchor_down  = MagicMock()
        controller.trigger_anchor_up    = MagicMock()
        controller.trigger_chain_out    = MagicMock()
        controller.trigger_mute_alarm   = MagicMock()
        controller.trigger_mooring_mode = MagicMock()
        controller.trigger_decrease_tolerance   = MagicMock()
        controller.trigger_increase_tolerance   = MagicMock()

        mock_bridge = MagicMock()
        mock_bridge.add_pgn_handler = MagicMock()
        mock_bridge.send_nmea = MagicMock()


        connector = MockDBusConnector(lambda: timer_provider, lambda settings, cb: MockSettingsDevice(settings, cb), mock_bridge, create_mock_dbus_service())
        connector.set_controller(controller)

        monitor = connector.mock_monitor()
        monitor.add_service('com.victronenergy.digitalinput.input01',
			values={
				'/ProductName': "qwe",
				'/CustomName': "qwe",
                '/State': 1,
                '/DeviceInstance': 0
			})

        service = connector.mock_service()

        def _check_all_not_called():
            controller.trigger_anchor_down.assert_not_called()
            controller.trigger_anchor_up.assert_not_called()
            controller.trigger_anchor_chain_out.assert_not_called()
            controller.trigger_mute_alarm.assert_not_called()
            controller.trigger_mooring_mode.assert_not_called()
            controller.trigger_decrease_tolerance.assert_not_called()
            controller.trigger_increase_tolerance.assert_not_called()

        _check_all_not_called()

        service.set_value('/Triggers/AnchorDown', '1')
        controller.trigger_anchor_down.assert_called_once()
        controller.trigger_anchor_down.reset_mock()
        _check_all_not_called()

        # check calling twice in a row
        service.set_value('/Triggers/AnchorDown', '1')
        controller.trigger_anchor_down.assert_called_once()
        controller.trigger_anchor_down.reset_mock()
        _check_all_not_called()


        service.set_value('/Triggers/AnchorUp', '1')
        controller.trigger_anchor_up.assert_called_once()
        controller.trigger_anchor_up.reset_mock()
        _check_all_not_called()


        service.set_value('/Triggers/ChainOut', '1')
        controller.trigger_chain_out.assert_called_once()
        controller.trigger_chain_out.reset_mock()
        _check_all_not_called()


        service.set_value('/Triggers/MuteAlarm', '1')
        controller.trigger_mute_alarm.assert_called_once()
        controller.trigger_mute_alarm.reset_mock()
        _check_all_not_called()

        service.set_value('/Triggers/MooringMode', '1')
        controller.trigger_mooring_mode.assert_called_once()
        controller.trigger_mooring_mode.reset_mock()
        _check_all_not_called()


        service.set_value('/Triggers/DecreaseTolerance', '1')
        controller.trigger_decrease_tolerance.assert_called_once()
        controller.trigger_decrease_tolerance.reset_mock()
        _check_all_not_called()

        service.set_value('/Triggers/IncreaseTolerance', '1')
        controller.trigger_increase_tolerance.assert_called_once()
        controller.trigger_increase_tolerance.reset_mock()
        _check_all_not_called()


    def test_show_message_on_feedback_digital_input(self):
        controller = MagicMock()
        controller.trigger_anchor_down  = MagicMock()
        controller.trigger_anchor_up    = MagicMock()
        controller.trigger_chain_out    = MagicMock()
        controller.trigger_mute_alarm   = MagicMock()

        mock_bridge = MagicMock()
        mock_bridge.add_pgn_handler = MagicMock()
        mock_bridge.send_nmea = MagicMock()

        connector = MockDBusConnector(lambda: timer_provider, lambda settings, cb: MockSettingsDevice(settings, cb), mock_bridge, create_mock_dbus_service())
        connector.set_controller(controller)
        connector._system_name_error_duration = 5000

        monitor = connector.mock_monitor()
        monitor.add_service('com.victronenergy.digitalinput.input01',
			values={
				'/ProductName': "qwe",
				'/CustomName': "qwe",
                '/DeviceInstance': 0
			})
        
        monitor.add_service('com.victronenergy.settings',
			values={
                '/Settings/DigitalInput/1/AlarmSetting': 0,
                '/Settings/DigitalInput/1/InvertAlarm': 0,
                '/Settings/SystemSetup/SystemName': 'system name'
			})
        
        monitor.add_service('com.victronenergy.platform',
			values={
                '/Notifications/Alarm': 0
			})

        # dbus doesn't show info messages
        connector.show_message("info", "something")
        self.assertEqual(monitor.get_value("com.victronenergy.settings", '/Settings/DigitalInput/1/AlarmSetting'), False)
        self.assertEqual(monitor.get_value("com.victronenergy.settings", '/Settings/DigitalInput/1/InvertAlarm'), False)
        self.assertEqual(monitor.get_value("com.victronenergy.settings", '/Settings/SystemSetup/SystemName'), 'system name')



        message = "something terrible happened"
        connector.show_message("error", message)

        self.assertEqual(monitor.get_value('com.victronenergy.digitalinput.input01', '/CustomName'), message)
        self.assertEqual(monitor.get_value('com.victronenergy.digitalinput.input01', '/ProductName'), message)
        self.assertEqual(monitor.get_value("com.victronenergy.settings", '/Settings/DigitalInput/1/AlarmSetting'), True)
        self.assertEqual(monitor.get_value("com.victronenergy.settings", '/Settings/DigitalInput/1/InvertAlarm'), True)





    def test_show_message_on_nonexistent_feedback_digital_input(self):
        controller = MagicMock()
        controller.trigger_anchor_down  = MagicMock()
        controller.trigger_anchor_up    = MagicMock()
        controller.trigger_chain_out    = MagicMock()
        controller.trigger_mute_alarm   = MagicMock()

        mock_bridge = MagicMock()
        mock_bridge.add_pgn_handler = MagicMock()
        mock_bridge.send_nmea = MagicMock()

        connector = MockDBusConnector(lambda: timer_provider, lambda settings, cb: MockSettingsDevice(settings, cb), mock_bridge, create_mock_dbus_service())
        connector.set_controller(controller)
        connector._system_name_error_duration = 5000

        monitor = connector.mock_monitor()
        monitor.add_service('com.victronenergy.digitalinput.input01',
			values={
				'/ProductName': "qwe",
				'/CustomName': "qwe",
                '/DeviceInstance': 0
			})
        
        monitor.add_service('com.victronenergy.settings',
			values={
                '/Settings/DigitalInput/1/AlarmSetting': 0,
                '/Settings/DigitalInput/1/InvertAlarm': 0,
                '/Settings/SystemSetup/SystemName': 'system name'
			})
        
        monitor.add_service('com.victronenergy.platform',
			values={
                '/Notifications/Alarm': 0
			})
        connector._settings['FeedbackDigitalInputNumber'] = 4

        # dbus doesn't show info messages
        connector.show_message("info", "something")
        self.assertEqual(monitor.get_value("com.victronenergy.settings", '/Settings/DigitalInput/1/AlarmSetting'), False)
        self.assertEqual(monitor.get_value("com.victronenergy.settings", '/Settings/DigitalInput/1/InvertAlarm'), False)
        self.assertEqual(monitor.get_value("com.victronenergy.settings", '/Settings/SystemSetup/SystemName'), 'system name')



        message = "something terrible happened"
        connector.show_message("error", message)

        self.assertEqual(monitor.get_value('com.victronenergy.digitalinput.input01', '/CustomName'), "qwe")
        self.assertEqual(monitor.get_value('com.victronenergy.digitalinput.input01', '/ProductName'), "qwe")
        self.assertEqual(monitor.get_value("com.victronenergy.settings", '/Settings/DigitalInput/1/AlarmSetting'), False)
        self.assertEqual(monitor.get_value("com.victronenergy.settings", '/Settings/DigitalInput/1/InvertAlarm'), False)

        self.assertEqual(monitor.get_value("com.victronenergy.settings", '/Settings/SystemSetup/SystemName'), message)
        timer_provider.tick()
        timer_provider.tick()
        self.assertEqual(monitor.get_value("com.victronenergy.settings", '/Settings/SystemSetup/SystemName'), message)
        timer_provider.tick()
        timer_provider.tick()
        timer_provider.tick()
        self.assertEqual(monitor.get_value("com.victronenergy.settings", '/Settings/SystemSetup/SystemName'), 'system name')


    def test_show_message_on_system_name(self):
        controller = MagicMock()
        controller.trigger_anchor_down  = MagicMock()
        controller.trigger_anchor_up    = MagicMock()
        controller.trigger_chain_out    = MagicMock()
        controller.trigger_mute_alarm   = MagicMock()

        mock_bridge = MagicMock()
        mock_bridge.add_pgn_handler = MagicMock()
        mock_bridge.send_nmea = MagicMock()

        connector = MockDBusConnector(lambda: timer_provider, lambda settings, cb: MockSettingsDevice(settings, cb), mock_bridge, create_mock_dbus_service())
        connector.set_controller(controller)
        connector._system_name_error_duration = 5000

        monitor = connector.mock_monitor()
        monitor.add_service('com.victronenergy.digitalinput.input01',
			values={
				'/ProductName': "qwe",
				'/CustomName': "qwe",
                '/DeviceInstance': 0
			})
        
        monitor.add_service('com.victronenergy.settings',
			values={
                '/Settings/DigitalInput/1/AlarmSetting': 0,
                '/Settings/DigitalInput/1/InvertAlarm': 0,
                '/Settings/SystemSetup/SystemName': 'system name'
			})
        
        monitor.add_service('com.victronenergy.platform',
			values={
                '/Notifications/Alarm': 0
			})
        
        connector._settings['FeedbackDigitalInputNumber'] = 0


        # dbus doesn't show info messages
        connector.show_message("info", "something")
        self.assertEqual(monitor.get_value("com.victronenergy.settings", '/Settings/DigitalInput/1/AlarmSetting'), False)
        self.assertEqual(monitor.get_value("com.victronenergy.settings", '/Settings/DigitalInput/1/InvertAlarm'), False)
        self.assertEqual(monitor.get_value("com.victronenergy.settings", '/Settings/SystemSetup/SystemName'), 'system name')



        message = "something terrible happened"
        connector.show_message("error", message)

        self.assertEqual(monitor.get_value('com.victronenergy.digitalinput.input01', '/CustomName'), "qwe")
        self.assertEqual(monitor.get_value('com.victronenergy.digitalinput.input01', '/ProductName'), "qwe")
        self.assertEqual(monitor.get_value("com.victronenergy.settings", '/Settings/DigitalInput/1/AlarmSetting'), False)
        self.assertEqual(monitor.get_value("com.victronenergy.settings", '/Settings/DigitalInput/1/InvertAlarm'), False)

        self.assertEqual(monitor.get_value("com.victronenergy.settings", '/Settings/SystemSetup/SystemName'), message)
        timer_provider.tick()
        timer_provider.tick()
        self.assertEqual(monitor.get_value("com.victronenergy.settings", '/Settings/SystemSetup/SystemName'), message)
        timer_provider.tick()
        timer_provider.tick()
        timer_provider.tick()
        self.assertEqual(monitor.get_value("com.victronenergy.settings", '/Settings/SystemSetup/SystemName'), 'system name')




        # test multiple errors during timer
        message2 = "something terrible happened again"

        connector.show_message("error", message)

        self.assertEqual(monitor.get_value("com.victronenergy.settings", '/Settings/SystemSetup/SystemName'), message)
        timer_provider.tick()
        self.assertEqual(monitor.get_value("com.victronenergy.settings", '/Settings/SystemSetup/SystemName'), message)
        timer_provider.tick()

        connector.show_message("error", message2)
        self.assertEqual(monitor.get_value("com.victronenergy.settings", '/Settings/SystemSetup/SystemName'), message2)
        timer_provider.tick()
        timer_provider.tick()
        self.assertEqual(monitor.get_value("com.victronenergy.settings", '/Settings/SystemSetup/SystemName'), message2)
        timer_provider.tick()
        timer_provider.tick()
        timer_provider.tick()
        self.assertEqual(monitor.get_value("com.victronenergy.settings", '/Settings/SystemSetup/SystemName'), 'system name')


    def test_ais_vessel_integration(self):
        """Test AIS vessel tracking integration with DBus connector"""
        controller = MagicMock()
        controller.get_gps_position = MagicMock(return_value=GPSPosition(14.0829979, -60.9595577))

        mock_bridge = MagicMock()
        mock_bridge.add_pgn_handler = MagicMock()
        mock_bridge.send_nmea = MagicMock()

        connector = MockDBusConnector(lambda: timer_provider, lambda settings, cb: MockSettingsDevice(settings, cb), mock_bridge, create_mock_dbus_service())
        connector.set_controller(controller)
        
        # Increase distance limit to allow test vessel (distance ~1369m)
        connector._settings['DistanceToVessel'] = 2000

        service = connector.mock_service()
        
        # Test AIS message processing
        ais_message = {
            "fields": {
                "User ID": 368081510,
                "Longitude": -60.9494,
                "Latitude": 14.0756,
                "COG": 1.7698,
                "SOG": 5.2
            }
        }
        
        # Process AIS message
        connector._on_ais_message(ais_message)
        
        # Call update_state to update DBus paths (this is normally called by timer)
        from anchor_alarm_model import AnchorAlarmState
        mock_state = AnchorAlarmState('IN_RADIUS', 'boat in radius', "short in radius message", 'info', False, {'drop_point': GPSPosition(10, 11), 'radius': 12, 'current_radius':5, 'radius_tolerance': 15, 'alarm_muted_count': 0, 'no_gps_count': 0, 'out_of_radius_count': 0})
        connector.update_state(mock_state)
        
        # Verify vessel was created and paths exist
        mmsi = "368081510"
        self.assertTrue(f'/Vessels/{mmsi}/Latitude' in service)
        self.assertTrue(f'/Vessels/{mmsi}/Longitude' in service)
        self.assertTrue(f'/Vessels/{mmsi}/SOG' in service)
        self.assertTrue(f'/Vessels/{mmsi}/COG' in service)
        self.assertTrue(f'/Vessels/{mmsi}/Tracks' in service)
        
        # Verify vessel data in service
        self.assertEqual(service[f'/Vessels/{mmsi}/Latitude'], 14.0756)
        self.assertEqual(service[f'/Vessels/{mmsi}/Longitude'], -60.9494)
        self.assertEqual(service[f'/Vessels/{mmsi}/SOG'], 5.2)


    def test_vessel_dbus_path_management(self):
        """Test vessel DBus path creation and removal"""
        controller = MagicMock()
        controller.get_gps_position = MagicMock(return_value=GPSPosition(14.0829979, -60.9595577))

        mock_bridge = MagicMock()
        mock_bridge.add_pgn_handler = MagicMock()
        mock_bridge.send_nmea = MagicMock()

        connector = MockDBusConnector(lambda: timer_provider, lambda settings, cb: MockSettingsDevice(settings, cb), mock_bridge, create_mock_dbus_service())
        connector.set_controller(controller)

        service = connector.mock_service()
        mmsi = "123456789"
        
        # Create vessel
        vessel = connector._create_vessel(mmsi)
        
        # Verify all expected paths exist
        expected_paths = [
            f'/Vessels/{mmsi}/Latitude',
            f'/Vessels/{mmsi}/Longitude', 
            f'/Vessels/{mmsi}/SOG',
            f'/Vessels/{mmsi}/COG',
            f'/Vessels/{mmsi}/Heading',
            f'/Vessels/{mmsi}/Tracks'
        ]
        
        for path in expected_paths:
            self.assertTrue(path in service, f"Path {path} should exist")
        
        # Remove vessel
        connector._remove_vessel(mmsi)
        
        # Verify all paths are removed
        for path in expected_paths:
            self.assertFalse(path in service, f"Path {path} should be removed")


    def test_vessel_pruning_timer_integration(self):
        """Test vessel pruning integration with timer system"""
        controller = MagicMock()
        controller.get_gps_position = MagicMock(return_value=GPSPosition(14.0829979, -60.9595577))

        mock_bridge = MagicMock()
        mock_bridge.add_pgn_handler = MagicMock()
        mock_bridge.send_nmea = MagicMock()

        connector = MockDBusConnector(lambda: timer_provider, lambda settings, cb: MockSettingsDevice(settings, cb), mock_bridge, create_mock_dbus_service())
        connector.set_controller(controller)

        # Set short prune interval for testing
        connector._settings['PruneInterval'] = 1  # 1 second
        
        # Create vessel
        mmsi = "123456789"
        vessel = connector._create_vessel(mmsi)
        vessel['distance'] = 100  # Within distance limit
        
        # Add old track
        vessel['tracks'].append({
            'latitude': 14.0756,
            'longitude': -60.9494,
            'timestamp': int(time.time()) - 10  # 10 seconds ago
        })
        
        # Verify vessel exists
        self.assertIn(mmsi, connector._vessels)
        
        # Prune vessels (should remove due to old track)
        connector._prune_vessels()
        
        # Vessel should be removed
        self.assertNotIn(mmsi, connector._vessels)


if __name__ == '__main__':
    unittest.main()