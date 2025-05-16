from anchor_alarm_model import AnchorAlarmConfiguration
from anchor_alarm_model import AnchorAlarmModel

import sys
import os
sys.path.insert(1, os.path.join(sys.path[0], '..'))
from utils import exit_on_error

from collections import namedtuple
GPSPosition = namedtuple('GPSPosition', ['latitude', 'longitude'])

import logging
logger = logging.getLogger(__name__)

class AnchorAlarmController(object):

    def __init__(self, timer_provider, settings_provider, gps_provider):
        self._settings_provider = settings_provider


        self._anchor_alarm = AnchorAlarmModel(self._on_state_changed)
        self.gps_provider = gps_provider

        self._connectors = []

        self._init_settings()

        timer_provider().timeout_add(1000, exit_on_error, self._on_timer_tick)

        # if the Active flag was set, reset_state
        if self._settings["Active"] == 1:
            logger.info("Resetting state to "+ str(self._settings["Latitude"]) + ";" + str(self._settings["Longitude"])+ " with radius "+ str(self._settings["Radius"]))
            drop_point = GPSPosition(self._settings["Latitude"], self._settings["Longitude"])
            self.reset_state(drop_point, self._settings["Radius"])
    
    def _init_settings(self):
        # create the setting that are needed
        settingsList = {
            # configuration
            "Tolerance":            ["/Settings/Anchoralarm/Configuration/RadiusTolerance", 15, 0, 512],
            "NoGPSCountThreshold":  ["/Settings/Anchoralarm/Configuration/NoGPSCountThreshold", 30, 0, 300],
            "MuteDuration":         ["/Settings/Anchoralarm/Configuration/MuteDuration", 30, 0, 300], 

            "Latitude":             ["/Settings/AnchorAlarm/Last/Position/Latitude", 0.0, -90.0, 90],
            "Longitude":            ["/Settings/AnchorAlarm/Last/Position/Longitude", 0.0, -180.0, 180],
            "Radius":               ["/Settings/AnchorAlarm/Last/Radius", 0, 0, 256],

            "Active":               ["/Settings/AnchorAlarm/Last/Active", 0, 0, 1],  
        }

        self._settings = self._settings_provider(settingsList, self._on_setting_changed)
        
        self._on_setting_changed("Tolerance", None, None)  # dummy values to trigger anchor_alarm.update_configuration
        if self._settings['Active'] == 1:
            self._on_setting_changed("Active", 0, 1)


    def _on_setting_changed(self, key, old_value, new_value):
        if not hasattr(self, '_settings'):
            return  # not yet instanciated
        
        if key in ["Tolerance", "NoGPSCountThreshold", "MuteDuration"]:
            conf = AnchorAlarmConfiguration(self._settings["Tolerance"], self._settings["NoGPSCountThreshold"], self._settings["MuteDuration"])
            self._anchor_alarm.update_configuration(conf)

        if key == "Active":
             # if the Active flag was set, reset_state
            if new_value == 1:
                logger.info("Resetting state to "+ str(self._settings["Latitude"]) + ";" + str(self._settings["Longitude"])+ " with radius "+ str(self._settings["Radius"]))
                drop_point = GPSPosition(self._settings["Latitude"], self._settings["Longitude"])
                self.reset_state(drop_point, self._settings["Radius"])
            else:
                logger.info("Disabling anchor alarm from Settings")
                self.trigger_anchor_up()

        


    def reset_state(self, drop_point, radius):
        try:
            self._anchor_alarm.reset_state(drop_point, radius)
        except Exception as e:
            logger.error(e) 

    def register_connector(self, connector):
        """Registers an external connector to interface with DBUS or MTTQ triggers"""
        connector.controller = self
        self._connectors.append(connector)
        try:
            current_state = self._anchor_alarm.get_current_state()
            logger.info("sending state "+ current_state.state +" to connector "+ str(connector))
            connector.on_state_changed(current_state)
        except Exception as e:
            logger.error(e)      

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
        if current_state.state == "IN_RADIUS" and 'drop_point' in current_state.params and 'radius' in current_state.params:
            self._settings['Latitude']   = current_state.params['drop_point'].latitude
            self._settings['Longitude']  = current_state.params['drop_point'].longitude
            self._settings['Radius']     = current_state.params['radius']
            self._settings["Active"]     = 1
            logger.info("Saved new position to Settings")
        elif current_state.state == "DISABLED":
            self._settings["Active"]     = 0
            logger.info("Set Active flag in Settings to 0")


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