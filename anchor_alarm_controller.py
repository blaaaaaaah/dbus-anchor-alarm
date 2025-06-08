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

from anchor_alarm_model import AnchorAlarmConfiguration
from anchor_alarm_model import AnchorAlarmModel

import sys
import os

from utils import exit_on_error

sys.path.insert(1, os.path.join(os.path.dirname(__file__), 'gps_providers'))
from abstract_gps_provider import GPSPosition


import logging
logger = logging.getLogger(__name__)

class AnchorAlarmController(object):

    def __init__(self, timer_provider, settings_provider):
        self._settings_provider = settings_provider


        self._anchor_alarm = AnchorAlarmModel(self._on_state_changed)
        self._gps_providers = []

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
            # Distance in meters that will be added to the safe radius
            "Tolerance":            ["/Settings/Anchoralarm/RadiusTolerance", 15, 0, 512],

            # Number of seconds the GPS can be lost before activating the alarm
            "NoGPSCountThreshold":  ["/Settings/Anchoralarm/NoGPSCountThreshold", 30, 0, 300],

            # Number of seconds the alarm will be muted for when the alarm is acknowledged
            "MuteDuration":         ["/Settings/Anchoralarm/MuteDuration", 30, 0, 300], 

            # Safe radius to use when activating mooring ball mode
            "MooringRadius":        ["/Settings/AnchorAlarm/MooringRadius", 15, 0, 256],

            # Last saved latitude where anchor was dropped. Used when device reboots or to set a specific location arbitrary
            "Latitude":             ["/Settings/AnchorAlarm/Last/Position/Latitude", 0.0, -90.0, 90],

            # Last saved longitude where anchor was dropped. Used when device reboots or to set a specific location arbitrary
            "Longitude":            ["/Settings/AnchorAlarm/Last/Position/Longitude", 0.0, -180.0, 180],

            # Last saved safe radius. Used when device reboots or to set a specific value arbitrary
            "Radius":               ["/Settings/AnchorAlarm/Last/Radius", 0, 0, 256],

            # Is the anchor alarm enabled ? Used when device reboots. Setting it to 0 will deactivate the alarm. Setting it to 1 will activate the alarm
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

    def register_gps_provider(self, gps_provider):
        self._gps_providers.append(gps_provider)

    def get_gps_position(self):
        logger.debug("Got "+str(len(self._gps_providers))+" gps providers")
        for gps_provider in self._gps_providers:
            position = gps_provider.get_gps_position()
            if position is not None:
                logger.debug("Returning GPSPosition: "+ str(position))
                return position
            else:
                logger.debug("Provider "+ str(gps_provider) + " didn't return a GPS position")
        
        return None
        

    def register_connector(self, connector):
        """Registers an external connector to interface with DBUS or MTTQ triggers"""
        connector.controller = self
        self._connectors.append(connector)
        try:
            current_state = self._anchor_alarm.get_current_state()
            logger.info("sending state "+ current_state.state +" to connector "+ str(connector))
            connector.on_state_changed(current_state)
        except Exception as e:
            logger.error(e, exc_info=True)      

    def trigger_anchor_down(self):
        """Delegate method called by connector when setting anchor"""
        try:
            self._anchor_alarm.anchor_down(self.get_gps_position())
        except Exception as e:
            return e

    def trigger_chain_out(self):
        """Delegate method called by connector when chain is out and anchor alarm needs to be armed"""
        try:
            self._anchor_alarm.chain_out(self.get_gps_position())
        except Exception as e:
            return e

    def trigger_anchor_up(self):
        """Delegate method called by connector when anchor is raised and anchor alarm needs to be disabled"""
        self._anchor_alarm.anchor_up()


    def trigger_mute_alarm(self):
        """Delegate method called by connector when alarm should be muted"""
        self._anchor_alarm.mute_alarm()


    def trigger_increase_tolerance(self):
        """Delegate method called by connector when tolerance should be increased by 5m"""
        new_tolerance = self._settings['Tolerance'] + 5
        if new_tolerance <= 50:
            self._settings['Tolerance'] = new_tolerance
            self.trigger_show_message("info", "Increased tolerance to "+ str(self._settings['Tolerance'])+ " meters")


    def trigger_decrease_tolerance(self):
        """Delegate method called by connector when tolerance should be decreased by 5m"""
        new_tolerance = self._settings['Tolerance'] - 5
        if new_tolerance >= 0:
            self._settings['Tolerance'] = new_tolerance
            self.trigger_show_message("info", "Decreased tolerance to "+ str(self._settings['Tolerance'])+ " meters")



    def trigger_mooring_mode(self):
        """Delegate method called by connector when mooring mode should be enabled"""
        try:
            self._anchor_alarm.reset_state(self.get_gps_position(), self._settings["MooringRadius"])
        except Exception as e:
            self.trigger_show_message("error", "Unable to activate mooring ball mode when anchor alarm is already enabled")


    def trigger_show_message(self, level, message):
        # notify connectors
        for connector in self._connectors:
            try:
                connector.show_message(level, message)
            except Exception:
                pass # TODO XXX     



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
            self._anchor_alarm.on_timer_tick(self.get_gps_position())

        # notify connectors
        for connector in self._connectors:
            try:
                connector.update_state(current_state)
            except Exception:
                pass # TODO XXX        

        return True