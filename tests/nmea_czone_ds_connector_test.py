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

from nmea_ds_connector import NMEADSConnector, NMEARawPGN
          
timer_provider = GLibTimerMock()




class TestNMEADSConnector(unittest.TestCase):

    def setUp(self):
        self.maxDiff = None



    def _get_czone_heartbeat(self, serial, state):
        heartbeat_nmea_message = NMEARawPGN(65284)
        heartbeat_nmea_message.Add2ByteUInt(0x9927)
        if serial is not None:
            heartbeat_nmea_message.AddByte(int(serial))
            heartbeat_nmea_message.AddByte(0x0f)
            heartbeat_nmea_message.AddByte(state)
        else:   # if handshake not done, send 0xff to ask for a 65290 config request
            heartbeat_nmea_message.AddByte(0xff)
            heartbeat_nmea_message.Add2ByteUInt(0x0f0f)

        heartbeat_nmea_message.Add2ByteUInt(0x0000)
        heartbeat_nmea_message.AddByte(0x00)

        return heartbeat_nmea_message

    def _get_czone_switch_status(self, serial, channel):
        state_nmea_message = NMEARawPGN(130817)
        state_nmea_message.Add2ByteUInt(0x9927)
        state_nmea_message.AddByte(0x01)   # ?? maybe an "instance" value

        state_nmea_message.AddByte(int(serial))

        state_nmea_message.AddByte(0x01 if channel==1 else 0x00)
        state_nmea_message.Add2ByteUInt(0x0000)

        state_nmea_message.AddByte(0x01 if channel==2 else 0x00)
        state_nmea_message.Add2ByteUInt(0x0000)

        state_nmea_message.AddByte(0x01 if channel==3 else 0x00)
        state_nmea_message.Add2ByteUInt(0x0000)

        state_nmea_message.AddByte(0x01 if channel==4 else 0x00)
        state_nmea_message.Add2ByteUInt(0x0000)

        state_nmea_message.AddByte(0)
        state_nmea_message.AddByte(0)
        state_nmea_message.AddByte(0)
        state_nmea_message.AddByte(0)
        state_nmea_message.AddByte(0)
        state_nmea_message.AddByte(0)

        return state_nmea_message


    def _get_config_request_message(self, dip_switch):
        config_request_message = NMEARawPGN(65290)
        # TODO XXX BIG INDIAN OR LITTEL INDIAN ????
        config_request_message.Add2ByteUInt(0x9927) # 0/1

        config_request_message.AddByte(0x3b) # ???  # 2
        config_request_message.AddByte(0x52) # ???  # 3
        config_request_message.AddByte(0x0f) # ???  # 4
        config_request_message.AddByte(0x00) # ???  # 5
        config_request_message.AddByte(0x40) # ???  # 6
        config_request_message.AddByte(int(dip_switch)) # 7 dipswitch

        return config_request_message


    def _get_config_response_message(self, serial):
        config_response_message = NMEARawPGN(65290)
        config_response_message.Add2ByteUInt(0x9927)
        config_response_message.AddByte(0x3b)
        config_response_message.AddByte(0x3b)
        config_response_message.AddByte(0x3b)
        config_response_message.Add2ByteUInt(0x0000)
        config_response_message.AddByte(int(serial))

        return config_response_message


    def _get_switch_change_ack(self, serial, state_as_byte):
        czone_switch_ack_msg = NMEARawPGN(65283)
        czone_switch_ack_msg.Add2ByteUInt(0x9927)
        czone_switch_ack_msg.AddByte(int(serial))
        czone_switch_ack_msg.AddByte(state_as_byte)
        czone_switch_ack_msg.Add2ByteUInt(0x0000)
        czone_switch_ack_msg.AddByte(0x00)
        czone_switch_ack_msg.AddByte(0x10)

        return czone_switch_ack_msg


    def _get_switch_change_request(self, dip_switch, channel, switch_value):
        # switch value is 0xf1 for on, 0xf2 for off, 0xf4 for toggle, 0x40 for end of change
        channels = [0x05, 0x06, 0x07, 0x08, 0x09, 0x0a, 0x0b, 0x0c]
        czone_switch_change_msg = NMEARawPGN(65280)
        czone_switch_change_msg.Add2ByteUInt(0x9927)        # 0-1
        czone_switch_change_msg.AddByte(channels[channel])  #  2 
        czone_switch_change_msg.AddByte(0x0)                # ?? 3 
        czone_switch_change_msg.AddByte(0x0)                # ?? 4
        czone_switch_change_msg.AddByte(int(dip_switch))    # 5
        czone_switch_change_msg.AddByte(switch_value)       # 6
        czone_switch_change_msg.AddByte(0x0)                # ?? 8

        return czone_switch_change_msg





    def test_no_interval(self):
        mock_bridge = MagicMock()
        
        handler = None
        def _set_handler(pgn, the_handler):
            nonlocal handler
            if pgn == 127502:
                handler = the_handler

        mock_bridge.add_pgn_handler = MagicMock(side_effect=_set_handler)              
        mock_bridge.send_nmea = MagicMock()


        connector = NMEADSConnector(lambda: timer_provider, MockSettingsDevice,  mock_bridge)
        connector._settings['CZoneBank1SerialNumber'] = "111"
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
        

    def test_handshake_and_heartbeat(self):
        mock_bridge = MagicMock()
        
        handlers = {}
        def _set_handler(pgn, the_handler):
            nonlocal handlers
            handlers[pgn] = the_handler

        mock_bridge.add_pgn_handler = MagicMock(side_effect=_set_handler)              
        mock_bridge.send_nmea = MagicMock()


        connector = NMEADSConnector(lambda: timer_provider, MockSettingsDevice,  mock_bridge)
        connector._settings['AdvertiseInterval'] = 2
        connector._settings['CZoneBank1SerialNumber'] = "111"
        connector._settings['CZoneBank2SerialNumber'] = "222"
        connector._settings['CZoneDipSwitch'] = 1


        controller = MagicMock()
        controller.trigger_anchor_down     = MagicMock()
        controller.trigger_chain_out       = MagicMock()
        controller.trigger_anchor_up       = MagicMock()
        controller.trigger_mute_alarm      = MagicMock()

        connector.set_controller(controller)

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

        mock_bridge.send_nmea.assert_not_called()
        timer_provider.tick()
        mock_bridge.send_nmea.assert_not_called()
        timer_provider.tick()


        heartbeat_65284 = self._get_czone_heartbeat(None, 0)

        switch_state_130817_1 = self._get_czone_switch_status("111", 0)
        switch_state_130817_2 = self._get_czone_switch_status("222", 0)

        # 2 unhandshaked heartbeats (bank 1&2) and 2 switch_states (bank 1 & 2)
        mock_bridge.send_nmea.assert_has_calls([
            call(status_all_off),
            call(heartbeat_65284), call(heartbeat_65284), call(switch_state_130817_1), call(switch_state_130817_2),
        ])

        timer_provider.tick()
        timer_provider.tick()

        mock_bridge.send_nmea.assert_has_calls([
            call(status_all_off),
            call(heartbeat_65284), call(heartbeat_65284), call(switch_state_130817_1), call(switch_state_130817_2),

            call(status_all_off),
            call(heartbeat_65284), call(heartbeat_65284), call(switch_state_130817_1), call(switch_state_130817_2),
            
        ])

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

        # state change doesn't change CZone switch states
        mock_bridge.send_nmea.assert_has_calls([
            call(status_all_off),
            call(heartbeat_65284), call(heartbeat_65284), call(switch_state_130817_1), call(switch_state_130817_2),

            call(status_all_off),
            call(heartbeat_65284), call(heartbeat_65284), call(switch_state_130817_1), call(switch_state_130817_2),
        ])

        # unshaken heartbeat should trigger a 65290 config request
        config_request_message = self._get_config_request_message(connector._settings['CZoneDipSwitch'])
        handlers[65290](config_request_message)

        # should respond with a 65290 response for each bank
        config_response_65290_1 = self._get_config_response_message("111")
        config_response_65290_2 = self._get_config_response_message("222")

        mock_bridge.send_nmea.assert_has_calls([
            call(status_all_off),
            call(heartbeat_65284), call(heartbeat_65284), call(switch_state_130817_1), call(switch_state_130817_2),

            call(status_all_off),
            call(heartbeat_65284), call(heartbeat_65284), call(switch_state_130817_1), call(switch_state_130817_2),

            call(drop_point_set_status),
            call(config_response_65290_1), call(config_response_65290_2)
        ])

        
        # now handshake should be OK, we should have handshaken heart beat
        timer_provider.tick()

        switch_change_ack_65283_1 = self._get_switch_change_ack("111", 0x0)
        switch_change_ack_65283_2 = self._get_switch_change_ack("222", 0x0)

        mock_bridge.send_nmea.assert_has_calls([
            call(status_all_off),
            call(heartbeat_65284), call(heartbeat_65284), call(switch_state_130817_1), call(switch_state_130817_2),

            call(status_all_off),
            call(heartbeat_65284), call(heartbeat_65284), call(switch_state_130817_1), call(switch_state_130817_2),

            call(drop_point_set_status),
            call(config_response_65290_1), call(config_response_65290_2),
            call(switch_change_ack_65283_1), call(switch_change_ack_65283_2),
        ])

        timer_provider.tick()

        handshaked_heartbeat_65284_1 = self._get_czone_heartbeat("111", 0)
        handshaked_heartbeat_65284_2 = self._get_czone_heartbeat("222", 0)

        mock_bridge.send_nmea.assert_has_calls([
            call(status_all_off),
            call(heartbeat_65284), call(heartbeat_65284), call(switch_state_130817_1), call(switch_state_130817_2),

            call(status_all_off),
            call(heartbeat_65284), call(heartbeat_65284), call(switch_state_130817_1), call(switch_state_130817_2),
            
            call(drop_point_set_status),
            call(config_response_65290_1), call(config_response_65290_2),
            call(switch_change_ack_65283_1), call(switch_change_ack_65283_2),
            
            call(drop_point_set_status),
            call(switch_change_ack_65283_1), call(switch_change_ack_65283_2),
            call(handshaked_heartbeat_65284_1), call(handshaked_heartbeat_65284_2), call(switch_state_130817_1), call(switch_state_130817_2),
        ])


        

    def test_ds_changes(self):
        mock_bridge = MagicMock()
        
        handlers = {}
        def _set_handler(pgn, the_handler):
            nonlocal handlers
            handlers[pgn] = the_handler

        mock_bridge.add_pgn_handler = MagicMock(side_effect=_set_handler)              
        mock_bridge.send_nmea = MagicMock()


        connector = NMEADSConnector(lambda: timer_provider, MockSettingsDevice,  mock_bridge)
        connector._settings['AdvertiseInterval'] = 2
        connector._settings['CZoneBank1SerialNumber'] = "111"
        connector._settings['CZoneBank2SerialNumber'] = "222"
        connector._settings['CZoneDipSwitch'] = 1

        controller = MagicMock()
        controller.trigger_anchor_down     = MagicMock()
        controller.trigger_chain_out       = MagicMock()
        controller.trigger_anchor_up       = MagicMock()
        controller.trigger_mute_alarm      = MagicMock()
        controller.trigger_mooring_mode    = MagicMock()
        controller.trigger_decrease_tolerance      = MagicMock()
        controller.trigger_increase_tolerance      = MagicMock()

        connector.set_controller(controller)

        def test_switch_status(nmea_message, assert_cb, status, czone_channel):
            mock_bridge.send_nmea.reset_mock()
            controller
            timer_provider.tick()
            mock_bridge.send_nmea.assert_has_calls([])
            timer_provider.tick()
            mock_bridge.send_nmea.assert_has_calls([call(status_all_off)])


            handlers[127502](nmea_message)
            assert_cb()

            heartbeat_65284 = self._get_czone_heartbeat(None, 0)

            switch_state_130817_1_off = self._get_czone_switch_status("111", 0)
            switch_state_130817_2_off = self._get_czone_switch_status("222", 0)

            switch_state_130817_1 = self._get_czone_switch_status("111", czone_channel if czone_channel < 5 else 0)
            switch_state_130817_2 = self._get_czone_switch_status("222", czone_channel-4 if czone_channel > 4 else 0)

            bit_mapping = [0x0, 0x01, 0x04, 0x10, 0x40]

            switch_change_ack_65283_1_off = self._get_switch_change_ack("111", 0)
            switch_change_ack_65283_2_off = self._get_switch_change_ack("222", 0)

            switch_change_ack_65283_1 = self._get_switch_change_ack("111", bit_mapping[czone_channel] if czone_channel < 5 else 0)
            switch_change_ack_65283_2 = self._get_switch_change_ack("222", bit_mapping[czone_channel-4] if czone_channel > 4 else 0)

            mock_bridge.send_nmea.assert_has_calls([call(status_all_off), 
                                                    call(heartbeat_65284), call(heartbeat_65284), call(switch_state_130817_1_off), call(switch_state_130817_2_off),
                                                    call(status), 
                                                    call(switch_change_ack_65283_1), call(switch_change_ack_65283_2)])
            timer_provider.tick()   # 1 second

            mock_bridge.send_nmea.assert_has_calls([call(status_all_off), 
                                                    call(heartbeat_65284), call(heartbeat_65284), call(switch_state_130817_1_off), call(switch_state_130817_2_off),
                                                    call(status), 
                                                    call(switch_change_ack_65283_1), call(switch_change_ack_65283_2),
                                                    
                                                    # all off
                                                    call(status_all_off), 
                                                    call(switch_change_ack_65283_1_off), call(switch_change_ack_65283_2_off),
                                                    call(heartbeat_65284), call(heartbeat_65284),
                                                    ])
            #mock_bridge.send_nmea.assert_has_calls([call(status_all_off), call(status), call(status_all_off)])
            timer_provider.tick()  
            mock_bridge.send_nmea.assert_has_calls([call(status_all_off), 
                                                    call(heartbeat_65284), call(heartbeat_65284), call(switch_state_130817_1_off), call(switch_state_130817_2_off),
                                                    call(status), 
                                                    call(switch_change_ack_65283_1), call(switch_change_ack_65283_2),
                                                    
                                                    # all off
                                                    call(status_all_off), 
                                                    call(switch_change_ack_65283_1_off), call(switch_change_ack_65283_2_off),
                                                    call(heartbeat_65284), call(heartbeat_65284),

                                                    call(status_all_off), 
                                                    call(heartbeat_65284), call(heartbeat_65284), call(switch_state_130817_1_off), call(switch_state_130817_2_off),
                                                    ])


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

        test_switch_status(ds_anchor_down, controller.trigger_anchor_down.assert_called_once, ds_anchor_down_status, 1)




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

        test_switch_status(ds_set_radius, controller.trigger_chain_out.assert_called_once, ds_set_radius_status, 2)



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

        test_switch_status(ds_anchor_up, controller.trigger_anchor_up.assert_called_once, ds_anchor_up_status, 3)



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

        
        test_switch_status(ds_mute_alarm, controller.trigger_mute_alarm.assert_called_once, ds_mute_alarm_status, 4)


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

        
        test_switch_status(ds_mooring_mode, controller.trigger_mooring_mode.assert_called_once, ds_mooring_mode_status, 5)


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

        
        test_switch_status(ds_decrease_tolerance, controller.trigger_decrease_tolerance.assert_called_once, ds_decrease_tolerance_status, 6)





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

        
        test_switch_status(ds_increase_tolerance, controller.trigger_increase_tolerance.assert_called_once, ds_increase_tolerance_status, 7)


        


    def test_switch_and_status(self):

        mock_bridge = MagicMock()
        handlers = {}
        def _set_handler(pgn, the_handler):
            nonlocal handlers
            handlers[pgn] = the_handler

        mock_bridge.add_pgn_handler = MagicMock(side_effect=_set_handler)        
        mock_bridge.send_nmea = MagicMock()


        connector = NMEADSConnector(lambda: timer_provider, MockSettingsDevice,  mock_bridge)
        connector._settings['AdvertiseInterval'] = 2
        connector._settings['CZoneBank1SerialNumber'] = "111"
        connector._settings['CZoneBank2SerialNumber'] = "222"
        connector._settings['CZoneDipSwitch'] = 1

        controller = MagicMock()
        controller.trigger_anchor_down   = MagicMock()
        connector.set_controller(controller)


        state_disabled = AnchorAlarmState('DISABLED', 'Anchor alarm disabled',"short message", 'info', False, {})    
        connector.on_state_changed(state_disabled)
        
        
        switch_change_message = self._get_switch_change_request(connector._settings['CZoneDipSwitch'], 1, 0xf1)
        handlers[65280](switch_change_message)

        controller.trigger_anchor_down.assert_called()



        ds_anchor_down = {
            "pgn":127502,
            "fields": {
                "Instance":221,
                "Switch1":"On",
            },
            "description":"Switch Bank Control"
        }

        ds_disabled_status = {
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

  
        mock_bridge.send_nmea.assert_has_calls([call(ds_disabled_status), call(ds_anchor_down), call(ds_disabled_anchor_down_status)])

        switch_change_message = self._get_switch_change_request(connector._settings['CZoneDipSwitch'], 1, 0x40)
        handlers[65280](switch_change_message)


        switch_change_ack_65283_1 = self._get_switch_change_ack("111", 0x1)

        mock_bridge.send_nmea.assert_has_calls([call(ds_disabled_status), call(ds_anchor_down), call(ds_disabled_anchor_down_status),
                                                call(switch_change_ack_65283_1)
                                                ])



if __name__ == '__main__':
    unittest.main()