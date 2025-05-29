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

# TODO XXX : move that import somewhere
from collections import namedtuple
GPSPosition = namedtuple('GPSPosition', ['latitude', 'longitude'])

from nmea_ds_connector import NMEADSConnector
          
timer_provider = GLibTimerMock()




class TestNMEADSConnector(unittest.TestCase):

    def setUp(self):
        self.maxDiff = None


    def test_no_interval(self):
        mock_bridge = MagicMock()
        
        handler = None
        def _set_handler(pgn, the_handler):
            nonlocal handler
            handler = the_handler

        mock_bridge.add_pgn_handler = MagicMock(side_effect=_set_handler)              
        mock_bridge.send_nmea = MagicMock()


        connector = NMEADSConnector(lambda: timer_provider, MockSettingsDevice,  mock_bridge)
        connector._settings['AdvertiseInterval'] = 0

        controller = MagicMock()
        controller.trigger_anchor_down     = MagicMock()
        controller.trigger_chain_out       = MagicMock()
        controller.trigger_anchor_up       = MagicMock()
        controller.trigger_mute_alarm      = MagicMock()

        connector.set_controller(controller)

        mock_bridge.send_nmea.assert_not_called()
        timer_provider.tick()
        mock_bridge.send_nmea.assert_not_called()

        state_drop_point_set = AnchorAlarmState('DROP_POINT_SET', 'Drop point set, please do blablala',"short message", 'info', False, {'drop_point': GPSPosition(10, 11)})
        connector.on_state_changed(state_drop_point_set)
        mock_bridge.send_nmea.assert_not_called()
        timer_provider.tick()
        mock_bridge.send_nmea.assert_not_called() 
        


    def test_no_channels(self):
        mock_bridge = MagicMock()
        
        handler = None
        def _set_handler(pgn, the_handler):
            nonlocal handler
            handler = the_handler

        mock_bridge.add_pgn_handler = MagicMock(side_effect=_set_handler)              
        mock_bridge.send_nmea = MagicMock()


        connector = NMEADSConnector(lambda: timer_provider, MockSettingsDevice,  mock_bridge)
        connector._settings['AdvertiseInterval'] = 2
        connector._settings['AnchorDownChannel'] = 0
        connector._settings['ChainOutChannel'] = 0
        connector._settings['AnchorUpChannel'] = 0
        connector._settings['MuteAlarmChannel'] = 0
        connector._settings['MooringModeChannel'] = 0
        connector._settings['DecreaseToleranceChannel'] = 0
        connector._settings['IncreaseToleranceChannel'] = 0
        connector._settings['DisabledFeedbackChannel'] = 0
        connector._settings['DropPointSetFeedbackChannel'] = 0
        connector._settings['InRadiusFeedbackChannel'] = 0
        connector._settings['AlarmDraggingFeedbackChannel'] = 0
        connector._settings['AlarmDraggingMutedFeedbackChannel'] = 0
        connector._settings['AlarmNoGPSFeedbackChannel'] = 0
        connector._settings['AlarmNoGPSMutedFeedbackChannel'] = 0

        controller = MagicMock()
        controller.trigger_anchor_down     = MagicMock()
        controller.trigger_chain_out       = MagicMock()
        controller.trigger_anchor_up       = MagicMock()
        controller.trigger_mute_alarm      = MagicMock()

        connector.set_controller(controller)

        mock_bridge.send_nmea.assert_not_called()
        timer_provider.tick()
        mock_bridge.send_nmea.assert_not_called()
        timer_provider.tick()
        mock_bridge.send_nmea.assert_not_called()
        timer_provider.tick()
        mock_bridge.send_nmea.assert_not_called()

        state_drop_point_set = AnchorAlarmState('DROP_POINT_SET', 'Drop point set, please do blablala',"short message", 'info', False, {'drop_point': GPSPosition(10, 11)})
        connector.on_state_changed(state_drop_point_set)
        mock_bridge.send_nmea.assert_not_called()
        timer_provider.tick()
        mock_bridge.send_nmea.assert_not_called() 
        timer_provider.tick()
        mock_bridge.send_nmea.assert_not_called()
        timer_provider.tick()
        mock_bridge.send_nmea.assert_not_called()
        
            

    def test_ds_changes(self):
        mock_bridge = MagicMock()
        
        handler = None
        def _set_handler(pgn, the_handler):
            nonlocal handler
            handler = the_handler

        mock_bridge.add_pgn_handler = MagicMock(side_effect=_set_handler)              
        mock_bridge.send_nmea = MagicMock()


        connector = NMEADSConnector(lambda: timer_provider, MockSettingsDevice,  mock_bridge)
        connector._settings['AdvertiseInterval'] = 2

        controller = MagicMock()
        controller.trigger_anchor_down     = MagicMock()
        controller.trigger_chain_out       = MagicMock()
        controller.trigger_anchor_up       = MagicMock()
        controller.trigger_mute_alarm      = MagicMock()
        controller.trigger_mooring_mode    = MagicMock()
        controller.trigger_decrease_tolerance      = MagicMock()
        controller.trigger_increase_tolerance      = MagicMock()

        connector.set_controller(controller)

        def test_switch_status(nmea_message, assert_cb, status):
            mock_bridge.send_nmea.reset_mock()
            controller
            timer_provider.tick()
            mock_bridge.send_nmea.assert_has_calls([])
            timer_provider.tick()
            mock_bridge.send_nmea.assert_has_calls([call(status_all_off)])


            handler(nmea_message)
            assert_cb()

            mock_bridge.send_nmea.assert_has_calls([call(status_all_off), call(status)])
            timer_provider.tick()   # 1 second
            mock_bridge.send_nmea.assert_has_calls([call(status_all_off), call(status), call(status_all_off)])
            timer_provider.tick()  
            mock_bridge.send_nmea.assert_has_calls([call(status_all_off), call(status), call(status_all_off), call(status_all_off)])



        status_all_off = {
            "pgn":127501,
            "fields": {
                "Instance":221,
                "Indicator1":"Off",
                "Indicator2":"Off",
                "Indicator3":"Off",
                "Indicator4":"Off",
                "Indicator5":"Off",
                "Indicator6":"Off",
                "Indicator7":"Off",

                # feedback status
                "Indicator11":"Off",
                "Indicator12":"Off",
                "Indicator13":"Off",
                "Indicator14":"Off",
                "Indicator15":"Off",
                "Indicator16":"Off",
                "Indicator17":"Off",
            },
            "description":"Binary Switch Bank Status"
        }





        ds_anchor_down = {
            "pgn":127502,
            "fields": {
                "Instance":221,
                "Switch1":"On",
            },
            "description":"Switch Bank Control"
        }

        ds_anchor_down_status = {
            "pgn":127501,
            "fields": {
                "Instance":221,
                "Indicator1":"On",
                "Indicator2":"Off",
                "Indicator3":"Off",
                "Indicator4":"Off",
                "Indicator5":"Off",
                "Indicator6":"Off",
                "Indicator7":"Off",

                # feedback status
                "Indicator11":"Off",
                "Indicator12":"Off",
                "Indicator13":"Off",
                "Indicator14":"Off",
                "Indicator15":"Off",
                "Indicator16":"Off",
                "Indicator17":"Off",
            },
            "description":"Binary Switch Bank Status"
        }

        test_switch_status(ds_anchor_down, controller.trigger_anchor_down.assert_called_once, ds_anchor_down_status)




        ds_set_radius = {
            "pgn":127502,
            "fields": {
                "Instance":221,
                "Switch2":"On",
            },
            "description":"Switch Bank Control"
        }

        ds_set_radius_status = {
            "pgn":127501,
            "fields": {
                "Instance":221,
                "Indicator1":"Off",
                "Indicator2":"On",
                "Indicator3":"Off",
                "Indicator4":"Off",
                "Indicator5":"Off",
                "Indicator6":"Off",
                "Indicator7":"Off",

                # feedback status
                "Indicator11":"Off",
                "Indicator12":"Off",
                "Indicator13":"Off",
                "Indicator14":"Off",
                "Indicator15":"Off",
                "Indicator16":"Off",
                "Indicator17":"Off",
            },
            "description":"Binary Switch Bank Status"
        }

        test_switch_status(ds_set_radius, controller.trigger_chain_out.assert_called_once, ds_set_radius_status)



        ds_anchor_up = {
            "pgn":127502,
            "fields": {
                "Instance":221,
                "Switch3":"On",
            },
            "description":"Switch Bank Control"
        }

        ds_anchor_up_status = {
            "pgn":127501,
            "fields": {
                "Instance":221,
                "Indicator1":"Off",
                "Indicator2":"Off",
                "Indicator3":"On",
                "Indicator4":"Off",
                "Indicator5":"Off",
                "Indicator6":"Off",
                "Indicator7":"Off",

                # feedback status
                "Indicator11":"Off",
                "Indicator12":"Off",
                "Indicator13":"Off",
                "Indicator14":"Off",
                "Indicator15":"Off",
                "Indicator16":"Off",
                "Indicator17":"Off",
            },
            "description":"Binary Switch Bank Status"
        }

        test_switch_status(ds_anchor_up, controller.trigger_anchor_up.assert_called_once, ds_anchor_up_status)



        ds_mute_alarm = {
            "pgn":127502,
            "fields": {
                "Instance":221,
                "Switch4":"On",
            },
            "description":"Switch Bank Control"
        }

        ds_mute_alarm_status = {
            "pgn":127501,
            "fields": {
                "Instance":221,
                "Indicator1":"Off",
                "Indicator2":"Off",
                "Indicator3":"Off",
                "Indicator4":"On",
                "Indicator5":"Off",
                "Indicator6":"Off",
                "Indicator7":"Off",

                # feedback status
                "Indicator11":"Off",
                "Indicator12":"Off",
                "Indicator13":"Off",
                "Indicator14":"Off",
                "Indicator15":"Off",
                "Indicator16":"Off",
                "Indicator17":"Off",
            },
            "description":"Binary Switch Bank Status"
        }

        
        test_switch_status(ds_mute_alarm, controller.trigger_mute_alarm.assert_called_once, ds_mute_alarm_status)


        ds_mooring_mode = {
            "pgn":127502,
            "fields": {
                "Instance":221,
                "Switch5":"On",
            },
            "description":"Switch Bank Control"
        }

        ds_mooring_mode_status = {
            "pgn":127501,
            "fields": {
                "Instance":221,
                "Indicator1":"Off",
                "Indicator2":"Off",
                "Indicator3":"Off",
                "Indicator4":"Off",
                "Indicator5":"On",
                "Indicator6":"Off",
                "Indicator7":"Off",

                # feedback status
                "Indicator11":"Off",
                "Indicator12":"Off",
                "Indicator13":"Off",
                "Indicator14":"Off",
                "Indicator15":"Off",
                "Indicator16":"Off",
                "Indicator17":"Off",
            },
            "description":"Binary Switch Bank Status"
        }

        
        test_switch_status(ds_mooring_mode, controller.trigger_mooring_mode.assert_called_once, ds_mooring_mode_status)


        ds_decrease_tolerance = {
            "pgn":127502,
            "fields": {
                "Instance":221,
                "Switch6":"On",
            },
            "description":"Switch Bank Control"
        }

        ds_decrease_tolerance_status = {
            "pgn":127501,
            "fields": {
                "Instance":221,
                "Indicator1":"Off",
                "Indicator2":"Off",
                "Indicator3":"Off",
                "Indicator4":"Off",
                "Indicator5":"Off",
                "Indicator6":"On",
                "Indicator7":"Off",
                
                # feedback status
                "Indicator11":"Off",
                "Indicator12":"Off",
                "Indicator13":"Off",
                "Indicator14":"Off",
                "Indicator15":"Off",
                "Indicator16":"Off",
                "Indicator17":"Off",
            },
            "description":"Binary Switch Bank Status"
        }

        
        test_switch_status(ds_decrease_tolerance, controller.trigger_decrease_tolerance.assert_called_once, ds_decrease_tolerance_status)





        ds_increase_tolerance = {
            "pgn":127502,
            "fields": {
                "Instance":221,
                "Switch7":"On",
            },
            "description":"Switch Bank Control"
        }

        ds_increase_tolerance_status = {
            "pgn":127501,
            "fields": {
                "Instance":221,
                "Indicator1":"Off",
                "Indicator2":"Off",
                "Indicator3":"Off",
                "Indicator4":"Off",
                "Indicator5":"Off",
                "Indicator6":"Off",
                "Indicator7":"On",
                
                # feedback status
                "Indicator11":"Off",
                "Indicator12":"Off",
                "Indicator13":"Off",
                "Indicator14":"Off",
                "Indicator15":"Off",
                "Indicator16":"Off",
                "Indicator17":"Off",
            },
            "description":"Binary Switch Bank Status"
        }

        
        test_switch_status(ds_increase_tolerance, controller.trigger_increase_tolerance.assert_called_once, ds_increase_tolerance_status)


        

        
                
    def test_advertised_status(self):
        mock_bridge = MagicMock()
        handler = None
        def _set_handler(pgn, the_handler):
            nonlocal handler
            handler = the_handler

        mock_bridge.add_pgn_handler = MagicMock(side_effect=_set_handler)        
        mock_bridge.send_nmea = MagicMock()


        connector = NMEADSConnector(lambda: timer_provider, MockSettingsDevice,  mock_bridge)
        connector._settings['AdvertiseInterval'] = 2

        controller = MagicMock()
        controller.trigger_mute_alarm   = MagicMock()
        connector.set_controller(controller)


               # AnchorAlarmState = namedtuple('AnchorAlarmState', ['state', 'message', 'level', 'muted', 'params'])
        state_drop_point_set = AnchorAlarmState('DROP_POINT_SET', 'Drop point set, please do blablala',"short message", 'info', False, {'drop_point': GPSPosition(10, 11)})
        state_in_radius = AnchorAlarmState('IN_RADIUS', 'boat in radius',"short message", 'info', False, {'drop_point': GPSPosition(10, 11), 'radius': 12})
        state_dragging = AnchorAlarmState('ALARM_DRAGGING', 'Anchor dragging !',"short message", 'emergency', False, {'drop_point': GPSPosition(10, 11), 'radius': 12})
        state_dragging_muted = AnchorAlarmState('ALARM_DRAGGING_MUTED', 'Anchor dragging ! (muted)',"short message", 'emergency', True, {'drop_point': GPSPosition(10, 11), 'radius': 12})
        state_disabled = AnchorAlarmState('DISABLED', 'Anchor alarm disabled',"short message", 'info', False, {})
        state_no_gps = AnchorAlarmState('ALARM_NO_GPS', 'alarm no gps',"short message", 'emergency', False, {})
        state_no_gps_muted = AnchorAlarmState('ALARM_NO_GPS_MUTED', 'alarm no gps',"short message", 'emergency', True, {})




        def test_state(state, channel):
            expected_status = {
                "pgn":127501,
                "fields": {
                    "Instance":221,
                    "Indicator1":"Off",
                    "Indicator2":"Off",
                    "Indicator3":"Off",
                    "Indicator4":"Off",
                    "Indicator5":"Off",
                    "Indicator6":"Off",
                    "Indicator7":"Off",

                    # feedback status
                    "Indicator11":"Off",
                    "Indicator12":"Off",
                    "Indicator13":"Off",
                    "Indicator14":"Off",
                    "Indicator15":"Off",
                    "Indicator16":"Off",
                    "Indicator17":"Off",
                },
                "description":"Binary Switch Bank Status"
            }
            expected_status['fields']['Indicator'+ str(channel)] = "On"

            mock_bridge.send_nmea.reset_mock()
            connector.on_state_changed(state)
            mock_bridge.send_nmea.assert_has_calls([call(expected_status)])
            timer_provider.tick()
            mock_bridge.send_nmea.assert_has_calls([call(expected_status)])
            timer_provider.tick()
            mock_bridge.send_nmea.assert_has_calls([call(expected_status), call(expected_status)])
            timer_provider.tick()
            mock_bridge.send_nmea.assert_has_calls([call(expected_status), call(expected_status)])
            timer_provider.tick()
            mock_bridge.send_nmea.assert_has_calls([call(expected_status), call(expected_status), call(expected_status)])


        test_state(state_disabled, 11)
        test_state(state_drop_point_set, 12)
        test_state(state_in_radius, 13)
        test_state(state_dragging, 14)
        test_state(state_dragging_muted, 15)
        test_state(state_no_gps, 16)
        test_state(state_no_gps_muted, 17)


    def test_switch_and_status(self):

        mock_bridge = MagicMock()
        handler = None
        def _set_handler(pgn, the_handler):
            nonlocal handler
            handler = the_handler

        mock_bridge.add_pgn_handler = MagicMock(side_effect=_set_handler)        
        mock_bridge.send_nmea = MagicMock()


        connector = NMEADSConnector(lambda: timer_provider, MockSettingsDevice,  mock_bridge)
        connector._settings['AdvertiseInterval'] = 2

        controller = MagicMock()
        controller.trigger_anchor_down   = MagicMock()
        connector.set_controller(controller)



        state_disabled = AnchorAlarmState('DISABLED', 'Anchor alarm disabled',"short message", 'info', False, {})
        disabled_status =  {
            "pgn":127501,
            "fields": {
                "Instance":221,
                "Indicator1":"Off",
                "Indicator2":"Off",
                "Indicator3":"Off",
                "Indicator4":"Off",
                "Indicator5":"Off",
                "Indicator6":"Off",
                "Indicator7":"Off",

                # feedback status
                "Indicator11":"On",
                "Indicator12":"Off",
                "Indicator13":"Off",
                "Indicator14":"Off",
                "Indicator15":"Off",
                "Indicator16":"Off",
                "Indicator17":"Off",
            },
            "description":"Binary Switch Bank Status"
        }
        connector.on_state_changed(state_disabled)
        mock_bridge.send_nmea.assert_has_calls([call(disabled_status)])
        timer_provider.tick()
        mock_bridge.send_nmea.assert_has_calls([call(disabled_status)])
        timer_provider.tick()
        mock_bridge.send_nmea.assert_has_calls([call(disabled_status), call(disabled_status)])




        ds_anchor_down = {
            "pgn":127502,
            "fields": {
                "Instance":221,
                "Switch1":"On",
            },
            "description":"Switch Bank Control"
        }

        ds_disabled_anchor_down_status = {
            "pgn":127501,
            "fields": {
                "Instance":221,
                "Indicator1":"On",
                "Indicator2":"Off",
                "Indicator3":"Off",
                "Indicator4":"Off",
                "Indicator5":"Off",
                "Indicator6":"Off",
                "Indicator7":"Off",

                # feedback status
                "Indicator11":"On",
                "Indicator12":"Off",
                "Indicator13":"Off",
                "Indicator14":"Off",
                "Indicator15":"Off",
                "Indicator16":"Off",
                "Indicator17":"Off",
            },
            "description":"Binary Switch Bank Status"
        }

        handler(ds_anchor_down)
        mock_bridge.send_nmea.assert_has_calls([call(disabled_status), call(disabled_status), call(ds_disabled_anchor_down_status)])

        state_drop_point_set = AnchorAlarmState('DROP_POINT_SET', 'Drop point set, please do blablala',"short message", 'info', False, {'drop_point': GPSPosition(10, 11)})
        connector.on_state_changed(state_drop_point_set)

        drop_point_set_status =  {
            "pgn":127501,
            "fields": {
                "Instance":221,
                "Indicator1":"Off",
                "Indicator2":"Off",
                "Indicator3":"Off",
                "Indicator4":"Off",
                "Indicator5":"Off",
                "Indicator6":"Off",
                "Indicator7":"Off",

                # feedback status
                "Indicator11":"Off",
                "Indicator12":"On",
                "Indicator13":"Off",
                "Indicator14":"Off",
                "Indicator15":"Off",
                "Indicator16":"Off",
                "Indicator17":"Off",
            },
            "description":"Binary Switch Bank Status"
        }
        
        drop_point_set_with_switch_status =  {
            "pgn":127501,
            "fields": {
                "Instance":221,
                "Indicator1":"On",
                "Indicator2":"Off",
                "Indicator3":"Off",
                "Indicator4":"Off",
                "Indicator5":"Off",
                "Indicator6":"Off",
                "Indicator7":"Off",

                # feedback status
                "Indicator11":"Off",
                "Indicator12":"On",
                "Indicator13":"Off",
                "Indicator14":"Off",
                "Indicator15":"Off",
                "Indicator16":"Off",
                "Indicator17":"Off",
            },
            "description":"Binary Switch Bank Status"
        }

        mock_bridge.send_nmea.assert_has_calls([
            call(disabled_status), call(disabled_status), call(ds_disabled_anchor_down_status),
            call(drop_point_set_with_switch_status)
            ])
        
        timer_provider.tick()

        mock_bridge.send_nmea.assert_has_calls([
            call(disabled_status), call(disabled_status), call(ds_disabled_anchor_down_status),
            call(drop_point_set_with_switch_status), call(drop_point_set_status)
            ])

if __name__ == '__main__':
    unittest.main()