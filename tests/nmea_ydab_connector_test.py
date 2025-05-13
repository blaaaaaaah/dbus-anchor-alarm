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

from nmea_ydab_connector import NMEAYDABConnector
          
timer_provider = GLibTimerMock()








class TestNMEAAlertConnector(unittest.TestCase):

    def setUp(self):
        self.maxDiff = None
        self._ADDRESS = 67

        
    def _get_pgn_for_command(self, command):
        return {
            "prio":3,
            "dst": self._ADDRESS,
            "pgn":126208,
            "fields":{
                "Function Code":"Command",
                "PGN":126998,
                "Number of Parameters":1,
                "list":[{
                    "Parameter":2,
                    "Value": command}]
            },
            "description":"NMEA - Command group function"
        }
    

    def test_states(self):
        mock_bridge = MagicMock()
        mock_bridge.add_pgn_handler = MagicMock()
        mock_bridge.send_nmea = MagicMock()


        connector = NMEAYDABConnector(lambda: timer_provider, MockSettingsDevice,  mock_bridge)
        #connector._settings['AutoAcknowledgeInterval'] = 3

        controller = MagicMock()
        controller.trigger_mute_alarm   = MagicMock()
        connector.set_controller(controller)

        # AnchorAlarmState = namedtuple('AnchorAlarmState', ['state', 'message', 'level', 'muted', 'params'])
        state_disabled = AnchorAlarmState('DISABLED', 'Anchor alarm disabled', 'info', False, {})
        led_0 = self._get_pgn_for_command("YD:LED 0")

        state_drop_point_set = AnchorAlarmState('DROP_POINT_SET', 'Drop point set, please do blablala', 'info', False, {'drop_point': {'latitude': 10, 'longitude':11}})
        ds_10 = {
            "pgn":127502,
            "fields": {
                "Instance":222,
                "Switch10":"On",
                "Switch11":"Off",
                "Switch12":"Off",
            },
            "description":"Switch Bank Control"
        }

        state_in_radius = AnchorAlarmState('IN_RADIUS', 'boat in radius', 'info', False, {'drop_point': {'latitude': 10, 'longitude':11}, 'radius': 12})
        led_21 = self._get_pgn_for_command("YD:LED 21")
        ds_all_off = {
            "pgn":127502,
            "fields": {
                "Instance":222,
                "Switch10":"Off",
                "Switch11":"Off",
                "Switch12":"Off",
            },
            "description":"Switch Bank Control"
        }

        state_dragging = AnchorAlarmState('ALARM_DRAGGING', 'Anchor dragging !', 'emergency', False, {'drop_point': {'latitude': 10, 'longitude':11}, 'radius': 12})
        state_no_gps = AnchorAlarmState('ALARM_NO_GPS', 'No GPS', 'emergency', False, {'drop_point': {'latitude': 10, 'longitude':11}, 'radius': 12})
        ds_11 = {
            "pgn":127502,
            "fields": {
                "Instance":222,
                "Switch10":"Off",
                "Switch11":"On",
                "Switch12":"Off",
            },
            "description":"Switch Bank Control"
        }

        state_dragging_muted = AnchorAlarmState('ALARM_DRAGGING_MUTED', 'Anchor dragging ! (muted)', 'emergency', True, {'drop_point': {'latitude': 10, 'longitude':11}, 'radius': 12})
        state_no_gps_muted = AnchorAlarmState('ALARM_NO_GPS_MUTED', 'No GPS (muted)', 'emergency', True, {'drop_point': {'latitude': 10, 'longitude':11}, 'radius': 12})
        ds_12 = {
            "pgn":127502,
            "fields": {
                "Instance":222,
                "Switch10":"Off",
                "Switch11":"Off",
                "Switch12":"On",
            },
            "description":"Switch Bank Control"
        }
        led_0 = self._get_pgn_for_command("YD:LED 0")
        
        connector.on_state_changed(state_disabled)
        mock_bridge.send_nmea.assert_has_calls([call(led_0), call(ds_all_off)])

        connector.on_state_changed(state_drop_point_set)
        mock_bridge.send_nmea.assert_has_calls([call(led_0), call(ds_all_off), call(ds_10)])

        connector.on_state_changed(state_in_radius)
        mock_bridge.send_nmea.assert_has_calls([call(led_0), call(ds_all_off), call(ds_10), call(led_21), call(ds_all_off)])

        connector.on_state_changed(state_dragging)
        mock_bridge.send_nmea.assert_has_calls([call(led_0), call(ds_all_off), call(ds_10), call(led_21), call(ds_all_off), call(ds_11)])

        connector.on_state_changed(state_dragging_muted)
        mock_bridge.send_nmea.assert_has_calls([call(led_0), call(ds_all_off), call(ds_10), call(led_21), call(ds_all_off), call(ds_11), call(ds_12)])

        connector.on_state_changed(state_disabled)
        mock_bridge.send_nmea.assert_has_calls([call(led_0), call(ds_all_off), call(ds_10), call(led_21), call(ds_all_off), call(ds_11), call(ds_12), call(led_0), call(ds_all_off)])

    def test_states_acks(self):
        mock_bridge = MagicMock()
        handler = None
        def _set_handler(pgn, the_handler):
            nonlocal handler
            handler = the_handler

        mock_bridge.add_pgn_handler = MagicMock(side_effect=_set_handler)        
        mock_bridge.send_nmea = MagicMock()


        connector = NMEAYDABConnector(lambda: timer_provider, MockSettingsDevice,  mock_bridge)
        #connector._settings['AutoAcknowledgeInterval'] = 3

        controller = MagicMock()
        controller.trigger_mute_alarm   = MagicMock()
        connector.set_controller(controller)


        pgn_wrong_bank = {
            "canId":233967171,
            "prio":3,
            "src":self._ADDRESS,
            "dst":255,
            "pgn":127502,
            "timestamp":"2025-05-08T04:42:33.723Z",
            "input":["2025-05-08T04:42:33.723Z,3,127502,67,255,8,00,ff,ff,3f,ff,ff,ff,ff"],
            "fields":{
                "Instance":0,
                "Switch12":"Off"
            },
            "description":"Switch Bank Control"
        }


        
        handler(pgn_wrong_bank)
        controller.trigger_chain_out.assert_not_called()
        controller.trigger_mute_alarm.assert_not_called()
        controller.trigger_anchor_down.assert_not_called()
        controller.trigger_anchor_up.assert_not_called()


        pgn_switch_10_off = {
            "canId":233967171,
            "prio":3,
            "src":self._ADDRESS,
            "dst":255,
            "pgn":127502,
            "timestamp":"2025-05-08T04:42:33.723Z",
            "input":["2025-05-08T04:42:33.723Z,3,127502,67,255,8,00,ff,ff,3f,ff,ff,ff,ff"],
            "fields":{
                "Instance":222,
                "Switch10":"Off"
            },
            "description":"Switch Bank Control"
        }

        handler(pgn_switch_10_off)
        controller.trigger_chain_out.assert_called_once()
        controller.trigger_mute_alarm.assert_not_called()
        controller.trigger_anchor_down.assert_not_called()
        controller.trigger_anchor_up.assert_not_called()

        controller.trigger_chain_out.reset_mock()



        pgn_switch_11_off = {
            "canId":233967171,
            "prio":3,
            "src":self._ADDRESS,
            "dst":255,
            "pgn":127502,
            "timestamp":"2025-05-08T04:42:33.723Z",
            "input":["2025-05-08T04:42:33.723Z,3,127502,67,255,8,00,ff,ff,3f,ff,ff,ff,ff"],
            "fields":{
                "Instance":222,
                "Switch11":"Off"
            },
            "description":"Switch Bank Control"
        }

        handler(pgn_switch_11_off)
        controller.trigger_chain_out.assert_not_called()
        controller.trigger_mute_alarm.assert_called_once()
        controller.trigger_anchor_down.assert_not_called()
        controller.trigger_anchor_up.assert_not_called()

        controller.trigger_mute_alarm.reset_mock()

        pgn_switch_12_off = {
            "canId":233967171,
            "prio":3,
            "src":self._ADDRESS,
            "dst":255,
            "pgn":127502,
            "timestamp":"2025-05-08T04:42:33.723Z",
            "input":["2025-05-08T04:42:33.723Z,3,127502,67,255,8,00,ff,ff,3f,ff,ff,ff,ff"],
            "fields":{
                "Instance":222,
                "Switch12":"Off"
            },
            "description":"Switch Bank Control"
        }


        
        handler(pgn_switch_12_off)
        controller.trigger_chain_out.assert_called_once()
        controller.trigger_mute_alarm.assert_not_called()
        controller.trigger_anchor_down.assert_not_called()
        controller.trigger_anchor_up.assert_not_called()

        controller.trigger_chain_out.reset_mock()

    def test_config_changes(self):
        mock_bridge = MagicMock()
        handler = None
        def _set_handler(pgn, the_handler):
            nonlocal handler
            if pgn == 126998:
                handler = the_handler

        mock_bridge.add_pgn_handler = MagicMock(side_effect=_set_handler)        
        mock_bridge.send_nmea = MagicMock()


        connector = NMEAYDABConnector(lambda: timer_provider, MockSettingsDevice,  mock_bridge)

        controller = MagicMock()
        controller.trigger_mute_alarm   = MagicMock()
        connector.set_controller(controller)

        connector._settings['NMEAAddress'] = 99
        connector._settings['AlarmSoundID'] = 9

        expected_commands = [
            "YD:RESET",
            "YD:MODE DS",
            "YD:CHANNEL 0",
            "YD:VOLUME 100",
            "YD:LINK 10 SOUND 0",
            "YD:LINK 10 LED 22",
            "YD:LINK 11 SOUND 9",
            "YD:LINK 11 LED 10",
            "YD:LINK 12 SOUND 0",
            "YD:LINK 12 LED 10",
        ]

        def get_config_call(command):
            return {
                "prio":3,
                "dst": 99,
                "pgn":126208,
                "fields":{
                    "Function Code":"Command",
                    "PGN":126998,
                    "Number of Parameters":1,
                    "list":[{
                        "Parameter":2,
                        "Value": command}]
                },
                "description":"NMEA - Command group function"
            }
        
        def get_ack_call(command) :
            return {
                "prio": 3,
                "dst": 255,
                "src": 99,
                "pgn": 126998,
                "fields": {
                    "Installation Description #2": command + " DONE"
                }
            }

        # trigger new config
        connector._settings['StartConfiguration'] = True

        mock_bridge.send_nmea.assert_called_once_with(get_config_call("YD:RESET"))

        # try to put setting back, should reject
        connector._settings['StartConfiguration'] = False
        self.assertTrue(connector._settings['StartConfiguration'])

        # test command send timeout
        timer_provider.tick()
        self.assertTrue(connector._settings['StartConfiguration'])
        self.assertEqual(len(connector._queued_config_commands), 10)
        timer_provider.tick()
        self.assertFalse(connector._settings['StartConfiguration'])
        self.assertIsNone(connector._queued_config_commands)

        # TODO XXX : test that we had an error feedback ?

        mock_bridge.send_nmea.reset_mock()

        connector._settings['StartConfiguration'] = True
        mock_bridge.send_nmea.assert_has_calls([call(get_config_call("YD:RESET"))])

        timer_provider.tick()
        self.assertTrue(connector._settings['StartConfiguration'])
        self.assertEqual(len(connector._queued_config_commands), 10)

        pgn_wrong_src = {
                "prio": 3,
                "dst": 255,
                "src": 1,
                "pgn": 126998,
                "fields": {
                    "Installation Description #2": "YD_RESET DONE"
                }
            }
        handler(pgn_wrong_src)
        self.assertTrue(connector._settings['StartConfiguration'])
        self.assertEqual(len(connector._queued_config_commands), 10)

        timer_provider.tick()
        self.assertFalse(connector._settings['StartConfiguration'])
        self.assertIsNone(connector._queued_config_commands)

        mock_bridge.send_nmea.reset_mock()
        connector._settings['StartConfiguration'] = True
        mock_bridge.send_nmea.assert_has_calls([call(get_config_call("YD:RESET"))])

        timer_provider.tick()
        self.assertTrue(connector._settings['StartConfiguration'])
        self.assertEqual(len(connector._queued_config_commands), 10)

        pgn_wrong_command = {
                "prio": 3,
                "dst": 255,
                "src": 1,
                "pgn": 126998,
                "fields": {
                    "Installation Description #2": "YD_QWE DONE"
                }
            }
        handler(pgn_wrong_command)
        self.assertTrue(connector._settings['StartConfiguration'])
        self.assertEqual(len(connector._queued_config_commands), 10)

        timer_provider.tick()
        self.assertFalse(connector._settings['StartConfiguration'])
        self.assertIsNone(connector._queued_config_commands)


        mock_bridge.send_nmea.reset_mock()
        connector._settings['StartConfiguration'] = True

        calls = []
        for i, command in enumerate(expected_commands):
            calls.append(call(get_config_call(command)))
            mock_bridge.send_nmea.assert_has_calls(calls)
            timer_provider.tick()
            handler(get_ack_call(command))

            if i < len(expected_commands)-1:
                self.assertTrue(connector._settings['StartConfiguration'])
                self.assertEqual(len(connector._queued_config_commands), len(expected_commands)-1-i)


        calls.append(call(get_config_call("YD:PLAY 6")))
        mock_bridge.send_nmea.assert_has_calls(calls)

        timer_provider.tick()
        
        calls.append(call(get_config_call("YD:PLAY 0")))
        mock_bridge.send_nmea.assert_has_calls(calls)

        self.assertFalse(connector._settings['StartConfiguration'])
        self.assertIsNone(connector._queued_config_commands)





if __name__ == '__main__':
    unittest.main()