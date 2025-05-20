import sys
import os
sys.path.insert(1, os.path.join(sys.path[0], '..'))

from anchor_alarm_controller import AnchorAlarmController
from anchor_alarm_model import AnchorAlarmConfiguration, AnchorAlarmState
from collections import namedtuple

import unittest
from unittest.mock import ANY
from unittest.mock import MagicMock

# TODO XXX : move that import somewhere
GPSPosition = namedtuple('GPSPosition', ['latitude', 'longitude'])


from glib_timer_mock import GLibTimerMock

sys.path.insert(1, os.path.join(os.path.dirname(__file__), '../ext/velib_python/test'))
from mock_settings_device import MockSettingsDevice


timer_provider = GLibTimerMock()

class TestAnchorAlarmController(unittest.TestCase):

    def setUp(self):
        self.maxDiff = None

        self.gps_position_anchor_down    = GPSPosition(18.5060715, -64.3725071)
        self.gps_position_16m            = GPSPosition(18.506100, -64.372655) 
        self.gps_position_21m            = GPSPosition(18.506105, -64.372700)

    def test_configuration_updated(self):
        gps_provider = MagicMock()
        gps_provider.get_gps_position = MagicMock(return_value=None)

        controller = AnchorAlarmController(lambda: timer_provider, MockSettingsDevice, gps_provider)
        model_mock =  MagicMock()
        model_mock.update_configuration = MagicMock()
        controller._anchor_alarm = model_mock

        controller._settings['Tolerance'] = 99
        model_mock.update_configuration.assert_called()


    def test_exceptions_catched(self):
        gps_provider = MagicMock()
        gps_provider.get_gps_position = MagicMock(return_value=None)

        controller = AnchorAlarmController(lambda: timer_provider, MockSettingsDevice, gps_provider)

        gps_provider.get_gps_position = MagicMock(return_value=None)
        self.assertIsInstance(controller.trigger_anchor_down(), RuntimeError)

        gps_provider.get_gps_position = MagicMock(return_value="qwe")
        self.assertIsInstance(controller.trigger_anchor_down(), TypeError)

        # give some position to change state
        gps_provider.get_gps_position = MagicMock(return_value=GPSPosition(0,0))
        controller.trigger_anchor_down()

        gps_provider.get_gps_position = MagicMock(return_value=None)
        self.assertIsInstance(controller.trigger_chain_out(), RuntimeError)

        # give some position to change state
        gps_provider.get_gps_position = MagicMock(return_value=GPSPosition(0,0))
        controller.trigger_anchor_down()

        gps_provider.get_gps_position = MagicMock(return_value="qwe")
        self.assertIsInstance(controller.trigger_chain_out(), TypeError)

    def test_save_state(self):
        gps_provider = MagicMock()
        gps_provider.get_gps_position = MagicMock(return_value=None)

        controller = AnchorAlarmController(lambda: timer_provider, MockSettingsDevice, gps_provider)
        self.assertEqual(controller._settings['Latitude'],  0)
        self.assertEqual(controller._settings['Longitude'], 0)
        self.assertEqual(controller._settings['Radius'],    0)
        self.assertEqual(controller._settings['Active'],    0)

        state_drop_point_set = AnchorAlarmState('DROP_POINT_SET', 'Drop point set, please do blablala', "short message", 'info', False, {'drop_point': GPSPosition(10, 11)})
        controller._on_state_changed(state_drop_point_set)
        self.assertEqual(controller._settings['Latitude'],  0)
        self.assertEqual(controller._settings['Longitude'], 0)
        self.assertEqual(controller._settings['Radius'],    0)
        self.assertEqual(controller._settings['Active'],    0)

        state_in_radius = AnchorAlarmState('IN_RADIUS', 'boat in radius', "short message", 'info', False, {'drop_point': GPSPosition(10, 11), 'radius': 12})
        controller._on_state_changed(state_in_radius)
        self.assertEqual(controller._settings['Latitude'],  state_in_radius.params['drop_point'].latitude)
        self.assertEqual(controller._settings['Longitude'], state_in_radius.params['drop_point'].longitude)
        self.assertEqual(controller._settings['Radius'],    state_in_radius.params['radius'])
        self.assertEqual(controller._settings['Active'],    1)

        state_dragging = AnchorAlarmState('ALARM_DRAGGING', 'Anchor dragging !', "short message", 'emergency', False, {'drop_point': GPSPosition(23, 23), 'radius': 23})
        # should keep in_radius values
        controller._on_state_changed(state_dragging)
        self.assertEqual(controller._settings['Latitude'],  state_in_radius.params['drop_point'].latitude)
        self.assertEqual(controller._settings['Longitude'], state_in_radius.params['drop_point'].longitude)
        self.assertEqual(controller._settings['Radius'],    state_in_radius.params['radius'])
        self.assertEqual(controller._settings['Active'],    1)

        # TODO XXX : test that if we call set_radius after dragging the radius is updated
        state_disabled = AnchorAlarmState('DISABLED', 'Anchor alarm disabled', "short message", 'info', False, {})
        controller._on_state_changed(state_disabled)
        self.assertEqual(controller._settings['Latitude'],  state_in_radius.params['drop_point'].latitude)
        self.assertEqual(controller._settings['Longitude'], state_in_radius.params['drop_point'].longitude)
        self.assertEqual(controller._settings['Radius'],    state_in_radius.params['radius'])
        self.assertEqual(controller._settings['Active'],    0)


    def test_reset_state(self):
        gps_provider = MagicMock()
        gps_provider.get_gps_position = MagicMock(return_value=None)
 
        def _create_settings_inactive(settingsList, onSettingsChanged):
            settings = MockSettingsDevice(settingsList, onSettingsChanged)
            settings['Latitude'] = 10
            settings['Longitude'] = 11
            settings['Radius'] = 20
            settings['Active'] = 0
            return settings

        controller = AnchorAlarmController(lambda: timer_provider, _create_settings_inactive, gps_provider)
        self.assertEqual(controller._settings['Latitude'],  10)
        self.assertEqual(controller._settings['Longitude'], 11)
        self.assertEqual(controller._settings['Radius'],    20)
        self.assertEqual(controller._settings['Active'],    0)

        connector = MagicMock()
        connector.on_state_changed =  MagicMock(return_value=None)
        connector.update_state =  MagicMock(return_value=None)

        mock_state_disabled = AnchorAlarmState('DISABLED', ANY, ANY, ANY, ANY, ANY)

        controller.register_connector(connector)
        connector.on_state_changed.assert_called_with(mock_state_disabled)






        def _create_settings_active(settingsList, onSettingsChanged):
            settings = MockSettingsDevice(settingsList, onSettingsChanged)
            settings['Latitude'] = 10
            settings['Longitude'] = 11
            settings['Radius'] = 20
            settings['Active'] = 1
            return settings

        controller = AnchorAlarmController(lambda: timer_provider, _create_settings_active, gps_provider)
        self.assertEqual(controller._settings['Latitude'],  10)
        self.assertEqual(controller._settings['Longitude'], 11)
        self.assertEqual(controller._settings['Radius'],    20)
        self.assertEqual(controller._settings['Active'],    1)

        connector = MagicMock()
        connector.on_state_changed =  MagicMock(return_value=None)
        connector.update_state =  MagicMock(return_value=None)

        mock_state_in_radius = AnchorAlarmState('IN_RADIUS', ANY, ANY, ANY, ANY, ANY)

        controller.register_connector(connector)
        connector.on_state_changed.assert_called_with(mock_state_in_radius)


        # test that settings change watch is working
        controller._settings['Active'] = 0
        connector.on_state_changed.assert_called_with(mock_state_disabled)

        controller._settings['Active'] = 1
        connector.on_state_changed.assert_called_with(mock_state_in_radius)



    def test_connector_mock(self):
        mock_state_disabled = AnchorAlarmState('DISABLED', ANY, ANY, ANY, ANY, ANY)
        mock_state_drop_point_set = AnchorAlarmState('DROP_POINT_SET', ANY, ANY, ANY, ANY, ANY)
        mock_state_in_radius = AnchorAlarmState('IN_RADIUS', ANY, ANY, ANY, ANY, ANY)

        gps_provider = MagicMock()
        gps_provider.get_gps_position = MagicMock(return_value=None)

        connector = MagicMock()
        connector.on_state_changed =  MagicMock(return_value=None)
        connector.update_state =  MagicMock(return_value=None)

        connector2 = MagicMock()
        connector2.on_state_changed =  MagicMock(return_value=None)
        connector2.update_state =  MagicMock(return_value=None)

    
        controller = AnchorAlarmController(lambda: timer_provider, MockSettingsDevice, gps_provider)

        controller.register_connector(connector)
        connector.on_state_changed.assert_called_with(mock_state_disabled)

        controller.register_connector(connector2)
        connector2.on_state_changed.assert_called_with(mock_state_disabled)

        gps_provider.get_gps_position = MagicMock(return_value=self.gps_position_anchor_down)
        controller.trigger_anchor_down()
        connector.on_state_changed.assert_called_with(mock_state_drop_point_set)
        connector2.on_state_changed.assert_called_with(mock_state_drop_point_set)
        connector.reset_mock()
        connector2.reset_mock()


        gps_provider.get_gps_position = MagicMock(return_value=self.gps_position_16m)
        controller.trigger_chain_out()
        connector.on_state_changed.assert_called_with(mock_state_in_radius)
        connector2.on_state_changed.assert_called_with(mock_state_in_radius)

        timer_provider.tick()
        connector.update_state.assert_called_with(mock_state_in_radius)
        connector2.update_state.assert_called_with(mock_state_in_radius)
        connector.reset_mock()
        connector2.reset_mock()

        timer_provider.tick()
        connector.update_state.assert_called_with(mock_state_in_radius)
        connector2.update_state.assert_called_with(mock_state_in_radius)
        connector.reset_mock()
        connector2.reset_mock()


        controller.trigger_anchor_up()
        connector.on_state_changed.assert_called_with(mock_state_disabled)
        connector2.on_state_changed.assert_called_with(mock_state_disabled)

        connector.update_state.assert_not_called()
        connector2.update_state.assert_not_called()



if __name__ == '__main__':
    unittest.main()