import sys
import os

# bundle our dependencies
sys.path.insert(1, os.path.join(os.path.dirname(__file__), 'ext'))



from transitions import Machine
import logging
logger = logging.getLogger(__name__)
from collections import namedtuple
from geopy.distance import geodesic


logger = logging.getLogger(__name__)


AnchorAlarmConfiguration = namedtuple('AnchorAlarmConfiguration', ['tolerance', 'no_gps_count_threshold', 'mute_duration'], defaults=[15, 30, 30])
# level = info | warning | error | emergency
AnchorAlarmState = namedtuple('AnchorAlarmState', ['state', 'message', 'level', 'muted', 'params'])




class AnchorAlarmModel(object):
    def __init__(self, on_state_change_fn):

        self._on_state_change_fn = on_state_change_fn

        # if you need that changed, call on_conf_updated
        self._radius_tolerance = 15
        self._no_gps_count_threshold = 30
        self._mute_duration = 30

        self._drop_point = None
        self._radius = None
        self._no_gps_count = 0
        self._out_of_radius_count = 0
        self._current_radius = None
        self._alarm_muted_count = 0

        states = [
            {'name': 'DISABLED'}, 
            {'name': 'DROP_POINT_SET'}, 
            {'name': 'IN_RADIUS'}, 
            {'name': 'ALARM_DRAGGING'}, 
            {'name': 'ALARM_DRAGGING_MUTED'}, 
            {'name': 'ALARM_NO_GPS'}, 
            {'name': 'ALARM_NO_GPS_MUTED'}]


        transitions = [
            { 'trigger': 'on_set_drop_point',   'source': 'DISABLED',               'dest': 'DROP_POINT_SET'},
            { 'trigger': 'on_set_radius',       'source': 'DROP_POINT_SET',         'dest': 'IN_RADIUS', 'after': 'on_after_set_radius'},
            
            { 'trigger': 'on_anchor_dragging',  'source': 'IN_RADIUS',              'dest': 'ALARM_DRAGGING' },
            { 'trigger': 'on_alarm_muted',      'source': 'ALARM_DRAGGING',         'dest': 'ALARM_DRAGGING_MUTED' },
            { 'trigger': 'on_anchor_dragging',  'source': 'ALARM_DRAGGING_MUTED',   'dest': 'ALARM_DRAGGING' },
            { 'trigger': 'on_anchor_dragging',  'source': 'ALARM_NO_GPS',           'dest': 'ALARM_DRAGGING' },
            { 'trigger': 'on_anchor_dragging',  'source': 'ALARM_NO_GPS_MUTED',     'dest': 'ALARM_DRAGGING' },

            { 'trigger': 'on_no_gps',           'source': 'IN_RADIUS',              'dest': 'ALARM_NO_GPS' },
            { 'trigger': 'on_no_gps',           'source': 'ALARM_NO_GPS_MUTED',     'dest': 'ALARM_NO_GPS' },
            { 'trigger': 'on_alarm_muted',      'source': 'ALARM_NO_GPS',           'dest': 'ALARM_NO_GPS_MUTED' },
            { 'trigger': 'on_in_radius',        'source': 'ALARM_NO_GPS',           'dest': 'IN_RADIUS' },
            { 'trigger': 'on_in_radius',        'source': 'ALARM_NO_GPS_MUTED',     'dest': 'IN_RADIUS' },

            { 'trigger': 'on_set_radius',       'source': 'ALARM_DRAGGING',         'dest': 'IN_RADIUS', 'after': 'on_after_set_radius' },
            { 'trigger': 'on_set_radius',       'source': 'ALARM_DRAGGING_MUTED',   'dest': 'IN_RADIUS', 'after': 'on_after_set_radius' },

            { 'trigger': 'on_tolerance_updated','source': 'ALARM_DRAGGING',         'dest': 'IN_RADIUS' },
            { 'trigger': 'on_tolerance_updated','source': 'ALARM_DRAGGING_MUTED',   'dest': 'IN_RADIUS' },

            { 'trigger': 'on_reset_state',      'source': 'DISABLED',               'dest': 'IN_RADIUS' },

            { 'trigger': 'on_anchor_up',        'source': 'DROP_POINT_SET',         'dest': 'DISABLED' },
            { 'trigger': 'on_anchor_up',        'source': 'IN_RADIUS',              'dest': 'DISABLED' },
            { 'trigger': 'on_anchor_up',        'source': 'ALARM_DRAGGING',         'dest': 'DISABLED' },
            { 'trigger': 'on_anchor_up',        'source': 'ALARM_DRAGGING_MUTED',   'dest': 'DISABLED' },
            { 'trigger': 'on_anchor_up',        'source': 'ALARM_NO_GPS',           'dest': 'DISABLED' },
            { 'trigger': 'on_anchor_up',        'source': 'ALARM_NO_GPS_MUTED',     'dest': 'DISABLED' },

            { 'trigger': 'on_error',            'source': '*',                      'dest': 'DISABLED' }
        ]

        # Initialize the state machine
        self._machine = Machine(model=self,  states=states, 
                                            transitions=transitions,
                                            initial='DISABLED', 
                                            after_state_change=self._after_state_change, 
                                            ignore_invalid_triggers=True)


    def update_configuration(self, conf):
        tolerance_updated = self._radius_tolerance != conf.tolerance

        self._radius_tolerance = conf.tolerance
        self._no_gps_count_threshold = conf.no_gps_count_threshold
        self._mute_duration = conf.mute_duration

        if tolerance_updated:
            # we're back in radius with new tolerance
            logger.info("Tolerance updated to "+ str(self._radius_tolerance))
            if self.state in ['ALARM_DRAGGING', 'ALARM_DRAGGING_MUTED'] and self._current_radius < self._radius + self._radius_tolerance:
                self._out_of_radius_count = 0
                self.on_tolerance_updated()


    def anchor_down(self, gps_position):
        """Called from setting change or external windlass down trigger.
        Will raise an exception if GPS position is not provided"""

        if self.state not in ['DISABLED']:
            return

        if gps_position is None:
            raise RuntimeError("Anchor alarm DISABLED. Unable to get GPS position for drop point.")

        if type(gps_position).__name__ != "GPSPosition":
            raise TypeError("gps_position must be a GPSPosition namedtuple")
        
        self.on_set_drop_point(gps_position)  
        logger.info("Set new drop point to "+ str(gps_position.longitude)+ ";"+ str(gps_position.latitude))



    def chain_out(self, gps_position):
        """Called from setting change or external 2000rpm/0SOG trigger or when resetting radius
        Will calculate current position from drop_point and current gps position
        Will raise an exception if gps_position is not provided and can't be calculated"""   

        if self.state not in ['DROP_POINT_SET', 'ALARM_DRAGGING', 'ALARM_DRAGGING_MUTED']:
            return

        if self._drop_point is None:
            self.on_error()
            raise RuntimeError("Anchor alarm DISABLED. Unable to calculate radius : no anchor drop point defined.")

        if gps_position is None:
            self.on_error()
            raise RuntimeError("Anchor alarm DISABLED. Unable to calculate radius : no GPS position given to calculate radius.")

        if type(gps_position).__name__ != "GPSPosition":
            self.on_error()
            raise TypeError("gps_position must be a GPSPosition namedtuple")

        radius = round(self._calculate_distance(self._drop_point, gps_position))
        self.on_set_radius(radius)
        logger.info("Set new radius to "+ str(radius))


    def on_timer_tick(self, gps_position):
        """Called every second when watching with GPS position.
        If no GPS position given for #no_gps_count_thresold#, will go in ALARM_NO_GPS state
        If GPS position is outside safe radius, will go in ALARM_DRAGGING state"""   


        # make sure this code is only run in IN_RADIUS, ALARM_DRAGGING or ALARM_NO_GPS
        if self.state not in ['IN_RADIUS', 'ALARM_DRAGGING', 'ALARM_NO_GPS', 'ALARM_DRAGGING_MUTED', 'ALARM_NO_GPS_MUTED']:
            return


        # handle mute state
        if self.state in ['ALARM_DRAGGING_MUTED', 'ALARM_NO_GPS_MUTED'] and self._alarm_muted_count < self._mute_duration:
            self._alarm_muted_count += 1
            should_transition = False
        elif self.state in ['ALARM_DRAGGING', 'ALARM_NO_GPS']:
            should_transition = False
        else:
            self._alarm_muted_count = 0
            should_transition = True

        is_anchor_dragging = self.state in ['ALARM_DRAGGING', 'ALARM_DRAGGING_MUTED']

        if gps_position is None:
            self._no_gps_count+=1
            self._current_radius = None

            if is_anchor_dragging:
                self._out_of_radius_count+=1    # if we are dragging already, still count out_of_radius
                if should_transition:           # do not go back yet to ALARM_DRAGGING if it's muted
                    self.on_anchor_dragging()

            if self._no_gps_count > self._no_gps_count_threshold:
                if should_transition:   # do not go back yet to ALARM_NO_GPS if it's muted
                    self.on_no_gps()    


        else:
            # we have a gps position
            self._no_gps_count = 0
            self._current_radius = round(self._calculate_distance(self._drop_point, gps_position))

            if self._current_radius >= self._radius + self._radius_tolerance :
                # outside radius
                self._out_of_radius_count += 1

                if should_transition:   # do not go back yet to ALARM_DRAGGING if muted
                    self.on_anchor_dragging()   

            else:
                # inside radius
                if is_anchor_dragging:
                    self._out_of_radius_count += 1  # when once dragging, being in safe radius again doesn't reset out_of_radius_count
                else:
                    self._out_of_radius_count = 0   # only reset out of radius count if not dragging
                    if self.state != "IN_RADIUS":
                        self.on_in_radius()

                #if last_state in ["ALARM_NO_GPS", "ALARM_NO_GPS_MUTED"]: 
                # TODO XXX how to get feedback that boat is safe again ?


            


    def anchor_up(self):
        """Called when raising anchor and anchor alarm should be disabled"""

        self.on_anchor_up()

    def mute_alarm(self):
        """Called when alarm is off and needs to be muted"""

        self.on_alarm_muted()

    def reset_state(self, drop_point, radius):
        """Called when system is (re)booting and anchor alarm needs to be set upon boot"""

        if self.state != 'DISABLED':
            raise RuntimeError("Cannot reset anchor alarm state if not disabled")

        if drop_point is None:
            raise RuntimeError("Cannot reset anchor alarm state without valid drop point")

        if type(drop_point).__name__ != "GPSPosition":
            raise TypeError("drop_point must be a GPSPosition namedtuple")

        if radius is None:
            raise RuntimeError("Cannot reset anchor alarm state without valid radius")

        # make sure we get an int
        radius = int(radius)

        self.on_enter_DROP_POINT_SET(drop_point)
        self.on_after_set_radius(radius)

        self.on_reset_state()



    def get_current_state(self):
        params = {
            "state": self.state,
            "radius_tolerance": self._radius_tolerance,
            "drop_point": self._drop_point,
            "radius": self._radius,
            "no_gps_count": self._no_gps_count,
            "out_of_radius_count": self._out_of_radius_count,
            "alarm_muted_count": self._alarm_muted_count,
            "current_radius": self._current_radius,
        }

        # TODO XXX : add in_tolerance param or IN_TOLERANCE_RADIUS state ?

        level = ""
        message = ""
        muted = False

        if self.state == "DISABLED":
            level = "info"
            message =  "Anchor alarm DISABLED, anchor raised."
            
        elif self.state == "DROP_POINT_SET":
            level = "info"
            message = "Drop point set, let chain out and secure bridle. 2000RPM and SOG of 0 will arm anchor alarm."


        elif self.state ==  "IN_RADIUS":
            level = "info"
            if self._current_radius is None:
                message = 'Anchor alarm ENABLED, temporarely no GPS position for {no_gps_count:.0f} seconds'.format(no_gps_count=self._no_gps_count)
            else:
                message = 'Anchor alarm ENABLED, currently {current_radius:.0f}m of {radius:.0f}m with {tolerance:.0f}m tolerance.'.format(current_radius=self._current_radius, radius=self._radius, tolerance=self._radius_tolerance)


        elif self.state ==  "ALARM_NO_GPS" or self.state == "ALARM_NO_GPS_MUTED":
            level = "emergency"
            message = 'No GPS position for {no_gps_count:.0f} seconds'.format(no_gps_count=self._no_gps_count)
            muted = self.state == "ALARM_NO_GPS_MUTED"

            
        elif self.state ==  "ALARM_DRAGGING" or self.state == "ALARM_DRAGGING_MUTED":
            level = "emergency"
            if self._current_radius is None:    # we temporarely have no GPS
                    message = 'Anchor dragging for {out_of_radius_count} seconds, temporarely having no GPS.'.format(out_of_radius_count=self._out_of_radius_count)
            else:
                out_of_radius_distance = self._current_radius - self._radius
                if out_of_radius_distance > 0:
                    message = 'Anchor dragging for {out_of_radius_count} seconds, {out_of_radius_distance:.0f}m out of {radius:.0f}m radius.'.format(out_of_radius_count=self._out_of_radius_count, out_of_radius_distance=out_of_radius_distance, radius=self._radius)
                else:
                    message = 'Anchor dragging for {out_of_radius_count} seconds, temporarely back in safe radius : {current_radius:.0f}m of {radius:.0f}m with {tolerance:.0f}m tolerance.'.format(out_of_radius_count=self._out_of_radius_count, current_radius=self._current_radius, radius=self._radius, tolerance=self._radius_tolerance)

            muted = self.state == "ALARM_DRAGGING_MUTED"

        else:
            raise RuntimeError("Unknown state "+ self.state)

        current_state = AnchorAlarmState(self.state, message, level, muted, params)

        return current_state




    def on_enter_DISABLED(self):
        self._drop_point = None
        self._radius = None
        self._no_gps_count = 0
        self._out_of_radius_count = 0
        self._alarm_muted_count = 0
        self._current_radius = None

    def on_enter_DROP_POINT_SET(self, gps_position):
        self._drop_point = gps_position


    def on_after_set_radius(self, radius):
        self._radius = radius
        self._current_radius = self._radius
        self._out_of_radius_count = 0

    def on_enter_ALARM_DRAGGING(self):
        self._alarm_muted_count = 0

    def on_enter_ALARM_NO_GPS(self):
        self._alarm_muted_count = 0

    def _after_state_change(self, *args, **kwargs):
        # notify state change
        if self._on_state_change_fn is not None: 
            self._on_state_change_fn(self.get_current_state())

    def _calculate_distance(self, drop_point, current_position):
        if current_position is None or drop_point is None:
            return None
        
        distance = geodesic((drop_point.latitude, drop_point.longitude), 
                          (current_position.latitude, current_position.longitude)).meters
        return distance

