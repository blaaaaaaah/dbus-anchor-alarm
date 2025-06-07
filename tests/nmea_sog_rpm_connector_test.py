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

from nmea_sog_rpm_connector import NMEASOGRPMConnector
          
timer_provider = GLibTimerMock()

from abstract_gps_provider import GPSPosition



class TestNMEASOGRPMConnector(unittest.TestCase):

    def setUp(self):
        self.maxDiff = None

        



    def test_both_engines(self):
        mock_bridge = MagicMock()

        sog_handler = None
        rpm_handler = None

        def _set_handler(pgn, the_handler):
            nonlocal sog_handler
            nonlocal rpm_handler
            if pgn == 129026:
                sog_handler = the_handler
            else:
                rpm_handler = the_handler

        mock_bridge = MagicMock()
        mock_bridge.add_pgn_handler = MagicMock(side_effect=_set_handler)        


        connector = NMEASOGRPMConnector(lambda: timer_provider, MockSettingsDevice,  mock_bridge)

        controller = MagicMock()
        controller.trigger_chain_out   = MagicMock()
        connector.set_controller(controller)

        state_drop_point_set = AnchorAlarmState('DROP_POINT_SET', 'Drop point set, please do blablala',"short message", 'info', False, {'drop_point': GPSPosition(10, 11)})
        connector.on_state_changed(state_drop_point_set)

        sog_0_07 = {'canId': 167248387, 'prio': 2, 'src': 3, 'dst': 255, 'pgn': 129026, 'timestamp': '2025-05-16T13:51:59.279Z', 
                   'fields': {'SID': 208, 'COG Reference': 'True', 'COG': 0.2787, 'SOG': 0.07}, 'description': 'COG & SOG, Rapid Update'}

        sog_0_4 = {'canId': 167248387, 'prio': 2, 'src': 3, 'dst': 255, 'pgn': 129026, 'timestamp': '2025-05-16T13:51:59.279Z', 
                   'fields': {'SID': 208, 'COG Reference': 'True', 'COG': 0.2787, 'SOG': 0.4}, 'description': 'COG & SOG, Rapid Update'}


        port_speed_1300 = {'canId': 166854714, 'prio': 2, 'src': 58, 'dst': 255, 'pgn': 127488, 'timestamp': '2025-05-16T13:57:08.889Z', 
                           'fields': {'Instance': 'Single Engine or Dual Engine Port', 'Speed': 1300, 'Boost Pressure': 0}, 'description': 'Engine Parameters, Rapid Update'}

        port_speed_1800 = {'canId': 166854714, 'prio': 2, 'src': 58, 'dst': 255, 'pgn': 127488, 'timestamp': '2025-05-16T13:57:08.889Z', 
                           'fields': {'Instance': 'Single Engine or Dual Engine Port', 'Speed': 1800, 'Boost Pressure': 0}, 'description': 'Engine Parameters, Rapid Update'}


        stb_speed_1300 =  {'canId': 166854712, 'prio': 2, 'src': 56, 'dst': 255, 'pgn': 127488, 'timestamp': '2025-05-16T13:57:41.254Z', 
                           'fields': {'Instance': 'Dual Engine Starboard', 'Speed': 1300, 'Boost Pressure': 0}, 'description': 'Engine Parameters, Rapid Update'}


        stb_speed_1800 =  {'canId': 166854712, 'prio': 2, 'src': 56, 'dst': 255, 'pgn': 127488, 'timestamp': '2025-05-16T13:57:41.254Z', 
                           'fields': {'Instance': 'Dual Engine Starboard', 'Speed': 1800, 'Boost Pressure': 0}, 'description': 'Engine Parameters, Rapid Update'}


        def assert_conditions_not_met():
            controller.trigger_chain_out.assert_not_called()
            self.assertIsNone(connector._timer_ids['conditions_met'])



        # speed too big and rpm too low
        sog_handler(sog_0_4)
        assert_conditions_not_met()
        rpm_handler(port_speed_1300)
        assert_conditions_not_met()
        rpm_handler(stb_speed_1300)
        assert_conditions_not_met()


         # speed ok and rpm too low
        sog_handler(sog_0_07)
        assert_conditions_not_met()
        rpm_handler(port_speed_1300)
        assert_conditions_not_met()
        rpm_handler(stb_speed_1300)
        assert_conditions_not_met()

        sog_handler(sog_0_07)
        assert_conditions_not_met()
        rpm_handler(port_speed_1800)
        assert_conditions_not_met()
        rpm_handler(stb_speed_1300)
        assert_conditions_not_met()

        sog_handler(sog_0_07)
        assert_conditions_not_met()
        rpm_handler(port_speed_1300)
        assert_conditions_not_met()
        rpm_handler(stb_speed_1800)
        assert_conditions_not_met()

        # speed to big but rpm ok
        sog_handler(sog_0_4)
        assert_conditions_not_met()
        rpm_handler(port_speed_1800)
        assert_conditions_not_met()
        rpm_handler(stb_speed_1800)
        assert_conditions_not_met()

        sog_handler(sog_0_4)
        assert_conditions_not_met()
        rpm_handler(port_speed_1800)
        assert_conditions_not_met()
        rpm_handler(stb_speed_1300)
        assert_conditions_not_met()

        sog_handler(sog_0_4)
        assert_conditions_not_met()
        rpm_handler(port_speed_1300)
        assert_conditions_not_met()
        rpm_handler(stb_speed_1800)
        assert_conditions_not_met()

        # speed ok and rpm ok
        sog_handler(sog_0_07)
        assert_conditions_not_met()
        rpm_handler(port_speed_1800)
        
        # timer armed
        self.assertIsNotNone(connector._timer_ids['conditions_met'])
        controller.trigger_chain_out.assert_not_called()

        timer_provider.tick()
        sog_handler(sog_0_07)
        rpm_handler(port_speed_1800)
        rpm_handler(stb_speed_1800)
        self.assertIsNotNone(connector._timer_ids['conditions_met'])
        controller.trigger_chain_out.assert_not_called()

        # increased speed
        sog_handler(sog_0_4)
        assert_conditions_not_met()
        timer_provider.tick()
        timer_provider.tick()
        timer_provider.tick()
        timer_provider.tick()
        controller.trigger_chain_out.assert_not_called()



        # back ok
        sog_handler(sog_0_07)
        rpm_handler(port_speed_1800)
        rpm_handler(stb_speed_1800)
        self.assertIsNotNone(connector._timer_ids['conditions_met'])
        controller.trigger_chain_out.assert_not_called()

        # decreased rpm
        rpm_handler(stb_speed_1300)
        assert_conditions_not_met()
        timer_provider.tick()
        timer_provider.tick()
        timer_provider.tick()
        timer_provider.tick()
        controller.trigger_chain_out.assert_not_called()


        # back ok
        sog_handler(sog_0_07)
        rpm_handler(port_speed_1800)
        rpm_handler(stb_speed_1800)
        self.assertIsNotNone(connector._timer_ids['conditions_met'])
        controller.trigger_chain_out.assert_not_called()


        # decreased rpm
        rpm_handler(port_speed_1300)
        assert_conditions_not_met()
        timer_provider.tick()
        timer_provider.tick()
        timer_provider.tick()
        timer_provider.tick()
        controller.trigger_chain_out.assert_not_called()



         # back ok
        sog_handler(sog_0_07)
        rpm_handler(port_speed_1800)
        rpm_handler(stb_speed_1800)
        timer_provider.tick()

        self.assertIsNotNone(connector._timer_ids['conditions_met'])
        controller.trigger_chain_out.assert_not_called()

        sog_handler(sog_0_07)
        rpm_handler(port_speed_1800)
        rpm_handler(stb_speed_1800)
        timer_provider.tick()

        self.assertIsNotNone(connector._timer_ids['conditions_met'])
        controller.trigger_chain_out.assert_not_called()

        sog_handler(sog_0_07)
        rpm_handler(port_speed_1800)
        rpm_handler(stb_speed_1800)
        timer_provider.tick()

        self.assertIsNone(connector._timer_ids['conditions_met'])
        controller.trigger_chain_out.assert_called_once()

    def test_one_engine(self):
        mock_bridge = MagicMock()

        sog_handler = None
        rpm_handler = None

        def _set_handler(pgn, the_handler):
            nonlocal sog_handler
            nonlocal rpm_handler
            if pgn == 129026:
                sog_handler = the_handler
            else:
                rpm_handler = the_handler

        mock_bridge = MagicMock()
        mock_bridge.add_pgn_handler = MagicMock(side_effect=_set_handler)        


        connector = NMEASOGRPMConnector(lambda: timer_provider, MockSettingsDevice,  mock_bridge)
        connector._settings['NumberOfEngines'] = 1

        controller = MagicMock()
        controller.trigger_chain_out   = MagicMock()
        connector.set_controller(controller)

        state_drop_point_set = AnchorAlarmState('DROP_POINT_SET', 'Drop point set, please do blablala',"short message", 'info', False, {'drop_point': GPSPosition(10, 11)})
        connector.on_state_changed(state_drop_point_set)


        sog_0_07 = {'canId': 167248387, 'prio': 2, 'src': 3, 'dst': 255, 'pgn': 129026, 'timestamp': '2025-05-16T13:51:59.279Z', 
                   'fields': {'SID': 208, 'COG Reference': 'True', 'COG': 0.2787, 'SOG': 0.07}, 'description': 'COG & SOG, Rapid Update'}

        sog_0_4 = {'canId': 167248387, 'prio': 2, 'src': 3, 'dst': 255, 'pgn': 129026, 'timestamp': '2025-05-16T13:51:59.279Z', 
                   'fields': {'SID': 208, 'COG Reference': 'True', 'COG': 0.2787, 'SOG': 0.4}, 'description': 'COG & SOG, Rapid Update'}


        port_speed_1300 = {'canId': 166854714, 'prio': 2, 'src': 58, 'dst': 255, 'pgn': 127488, 'timestamp': '2025-05-16T13:57:08.889Z', 
                           'fields': {'Instance': 'Single Engine or Dual Engine Port', 'Speed': 1300, 'Boost Pressure': 0}, 'description': 'Engine Parameters, Rapid Update'}

        port_speed_1800 = {'canId': 166854714, 'prio': 2, 'src': 58, 'dst': 255, 'pgn': 127488, 'timestamp': '2025-05-16T13:57:08.889Z', 
                           'fields': {'Instance': 'Single Engine or Dual Engine Port', 'Speed': 1800, 'Boost Pressure': 0}, 'description': 'Engine Parameters, Rapid Update'}



        def assert_conditions_not_met():
            controller.trigger_chain_out.assert_not_called()
            self.assertIsNone(connector._timer_ids['conditions_met'])

        # speed too big and rpm too low
        sog_handler(sog_0_4)
        assert_conditions_not_met()
        rpm_handler(port_speed_1300)
        assert_conditions_not_met()



         # speed ok and rpm too low
        sog_handler(sog_0_07)
        assert_conditions_not_met()
        rpm_handler(port_speed_1300)
        assert_conditions_not_met()
 

        # speed too big but rpm ok
        sog_handler(sog_0_4)
        assert_conditions_not_met()
        rpm_handler(port_speed_1800)
        assert_conditions_not_met()


        rpm_handler(port_speed_1300)
        # speed ok and rpm ok
        sog_handler(sog_0_07)
        assert_conditions_not_met()
        rpm_handler(port_speed_1800)
        
        # timer armed
        self.assertIsNotNone(connector._timer_ids['conditions_met'])
        controller.trigger_chain_out.assert_not_called()

        timer_provider.tick()
        sog_handler(sog_0_07)
        rpm_handler(port_speed_1800)
        self.assertIsNotNone(connector._timer_ids['conditions_met'])
        controller.trigger_chain_out.assert_not_called()

        # increased speed
        sog_handler(sog_0_4)
        assert_conditions_not_met()
        timer_provider.tick()
        timer_provider.tick()
        timer_provider.tick()
        timer_provider.tick()
        controller.trigger_chain_out.assert_not_called()



        # back ok
        sog_handler(sog_0_07)
        rpm_handler(port_speed_1800)
        self.assertIsNotNone(connector._timer_ids['conditions_met'])
        controller.trigger_chain_out.assert_not_called()


        # decreased rpm
        rpm_handler(port_speed_1300)
        assert_conditions_not_met()
        timer_provider.tick()
        timer_provider.tick()
        timer_provider.tick()
        timer_provider.tick()
        controller.trigger_chain_out.assert_not_called()



         # back ok
        sog_handler(sog_0_07)
        rpm_handler(port_speed_1800)
        timer_provider.tick()

        self.assertIsNotNone(connector._timer_ids['conditions_met'])
        controller.trigger_chain_out.assert_not_called()

        sog_handler(sog_0_07)
        rpm_handler(port_speed_1800)
        timer_provider.tick()

        self.assertIsNotNone(connector._timer_ids['conditions_met'])
        controller.trigger_chain_out.assert_not_called()

        sog_handler(sog_0_07)
        rpm_handler(port_speed_1800)

        # make sure stb rpm is ignored
        stb_speed_1300 =  {'canId': 166854712, 'prio': 2, 'src': 56, 'dst': 255, 'pgn': 127488, 'timestamp': '2025-05-16T13:57:41.254Z', 
                           'fields': {'Instance': 'Dual Engine Starboard', 'Speed': 1300, 'Boost Pressure': 0}, 'description': 'Engine Parameters, Rapid Update'}

        rpm_handler(stb_speed_1300)
        timer_provider.tick()

        self.assertIsNone(connector._timer_ids['conditions_met'])
        controller.trigger_chain_out.assert_called_once()



    def test_none_comparaisons(self):
        # when first initialized, values are None in the connector which triggers error when comparing to int
        sog_handler = None
        rpm_handler = None

        def _set_handler(pgn, the_handler):
            nonlocal sog_handler
            nonlocal rpm_handler
            if pgn == 129026:
                sog_handler = the_handler
            else:
                rpm_handler = the_handler

        mock_bridge = MagicMock()
        mock_bridge.add_pgn_handler = MagicMock(side_effect=_set_handler)        


        connector = NMEASOGRPMConnector(lambda: timer_provider, MockSettingsDevice,  mock_bridge)

        controller = MagicMock()
        controller.trigger_chain_out   = MagicMock()
        connector.set_controller(controller)


        sog_0_07 = {'canId': 167248387, 'prio': 2, 'src': 3, 'dst': 255, 'pgn': 129026, 'timestamp': '2025-05-16T13:51:59.279Z', 
                   'fields': {'SID': 208, 'COG Reference': 'True', 'COG': 0.2787, 'SOG': 0.07}, 'description': 'COG & SOG, Rapid Update'}

        sog_0_4 = {'canId': 167248387, 'prio': 2, 'src': 3, 'dst': 255, 'pgn': 129026, 'timestamp': '2025-05-16T13:51:59.279Z', 
                   'fields': {'SID': 208, 'COG Reference': 'True', 'COG': 0.2787, 'SOG': 0.4}, 'description': 'COG & SOG, Rapid Update'}


        port_speed_1300 = {'canId': 166854714, 'prio': 2, 'src': 58, 'dst': 255, 'pgn': 127488, 'timestamp': '2025-05-16T13:57:08.889Z', 
                           'fields': {'Instance': 'Single Engine or Dual Engine Port', 'Speed': 1300, 'Boost Pressure': 0}, 'description': 'Engine Parameters, Rapid Update'}

        port_speed_1800 = {'canId': 166854714, 'prio': 2, 'src': 58, 'dst': 255, 'pgn': 127488, 'timestamp': '2025-05-16T13:57:08.889Z', 
                           'fields': {'Instance': 'Single Engine or Dual Engine Port', 'Speed': 1800, 'Boost Pressure': 0}, 'description': 'Engine Parameters, Rapid Update'}


        stb_speed_1300 =  {'canId': 166854712, 'prio': 2, 'src': 56, 'dst': 255, 'pgn': 127488, 'timestamp': '2025-05-16T13:57:41.254Z', 
                           'fields': {'Instance': 'Dual Engine Starboard', 'Speed': 1300, 'Boost Pressure': 0}, 'description': 'Engine Parameters, Rapid Update'}


        stb_speed_1800 =  {'canId': 166854712, 'prio': 2, 'src': 56, 'dst': 255, 'pgn': 127488, 'timestamp': '2025-05-16T13:57:41.254Z', 
                           'fields': {'Instance': 'Dual Engine Starboard', 'Speed': 1800, 'Boost Pressure': 0}, 'description': 'Engine Parameters, Rapid Update'}


        # make sure that connector's _conditions_met are correctly handling None values

        rpm_handler(port_speed_1800)
        sog_handler(sog_0_07)

        # TODO XXX : make this test more robust


    def test_listen_only_in_drop_point_set_state(self):
        sog_handler = None
        rpm_handler = None

        def _set_handler(pgn, the_handler):
            nonlocal sog_handler
            nonlocal rpm_handler
            if pgn == 129026:
                sog_handler = the_handler
            else:
                rpm_handler = the_handler

        mock_bridge = MagicMock()
        mock_bridge.add_pgn_handler = MagicMock(side_effect=_set_handler)        


        connector = NMEASOGRPMConnector(lambda: timer_provider, MockSettingsDevice,  mock_bridge)

        controller = MagicMock()
        controller.trigger_chain_out   = MagicMock()
        connector.set_controller(controller)


        sog_0_07 = {'canId': 167248387, 'prio': 2, 'src': 3, 'dst': 255, 'pgn': 129026, 'timestamp': '2025-05-16T13:51:59.279Z', 
                   'fields': {'SID': 208, 'COG Reference': 'True', 'COG': 0.2787, 'SOG': 0.07}, 'description': 'COG & SOG, Rapid Update'}

        sog_0_4 = {'canId': 167248387, 'prio': 2, 'src': 3, 'dst': 255, 'pgn': 129026, 'timestamp': '2025-05-16T13:51:59.279Z', 
                   'fields': {'SID': 208, 'COG Reference': 'True', 'COG': 0.2787, 'SOG': 0.4}, 'description': 'COG & SOG, Rapid Update'}


        port_speed_1300 = {'canId': 166854714, 'prio': 2, 'src': 58, 'dst': 255, 'pgn': 127488, 'timestamp': '2025-05-16T13:57:08.889Z', 
                           'fields': {'Instance': 'Single Engine or Dual Engine Port', 'Speed': 1300, 'Boost Pressure': 0}, 'description': 'Engine Parameters, Rapid Update'}

        port_speed_1800 = {'canId': 166854714, 'prio': 2, 'src': 58, 'dst': 255, 'pgn': 127488, 'timestamp': '2025-05-16T13:57:08.889Z', 
                           'fields': {'Instance': 'Single Engine or Dual Engine Port', 'Speed': 1800, 'Boost Pressure': 0}, 'description': 'Engine Parameters, Rapid Update'}


        stb_speed_1300 =  {'canId': 166854712, 'prio': 2, 'src': 56, 'dst': 255, 'pgn': 127488, 'timestamp': '2025-05-16T13:57:41.254Z', 
                           'fields': {'Instance': 'Dual Engine Starboard', 'Speed': 1300, 'Boost Pressure': 0}, 'description': 'Engine Parameters, Rapid Update'}


        stb_speed_1800 =  {'canId': 166854712, 'prio': 2, 'src': 56, 'dst': 255, 'pgn': 127488, 'timestamp': '2025-05-16T13:57:41.254Z', 
                           'fields': {'Instance': 'Dual Engine Starboard', 'Speed': 1800, 'Boost Pressure': 0}, 'description': 'Engine Parameters, Rapid Update'}


        # make sure that connector is only listening 

        rpm_handler(port_speed_1800)
        rpm_handler(stb_speed_1800)
        sog_handler(sog_0_07)

        controller.trigger_chain_out.assert_not_called()

        state_disabled = AnchorAlarmState('DISABLED', 'Anchor alarm disabled',"short message", 'info', False, {})
        state_drop_point_set = AnchorAlarmState('DROP_POINT_SET', 'Drop point set, please do blablala',"short message", 'info', False, {'drop_point': GPSPosition(10, 11)})

        connector.on_state_changed(state_drop_point_set)
        rpm_handler(port_speed_1800)
        rpm_handler(stb_speed_1800)
        sog_handler(sog_0_07)
        controller.trigger_chain_out.assert_not_called()

        timer_provider.tick()
        rpm_handler(port_speed_1800)
        rpm_handler(stb_speed_1800)
        sog_handler(sog_0_07)
        controller.trigger_chain_out.assert_not_called()

        timer_provider.tick()
        rpm_handler(port_speed_1800)
        rpm_handler(stb_speed_1800)
        sog_handler(sog_0_07)
        controller.trigger_chain_out.assert_not_called()

        connector.on_state_changed(state_disabled)
        timer_provider.tick()
        rpm_handler(port_speed_1800)
        rpm_handler(stb_speed_1800)
        sog_handler(sog_0_07)
        controller.trigger_chain_out.assert_not_called()

        timer_provider.tick()
        rpm_handler(port_speed_1800)
        rpm_handler(stb_speed_1800)
        sog_handler(sog_0_07)
        controller.trigger_chain_out.assert_not_called()


        connector.on_state_changed(state_drop_point_set)
        rpm_handler(port_speed_1800)
        rpm_handler(stb_speed_1800)
        sog_handler(sog_0_07)
        controller.trigger_chain_out.assert_not_called()

        timer_provider.tick()
        rpm_handler(port_speed_1800)
        rpm_handler(stb_speed_1800)
        sog_handler(sog_0_07)
        controller.trigger_chain_out.assert_not_called()

        timer_provider.tick()
        rpm_handler(port_speed_1800)
        rpm_handler(stb_speed_1800)
        sog_handler(sog_0_07)
        controller.trigger_chain_out.assert_not_called()

        timer_provider.tick()
        rpm_handler(port_speed_1800)
        rpm_handler(stb_speed_1800)
        sog_handler(sog_0_07)
        controller.trigger_chain_out.assert_called_once()


if __name__ == '__main__':
    unittest.main()