import sys
import os
sys.path.insert(1, os.path.join(sys.path[0], '..'))

from anchor_alarm_model import AnchorAlarmModel
from anchor_alarm_model import AnchorAlarmState
from anchor_alarm_model import AnchorAlarmConfiguration
from collections import namedtuple

import unittest
from unittest.mock import ANY

# TODO XXX : move that import somewhere
GPSPosition = namedtuple('GPSPosition', ['latitude', 'longitude'])


class TestAnchorAlarmModel(unittest.TestCase):

    def setUp(self):
        self.maxDiff = None
        self.last_state_change = None

        self.gps_position_anchor_down    = GPSPosition(18.5060715, -64.3725071)
        self.gps_position_16m            = GPSPosition(18.506100, -64.372655) 
        self.gps_position_21m            = GPSPosition(18.506105, -64.372700)
        self.gps_position_37m            = GPSPosition(18.506111, -64.372855)
        self.gps_position_64m            = GPSPosition(18.506511, -64.372900)
        self.gps_position_124m           = GPSPosition(18.507111, -64.372955)
        
        self.tolerance                   = 20

        self.out_of_radius_count         = 0

    def next_out_of_radius_count(self):
        self.out_of_radius_count+=1
        return self.out_of_radius_count


    def _update_last_state(self, state):
        self.last_state_change = state.state

    def assertState(self, anchor_alarm, expected_state_change, anchor_alarm_state):
        self.assertEqual(anchor_alarm.get_current_state()._asdict(), anchor_alarm_state._asdict())
        self.assertEqual(self.last_state_change, expected_state_change)
        self.last_state_change = None




    def _ticks_in_radius_with_some_no_gps(self, anchor_alarm):
        # tick at chain out gps position
        anchor_alarm.on_timer_tick(self.gps_position_21m)    
        self.assertState(anchor_alarm, None, AnchorAlarmState('IN_RADIUS', ANY, "info", False, {"state": 'IN_RADIUS', "radius_tolerance": self.tolerance, "drop_point": self.gps_position_anchor_down, "radius": 21, "no_gps_count": 0, "out_of_radius_count": 0, "alarm_muted_count": 0, "current_radius": 21}))

        # tick in radius
        anchor_alarm.on_timer_tick(self.gps_position_16m)
        self.assertState(anchor_alarm, None, AnchorAlarmState('IN_RADIUS', ANY, "info", False, {"state": 'IN_RADIUS', "radius_tolerance": self.tolerance, "drop_point": self.gps_position_anchor_down, "radius": 21, "no_gps_count": 0, "out_of_radius_count": 0, "alarm_muted_count": 0, "current_radius": 16}))

        # tick out radius but in tolerance
        anchor_alarm.on_timer_tick(self.gps_position_37m)
        self.assertState(anchor_alarm, None, AnchorAlarmState('IN_RADIUS', ANY, "info", False, {"state": 'IN_RADIUS', "radius_tolerance": self.tolerance, "drop_point": self.gps_position_anchor_down, "radius": 21, "no_gps_count": 0, "out_of_radius_count": 0, "alarm_muted_count": 0, "current_radius": 37}))

        # tick in radius again
        anchor_alarm.on_timer_tick(self.gps_position_16m)
        self.assertState(anchor_alarm, None, AnchorAlarmState('IN_RADIUS', ANY, "info", False, {"state": 'IN_RADIUS', "radius_tolerance": self.tolerance, "drop_point": self.gps_position_anchor_down, "radius": 21, "no_gps_count": 0, "out_of_radius_count": 0, "alarm_muted_count": 0, "current_radius": 16}))

        # tick in no gps 1/3
        anchor_alarm.on_timer_tick(None)
        self.assertState(anchor_alarm, None, AnchorAlarmState('IN_RADIUS', ANY, "info", False, {"state": 'IN_RADIUS', "radius_tolerance": self.tolerance, "drop_point": self.gps_position_anchor_down, "radius": 21, "no_gps_count": 1, "out_of_radius_count": 0, "alarm_muted_count": 0, "current_radius": None}))

        # tick in no gps 2/3
        anchor_alarm.on_timer_tick(None)
        self.assertState(anchor_alarm, None, AnchorAlarmState('IN_RADIUS', ANY, "info", False, {"state": 'IN_RADIUS', "radius_tolerance": self.tolerance, "drop_point": self.gps_position_anchor_down, "radius": 21, "no_gps_count": 2, "out_of_radius_count": 0, "alarm_muted_count": 0, "current_radius": None}))

        # tick in radius again
        anchor_alarm.on_timer_tick(self.gps_position_16m)
        self.assertState(anchor_alarm, None, AnchorAlarmState('IN_RADIUS', ANY, "info", False, {"state": 'IN_RADIUS', "radius_tolerance": self.tolerance, "drop_point": self.gps_position_anchor_down, "radius": 21, "no_gps_count": 0, "out_of_radius_count": 0, "alarm_muted_count": 0, "current_radius": 16}))



    def _no_gps_alarm_with_mute(self, anchor_alarm):

        # tick in no gps 1/3
        anchor_alarm.on_timer_tick(None)
        self.assertState(anchor_alarm, None, AnchorAlarmState("IN_RADIUS", ANY, "info", False, {"state": "IN_RADIUS", "radius_tolerance": self.tolerance, "drop_point": self.gps_position_anchor_down, "radius": 21, "no_gps_count": 1, "out_of_radius_count": 0, "alarm_muted_count": 0, "current_radius": None}))

        # tick in no gps 2/3
        anchor_alarm.on_timer_tick(None)
        self.assertState(anchor_alarm, None, AnchorAlarmState("IN_RADIUS", ANY, "info", False, {"state": "IN_RADIUS", "radius_tolerance": self.tolerance, "drop_point": self.gps_position_anchor_down, "radius": 21, "no_gps_count": 2, "out_of_radius_count": 0, "alarm_muted_count": 0, "current_radius": None}))

        # tick in no gps 3/3
        anchor_alarm.on_timer_tick(None)
        self.assertState(anchor_alarm, None, AnchorAlarmState("IN_RADIUS", ANY, "info", False, {"state": "IN_RADIUS", "radius_tolerance": self.tolerance, "drop_point": self.gps_position_anchor_down, "radius": 21, "no_gps_count": 3, "out_of_radius_count": 0, "alarm_muted_count": 0, "current_radius": None}))

        # tick in no gps alarm
        anchor_alarm.on_timer_tick(None)
        self.assertState(anchor_alarm, 'ALARM_NO_GPS', AnchorAlarmState('ALARM_NO_GPS', ANY, "emergency", False, {"state": 'ALARM_NO_GPS', "radius_tolerance": self.tolerance, "drop_point": self.gps_position_anchor_down, "radius": 21, "no_gps_count": 4, "out_of_radius_count": 0, "alarm_muted_count": 0, "current_radius": None}))

        # tick in no gps alarm
        anchor_alarm.on_timer_tick(None)
        self.assertState(anchor_alarm, None, AnchorAlarmState('ALARM_NO_GPS', ANY, "emergency", False, {"state": 'ALARM_NO_GPS', "radius_tolerance": self.tolerance, "drop_point": self.gps_position_anchor_down, "radius": 21, "no_gps_count": 5, "out_of_radius_count": 0, "alarm_muted_count": 0, "current_radius": None}))

        anchor_alarm.mute_alarm()
        self.assertState(anchor_alarm, 'ALARM_NO_GPS_MUTED', AnchorAlarmState('ALARM_NO_GPS_MUTED', ANY, "emergency", True, {"state": 'ALARM_NO_GPS_MUTED', "radius_tolerance": self.tolerance, "drop_point": self.gps_position_anchor_down, "radius": 21, "no_gps_count": 5, "out_of_radius_count": 0, "alarm_muted_count": 0, "current_radius": None}))

        # tick in no gps alarm mute 1/5
        anchor_alarm.on_timer_tick(None)
        self.assertState(anchor_alarm, None, AnchorAlarmState('ALARM_NO_GPS_MUTED', ANY, "emergency", True, {"state": 'ALARM_NO_GPS_MUTED', "radius_tolerance": self.tolerance, "drop_point": self.gps_position_anchor_down, "radius": 21, "no_gps_count": 6, "out_of_radius_count": 0, "alarm_muted_count": 1, "current_radius": None}))

         # tick in no gps alarm mute 2/5
        anchor_alarm.on_timer_tick(None)
        self.assertState(anchor_alarm, None, AnchorAlarmState('ALARM_NO_GPS_MUTED', ANY, "emergency", True, {"state": 'ALARM_NO_GPS_MUTED', "radius_tolerance": self.tolerance, "drop_point": self.gps_position_anchor_down, "radius": 21, "no_gps_count": 7, "out_of_radius_count": 0, "alarm_muted_count": 2, "current_radius": None}))

         # tick in no gps alarm mute 3/5
        anchor_alarm.on_timer_tick(None)
        self.assertState(anchor_alarm, None, AnchorAlarmState('ALARM_NO_GPS_MUTED', ANY, "emergency", True, {"state": 'ALARM_NO_GPS_MUTED', "radius_tolerance": self.tolerance, "drop_point": self.gps_position_anchor_down, "radius": 21, "no_gps_count": 8, "out_of_radius_count": 0, "alarm_muted_count": 3, "current_radius": None}))

         # tick in no gps alarm mute 4/5
        anchor_alarm.on_timer_tick(None)
        self.assertState(anchor_alarm, None, AnchorAlarmState('ALARM_NO_GPS_MUTED', ANY, "emergency", True, {"state": 'ALARM_NO_GPS_MUTED', "radius_tolerance": self.tolerance, "drop_point": self.gps_position_anchor_down, "radius": 21, "no_gps_count": 9, "out_of_radius_count": 0, "alarm_muted_count": 4, "current_radius": None}))

        # tick in no gps alarm mute 5/5
        anchor_alarm.on_timer_tick(None)
        self.assertState(anchor_alarm, None, AnchorAlarmState('ALARM_NO_GPS_MUTED', ANY, "emergency", True, {"state": 'ALARM_NO_GPS_MUTED', "radius_tolerance": self.tolerance, "drop_point": self.gps_position_anchor_down, "radius": 21, "no_gps_count": 10, "out_of_radius_count": 0, "alarm_muted_count": 5, "current_radius": None}))

        # tick in no gps alarm back to unmuted
        anchor_alarm.on_timer_tick(None)
        self.assertState(anchor_alarm, 'ALARM_NO_GPS', AnchorAlarmState('ALARM_NO_GPS', ANY, "emergency", False, {"state": 'ALARM_NO_GPS', "radius_tolerance": self.tolerance, "drop_point": self.gps_position_anchor_down, "radius": 21, "no_gps_count": 11, "out_of_radius_count": 0, "alarm_muted_count": 0, "current_radius": None}))

        # tick in no gps alarm 
        anchor_alarm.on_timer_tick(None)
        self.assertState(anchor_alarm, None, AnchorAlarmState('ALARM_NO_GPS', ANY, "emergency", False, {"state": 'ALARM_NO_GPS', "radius_tolerance": self.tolerance, "drop_point": self.gps_position_anchor_down, "radius": 21, "no_gps_count": 12, "out_of_radius_count": 0, "alarm_muted_count": 0, "current_radius": None}))



    def _tick_out_of_radius_with_mute_when_already_dragging(self, anchor_alarm):

        
        # tick out radius
        anchor_alarm.on_timer_tick(self.gps_position_124m)
        self.assertState(anchor_alarm, None, AnchorAlarmState('ALARM_DRAGGING', ANY, "emergency", False, {"state": 'ALARM_DRAGGING', "radius_tolerance": self.tolerance, "drop_point": self.gps_position_anchor_down, "radius": 21, "no_gps_count": 0, "out_of_radius_count": self.next_out_of_radius_count(), "alarm_muted_count": 0, "current_radius": 124}))


        # tick out radius
        anchor_alarm.on_timer_tick(self.gps_position_64m)
        self.assertState(anchor_alarm, None, AnchorAlarmState('ALARM_DRAGGING', ANY, "emergency", False, {"state": 'ALARM_DRAGGING', "radius_tolerance": self.tolerance, "drop_point": self.gps_position_anchor_down, "radius": 21, "no_gps_count": 0, "out_of_radius_count": self.next_out_of_radius_count(), "alarm_muted_count": 0, "current_radius": 64}))


        # tick out radius but in tolerance
        anchor_alarm.on_timer_tick(self.gps_position_37m)
        self.assertState(anchor_alarm, None, AnchorAlarmState('ALARM_DRAGGING', ANY, "emergency", False, {"state": 'ALARM_DRAGGING', "radius_tolerance": self.tolerance, "drop_point": self.gps_position_anchor_down, "radius": 21, "no_gps_count": 0, "out_of_radius_count": self.next_out_of_radius_count(), "alarm_muted_count": 0, "current_radius": 37}))


        # tick out radius
        anchor_alarm.on_timer_tick(self.gps_position_64m)
        self.assertState(anchor_alarm, None, AnchorAlarmState('ALARM_DRAGGING', ANY, "emergency", False, {"state": 'ALARM_DRAGGING', "radius_tolerance": self.tolerance, "drop_point": self.gps_position_anchor_down, "radius": 21, "no_gps_count": 0, "out_of_radius_count": self.next_out_of_radius_count(), "alarm_muted_count": 0, "current_radius": 64}))


        # tick in radius
        anchor_alarm.on_timer_tick(self.gps_position_16m)
        self.assertState(anchor_alarm, None, AnchorAlarmState('ALARM_DRAGGING', ANY, "emergency", False, {"state": 'ALARM_DRAGGING', "radius_tolerance": self.tolerance, "drop_point": self.gps_position_anchor_down, "radius": 21, "no_gps_count": 0, "out_of_radius_count": self.next_out_of_radius_count(), "alarm_muted_count": 0, "current_radius": 16}))


        # tick out radius
        anchor_alarm.on_timer_tick(self.gps_position_124m)
        self.assertState(anchor_alarm, None, AnchorAlarmState('ALARM_DRAGGING', ANY, "emergency", False, {"state": 'ALARM_DRAGGING', "radius_tolerance": self.tolerance, "drop_point": self.gps_position_anchor_down, "radius": 21, "no_gps_count": 0, "out_of_radius_count": self.next_out_of_radius_count(), "alarm_muted_count": 0, "current_radius": 124}))


        # mute alarm
        anchor_alarm.mute_alarm()
        self.assertState(anchor_alarm, 'ALARM_DRAGGING_MUTED', AnchorAlarmState('ALARM_DRAGGING_MUTED', ANY, "emergency", True, {"state": 'ALARM_DRAGGING_MUTED', "radius_tolerance": self.tolerance, "drop_point": self.gps_position_anchor_down, "radius": 21, "no_gps_count": 0, "out_of_radius_count": self.out_of_radius_count, "alarm_muted_count": 0, "current_radius": 124}))

        # mute alarm again, shouldn't do anything
        anchor_alarm.mute_alarm()
        self.assertState(anchor_alarm, None, AnchorAlarmState('ALARM_DRAGGING_MUTED', ANY, "emergency", True, {"state": 'ALARM_DRAGGING_MUTED', "radius_tolerance": self.tolerance, "drop_point": self.gps_position_anchor_down, "radius": 21, "no_gps_count": 0, "out_of_radius_count": self.out_of_radius_count, "alarm_muted_count": 0, "current_radius": 124}))

        # tick out radius mute 1/5
        anchor_alarm.on_timer_tick(self.gps_position_124m)
        self.assertState(anchor_alarm, None, AnchorAlarmState('ALARM_DRAGGING_MUTED', ANY, "emergency", True, {"state": 'ALARM_DRAGGING_MUTED', "radius_tolerance": self.tolerance, "drop_point": self.gps_position_anchor_down, "radius": 21, "no_gps_count": 0, "out_of_radius_count": self.next_out_of_radius_count(), "alarm_muted_count": 1, "current_radius": 124}))

        # mute alarm again, shouldn't do anything
        anchor_alarm.mute_alarm()
        self.assertState(anchor_alarm, None, AnchorAlarmState('ALARM_DRAGGING_MUTED', ANY, "emergency", True, {"state": 'ALARM_DRAGGING_MUTED', "radius_tolerance": self.tolerance, "drop_point": self.gps_position_anchor_down, "radius": 21, "no_gps_count": 0, "out_of_radius_count": self.out_of_radius_count, "alarm_muted_count": 1, "current_radius": 124}))

        # tick out radius mute 2/5
        anchor_alarm.on_timer_tick(self.gps_position_124m)
        self.assertState(anchor_alarm, None, AnchorAlarmState('ALARM_DRAGGING_MUTED', ANY, "emergency", True, {"state": 'ALARM_DRAGGING_MUTED', "radius_tolerance": self.tolerance, "drop_point": self.gps_position_anchor_down, "radius": 21, "no_gps_count": 0, "out_of_radius_count": self.next_out_of_radius_count(), "alarm_muted_count": 2, "current_radius": 124}))


        # tick in radius mute 3/5
        anchor_alarm.on_timer_tick(self.gps_position_16m)
        self.assertState(anchor_alarm, None, AnchorAlarmState('ALARM_DRAGGING_MUTED', ANY, "emergency", True, {"state": 'ALARM_DRAGGING_MUTED', "radius_tolerance": self.tolerance, "drop_point": self.gps_position_anchor_down, "radius": 21, "no_gps_count": 0, "out_of_radius_count": self.next_out_of_radius_count(), "alarm_muted_count": 3, "current_radius": 16}))


        # tick out radius mute 4/5
        anchor_alarm.on_timer_tick(self.gps_position_64m)
        self.assertState(anchor_alarm, None, AnchorAlarmState('ALARM_DRAGGING_MUTED', ANY, "emergency", True, {"state": 'ALARM_DRAGGING_MUTED', "radius_tolerance": self.tolerance, "drop_point": self.gps_position_anchor_down, "radius": 21, "no_gps_count": 0, "out_of_radius_count": self.next_out_of_radius_count(), "alarm_muted_count": 4, "current_radius": 64}))


        # tick out radius but in tolerance mute 5/5
        anchor_alarm.on_timer_tick(self.gps_position_37m)
        self.assertState(anchor_alarm, None, AnchorAlarmState('ALARM_DRAGGING_MUTED', ANY, "emergency", True, {"state": 'ALARM_DRAGGING_MUTED', "radius_tolerance": self.tolerance, "drop_point": self.gps_position_anchor_down, "radius": 21, "no_gps_count": 0, "out_of_radius_count": self.next_out_of_radius_count(), "alarm_muted_count": 5, "current_radius": 37}))


        # tick out radius, alarm_dragging again
        anchor_alarm.on_timer_tick(self.gps_position_64m)
        self.assertState(anchor_alarm, 'ALARM_DRAGGING', AnchorAlarmState('ALARM_DRAGGING', ANY, "emergency", False, {"state": 'ALARM_DRAGGING', "radius_tolerance": self.tolerance, "drop_point": self.gps_position_anchor_down, "radius": 21, "no_gps_count": 0, "out_of_radius_count": self.next_out_of_radius_count(), "alarm_muted_count": 0, "current_radius": 64}))

        # tick out radius n
        anchor_alarm.on_timer_tick(self.gps_position_64m)
        self.assertState(anchor_alarm, None, AnchorAlarmState('ALARM_DRAGGING', ANY, "emergency", False, {"state": 'ALARM_DRAGGING', "radius_tolerance": self.tolerance, "drop_point": self.gps_position_anchor_down, "radius": 21, "no_gps_count": 0, "out_of_radius_count": self.next_out_of_radius_count(), "alarm_muted_count": 0, "current_radius": 64}))






    def _no_gps_alarm_with_mute_when_dragging(self, anchor_alarm):

        # tick in no gps 1/3
        anchor_alarm.on_timer_tick(None)
        self.assertState(anchor_alarm, None, AnchorAlarmState("ALARM_DRAGGING", ANY, "emergency", False, {"state": "ALARM_DRAGGING", "radius_tolerance": self.tolerance, "drop_point": self.gps_position_anchor_down, "radius": 21, "no_gps_count": 1, "out_of_radius_count": self.next_out_of_radius_count(), "alarm_muted_count": 0, "current_radius": None}))

        # tick in no gps 2/3
        anchor_alarm.on_timer_tick(None)
        self.assertState(anchor_alarm, None, AnchorAlarmState("ALARM_DRAGGING", ANY, "emergency", False, {"state": "ALARM_DRAGGING", "radius_tolerance": self.tolerance, "drop_point": self.gps_position_anchor_down, "radius": 21, "no_gps_count": 2, "out_of_radius_count": self.next_out_of_radius_count(), "alarm_muted_count": 0, "current_radius": None}))

        # tick in no gps 3/3
        anchor_alarm.on_timer_tick(None)
        self.assertState(anchor_alarm, None, AnchorAlarmState("ALARM_DRAGGING", ANY, "emergency", False, {"state": "ALARM_DRAGGING", "radius_tolerance": self.tolerance, "drop_point": self.gps_position_anchor_down, "radius": 21, "no_gps_count": 3, "out_of_radius_count": self.next_out_of_radius_count(), "alarm_muted_count": 0, "current_radius": None}))

        # tick in no gps alarm
        anchor_alarm.on_timer_tick(None)
        self.assertState(anchor_alarm, None, AnchorAlarmState('ALARM_DRAGGING', ANY, "emergency", False, {"state": 'ALARM_DRAGGING', "radius_tolerance": self.tolerance, "drop_point": self.gps_position_anchor_down, "radius": 21, "no_gps_count": 4, "out_of_radius_count": self.next_out_of_radius_count(), "alarm_muted_count": 0, "current_radius": None}))

        # tick in no gps alarm
        anchor_alarm.on_timer_tick(None)
        self.assertState(anchor_alarm, None, AnchorAlarmState('ALARM_DRAGGING', ANY, "emergency", False, {"state": 'ALARM_DRAGGING', "radius_tolerance": self.tolerance, "drop_point": self.gps_position_anchor_down, "radius": 21, "no_gps_count": 5, "out_of_radius_count": self.next_out_of_radius_count(), "alarm_muted_count": 0, "current_radius": None}))

        anchor_alarm.mute_alarm()
        self.assertState(anchor_alarm, 'ALARM_DRAGGING_MUTED', AnchorAlarmState('ALARM_DRAGGING_MUTED', ANY, "emergency", True, {"state": 'ALARM_DRAGGING_MUTED', "radius_tolerance": self.tolerance, "drop_point": self.gps_position_anchor_down, "radius": 21, "no_gps_count": 5, "out_of_radius_count": self.out_of_radius_count, "alarm_muted_count": 0, "current_radius": None}))

        # tick in no gps alarm mute 1/5
        anchor_alarm.on_timer_tick(None)
        self.assertState(anchor_alarm, None, AnchorAlarmState('ALARM_DRAGGING_MUTED', ANY, "emergency", True, {"state": 'ALARM_DRAGGING_MUTED', "radius_tolerance": self.tolerance, "drop_point": self.gps_position_anchor_down, "radius": 21, "no_gps_count": 6, "out_of_radius_count": self.next_out_of_radius_count(), "alarm_muted_count": 1, "current_radius": None}))

         # tick in no gps alarm mute 2/5
        anchor_alarm.on_timer_tick(None)
        self.assertState(anchor_alarm, None, AnchorAlarmState('ALARM_DRAGGING_MUTED', ANY, "emergency", True, {"state": 'ALARM_DRAGGING_MUTED', "radius_tolerance": self.tolerance, "drop_point": self.gps_position_anchor_down, "radius": 21, "no_gps_count": 7, "out_of_radius_count": self.next_out_of_radius_count(), "alarm_muted_count": 2, "current_radius": None}))

         # tick in no gps alarm mute 3/5
        anchor_alarm.on_timer_tick(None)
        self.assertState(anchor_alarm, None, AnchorAlarmState('ALARM_DRAGGING_MUTED', ANY, "emergency", True, {"state": 'ALARM_DRAGGING_MUTED', "radius_tolerance": self.tolerance, "drop_point": self.gps_position_anchor_down, "radius": 21, "no_gps_count": 8, "out_of_radius_count": self.next_out_of_radius_count(), "alarm_muted_count": 3, "current_radius": None}))

         # tick in no gps alarm mute 4/5
        anchor_alarm.on_timer_tick(None)
        self.assertState(anchor_alarm, None, AnchorAlarmState('ALARM_DRAGGING_MUTED', ANY, "emergency", True, {"state": 'ALARM_DRAGGING_MUTED', "radius_tolerance": self.tolerance, "drop_point": self.gps_position_anchor_down, "radius": 21, "no_gps_count": 9, "out_of_radius_count": self.next_out_of_radius_count(), "alarm_muted_count": 4, "current_radius": None}))

        # tick in no gps alarm mute 5/5
        anchor_alarm.on_timer_tick(None)
        self.assertState(anchor_alarm, None, AnchorAlarmState('ALARM_DRAGGING_MUTED', ANY, "emergency", True, {"state": 'ALARM_DRAGGING_MUTED', "radius_tolerance": self.tolerance, "drop_point": self.gps_position_anchor_down, "radius": 21, "no_gps_count": 10, "out_of_radius_count": self.next_out_of_radius_count(), "alarm_muted_count": 5, "current_radius": None}))

        # tick in no gps alarm back to unmuted
        anchor_alarm.on_timer_tick(None)
        self.assertState(anchor_alarm, 'ALARM_DRAGGING', AnchorAlarmState('ALARM_DRAGGING', ANY, "emergency", False, {"state": 'ALARM_DRAGGING', "radius_tolerance": self.tolerance, "drop_point": self.gps_position_anchor_down, "radius": 21, "no_gps_count": 11, "out_of_radius_count": self.next_out_of_radius_count(), "alarm_muted_count": 0, "current_radius": None}))

        # tick in no gps alarm 
        anchor_alarm.on_timer_tick(None)
        self.assertState(anchor_alarm, None, AnchorAlarmState('ALARM_DRAGGING', ANY, "emergency", False, {"state": 'ALARM_DRAGGING', "radius_tolerance": self.tolerance, "drop_point": self.gps_position_anchor_down, "radius": 21, "no_gps_count": 12, "out_of_radius_count": self.next_out_of_radius_count(), "alarm_muted_count": 0, "current_radius": None}))


        # tick outside radius
        anchor_alarm.on_timer_tick(self.gps_position_64m)
        self.assertState(anchor_alarm, None, AnchorAlarmState('ALARM_DRAGGING', ANY, "emergency", False, {"state": 'ALARM_DRAGGING', "radius_tolerance": self.tolerance, "drop_point": self.gps_position_anchor_down, "radius": 21, "no_gps_count": 0, "out_of_radius_count": self.next_out_of_radius_count(), "alarm_muted_count": 0, "current_radius": 64}))

        # mute alarm
        anchor_alarm.mute_alarm()
        self.assertState(anchor_alarm, 'ALARM_DRAGGING_MUTED', AnchorAlarmState('ALARM_DRAGGING_MUTED', ANY, "emergency", True, {"state": 'ALARM_DRAGGING_MUTED', "radius_tolerance": self.tolerance, "drop_point": self.gps_position_anchor_down, "radius": 21, "no_gps_count": 0, "out_of_radius_count": self.out_of_radius_count, "alarm_muted_count": 0, "current_radius": 64}))

        # tick out radius mute 1/5
        anchor_alarm.on_timer_tick(self.gps_position_124m)
        self.assertState(anchor_alarm, None, AnchorAlarmState('ALARM_DRAGGING_MUTED', ANY, "emergency", True, {"state": 'ALARM_DRAGGING_MUTED', "radius_tolerance": self.tolerance, "drop_point": self.gps_position_anchor_down, "radius": 21, "no_gps_count": 0, "out_of_radius_count": self.next_out_of_radius_count(), "alarm_muted_count": 1, "current_radius": 124}))


        # tick in no gps alarm mute 2/5
        anchor_alarm.on_timer_tick(None)
        self.assertState(anchor_alarm, None, AnchorAlarmState('ALARM_DRAGGING_MUTED', ANY, "emergency", True, {"state": 'ALARM_DRAGGING_MUTED', "radius_tolerance": self.tolerance, "drop_point": self.gps_position_anchor_down, "radius": 21, "no_gps_count": 1, "out_of_radius_count": self.next_out_of_radius_count(), "alarm_muted_count": 2, "current_radius": None}))

        # tick in no gps alarm mute 3/5
        anchor_alarm.on_timer_tick(None)
        self.assertState(anchor_alarm, None, AnchorAlarmState('ALARM_DRAGGING_MUTED', ANY, "emergency", True, {"state": 'ALARM_DRAGGING_MUTED', "radius_tolerance": self.tolerance, "drop_point": self.gps_position_anchor_down, "radius": 21, "no_gps_count": 2, "out_of_radius_count": self.next_out_of_radius_count(), "alarm_muted_count": 3, "current_radius": None}))

        # tick in no gps alarm mute 4/5
        anchor_alarm.on_timer_tick(None)
        self.assertState(anchor_alarm, None, AnchorAlarmState('ALARM_DRAGGING_MUTED', ANY, "emergency", True, {"state": 'ALARM_DRAGGING_MUTED', "radius_tolerance": self.tolerance, "drop_point": self.gps_position_anchor_down, "radius": 21, "no_gps_count": 3, "out_of_radius_count": self.next_out_of_radius_count(), "alarm_muted_count": 4, "current_radius": None}))

        # tick in no gps alarm mute 5/5
        anchor_alarm.on_timer_tick(None)
        self.assertState(anchor_alarm, None, AnchorAlarmState('ALARM_DRAGGING_MUTED', ANY, "emergency", True, {"state": 'ALARM_DRAGGING_MUTED', "radius_tolerance": self.tolerance, "drop_point": self.gps_position_anchor_down, "radius": 21, "no_gps_count": 4, "out_of_radius_count": self.next_out_of_radius_count(), "alarm_muted_count": 5, "current_radius": None}))

        # tick in no gps 
        anchor_alarm.on_timer_tick(None)
        self.assertState(anchor_alarm, 'ALARM_DRAGGING', AnchorAlarmState('ALARM_DRAGGING', ANY, "emergency", False, {"state": 'ALARM_DRAGGING', "radius_tolerance": self.tolerance, "drop_point": self.gps_position_anchor_down, "radius": 21, "no_gps_count": 5, "out_of_radius_count": self.next_out_of_radius_count(), "alarm_muted_count": 0, "current_radius": None}))



    def _out_of_sequence_calls(self, anchor_alarm):
        anchor_alarm_state = anchor_alarm.get_current_state()

        ## Wrong calls for DISABLED
        if ( anchor_alarm_state.state == 'DISABLED' ): 
            #anchor_alarm.anchor_down(self.gps_position_anchor_down)

            anchor_alarm.chain_out(self.gps_position_21m)
            self.assertState(anchor_alarm, None, anchor_alarm_state)  

            anchor_alarm.on_timer_tick(self.gps_position_21m)
            self.assertState(anchor_alarm, None, anchor_alarm_state) 

            anchor_alarm.mute_alarm()
            self.assertState(anchor_alarm, None, anchor_alarm_state) 

            anchor_alarm.anchor_up()
            self.assertState(anchor_alarm, None, anchor_alarm_state)  # TODO XXX : why does that trigger an event change ?

            #anchor_alarm.reset_state(self.gps_position_anchor_down, 21)

        elif ( anchor_alarm_state.state == 'DROP_POINT_SET' ): 
            anchor_alarm.anchor_down(self.gps_position_anchor_down)
            self.assertState(anchor_alarm, None, anchor_alarm_state) 

            # anchor_alarm.chain_out(self.gps_position_21m)

            anchor_alarm.on_timer_tick(self.gps_position_21m)
            self.assertState(anchor_alarm, None, anchor_alarm_state) 

            anchor_alarm.mute_alarm()
            self.assertState(anchor_alarm, None, anchor_alarm_state) 

            # anchor_alarm.anchor_up()

            with self.assertRaises(RuntimeError):
                anchor_alarm.reset_state(self.gps_position_anchor_down, 21)
            self.assertState(anchor_alarm, None, anchor_alarm_state) 

        elif ( anchor_alarm_state.state in ['IN_RADIUS'] ): 
            anchor_alarm.anchor_down(self.gps_position_anchor_down)
            self.assertState(anchor_alarm, None, anchor_alarm_state) 

            anchor_alarm.chain_out(self.gps_position_21m)               # TODO XXX : when to allow reset radius?
            self.assertState(anchor_alarm, None, anchor_alarm_state) 

            #anchor_alarm.on_timer_tick(self.gps_position_21m)
            #self.assertState(anchor_alarm, None, anchor_alarm_state) 

            anchor_alarm.mute_alarm()
            self.assertState(anchor_alarm, None, anchor_alarm_state) 

            # anchor_alarm.anchor_up()

            with self.assertRaises(RuntimeError):
                anchor_alarm.reset_state(self.gps_position_anchor_down, 21)
            self.assertState(anchor_alarm, None, anchor_alarm_state) 

        elif ( anchor_alarm_state.state in ['ALARM_NO_GPS'] ): 
            anchor_alarm.anchor_down(self.gps_position_anchor_down)
            self.assertState(anchor_alarm, None, anchor_alarm_state) 

            anchor_alarm.chain_out(self.gps_position_21m)               # TODO XXX : when to allow reset radius?
            self.assertState(anchor_alarm, None, anchor_alarm_state) 

            #anchor_alarm.on_timer_tick(self.gps_position_21m)
            #self.assertState(anchor_alarm, None, anchor_alarm_state) 

            #anchor_alarm.mute_alarm()
            #self.assertState(anchor_alarm, None, anchor_alarm_state) 

            # anchor_alarm.anchor_up()

            with self.assertRaises(RuntimeError):
                anchor_alarm.reset_state(self.gps_position_anchor_down, 21)
            self.assertState(anchor_alarm, None, anchor_alarm_state) 

        elif ( anchor_alarm_state.state in ['ALARM_DRAGGING'] ): 
            anchor_alarm.anchor_down(self.gps_position_anchor_down)
            self.assertState(anchor_alarm, None, anchor_alarm_state) 

            #anchor_alarm.chain_out(self.gps_position_21m) 
            #self.assertState(anchor_alarm, None, anchor_alarm_state) 

            #anchor_alarm.on_timer_tick(self.gps_position_21m)
            #self.assertState(anchor_alarm, None, anchor_alarm_state) 

            #anchor_alarm.mute_alarm()
            #self.assertState(anchor_alarm, None, anchor_alarm_state) 

            # anchor_alarm.anchor_up()

            with self.assertRaises(RuntimeError):
                anchor_alarm.reset_state(self.gps_position_anchor_down, 21)
            self.assertState(anchor_alarm, None, anchor_alarm_state) 



    def test_complete_cycle(self):

        self.out_of_radius_count         = 0
        anchor_alarm =  AnchorAlarmModel(self._update_last_state)
        anchor_alarm.update_configuration(AnchorAlarmConfiguration(self.tolerance, 3, 5))
        
        self.assertState(anchor_alarm, None, AnchorAlarmState('DISABLED', ANY, "info", False, {"state": 'DISABLED', "radius_tolerance": self.tolerance, "drop_point": None, "radius": None, "no_gps_count": 0, "out_of_radius_count": 0, "alarm_muted_count": 0, "current_radius": None}))
        self._out_of_sequence_calls(anchor_alarm)

        # anchor down
        anchor_alarm.anchor_down(self.gps_position_anchor_down)
        self.assertState(anchor_alarm, 'DROP_POINT_SET', AnchorAlarmState('DROP_POINT_SET', ANY, "info", False, {"state": 'DROP_POINT_SET', "radius_tolerance": self.tolerance, "drop_point": self.gps_position_anchor_down, "radius": None, "no_gps_count": 0, "out_of_radius_count": 0, "alarm_muted_count": 0, "current_radius": None}))
        self._out_of_sequence_calls(anchor_alarm)


        # let chain out
        anchor_alarm.chain_out(self.gps_position_21m)
        self.assertState(anchor_alarm, 'IN_RADIUS', AnchorAlarmState('IN_RADIUS', ANY, "info", False, {"state": 'IN_RADIUS', "radius_tolerance": self.tolerance, "drop_point": self.gps_position_anchor_down, "radius": 21, "no_gps_count": 0, "out_of_radius_count": 0, "alarm_muted_count": 0, "current_radius": 21}))
        self._out_of_sequence_calls(anchor_alarm)

        # test various ticks in radius, with some no_gps with last tick in radius
        self._ticks_in_radius_with_some_no_gps(anchor_alarm)

        # test no gps alarm then mute then alarm again
        self._no_gps_alarm_with_mute(anchor_alarm)    
        self._out_of_sequence_calls(anchor_alarm)

        # TODO XXX : how can we pass the feedback that the bopat is again in safe radius ?

        # tick back in radius to verify that we have the IN_RADIUS state change event
        anchor_alarm.on_timer_tick(self.gps_position_16m)
        self.assertState(anchor_alarm, 'IN_RADIUS', AnchorAlarmState('IN_RADIUS', ANY, "info", False, {"state": 'IN_RADIUS', "radius_tolerance": self.tolerance, "drop_point": self.gps_position_anchor_down, "radius": 21, "no_gps_count": 0, "out_of_radius_count": 0, "alarm_muted_count": 0, "current_radius": 16}))
        self._out_of_sequence_calls(anchor_alarm)

        # test various ticks in radius again, with some no_gps with last tick in radius
        self._ticks_in_radius_with_some_no_gps(anchor_alarm)
        self._out_of_sequence_calls(anchor_alarm)

        
        # tick out radius, check state change event
        anchor_alarm.on_timer_tick(self.gps_position_64m)
        self.assertState(anchor_alarm, 'ALARM_DRAGGING', AnchorAlarmState('ALARM_DRAGGING', ANY, "emergency", False, {"state": 'ALARM_DRAGGING', "radius_tolerance": self.tolerance, "drop_point": self.gps_position_anchor_down, "radius": 21, "no_gps_count": 0, "out_of_radius_count": self.next_out_of_radius_count(), "alarm_muted_count": 0, "current_radius": 64}))
        self._out_of_sequence_calls(anchor_alarm)

        # test out of radius with mute
        self._tick_out_of_radius_with_mute_when_already_dragging(anchor_alarm)
        self._out_of_sequence_calls(anchor_alarm)

        # test no gps with mute when already dragging
        self._no_gps_alarm_with_mute_when_dragging(anchor_alarm)        
        self._out_of_sequence_calls(anchor_alarm)

        # test again out of radius with mute
        self._tick_out_of_radius_with_mute_when_already_dragging(anchor_alarm)
        self._out_of_sequence_calls(anchor_alarm)


        # TODO XXX : test set_tolerance

        # reset radius
        anchor_alarm.chain_out(self.gps_position_21m)
        self.out_of_radius_count = 0
        self.assertState(anchor_alarm, 'IN_RADIUS', AnchorAlarmState('IN_RADIUS', ANY, "info", False, {"state": 'IN_RADIUS', "radius_tolerance": self.tolerance, "drop_point": self.gps_position_anchor_down, "radius": 21, "no_gps_count": 0, "out_of_radius_count": 0, "alarm_muted_count": 0, "current_radius": 21}))
        self._out_of_sequence_calls(anchor_alarm)


        anchor_alarm.anchor_up()
        self.assertState(anchor_alarm, 'DISABLED', AnchorAlarmState('DISABLED', ANY, "info", False, {"state": 'DISABLED', "radius_tolerance": self.tolerance, "drop_point": None, "radius": None, "no_gps_count": 0, "out_of_radius_count": 0, "alarm_muted_count": 0, "current_radius": None}))
        self._out_of_sequence_calls(anchor_alarm)


    def test_anchor_up_from_disabled(self):
        # from DISABLED
        self.out_of_radius_count         = 0
        anchor_alarm =  AnchorAlarmModel(self._update_last_state)
        anchor_alarm.update_configuration(AnchorAlarmConfiguration(self.tolerance, 3, 5))
        
        self.assertState(anchor_alarm, None, AnchorAlarmState('DISABLED', ANY, "info", False, {"state": 'DISABLED', "radius_tolerance": self.tolerance, "drop_point": None, "radius": None, "no_gps_count": 0, "out_of_radius_count": 0, "alarm_muted_count": 0, "current_radius": None}))
        self._out_of_sequence_calls(anchor_alarm)

        anchor_alarm.anchor_up()
        self.assertState(anchor_alarm, None, AnchorAlarmState('DISABLED', ANY, "info", False, {"state": 'DISABLED', "radius_tolerance": self.tolerance, "drop_point": None, "radius": None, "no_gps_count": 0, "out_of_radius_count": 0, "alarm_muted_count": 0, "current_radius": None}))
        self._out_of_sequence_calls(anchor_alarm)



    def test_anchor_up_from_drop_point_set(self):
        # from DROP_POINT_SET
        self.out_of_radius_count         = 0
        anchor_alarm =  AnchorAlarmModel(self._update_last_state)
        anchor_alarm.update_configuration(AnchorAlarmConfiguration(self.tolerance, 3, 5))
        
        self.assertState(anchor_alarm, None, AnchorAlarmState('DISABLED', ANY, "info", False, {"state": 'DISABLED', "radius_tolerance": self.tolerance, "drop_point": None, "radius": None, "no_gps_count": 0, "out_of_radius_count": 0, "alarm_muted_count": 0, "current_radius": None}))
        self._out_of_sequence_calls(anchor_alarm)

        anchor_alarm.anchor_down(self.gps_position_anchor_down)
        self.assertState(anchor_alarm, 'DROP_POINT_SET', AnchorAlarmState('DROP_POINT_SET', ANY, "info", False, {"state": 'DROP_POINT_SET', "radius_tolerance": self.tolerance, "drop_point": self.gps_position_anchor_down, "radius": None, "no_gps_count": 0, "out_of_radius_count": 0, "alarm_muted_count": 0, "current_radius": None}))
        self._out_of_sequence_calls(anchor_alarm)

        anchor_alarm.anchor_up()
        self.assertState(anchor_alarm, 'DISABLED', AnchorAlarmState('DISABLED', ANY, "info", False, {"state": 'DISABLED', "radius_tolerance": self.tolerance, "drop_point": None, "radius": None, "no_gps_count": 0, "out_of_radius_count": 0, "alarm_muted_count": 0, "current_radius": None}))
        self._out_of_sequence_calls(anchor_alarm)


    def test_anchor_up_from_with_radius_set(self):
        self.out_of_radius_count         = 0
        anchor_alarm =  AnchorAlarmModel(self._update_last_state)
        anchor_alarm.update_configuration(AnchorAlarmConfiguration(self.tolerance, 3, 5))
        
        self.assertState(anchor_alarm, None, AnchorAlarmState('DISABLED', ANY, "info", False, {"state": 'DISABLED', "radius_tolerance": self.tolerance, "drop_point": None, "radius": None, "no_gps_count": 0, "out_of_radius_count": 0, "alarm_muted_count": 0, "current_radius": None}))
        self._out_of_sequence_calls(anchor_alarm)

        anchor_alarm.anchor_down(self.gps_position_anchor_down)
        self.assertState(anchor_alarm, 'DROP_POINT_SET', AnchorAlarmState('DROP_POINT_SET', ANY, "info", False, {"state": 'DROP_POINT_SET', "radius_tolerance": self.tolerance, "drop_point": self.gps_position_anchor_down, "radius": None, "no_gps_count": 0, "out_of_radius_count": 0, "alarm_muted_count": 0, "current_radius": None}))
        self._out_of_sequence_calls(anchor_alarm)

        anchor_alarm.chain_out(self.gps_position_21m)
        self.assertState(anchor_alarm, 'IN_RADIUS', AnchorAlarmState('IN_RADIUS', ANY, "info", False, {"state": 'IN_RADIUS', "radius_tolerance": self.tolerance, "drop_point": self.gps_position_anchor_down, "radius": 21, "no_gps_count": 0, "out_of_radius_count": 0, "alarm_muted_count": 0, "current_radius": 21}))
        self._out_of_sequence_calls(anchor_alarm)

        anchor_alarm.anchor_up()
        self.assertState(anchor_alarm, 'DISABLED', AnchorAlarmState('DISABLED', ANY, "info", False, {"state": 'DISABLED', "radius_tolerance": self.tolerance, "drop_point": None, "radius": None, "no_gps_count": 0, "out_of_radius_count": 0, "alarm_muted_count": 0, "current_radius": None}))
        self._out_of_sequence_calls(anchor_alarm)
        

    def test_anchor_up_after_a_few_ticks(self):
        # anchor_up after a few ticks
        self.out_of_radius_count         = 0
        anchor_alarm =  AnchorAlarmModel(self._update_last_state)
        anchor_alarm.update_configuration(AnchorAlarmConfiguration(self.tolerance, 3, 5))
        
        self.assertState(anchor_alarm, None, AnchorAlarmState('DISABLED', ANY, "info", False, {"state": 'DISABLED', "radius_tolerance": self.tolerance, "drop_point": None, "radius": None, "no_gps_count": 0, "out_of_radius_count": 0, "alarm_muted_count": 0, "current_radius": None}))
        self._out_of_sequence_calls(anchor_alarm)

        # anchor down
        anchor_alarm.anchor_down(self.gps_position_anchor_down)
        self.assertState(anchor_alarm, 'DROP_POINT_SET', AnchorAlarmState('DROP_POINT_SET', ANY, "info", False, {"state": 'DROP_POINT_SET', "radius_tolerance": self.tolerance, "drop_point": self.gps_position_anchor_down, "radius": None, "no_gps_count": 0, "out_of_radius_count": 0, "alarm_muted_count": 0, "current_radius": None}))
        self._out_of_sequence_calls(anchor_alarm)


        # let chain out
        anchor_alarm.chain_out(self.gps_position_21m)
        self.assertState(anchor_alarm, 'IN_RADIUS', AnchorAlarmState('IN_RADIUS', ANY, "info", False, {"state": 'IN_RADIUS', "radius_tolerance": self.tolerance, "drop_point": self.gps_position_anchor_down, "radius": 21, "no_gps_count": 0, "out_of_radius_count": 0, "alarm_muted_count": 0, "current_radius": 21}))
        self._out_of_sequence_calls(anchor_alarm)

        # test various ticks in radius, with some no_gps with last tick in radius
        self._ticks_in_radius_with_some_no_gps(anchor_alarm)

        anchor_alarm.anchor_up()
        self.assertState(anchor_alarm, 'DISABLED', AnchorAlarmState('DISABLED', ANY, "info", False, {"state": 'DISABLED', "radius_tolerance": self.tolerance, "drop_point": None, "radius": None, "no_gps_count": 0, "out_of_radius_count": 0, "alarm_muted_count": 0, "current_radius": None}))
        self._out_of_sequence_calls(anchor_alarm)



    def test_anchor_up_alarm_no_gps(self):
        self.out_of_radius_count         = 0
        anchor_alarm =  AnchorAlarmModel(self._update_last_state)
        anchor_alarm.update_configuration(AnchorAlarmConfiguration(self.tolerance, 3, 5))
        
        self.assertState(anchor_alarm, None, AnchorAlarmState('DISABLED', ANY, "info", False, {"state": 'DISABLED', "radius_tolerance": self.tolerance, "drop_point": None, "radius": None, "no_gps_count": 0, "out_of_radius_count": 0, "alarm_muted_count": 0, "current_radius": None}))
        self._out_of_sequence_calls(anchor_alarm)

        # anchor down
        anchor_alarm.anchor_down(self.gps_position_anchor_down)
        self.assertState(anchor_alarm, 'DROP_POINT_SET', AnchorAlarmState('DROP_POINT_SET', ANY, "info", False, {"state": 'DROP_POINT_SET', "radius_tolerance": self.tolerance, "drop_point": self.gps_position_anchor_down, "radius": None, "no_gps_count": 0, "out_of_radius_count": 0, "alarm_muted_count": 0, "current_radius": None}))
        self._out_of_sequence_calls(anchor_alarm)


        # let chain out
        anchor_alarm.chain_out(self.gps_position_21m)
        self.assertState(anchor_alarm, 'IN_RADIUS', AnchorAlarmState('IN_RADIUS', ANY, "info", False, {"state": 'IN_RADIUS', "radius_tolerance": self.tolerance, "drop_point": self.gps_position_anchor_down, "radius": 21, "no_gps_count": 0, "out_of_radius_count": 0, "alarm_muted_count": 0, "current_radius": 21}))
        self._out_of_sequence_calls(anchor_alarm)

        # test various ticks in radius, with some no_gps with last tick in radius
        self._ticks_in_radius_with_some_no_gps(anchor_alarm)

        # test no gps alarm then mute then alarm again
        self._no_gps_alarm_with_mute(anchor_alarm)    
        self._out_of_sequence_calls(anchor_alarm)

        anchor_alarm.anchor_up()
        self.assertState(anchor_alarm, 'DISABLED', AnchorAlarmState('DISABLED', ANY, "info", False, {"state": 'DISABLED', "radius_tolerance": self.tolerance, "drop_point": None, "radius": None, "no_gps_count": 0, "out_of_radius_count": 0, "alarm_muted_count": 0, "current_radius": None}))
        self._out_of_sequence_calls(anchor_alarm)


    def test_anchor_up_alarm_no_gps_muted(self):
        self.out_of_radius_count         = 0
        anchor_alarm =  AnchorAlarmModel(self._update_last_state)
        anchor_alarm.update_configuration(AnchorAlarmConfiguration(self.tolerance, 3, 5))
        
        self.assertState(anchor_alarm, None, AnchorAlarmState('DISABLED', ANY, "info", False, {"state": 'DISABLED', "radius_tolerance": self.tolerance, "drop_point": None, "radius": None, "no_gps_count": 0, "out_of_radius_count": 0, "alarm_muted_count": 0, "current_radius": None}))
        self._out_of_sequence_calls(anchor_alarm)

        # anchor down
        anchor_alarm.anchor_down(self.gps_position_anchor_down)
        self.assertState(anchor_alarm, 'DROP_POINT_SET', AnchorAlarmState('DROP_POINT_SET', ANY, "info", False, {"state": 'DROP_POINT_SET', "radius_tolerance": self.tolerance, "drop_point": self.gps_position_anchor_down, "radius": None, "no_gps_count": 0, "out_of_radius_count": 0, "alarm_muted_count": 0, "current_radius": None}))
        self._out_of_sequence_calls(anchor_alarm)


        # let chain out
        anchor_alarm.chain_out(self.gps_position_21m)
        self.assertState(anchor_alarm, 'IN_RADIUS', AnchorAlarmState('IN_RADIUS', ANY, "info", False, {"state": 'IN_RADIUS', "radius_tolerance": self.tolerance, "drop_point": self.gps_position_anchor_down, "radius": 21, "no_gps_count": 0, "out_of_radius_count": 0, "alarm_muted_count": 0, "current_radius": 21}))
        self._out_of_sequence_calls(anchor_alarm)

        # test various ticks in radius, with some no_gps with last tick in radius
        self._ticks_in_radius_with_some_no_gps(anchor_alarm)

        # test no gps alarm then mute then alarm again
        self._no_gps_alarm_with_mute(anchor_alarm)    
        self._out_of_sequence_calls(anchor_alarm)

        anchor_alarm.mute_alarm()
        self.assertState(anchor_alarm, 'ALARM_NO_GPS_MUTED', AnchorAlarmState('ALARM_NO_GPS_MUTED', ANY, "emergency", True, {"state": 'ALARM_NO_GPS_MUTED', "radius_tolerance": self.tolerance, "drop_point": self.gps_position_anchor_down, "radius": 21, "no_gps_count": 12, "out_of_radius_count": 0, "alarm_muted_count": 0, "current_radius": None}))


        anchor_alarm.anchor_up()
        self.assertState(anchor_alarm, 'DISABLED', AnchorAlarmState('DISABLED', ANY, "info", False, {"state": 'DISABLED', "radius_tolerance": self.tolerance, "drop_point": None, "radius": None, "no_gps_count": 0, "out_of_radius_count": 0, "alarm_muted_count": 0, "current_radius": None}))
        self._out_of_sequence_calls(anchor_alarm)





    def test_anchor_up_alarm_dragging(self):
        self.out_of_radius_count         = 0
        anchor_alarm =  AnchorAlarmModel(self._update_last_state)
        anchor_alarm.update_configuration(AnchorAlarmConfiguration(self.tolerance, 3, 5))
        
        self.assertState(anchor_alarm, None, AnchorAlarmState('DISABLED', ANY, "info", False, {"state": 'DISABLED', "radius_tolerance": self.tolerance, "drop_point": None, "radius": None, "no_gps_count": 0, "out_of_radius_count": 0, "alarm_muted_count": 0, "current_radius": None}))
        self._out_of_sequence_calls(anchor_alarm)

        # anchor down
        anchor_alarm.anchor_down(self.gps_position_anchor_down)
        self.assertState(anchor_alarm, 'DROP_POINT_SET', AnchorAlarmState('DROP_POINT_SET', ANY, "info", False, {"state": 'DROP_POINT_SET', "radius_tolerance": self.tolerance, "drop_point": self.gps_position_anchor_down, "radius": None, "no_gps_count": 0, "out_of_radius_count": 0, "alarm_muted_count": 0, "current_radius": None}))
        self._out_of_sequence_calls(anchor_alarm)


        # let chain out
        anchor_alarm.chain_out(self.gps_position_21m)
        self.assertState(anchor_alarm, 'IN_RADIUS', AnchorAlarmState('IN_RADIUS', ANY, "info", False, {"state": 'IN_RADIUS', "radius_tolerance": self.tolerance, "drop_point": self.gps_position_anchor_down, "radius": 21, "no_gps_count": 0, "out_of_radius_count": 0, "alarm_muted_count": 0, "current_radius": 21}))
        self._out_of_sequence_calls(anchor_alarm)
        
        # tick out radius, check state change event
        anchor_alarm.on_timer_tick(self.gps_position_64m)
        self.assertState(anchor_alarm, 'ALARM_DRAGGING', AnchorAlarmState('ALARM_DRAGGING', ANY, "emergency", False, {"state": 'ALARM_DRAGGING', "radius_tolerance": self.tolerance, "drop_point": self.gps_position_anchor_down, "radius": 21, "no_gps_count": 0, "out_of_radius_count": self.next_out_of_radius_count(), "alarm_muted_count": 0, "current_radius": 64}))
        self._out_of_sequence_calls(anchor_alarm)


        anchor_alarm.anchor_up()
        self.assertState(anchor_alarm, 'DISABLED', AnchorAlarmState('DISABLED', ANY, "info", False, {"state": 'DISABLED', "radius_tolerance": self.tolerance, "drop_point": None, "radius": None, "no_gps_count": 0, "out_of_radius_count": 0, "alarm_muted_count": 0, "current_radius": None}))
        self._out_of_sequence_calls(anchor_alarm)


    
    def test_anchor_up_alarm_dragging_muted(self):
        self.out_of_radius_count         = 0
        anchor_alarm =  AnchorAlarmModel(self._update_last_state)
        anchor_alarm.update_configuration(AnchorAlarmConfiguration(self.tolerance, 3, 5))
        
        self.assertState(anchor_alarm, None, AnchorAlarmState('DISABLED', ANY, "info", False, {"state": 'DISABLED', "radius_tolerance": self.tolerance, "drop_point": None, "radius": None, "no_gps_count": 0, "out_of_radius_count": 0, "alarm_muted_count": 0, "current_radius": None}))
        self._out_of_sequence_calls(anchor_alarm)

        # anchor down
        anchor_alarm.anchor_down(self.gps_position_anchor_down)
        self.assertState(anchor_alarm, 'DROP_POINT_SET', AnchorAlarmState('DROP_POINT_SET', ANY, "info", False, {"state": 'DROP_POINT_SET', "radius_tolerance": self.tolerance, "drop_point": self.gps_position_anchor_down, "radius": None, "no_gps_count": 0, "out_of_radius_count": 0, "alarm_muted_count": 0, "current_radius": None}))
        self._out_of_sequence_calls(anchor_alarm)


        # let chain out
        anchor_alarm.chain_out(self.gps_position_21m)
        self.assertState(anchor_alarm, 'IN_RADIUS', AnchorAlarmState('IN_RADIUS', ANY, "info", False, {"state": 'IN_RADIUS', "radius_tolerance": self.tolerance, "drop_point": self.gps_position_anchor_down, "radius": 21, "no_gps_count": 0, "out_of_radius_count": 0, "alarm_muted_count": 0, "current_radius": 21}))
        self._out_of_sequence_calls(anchor_alarm)
        
        # tick out radius, check state change event
        anchor_alarm.on_timer_tick(self.gps_position_64m)
        self.assertState(anchor_alarm, 'ALARM_DRAGGING', AnchorAlarmState('ALARM_DRAGGING', ANY, "emergency", False, {"state": 'ALARM_DRAGGING', "radius_tolerance": self.tolerance, "drop_point": self.gps_position_anchor_down, "radius": 21, "no_gps_count": 0, "out_of_radius_count": self.next_out_of_radius_count(), "alarm_muted_count": 0, "current_radius": 64}))
        self._out_of_sequence_calls(anchor_alarm)

        # mute alarm
        anchor_alarm.mute_alarm()
        self.assertState(anchor_alarm, 'ALARM_DRAGGING_MUTED', AnchorAlarmState('ALARM_DRAGGING_MUTED', ANY, "emergency", True, {"state": 'ALARM_DRAGGING_MUTED', "radius_tolerance": self.tolerance, "drop_point": self.gps_position_anchor_down, "radius": 21, "no_gps_count": 0, "out_of_radius_count": self.out_of_radius_count, "alarm_muted_count": 0, "current_radius": 64}))


        anchor_alarm.anchor_up()
        self.assertState(anchor_alarm, 'DISABLED', AnchorAlarmState('DISABLED', ANY, "info", False, {"state": 'DISABLED', "radius_tolerance": self.tolerance, "drop_point": None, "radius": None, "no_gps_count": 0, "out_of_radius_count": 0, "alarm_muted_count": 0, "current_radius": None}))
        self._out_of_sequence_calls(anchor_alarm)


    def test_params_exceptions(self):
        self.out_of_radius_count         = 0

        anchor_alarm =  AnchorAlarmModel(self._update_last_state)
        anchor_alarm.update_configuration(AnchorAlarmConfiguration(self.tolerance, 3, 5)) 
        self.assertState(anchor_alarm, None, AnchorAlarmState('DISABLED', ANY, "info", False, {"state": 'DISABLED', "radius_tolerance": self.tolerance, "drop_point": None, "radius": None, "no_gps_count": 0, "out_of_radius_count": 0, "alarm_muted_count": 0, "current_radius": None}))

        # anchor down
        with self.assertRaises(TypeError):
            anchor_alarm.anchor_down("qwe")
        self.assertState(anchor_alarm, None, AnchorAlarmState('DISABLED', ANY, "info", False, {"state": 'DISABLED', "radius_tolerance": self.tolerance, "drop_point": None, "radius": None, "no_gps_count": 0, "out_of_radius_count": 0, "alarm_muted_count": 0, "current_radius": None}))



        # anchor down
        with self.assertRaises(RuntimeError):
            anchor_alarm.anchor_down(None)
        self.assertState(anchor_alarm, None, AnchorAlarmState('DISABLED', ANY, "info", False, {"state": 'DISABLED', "radius_tolerance": self.tolerance, "drop_point": None, "radius": None, "no_gps_count": 0, "out_of_radius_count": 0, "alarm_muted_count": 0, "current_radius": None}))


        # anchor down
        anchor_alarm.anchor_down(self.gps_position_anchor_down)
        self.assertState(anchor_alarm, 'DROP_POINT_SET', AnchorAlarmState('DROP_POINT_SET', ANY, "info", False, {"state": 'DROP_POINT_SET', "radius_tolerance": self.tolerance, "drop_point": self.gps_position_anchor_down, "radius": None, "no_gps_count": 0, "out_of_radius_count": 0, "alarm_muted_count": 0, "current_radius": None}))



        # let chain out
        with self.assertRaises(TypeError):
            anchor_alarm.chain_out("qwe")
        self.assertState(anchor_alarm, 'DISABLED', AnchorAlarmState('DISABLED', ANY, "info", False, {"state": 'DISABLED', "radius_tolerance": self.tolerance, "drop_point": None, "radius": None, "no_gps_count": 0, "out_of_radius_count": 0, "alarm_muted_count": 0, "current_radius": None}))


         # anchor down
        anchor_alarm.anchor_down(self.gps_position_anchor_down)
        self.assertState(anchor_alarm, 'DROP_POINT_SET', AnchorAlarmState('DROP_POINT_SET', ANY, "info", False, {"state": 'DROP_POINT_SET', "radius_tolerance": self.tolerance, "drop_point": self.gps_position_anchor_down, "radius": None, "no_gps_count": 0, "out_of_radius_count": 0, "alarm_muted_count": 0, "current_radius": None}))


         # let chain out
        with self.assertRaises(RuntimeError):
            anchor_alarm.chain_out(None)
        self.assertState(anchor_alarm, 'DISABLED', AnchorAlarmState('DISABLED', ANY, "info", False, {"state": 'DISABLED', "radius_tolerance": self.tolerance, "drop_point": None, "radius": None, "no_gps_count": 0, "out_of_radius_count": 0, "alarm_muted_count": 0, "current_radius": None}))



    def test_reset_state(self):
        self.out_of_radius_count         = 0

        anchor_alarm =  AnchorAlarmModel(self._update_last_state)
        anchor_alarm.update_configuration(AnchorAlarmConfiguration(self.tolerance, 3, 5)) 
        self.assertState(anchor_alarm, None, AnchorAlarmState('DISABLED', ANY, "info", False, {"state": 'DISABLED', "radius_tolerance": self.tolerance, "drop_point": None, "radius": None, "no_gps_count": 0, "out_of_radius_count": 0, "alarm_muted_count": 0, "current_radius": None}))

        with self.assertRaises(RuntimeError):
            anchor_alarm.reset_state(None, 21)

        with self.assertRaises(TypeError):
            anchor_alarm.reset_state("qwe", 21)

        with self.assertRaises(RuntimeError):
            anchor_alarm.reset_state(self.gps_position_anchor_down, None)

        with self.assertRaises(ValueError):
            anchor_alarm.reset_state(self.gps_position_anchor_down, "qwe")

        anchor_alarm.reset_state(self.gps_position_anchor_down, 21)
        self.assertState(anchor_alarm, 'IN_RADIUS', AnchorAlarmState('IN_RADIUS', ANY, "info", False, {"state": 'IN_RADIUS', "radius_tolerance": self.tolerance, "drop_point": self.gps_position_anchor_down, "radius": 21, "no_gps_count": 0, "out_of_radius_count": 0, "alarm_muted_count": 0, "current_radius": 21}))




    def test_config_updated(self):
        anchor_alarm =  AnchorAlarmModel(self._update_last_state) 
        anchor_alarm.update_configuration(AnchorAlarmConfiguration(5, 3, 5))
        self.assertEqual(5, anchor_alarm._radius_tolerance)
        self.assertEqual(3, anchor_alarm._no_gps_count_threshold)
        self.assertEqual(5, anchor_alarm._mute_duration)

    def test_tolerance_increased(self):
        # test that when anchor is dragging or muted and tolerance is increased enough, it goes back to IN_RADIUS state
        self.out_of_radius_count         = 0
        anchor_alarm =  AnchorAlarmModel(self._update_last_state)
        anchor_alarm.update_configuration(AnchorAlarmConfiguration(self.tolerance, 3, 5))
        self.assertState(anchor_alarm, None, AnchorAlarmState('DISABLED', ANY, "info", False, {"state": 'DISABLED', "radius_tolerance": self.tolerance, "drop_point": None, "radius": None, "no_gps_count": 0, "out_of_radius_count": 0, "alarm_muted_count": 0, "current_radius": None}))
        self._out_of_sequence_calls(anchor_alarm)

        # anchor down
        anchor_alarm.anchor_down(self.gps_position_anchor_down)
        self.assertState(anchor_alarm, 'DROP_POINT_SET', AnchorAlarmState('DROP_POINT_SET', ANY, "info", False, {"state": 'DROP_POINT_SET', "radius_tolerance": self.tolerance, "drop_point": self.gps_position_anchor_down, "radius": None, "no_gps_count": 0, "out_of_radius_count": 0, "alarm_muted_count": 0, "current_radius": None}))
        self._out_of_sequence_calls(anchor_alarm)


        # let chain out
        anchor_alarm.chain_out(self.gps_position_21m)
        self.assertState(anchor_alarm, 'IN_RADIUS', AnchorAlarmState('IN_RADIUS', ANY, "info", False, {"state": 'IN_RADIUS', "radius_tolerance": self.tolerance, "drop_point": self.gps_position_anchor_down, "radius": 21, "no_gps_count": 0, "out_of_radius_count": 0, "alarm_muted_count": 0, "current_radius": 21}))
        self._out_of_sequence_calls(anchor_alarm)
        
        # tick out radius, check state change event
        anchor_alarm.on_timer_tick(self.gps_position_64m)
        self.assertState(anchor_alarm, 'ALARM_DRAGGING', AnchorAlarmState('ALARM_DRAGGING', ANY, "emergency", False, {"state": 'ALARM_DRAGGING', "radius_tolerance": self.tolerance, "drop_point": self.gps_position_anchor_down, "radius": 21, "no_gps_count": 0, "out_of_radius_count": self.next_out_of_radius_count(), "alarm_muted_count": 0, "current_radius": 64}))
        self._out_of_sequence_calls(anchor_alarm)

        anchor_alarm.update_configuration(AnchorAlarmConfiguration(20, 3, 5))

        # tick out radius, check state change event
        anchor_alarm.on_timer_tick(self.gps_position_64m)
        self.assertState(anchor_alarm, None, AnchorAlarmState('ALARM_DRAGGING', ANY, "emergency", False, {"state": 'ALARM_DRAGGING', "radius_tolerance": self.tolerance, "drop_point": self.gps_position_anchor_down, "radius": 21, "no_gps_count": 0, "out_of_radius_count": self.next_out_of_radius_count(), "alarm_muted_count": 0, "current_radius": 64}))
        self._out_of_sequence_calls(anchor_alarm)

        
        anchor_alarm.update_configuration(AnchorAlarmConfiguration(50, 3, 5))
        self.assertState(anchor_alarm, 'IN_RADIUS', AnchorAlarmState('IN_RADIUS', ANY, "info", False, {"state": 'IN_RADIUS', "radius_tolerance": 50, "drop_point": self.gps_position_anchor_down, "radius": 21, "no_gps_count": 0, "out_of_radius_count": 0, "alarm_muted_count": 0, "current_radius": 64}))
        self._out_of_sequence_calls(anchor_alarm)


        anchor_alarm.update_configuration(AnchorAlarmConfiguration(20, 3, 5))
        self.out_of_radius_count         = 0

        # tick out radius, check state change event
        anchor_alarm.on_timer_tick(self.gps_position_64m)
        self.assertState(anchor_alarm, 'ALARM_DRAGGING', AnchorAlarmState('ALARM_DRAGGING', ANY, "emergency", False, {"state": 'ALARM_DRAGGING', "radius_tolerance": self.tolerance, "drop_point": self.gps_position_anchor_down, "radius": 21, "no_gps_count": 0, "out_of_radius_count": self.next_out_of_radius_count(), "alarm_muted_count": 0, "current_radius": 64}))
        self._out_of_sequence_calls(anchor_alarm)




        # test that when mute_duration is decreased in MUTE state, state goes back to alarm

        # test that when mute_duration is increased in MUTE, state stays in muted


        # test that when no_gps_count_threshold is decreased in no_gps condition but not yet in state ALARM_NO_GPS

        # test that when no_gps_count_threshold is increased, state goes to alarm



if __name__ == '__main__':
    unittest.main()