import sys
import os

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

# TODO XXX : move that import somewhere
from collections import namedtuple
GPSPosition = namedtuple('GPSPosition', ['latitude', 'longitude'])

sys.path.insert(1, os.path.join(sys.path[0], '../connectors'))

from nmea_alert_connector import NMEAAlertConnector
          
timer_provider = GLibTimerMock()






class TestNMEAAlertConnector(unittest.TestCase):

    def setUp(self):
        self.maxDiff = None

        



    def test_nmea_messages(self):
        mock_bridge = MagicMock()
        mock_bridge.add_pgn_handler = MagicMock()
        mock_bridge.send_nmea = MagicMock()


        connector = NMEAAlertConnector(lambda: timer_provider, MockSettingsDevice,  mock_bridge)
        connector._settings['AutoAcknowledgeInterval'] = 3

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

        

        alert_nmea_message_active = {
            "pgn": 126983,
            "Alert ID": connector._ALERT_ID,
            "Alert Type": "Caution",
            "Alert State": "Active",
            "Alert Category": "Technical",
            "Alert System": 5,
            "Alert Sub-System": 0,
            "Data Source Network ID NAME": connector._ALERT_ID,
            "Data Source Instance": 0,
            "Data Source Index-Source": 0,
            "Alert Occurrence Number": 0,
            "Temporary Silence Status": 0,
            "Acknowledge Status": 0,
            "Escalation Status": 0,
            "Temporary Silence Support": 0,
            "Acknowledge Support": 1,
            "Escalation Support": 0,
            "Trigger Condition": 2,
            "Threshold Status": 1,
            "Alert Priority": 0
        }

        alert_nmea_message_normal = {
            "pgn": 126983,
            "Alert ID": connector._ALERT_ID,
            "Alert Type": "Caution",
            "Alert State": "Normal",
            "Alert Category": "Technical",
            "Alert System": 5,
            "Alert Sub-System": 0,
            "Data Source Network ID NAME": connector._ALERT_ID,
            "Data Source Instance": 0,
            "Data Source Index-Source": 0,
            "Alert Occurrence Number": 0,
            "Temporary Silence Status": 0,
            "Acknowledge Status": 0,
            "Escalation Status": 0,
            "Temporary Silence Support": 0,
            "Acknowledge Support": 1,
            "Escalation Support": 0,
            "Trigger Condition": 2,
            "Threshold Status": 1,
            "Alert Priority": 0
        }

        text_nmea_message = {
            "pgn": 126985,
            "Alert ID": connector._ALERT_ID,
            "Alert Type": "Caution",
            "Alert Category": "Technical",
            "Alert System": 5,
            "Alert Sub-System": 0,
            "Data Source Network ID NAME": connector._ALERT_ID,
            "Data Source Instance": 0,
            "Data Source Index-Source": 0,
            "Alert Occurrence Number": 0,
            "Language ID": 0,
            "Alert Text Description": state_drop_point_set.message
        }

        in_radius_nmea_message = {
            "pgn": 126985,
            "Alert ID": connector._ALERT_ID,
            "Alert Type": "Caution",
            "Alert Category": "Technical",
            "Alert System": 5,
            "Alert Sub-System": 0,
            "Data Source Network ID NAME": connector._ALERT_ID,
            "Data Source Instance": 0,
            "Data Source Index-Source": 0,
            "Alert Occurrence Number": 0,
            "Language ID": 0,
            "Alert Text Description": state_in_radius.message
        }

        in_radius2_nmea_message = {
            "pgn": 126985,
            "Alert ID": connector._ALERT_ID,
            "Alert Type": "Caution",
            "Alert Category": "Technical",
            "Alert System": 5,
            "Alert Sub-System": 0,
            "Data Source Network ID NAME": connector._ALERT_ID,
            "Data Source Instance": 0,
            "Data Source Index-Source": 0,
            "Alert Occurrence Number": 0,
            "Language ID": 0,
            "Alert Text Description": state_in_radius2.message
        }

        in_radius3_nmea_message = {
            "pgn": 126985,
            "Alert ID": connector._ALERT_ID,
            "Alert Type": "Caution",
            "Alert Category": "Technical",
            "Alert System": 5,
            "Alert Sub-System": 0,
            "Data Source Network ID NAME": connector._ALERT_ID,
            "Data Source Instance": 0,
            "Data Source Index-Source": 0,
            "Alert Occurrence Number": 0,
            "Language ID": 0,
            "Alert Text Description": state_in_radius3.message
        }

        text_nmea_message_disabled = {
            "pgn": 126985,
            "Alert ID": connector._ALERT_ID,
            "Alert Type": "Caution",
            "Alert Category": "Technical",
            "Alert System": 5,
            "Alert Sub-System": 0,
            "Data Source Network ID NAME": connector._ALERT_ID,
            "Data Source Instance": 0,
            "Data Source Index-Source": 0,
            "Alert Occurrence Number": 0,
            "Language ID": 0,
            "Alert Text Description": state_disabled.message
        }


        alarm_nmea_message_active = {
            "pgn": 126983,
            "Alert ID": connector._ALERT_ID,
            "Alert Type": "Emergency Alarm",
            "Alert State": "Active",
            "Alert Category": "Technical",
            "Alert System": 5,
            "Alert Sub-System": 0,
            "Data Source Network ID NAME": connector._ALERT_ID,
            "Data Source Instance": 0,
            "Data Source Index-Source": 0,
            "Alert Occurrence Number": 0,
            "Temporary Silence Status": 0,
            "Acknowledge Status": 0,
            "Escalation Status": 0,
            "Temporary Silence Support": 0,
            "Acknowledge Support": 1,
            "Escalation Support": 0,
            "Trigger Condition": 2,
            "Threshold Status": 1,
            "Alert Priority": 0
        }

        alarm_nmea_message_normal = {
            "pgn": 126983,
            "Alert ID": connector._ALERT_ID,
            "Alert Type": "Emergency Alarm",
            "Alert State": "Normal",
            "Alert Category": "Technical",
            "Alert System": 5,
            "Alert Sub-System": 0,
            "Data Source Network ID NAME": connector._ALERT_ID,
            "Data Source Instance": 0,
            "Data Source Index-Source": 0,
            "Alert Occurrence Number": 0,
            "Temporary Silence Status": 0,
            "Acknowledge Status": 0,
            "Escalation Status": 0,
            "Temporary Silence Support": 0,
            "Acknowledge Support": 1,
            "Escalation Support": 0,
            "Trigger Condition": 2,
            "Threshold Status": 1,
            "Alert Priority": 0
        }

        alarm_nmea_message = {
            "pgn": 126985,
            "Alert ID": connector._ALERT_ID,
            "Alert Type": "Emergency Alarm",
            "Alert Category": "Technical",
            "Alert System": 5,
            "Alert Sub-System": 0,
            "Data Source Network ID NAME": connector._ALERT_ID,
            "Data Source Instance": 0,
            "Data Source Index-Source": 0,
            "Alert Occurrence Number": 0,
            "Language ID": 0,
            "Alert Text Description": state_dragging.message
        }

        alarm_muted_nmea_message = {
            "pgn": 126985,
            "Alert ID": connector._ALERT_ID,
            "Alert Type": "Emergency Alarm",
            "Alert Category": "Technical",
            "Alert System": 5,
            "Alert Sub-System": 0,
            "Data Source Network ID NAME": connector._ALERT_ID,
            "Data Source Instance": 0,
            "Data Source Index-Source": 0,
            "Alert Occurrence Number": 0,
            "Language ID": 0,
            "Alert Text Description": state_dragging_muted.message
        }





        connector.on_state_changed(state_drop_point_set)

        mock_bridge.send_nmea.assert_has_calls([call(alert_nmea_message_active), call(text_nmea_message)])

        timer_provider.tick()
        timer_provider.tick()
        timer_provider.tick()
        
        #check also auto aknowledge
        mock_bridge.send_nmea.assert_has_calls([call(alert_nmea_message_active), call(text_nmea_message), call(alert_nmea_message_normal)])
        

        # check  in_radius sent, in_radius_2 text sent, auto aknowledged

        connector.on_state_changed(state_in_radius)
        mock_bridge.send_nmea.assert_has_calls([
                call(alert_nmea_message_active), call(text_nmea_message), call(alert_nmea_message_normal),
                call(alert_nmea_message_active), call(in_radius_nmea_message),
                ])

        timer_provider.tick()
        mock_bridge.send_nmea.assert_has_calls([
                call(alert_nmea_message_active), call(text_nmea_message), call(alert_nmea_message_normal),
                call(alert_nmea_message_active), call(in_radius_nmea_message),
                ])
        
        connector.update_state(state_in_radius2)
        timer_provider.tick()

        mock_bridge.send_nmea.assert_has_calls([
                call(alert_nmea_message_active), call(text_nmea_message), call(alert_nmea_message_normal),
                call(alert_nmea_message_active), call(in_radius_nmea_message), call(in_radius2_nmea_message),
                ])

        #check auto_acknowledge
        timer_provider.tick()
        mock_bridge.send_nmea.assert_has_calls([
                call(alert_nmea_message_active), call(text_nmea_message), call(alert_nmea_message_normal),
                call(alert_nmea_message_active), call(in_radius_nmea_message), call(in_radius2_nmea_message), call(alert_nmea_message_normal),
                ])

        # check we get updates
        connector.update_state(state_in_radius3)
        mock_bridge.send_nmea.assert_has_calls([
                call(alert_nmea_message_active), call(text_nmea_message), call(alert_nmea_message_normal),
                call(alert_nmea_message_active), call(in_radius_nmea_message), call(in_radius2_nmea_message), call(alert_nmea_message_normal), call(in_radius3_nmea_message)
                ])



        # check that alert is sent with auto-acknowledge, a new alert will reset auto-ackownledge timer
        mock_bridge.send_nmea.reset_mock()


        connector.on_state_changed(state_drop_point_set)
        mock_bridge.send_nmea.assert_has_calls([call(alert_nmea_message_active), call(text_nmea_message)])

        # only 2 ticks
        timer_provider.tick()
        timer_provider.tick()

        connector.on_state_changed(state_in_radius)
        mock_bridge.send_nmea.assert_has_calls([
                call(alert_nmea_message_active), call(text_nmea_message),
                call(alert_nmea_message_active), call(in_radius_nmea_message),
                ])
        
        # only 2 ticks
        timer_provider.tick()
        timer_provider.tick()
        mock_bridge.send_nmea.assert_has_calls([
                call(alert_nmea_message_active), call(text_nmea_message),
                call(alert_nmea_message_active), call(in_radius_nmea_message),
                ])
        
        timer_provider.tick()
        mock_bridge.send_nmea.assert_has_calls([
                call(alert_nmea_message_active), call(text_nmea_message),
                call(alert_nmea_message_active), call(in_radius_nmea_message),
                call(alert_nmea_message_normal)
                ])
        

        # check that alert is sent with auto-acknowledge, then a alarm is sent before, make sure alert is acknowledged and it's not auto acknowledged
        mock_bridge.send_nmea.reset_mock()


        connector.on_state_changed(state_drop_point_set)
        mock_bridge.send_nmea.assert_has_calls([call(alert_nmea_message_active), call(text_nmea_message)])

        # only 2 ticks
        timer_provider.tick()
        timer_provider.tick()

        connector.on_state_changed(state_in_radius)
        mock_bridge.send_nmea.assert_has_calls([
                call(alert_nmea_message_active), call(text_nmea_message),
                call(alert_nmea_message_active), call(in_radius_nmea_message),
                ])
        
        # only 2 ticks
        timer_provider.tick()
        timer_provider.tick()
        mock_bridge.send_nmea.assert_has_calls([
                call(alert_nmea_message_active), call(text_nmea_message),
                call(alert_nmea_message_active), call(in_radius_nmea_message),
                ])
        
        # alarm will clear alert immediately
        connector.on_state_changed(state_dragging)
        mock_bridge.send_nmea.assert_has_calls([
                call(alert_nmea_message_active), call(text_nmea_message),
                call(alert_nmea_message_active), call(in_radius_nmea_message),
                call(alert_nmea_message_normal), call(alarm_nmea_message_active), call(alarm_nmea_message)
                ])
        

        # no auto aknowledge
        timer_provider.tick()
        timer_provider.tick()
        timer_provider.tick()
        timer_provider.tick()
        mock_bridge.send_nmea.assert_has_calls([
                call(alert_nmea_message_active), call(text_nmea_message),
                call(alert_nmea_message_active), call(in_radius_nmea_message),
                call(alert_nmea_message_normal), call(alarm_nmea_message_active), call(alarm_nmea_message)
                ])
        

        connector.on_state_changed(state_dragging_muted)
        mock_bridge.send_nmea.assert_has_calls([
                call(alert_nmea_message_active), call(text_nmea_message),
                call(alert_nmea_message_active), call(in_radius_nmea_message),
                call(alert_nmea_message_normal), call(alarm_nmea_message_active), call(alarm_nmea_message),
                call(alarm_nmea_message_normal), call(alarm_muted_nmea_message)
                ])
        
        # after mute period
        connector.on_state_changed(state_dragging)
        mock_bridge.send_nmea.assert_has_calls([
                call(alert_nmea_message_active), call(text_nmea_message),
                call(alert_nmea_message_active), call(in_radius_nmea_message),
                call(alert_nmea_message_normal), call(alarm_nmea_message_active), call(alarm_nmea_message),
                call(alarm_nmea_message_normal), call(alarm_muted_nmea_message),
                call(alarm_nmea_message_active), call(alarm_nmea_message),
                ])
        
        connector.on_state_changed(state_disabled)
        mock_bridge.send_nmea.assert_has_calls([
                call(alert_nmea_message_active), call(text_nmea_message),
                call(alert_nmea_message_active), call(in_radius_nmea_message),
                call(alert_nmea_message_normal), call(alarm_nmea_message_active), call(alarm_nmea_message),
                call(alarm_nmea_message_normal), call(alarm_muted_nmea_message),
                call(alarm_nmea_message_active), call(alarm_nmea_message),
                call(alarm_nmea_message_normal), call(alert_nmea_message_active), call(text_nmea_message_disabled)
                ])
        



    def test_alert_aknowledge(self):

        handler = None
        def _set_handler(pgn, the_handler):
            nonlocal handler
            handler = the_handler

        mock_bridge = MagicMock()
        mock_bridge.add_pgn_handler = MagicMock(side_effect=_set_handler)
        mock_bridge.send_nmea = MagicMock()

        connector = NMEAAlertConnector(lambda: timer_provider, MockSettingsDevice, mock_bridge)
        connector._settings['AutoAcknowledgeInterval'] = 3

        controller = MagicMock()
        controller.trigger_mute_alarm   = MagicMock()
        connector.set_controller(controller)

        controller.trigger_mute_alarm.assert_not_called()

        pgn_wrong_id = {
            "pgn": 126984,
            "fields": {
                "Alert Type": "Caution",
                "Alert Category": "Technical",
                "Alert System":5,
                "Alert ID": 456,
                "Data Source Network ID NAME": "0000000000000012",
                "Data Source Instance": 0,
                "Data Source Index-Source": 0,
                "Alert Occurrence Number": 0,
                "Acknowledge Source Network ID NAME": "0000000000000012",
                "Response Command": "Acknowledge"
                }
        }

        
        handler(pgn_wrong_id)
        controller.trigger_mute_alarm.assert_not_called()


        pgn_wrong_type = {
            "pgn": 126984,
            "fields": {
                "Alert Type": "Caution",
                "Alert Category": "Technical",
                "Alert System":5,
                "Alert ID": connector._ALERT_ID,
                "Data Source Network ID NAME": "0000000000000012",
                "Data Source Instance": 0,
                "Data Source Index-Source": 0,
                "Alert Occurrence Number": 0,
                "Acknowledge Source Network ID NAME": "0000000000000012",
                "Response Command": "Acknowledge"
            }
        }

        
        handler(pgn_wrong_type)
        controller.trigger_mute_alarm.assert_not_called()



        pgn_aknowledge = {
            'canId': 166725639, 
            'prio': 2, 
            'src': 7, 
            'dst': 255, 
            'pgn': 126984, 
            'timestamp': '2025-05-15T18:31:09.659Z', 
            'input': [], 
            'fields': {
                'Alert Type': 'Emergency Alarm',
                'Alert Category': 'Technical',
                'Alert System': 5,
                'Alert Sub-System': 0,
                'Alert ID': 54321,
                'Data Source Network ID NAME': 54321,
                'Data Source Instance': 0, 
                'Data Source Index-Source': 0, 
                'Alert Occurrence Number': 0, 
                'Acknowledge Source Network ID NAME': 13902754986684846000, 
                'Response Command': 'Acknowledge', 
                'Reserved1': 0}, 
            'description': 'Alert Response'}

        
        handler(pgn_aknowledge)
        controller.trigger_mute_alarm.assert_called_once()


if __name__ == '__main__':
    unittest.main()