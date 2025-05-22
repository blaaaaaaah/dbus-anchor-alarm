import sys
import os
from unittest import mock

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

sys.path.insert(1, os.path.join(sys.path[0], '../connectors'))

from nmea_ds_connector import NMEADSConnector
          
timer_provider = GLibTimerMock()


# TODO XXX : move that import somewhere
from collections import namedtuple
GPSPosition = namedtuple('GPSPosition', ['latitude', 'longitude'])





class TestNMEADSConnector(unittest.TestCase):

    def setUp(self):
        self.maxDiff = None
        self._ADDRESS = 67

    

    def test_ds_changes(self):
        mock_bridge = MagicMock()
        
        handler = None
        def _set_handler(pgn, the_handler):
            nonlocal handler
            handler = the_handler

        mock_bridge.add_pgn_handler = MagicMock(side_effect=_set_handler)              
        mock_bridge.send_nmea = MagicMock()


        connector = NMEADSConnector(lambda: timer_provider, MockSettingsDevice,  mock_bridge)
        #connector._settings['AutoAcknowledgeInterval'] = 3

        controller = MagicMock()
        controller.trigger_anchor_down     = MagicMock()
        controller.trigger_chain_out       = MagicMock()
        controller.trigger_anchor_up       = MagicMock()
        controller.trigger_mute_alarm      = MagicMock()

        connector.set_controller(controller)

        ds_anchor_down = {
            "pgn":127502,
            "fields": {
                "Instance":221,
                "Switch1":"On",
            },
            "description":"Switch Bank Control"
        }
        handler(ds_anchor_down)
        controller.trigger_anchor_down.assert_called_once()

        ds_set_radius = {
            "pgn":127502,
            "fields": {
                "Instance":221,
                "Switch2":"On",
            },
            "description":"Switch Bank Control"
        }
        handler(ds_set_radius)
        controller.trigger_chain_out.assert_called_once()


        ds_anchor_up = {
            "pgn":127502,
            "fields": {
                "Instance":221,
                "Switch3":"On",
            },
            "description":"Switch Bank Control"
        }
        handler(ds_anchor_up)
        controller.trigger_anchor_up.assert_called_once()


        ds_mute_alarm = {
            "pgn":127502,
            "fields": {
                "Instance":221,
                "Switch4":"On",
            },
            "description":"Switch Bank Control"
        }
        handler(ds_mute_alarm)
        controller.trigger_mute_alarm.assert_called_once()
        
                
    def test_advertised_status(self):
        mock_bridge = MagicMock()
        handler = None
        def _set_handler(pgn, the_handler):
            nonlocal handler
            handler = the_handler

        mock_bridge.add_pgn_handler = MagicMock(side_effect=_set_handler)        
        mock_bridge.send_nmea = MagicMock()


        connector = NMEADSConnector(lambda: timer_provider, MockSettingsDevice,  mock_bridge)
        #connector._settings['AutoAcknowledgeInterval'] = 3

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


        ds_all_off = {
            "pgn":127501,
            "fields": {
                "Instance":221,
                "Indicator1":"Off",
                "Indicator2":"Off",
                "Indicator3":"Off",
                "Indicator4":"Off",
            },
            "description":"Binary Switch Bank Status"
        }

        ds_1 = {
            "pgn":127501,
            "fields": {
                "Instance":221,
                "Indicator1":"On",
                "Indicator2":"Off",
                "Indicator3":"Off",
                "Indicator4":"Off",
            },
            "description":"Binary Switch Bank Status"
        }

        ds_2 = {
            "pgn":127501,
            "fields": {
                "Instance":221,
                "Indicator1":"Off",
                "Indicator2":"On",
                "Indicator3":"Off",
                "Indicator4":"Off",
            },
            "description":"Binary Switch Bank Status"
        }

        ds_3 = {
            "pgn":127501,
            "fields": {
                "Instance":221,
                "Indicator1":"Off",
                "Indicator2":"Off",
                "Indicator3":"On",
                "Indicator4":"Off",
            },
            "description":"Binary Switch Bank Status"
        }

        ds_4 = {
            "pgn":127501,
            "fields": {
                "Instance":221,
                "Indicator1":"Off",
                "Indicator2":"Off",
                "Indicator3":"Off",
                "Indicator4":"On",
            },
            "description":"Binary Switch Bank Status"
        }


        #connector.on_state_changed(state_disabled)
        mock_bridge.send_nmea.assert_has_calls([])
        timer_provider.tick()
        mock_bridge.send_nmea.assert_has_calls([])
        timer_provider.tick()
        mock_bridge.send_nmea.assert_has_calls([call(ds_all_off)])
        timer_provider.tick()
        mock_bridge.send_nmea.assert_has_calls([call(ds_all_off)])
        timer_provider.tick()
        mock_bridge.send_nmea.assert_has_calls([call(ds_all_off), call(ds_all_off)])

        connector.on_state_changed(state_disabled)
        mock_bridge.send_nmea.assert_has_calls([call(ds_all_off), call(ds_all_off), call(ds_3)])
        timer_provider.tick()
        mock_bridge.send_nmea.assert_has_calls([call(ds_all_off), call(ds_all_off), call(ds_3)])
        timer_provider.tick()
        mock_bridge.send_nmea.assert_has_calls([call(ds_all_off), call(ds_all_off), call(ds_3), call(ds_all_off)])

        timer_provider.tick()
        connector.on_state_changed(state_drop_point_set)
        mock_bridge.send_nmea.assert_has_calls([call(ds_all_off), call(ds_all_off), call(ds_3), call(ds_all_off),
                                                call(ds_1)
                                                ])
        timer_provider.tick()
        mock_bridge.send_nmea.assert_has_calls([call(ds_all_off), call(ds_all_off), call(ds_3), call(ds_all_off),
                                                call(ds_1), call(ds_all_off)
                                                ])
        timer_provider.tick()
        mock_bridge.send_nmea.assert_has_calls([call(ds_all_off), call(ds_all_off), call(ds_3), call(ds_all_off),
                                                call(ds_1), call(ds_all_off)
                                                ])
        
        timer_provider.tick()
        mock_bridge.send_nmea.assert_has_calls([call(ds_all_off), call(ds_all_off), call(ds_3), call(ds_all_off),
                                                call(ds_1), call(ds_all_off), call(ds_all_off), 
                                                ])

        connector.on_state_changed(state_in_radius)
        timer_provider.tick()
        mock_bridge.send_nmea.assert_has_calls([call(ds_all_off), call(ds_all_off), call(ds_3), call(ds_all_off),
                                                call(ds_1), call(ds_all_off), call(ds_all_off), 
                                                call(ds_2), 
                                                ])
        
        connector.on_state_changed(state_dragging)
        mock_bridge.send_nmea.assert_has_calls([call(ds_all_off), call(ds_all_off), call(ds_3), call(ds_all_off),
                                                call(ds_1), call(ds_all_off), call(ds_all_off), 
                                                call(ds_2),
                                                ])
        timer_provider.tick()
        mock_bridge.send_nmea.assert_has_calls([call(ds_all_off), call(ds_all_off), call(ds_3), call(ds_all_off),
                                                call(ds_1), call(ds_all_off), call(ds_all_off), 
                                                call(ds_2),
                                                call(ds_all_off)
                                                ])
        
        connector.on_state_changed(state_dragging_muted)
        mock_bridge.send_nmea.assert_has_calls([call(ds_all_off), call(ds_all_off), call(ds_3), call(ds_all_off),
                                                call(ds_1), call(ds_all_off), call(ds_all_off), 
                                                call(ds_2),
                                                call(ds_all_off),
                                                call(ds_4)
                                                ])
        timer_provider.tick()
        mock_bridge.send_nmea.assert_has_calls([call(ds_all_off), call(ds_all_off), call(ds_3), call(ds_all_off),
                                                call(ds_1), call(ds_all_off), call(ds_all_off), 
                                                call(ds_2),
                                                call(ds_all_off),
                                                call(ds_4)
                                                ])
        timer_provider.tick()
        mock_bridge.send_nmea.assert_has_calls([call(ds_all_off), call(ds_all_off), call(ds_3), call(ds_all_off),
                                                call(ds_1), call(ds_all_off), call(ds_all_off), 
                                                call(ds_2),
                                                call(ds_all_off),
                                                call(ds_4),
                                                call(ds_all_off),
                                                ])


if __name__ == '__main__':
    unittest.main()