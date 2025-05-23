import sys
import os

sys.path.insert(1, os.path.join(sys.path[0], '..'))
from utils import exit_on_error

from anchor_alarm_model import AnchorAlarmState
from anchor_alarm_controller import AnchorAlarmController


class AbstractConnector:
    def __init__(self, timer_provider, settings_provider):
        self._timer_provider = timer_provider
        self._settings_provider = settings_provider

        self.controller = None
        self._timer_ids = {}
        pass

    def set_controller(self, controller:AnchorAlarmController):
        """Controller has :
            - trigger_anchor_down
            - trigger_chain_out
            - trigger_anchor_up
            - trigger_mute_alarm
        """

        self.controller = controller

    def on_state_changed(self, current_state:AnchorAlarmState):
        """Called by controller when state changed"""
        pass

    def update_state(self, current_state:AnchorAlarmState):
        """Called by controller every second with updated state"""
        pass


    def _add_timer(self, timer_name, cb, duration, once=True):
        self._remove_timer(timer_name)
#        print("Adding timer "+timer_name + " with duration "+ str(duration))
        self._timer_ids[timer_name] = self._timer_provider().timeout_add(duration, exit_on_error, self._trigger_and_remove_timer, timer_name, cb, once)


    def _remove_timer(self, timer_name):
        if timer_name in self._timer_ids and self._timer_ids[timer_name] is not None:
#            print("Removing timer "+timer_name)
            self._timer_provider().source_remove(self._timer_ids[timer_name])
            self._timer_ids[timer_name] = None

    def _trigger_and_remove_timer(self, timer_name, cb, once):
        should_keep_trigger = cb()

        if once or not should_keep_trigger:
            self._timer_ids[timer_name] = None
            return False
        
        return should_keep_trigger
