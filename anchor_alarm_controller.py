from anchor_alarm_model import AnchorAlarmConfiguration
from anchor_alarm_model import AnchorAlarmModel

from collections import namedtuple
GPSPosition = namedtuple('GPSPosition', ['latitude', 'longitude'])


class AnchorAlarmController(object):

    def __init__(self, conf:AnchorAlarmConfiguration, timer_provider, gps_provider):
        # TODO XXX : change to use settings directly ?
        self._anchor_alarm = AnchorAlarmModel(self._on_state_changed, conf)
        self.gps_provider = gps_provider

        self._connectors = []

        timer_provider.timeout_add(self._on_timer_tick, 1000)
    
    def reset_state(self, drop_point, radius):
        self._anchor_alarm.reset_state(drop_point, radius)

    def register_connector(self, connector):
        """Registers an external connector to interface with DBUS or MTTQ triggers"""
        connector.controller = self
        self._connectors.append(connector)
        try:
            current_state = self._anchor_alarm.get_current_state()
            connector.update_state(current_state)
        except Exception:
            pass # TODO XXX        

    def trigger_anchor_down(self):
        """Delegate method called by connector when setting anchor"""
        try:
            position = self.gps_provider.get_gps_position()
            self._anchor_alarm.anchor_down(position)
        except Exception as e:
            return e

    def trigger_chain_out(self):
        """Delegate method called by connector when chain is out and anchor alarm needs to be armed"""
        try:
            position = self.gps_provider.get_gps_position()
            self._anchor_alarm.chain_out(position)
        except Exception as e:
            return e

    def trigger_anchor_up(self):
        """Delegate method called by connector when anchor is raised and anchor alarm needs to be disabled"""
        self._anchor_alarm.anchor_up()


    def trigger_mute_alarm(self):
        """Delegate method called by connector when alarm should be muted"""
        self._anchor_alarm.mute_alarm()



    # called by anchor_alarm when its state changes
    def _on_state_changed(self, current_state):
        # notify connectors
        for connector in self._connectors:
            try:
                connector.on_state_changed(current_state)
                # TODO XXX maybe call update_state as well ?
            except Exception:
                pass # TODO XXX

    def _on_timer_tick(self):
        current_state = self._anchor_alarm.get_current_state()
        if current_state.state != 'DISABLED':
            self._anchor_alarm.on_timer_tick(self.gps_provider.get_gps_position())

        # notify connectors
        for connector in self._connectors:
            try:
                connector.update_state(current_state)
            except Exception:
                pass # TODO XXX        

        return True