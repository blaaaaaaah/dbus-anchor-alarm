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


from re import M
import sys
import os
import json

import logging
logger = logging.getLogger(__name__)

sys.path.insert(1, os.path.join(sys.path[0], '..'))


from abstract_connector import AbstractConnector
from anchor_alarm_controller import AnchorAlarmController
from anchor_alarm_controller import GPSPosition
from anchor_alarm_model import AnchorAlarmState

from collections import deque
import time
import math
from geopy.distance import geodesic


# our own packages
sys.path.insert(1, os.path.join(os.path.dirname(__file__), '../ext/velib_python'))


class DBusConnector(AbstractConnector):
    def __init__(self, timer_provider, settings_provider, nmea_bridge, service_name="com.victronenergy.anchoralarm"):
        super().__init__(timer_provider, settings_provider)

        self._timer_ids = {
            'anchor_up': None,
            'anchor_down': None,
            'chain_out': None,
            'mute_alarm': None,

            'show_error_timeout': None,

            'extended_status': None
        }

        self._previous_system_name = None
        self._system_name_error_duration = 15000
        self._ais_self_distance_threshold = 5  # meters, distance below which we consider the vessel is self

        self._vessels = {}

        # environment
        self._last_depth = None 
        self._last_awa = None
        self._last_aws = None

        self._bridge = nmea_bridge

        self._init_settings()
        
        self._update_digital_input_names()

        self._init_dbus_monitor()
        self._init_dbus_service(service_name)
        self._create_vessel('self')

        self._bridge.add_pgn_handler(129026, self._on_sog)
        self._bridge.add_pgn_handler(128267, self._on_depth)
        self._bridge.add_pgn_handler(130306, self._on_wind)
        self._bridge.add_pgn_handler(127250, self._on_heading)
        self._bridge.add_pgn_handler(129039, self._on_ais_message)  # AIS Class B Position Report
        self._bridge.add_pgn_handler(129810, self._on_ais_extended_message)  # AIS Class B static data (msg 24 Part B)

        
    def _init_settings(self):
        # create the setting that are needed
        settingsList = {
            # Digital input number for Anchor Down trigger. 
            # Wire a relay between windlass DOWN contactor/button and digital input. Use "0" to disable.
            # Enable the digital input on the Cerbo in Settings/IO/Digital inputs/Digital input [0-4] and set "Bilge pump". 
            "AnchorDownDigitalInputNumber":     ["/Settings/AnchorAlarm/DigitalInputs/AnchorDown/DigitalInputNumber", 2, 0, 4],

            # Duration for which the digital input must be activated before triggering an Anchor Down event. 
            # 3 seconds seems to be a good value. Too short and you might get false positives, too long you might get 
            # inacuracies with the boat drifting while dropping the anchor
            "AnchorDownDigitalInputDuration":   ["/Settings/AnchorAlarm/DigitalInputs/AnchorDown/DigitalInputDuration", 3, 0, 30],

            # Digital input number for the desired chain out/set radius trigger. 
            # You can wire a button but this event is usually handled by the NMEA bus. Use "0" to disable.
            # Enable the digital input on the Cerbo in Settings/IO/Digital inputs/Digital input [0-4] and set "Bilge pump"
            "ChainOutDigitalInputNumber":       ["/Settings/AnchorAlarm/DigitalInputs/ChainOut/DigitalInputNumber", 0, 0, 4],

            # Duration for which the digital input must be activated before triggering an Chain Out event. 
            "ChainOutDigitalInputDuration":     ["/Settings/AnchorAlarm/DigitalInputs/ChainOut/DigitalInputDuration", 0, 0, 30], 

            # Digital input number for Anchor Up trigger. 
            # Wire a relay between windlass UP contactor/button and digital input. Use "0" to disable.
            # Enable the digital input on the Cerbo in Settings/IO/Digital inputs/Digital input [0-4] and set "Bilge pump"
            "AnchorUpDigitalInputNumber":       ["/Settings/AnchorAlarm/DigitalInputs/AnchorUp/DigitalInputNumber", 1, 0, 4],

            # Duration for which the digital input must be activated before triggering an Anchor Up event. 
            "AnchorUpDigitalInputDuration":     ["/Settings/AnchorAlarm/DigitalInputs/AnchorUp/DigitalInputDuration", 3, 0, 30], 

            # Digital input number for Mute Alarm trigger. 
            # You can wire a button but this event is usually handled by the NMEA bus. Use "0" to disable.
            # Enable the digital input on the Cerbo in Settings/IO/Digital inputs/Digital input [0-4] and set "Bilge pump"
            "MuteAlarmDigitalInputNumber":      ["/Settings/AnchorAlarm/DigitalInputs/MuteAlarm/DigitalInputNumber", 0, 0, 4],

            # Duration for which the digital input must be activated before triggering an Mute alarm event. 
            "MuteAlarmDigitalInputDuration":    ["/Settings/AnchorAlarm/DigitalInputs/MuteAlarm/DigitalInputDuration", 0, 0, 30], 


            # Digital input number for Mooring ball mode trigger. 
            # You can wire a button but this event is usually handled by the NMEA bus. Use "0" to disable.
            # Enable the digital input on the Cerbo in Settings/IO/Digital inputs/Digital input [0-4] and set "Bilge pump"
            "MooringModeDigitalInputNumber":      ["/Settings/AnchorAlarm/DigitalInputs/MooringMode/DigitalInputNumber", 0, 0, 4],

            # Duration for which the digital input must be activated before triggering an Mooring mode event. 
            "MooringModeDigitalInputDuration":    ["/Settings/AnchorAlarm/DigitalInputs/MooringMode/DigitalInputDuration", 0, 0, 30], 


            # Digital input number to use to show feedback and handle notifications on the Cerbo
            # You can use an unused one re-use Anchor Down or Anchor Up digital inputs as it will only change the name
            # of the digital input. Use "0" to disable.
            # Cerbo's Alarm/Notifications system is very hard coded, so abusing the Digital input system is a 
            # good compromise.
            "FeedbackDigitalInputNumber"  :      ["/Settings/AnchorAlarm/DigitalInputs/Feedback/DigitalInputNumber", 1, 0, 4],

            # Use or not the custom System Name of the system to show messages on the main top middle tile
            # Will override any custom name and will not save the previous one so write it down if needed
            "FeedbackUseSystemName":            ["/Settings/AnchorAlarm/FeedbackUseSystemName", 0, 0, 1],


            # Number of tracks to keep for each vessel
            "NumberOfTracks":            ["/Settings/AnchorAlarm/Vessels/NumberOfTracks", 100, 0, 1000],

            # Interval in seconds to add a track point for each vessel
            "TracksInterval":            ["/Settings/AnchorAlarm/Vessels/TracksInterval", 30, 0, 1000],

            # Interval in seconds to prune old tracks for each vessel
            "PruneInterval":             ["/Settings/AnchorAlarm/Vessels/PruneInterval", 180, 0, 3600],

            # Distance to vessels to keep track of
            "DistanceToVessel":            ["/Settings/AnchorAlarm/Vessels/DistanceToVessel", 400, 0, 2000],


            # Maximum number ofvessels to keep track of
            "MaxVessels":                 ["/Settings/AnchorAlarm/Vessels/MaxVessels", 10, 0, 30],

        }

        self._settings = self._settings_provider(settingsList, self._on_setting_changed)

    
    def _init_dbus_monitor(self):
        # listen to all 4 digital inputs so we don't have to recreate/update the dbus monitor

        dummy = {'code': None, 'whenToLog': 'configChange', 'accessLevel': None}
        
        monitorlist = {
            'com.victronenergy.digitalinput': {
                '/CustomName': dummy,	
                '/ProductName': dummy, 
                '/State': dummy
            }, 
            'com.victronenergy.settings': {
                '/Settings/DigitalInput/1/AlarmSetting': dummy,
                '/Settings/DigitalInput/2/AlarmSetting': dummy,
                '/Settings/DigitalInput/3/AlarmSetting': dummy,
                '/Settings/DigitalInput/4/AlarmSetting': dummy,
                
                '/Settings/DigitalInput/1/InvertAlarm': dummy,
                '/Settings/DigitalInput/2/InvertAlarm': dummy,
                '/Settings/DigitalInput/3/InvertAlarm': dummy,
                '/Settings/DigitalInput/4/InvertAlarm': dummy,

                '/Settings/SystemSetup/SystemName':      dummy
            },
            'com.victronenergy.platform': {
                '/Notifications/Alarm': dummy
            }
        }

        # TODO XXX : add deviceAddedCallback handler in case of digitalinput service is loaded after us ?
        self._alarm_monitor = self._create_dbus_monitor(monitorlist, self._on_digitalinput_service_changed, deviceAddedCallback=None, deviceRemovedCallback=None)

    def _create_dbus_monitor(self, *args, **kwargs):
        from dbusmonitor import DbusMonitor
        return DbusMonitor(*args, **kwargs)



    def _init_dbus_service(self, service_name):
        self._dbus_service = self._create_dbus_service(service_name, register=False)

        self._dbus_service.add_mandatory_paths(sys.argv[0], self._get_version(), None, 0, 0, 'Anchor Alarm', 0, 0, 1)

            # Alarm Information
        self._dbus_service.add_path('/Alarm/State', 'DISABLED', "Current alarm state")
        self._dbus_service.add_path('/Alarm/Message', '', "Current alarm message")
        self._dbus_service.add_path('/Alarm/Level', '', "Info, Warning, Alarm, or Emergency")
        self._dbus_service.add_path('/Alarm/Alarm', 0, "Is in alarm state")
        self._dbus_service.add_path('/Alarm/Muted', 0, "Is alarm muted")
        self._dbus_service.add_path('/Alarm/Active', 0, "Is alarm currently on")
        self._dbus_service.add_path('/Alarm/MutedDuration', 0, "Seconds alarm has been muted")
        self._dbus_service.add_path('/Alarm/NoGPSDuration', 0, "Seconds without GPS")
        self._dbus_service.add_path('/Alarm/OutOfRadiusDuration', 0, "Seconds outside radius")

        # Anchor Info
        self._dbus_service.add_path('/Anchor/Latitude', "", "Anchor latitude", writeable=False)
        self._dbus_service.add_path('/Anchor/Longitude', "", "Anchor longitude", writeable=False)
        self._dbus_service.add_path('/Anchor/Radius', "", "Safe radius (m)", writeable=False)
        self._dbus_service.add_path('/Anchor/Distance', "", "Distance to anchor (m)", writeable=False)
        self._dbus_service.add_path('/Anchor/Tolerance', "", "Tolerance (m)", writeable=False)        

        # Environment Info
        self._dbus_service.add_path('/Environment/Depth', "", "Depth (m)", writeable=False)
        self._dbus_service.add_path('/Environment/Wind/Speed', "", "Wind speed (knots)", writeable=False)
        self._dbus_service.add_path('/Environment/Wind/Direction', "", "Wind direction (degrees)", writeable=False)


        # create trigger points for other people to manipulate state
        self._dbus_service.add_path('/Triggers/AnchorDown', 0, "Set 1 to trigger anchor down and define drop point", writeable=True, onchangecallback=self._on_service_changed)
        self._dbus_service.add_path('/Triggers/ChainOut',   0, "Set 1 to trigger chain out and set radius"         , writeable=True, onchangecallback=self._on_service_changed)
        self._dbus_service.add_path('/Triggers/AnchorUp',   0, "Set 1 to trigger anchor up and disable alarm"      , writeable=True, onchangecallback=self._on_service_changed)
        self._dbus_service.add_path('/Triggers/MuteAlarm',  0, "Set 1 to mute current alarm"                       , writeable=True, onchangecallback=self._on_service_changed)
        self._dbus_service.add_path('/Triggers/MooringMode',0, "Set 1 to enable mooring mode"                      , writeable=True, onchangecallback=self._on_service_changed)
        self._dbus_service.add_path('/Triggers/DecreaseTolerance',  0, "Set 1 to decrease tolerance by 5m"         , writeable=True, onchangecallback=self._on_service_changed)
        self._dbus_service.add_path('/Triggers/IncreaseTolerance',  0, "Set 1 to increase tolerance by 5m"         , writeable=True, onchangecallback=self._on_service_changed)

        self._dbus_service.register()


    def _create_dbus_service(self, *args, **kwargs):
        from vedbus import VeDbusService
        return VeDbusService(*args, **kwargs)



    def on_state_changed(self, current_state:AnchorAlarmState):
        """Called by controller when state changed"""
        logger.info("On state changed "+ current_state.state)

        # update values on DBUS
        self.update_state(current_state)


        alarm_state = 1 if current_state.state in ['ALARM_DRAGGING', 'ALARM_NO_GPS'] else 0

        # toggle alarm state
        # we can't simply change the /Alarm path on the digital_input dbus. We need to workaround using settings and creating
        # an alarm condition by setting Alarm to True and invert Alarm to True as well 
        if self._settings['FeedbackDigitalInputNumber'] != 0:
            self._alarm_monitor.set_value("com.victronenergy.settings", '/Settings/DigitalInput/'+ str(self._settings['FeedbackDigitalInputNumber']) +'/AlarmSetting', alarm_state)
            self._alarm_monitor.set_value("com.victronenergy.settings", '/Settings/DigitalInput/'+ str(self._settings['FeedbackDigitalInputNumber']) +'/InvertAlarm', alarm_state)


    def update_state(self, current_state:AnchorAlarmState):
        """Called by controller every second with updated state"""

        # Alarm info
        self._dbus_service['/Alarm/State']    = current_state.state
        self._dbus_service['/Alarm/Message']  = current_state.message
        self._dbus_service['/Alarm/Level']    = current_state.level
        self._dbus_service['/Alarm/Muted']    = 1 if current_state.muted else 0
        self._dbus_service['/Alarm/Alarm']    = 1 if current_state.state in ['ALARM_DRAGGING', 'ALARM_DRAGGING_MUTED', 'ALARM_NO_GPS', 'ALARM_NO_GPS_MUTED'] else 0
        self._dbus_service['/Alarm/MutedDuration']          = current_state.params['alarm_muted_count']
        self._dbus_service['/Alarm/NoGPSDuration']          = current_state.params['no_gps_count']
        self._dbus_service['/Alarm/OutOfRadiusDuration']    = current_state.params['out_of_radius_count']


        # Anchor info
        self._dbus_service['/Anchor/Latitude']          = "" if current_state.params['drop_point'] is None else current_state.params['drop_point'].latitude
        self._dbus_service['/Anchor/Longitude']         = "" if current_state.params['drop_point'] is None else current_state.params['drop_point'].longitude
        self._dbus_service['/Anchor/Radius']            = current_state.params['radius']
        self._dbus_service['/Anchor/Distance']          = current_state.params['current_radius']
        self._dbus_service['/Anchor/Tolerance']         = current_state.params['radius_tolerance']


        # Vessel info
        if self.controller is not None:
            gps_position = self.controller.get_gps_position()
            if gps_position is not None:
                self._vessels['self']['latitude'] = gps_position.latitude
                self._vessels['self']['longitude'] = gps_position.longitude

        # update vessels info
        self._prune_vessels()
        for mmsi in list(self._vessels.keys()):
            self._write_vessel_info(mmsi)


        # Environment Info
        self._dbus_service['/Environment/Wind/Speed']       = self._last_aws if self._last_aws is not None else ""
        self._dbus_service['/Environment/Wind/Direction']   = self._last_awa if self._last_awa is not None else ""
        self._dbus_service['/Environment/Depth']            = self._last_depth if self._last_depth is not None else ""


        if self._settings['FeedbackDigitalInputNumber'] != 0:
            self._alarm_monitor.set_value(self._feedback_digital_input, '/CustomName', current_state.message)
            self._alarm_monitor.set_value(self._feedback_digital_input, '/ProductName', current_state.message)

        # do not update system name if currently showing an error
        if self._settings['FeedbackUseSystemName'] != 0 and self._previous_system_name is None:
            self._alarm_monitor.set_value('com.victronenergy.settings', '/Settings/SystemSetup/SystemName', current_state.short_message)


    def show_message(self, level, message):
        if level != "error":
            return  # only support error message
        
        # make sure the FeedbackDigitalInputNumber digital input actually exists so we can fallback on system name
        if self._settings['FeedbackDigitalInputNumber'] != 0 and self._alarm_monitor.exists(self._feedback_digital_input, '/CustomName'):
            self._alarm_monitor.set_value(self._feedback_digital_input, '/CustomName', message)
            self._alarm_monitor.set_value(self._feedback_digital_input, '/ProductName', message)
            self._alarm_monitor.set_value("com.victronenergy.settings", '/Settings/DigitalInput/'+ str(self._settings['FeedbackDigitalInputNumber']) +'/AlarmSetting', 1)
            self._alarm_monitor.set_value("com.victronenergy.settings", '/Settings/DigitalInput/'+ str(self._settings['FeedbackDigitalInputNumber']) +'/InvertAlarm', 1)

        # if feedback digital input number is not set, use system name 
        else:
            # save previous system name to restore it afterwards
            if self._previous_system_name is None:
                self._previous_system_name =  self._alarm_monitor.get_value('com.victronenergy.settings', '/Settings/SystemSetup/SystemName')

            self._alarm_monitor.set_value('com.victronenergy.settings', '/Settings/SystemSetup/SystemName', message)

            def _restore_system_name():
                self._alarm_monitor.set_value('com.victronenergy.settings', '/Settings/SystemSetup/SystemName', self._previous_system_name)
            
            self._add_timer('show_error_timeout', _restore_system_name, self._system_name_error_duration)


    def _on_setting_changed(self, path, old_value, new_value):
        # just recompute all names
        self._update_digital_input_names()
        

    def _update_digital_input_names(self):
        # com.victronenergy.digitalinput.input00 doesn't exist, so if any XXXDigitalInputNumber is 0, it will won't match a
        # a changed dbusPath and will be ignored 
        self._anchor_down_digital_input = 'com.victronenergy.digitalinput.input0' + str(self._settings['AnchorDownDigitalInputNumber'])
        self._chain_out_digital_input   = 'com.victronenergy.digitalinput.input0' + str(self._settings['ChainOutDigitalInputNumber'])
        self._anchor_up_digital_input   = 'com.victronenergy.digitalinput.input0' + str(self._settings['AnchorUpDigitalInputNumber'])
        self._mute_alarm_digital_input  = 'com.victronenergy.digitalinput.input0' + str(self._settings['MuteAlarmDigitalInputNumber'])
        self._mooring_mode_digital_input= 'com.victronenergy.digitalinput.input0' + str(self._settings['MooringModeDigitalInputNumber'])
        self._feedback_digital_input    = 'com.victronenergy.digitalinput.input0' + str(self._settings['FeedbackDigitalInputNumber'])


    def _on_digitalinput_service_changed(self, dbusServiceName, dbusPath, dict, changes, deviceInstance):
        # controller is not set yet
        if self.controller is None:
            return
        
        logger.debug("DBUSMonitor "+ dbusServiceName + " "+ dbusPath + " " + str(changes["Value"]))

        # digital inputs states are pairs of ints. 0 is low, 1 is high, 2 is off, 3 is on and so on 
        # depending on input type in settings

        # mute alarm
        if ( dbusServiceName == 'com.victronenergy.platform'
                and dbusPath == '/Notifications/Alarm'
                and changes['Value'] == 0 
                and self._dbus_service['/Alarm/State'] in ['ALARM_DRAGGING', 'ALARM_NO_GPS']):

            self.controller.trigger_mute_alarm()


        # anchor_down digital input trigger
        if ( dbusServiceName == self._anchor_down_digital_input
                and dbusPath == '/State' ):
            
            logger.debug("anchor_down digital input trigger :" + "On" if changes['Value'] % 2 == 1 else "Off")
            if ( changes['Value'] % 2 == 1 ):
                self._add_timer('anchor_down', self.controller.trigger_anchor_down, int(self._settings['AnchorDownDigitalInputDuration'])*1000)
            else:
                self._remove_timer('anchor_down')


        # anchor up digital input trigger
        if ( dbusServiceName == self._anchor_up_digital_input
                and dbusPath == '/State' ):
            
            logger.debug("anchor_up digital input trigger :" + "On" if changes['Value'] % 2 == 1 else "Off")
            if ( changes['Value'] % 2 == 1 ):
                self._add_timer('anchor_up', self.controller.trigger_anchor_up, int(self._settings['AnchorUpDigitalInputDuration'])*1000)
            else:
                self._remove_timer('anchor_up')

        # chain out digital input trigger
        if ( dbusServiceName == self._chain_out_digital_input
                and dbusPath == '/State' ):
            
            if ( changes['Value'] % 2 == 1 ):
                self._add_timer('chain_out', self.controller.trigger_chain_out, int(self._settings['ChainOutDigitalInputDuration'])*1000)
            else:
                self._remove_timer('chain_out')


        # mute alarm digital input trigger
        if ( dbusServiceName == self._mute_alarm_digital_input
                and dbusPath == '/State' ):
            
            if ( changes['Value'] % 2 == 1 ):
                self._add_timer('mute_alarm', self.controller.trigger_mute_alarm, int(self._settings['MuteAlarmDigitalInputDuration'])*1000)
            else:
                self._remove_timer('mute_alarm')

        # mooring mode digital input trigger
        if ( dbusServiceName == self._mooring_mode_digital_input
                and dbusPath == '/State' ):
            
            if ( changes['Value'] % 2 == 1 ):
                self._add_timer('mooring_mode', self.controller.trigger_mooring_mode, int(self._settings['MooringModeDigitalInputDuration'])*1000)
            else:
                self._remove_timer('mooring_mode')


    # WARNING : triggering '/Triggers/AnchorDown' etc by setting 1 in dbus-spy will only work the first time
    # since dbus-spy doesn't interpret return False to reject the change correctly.
    # Use dbus -y com.victronenergy.anchoralarm /Triggers/AnchorDown SetValue %1   instead

    def _on_service_changed(self, path, newvalue):
        if path == '/Triggers/AnchorDown':
            self.controller.trigger_anchor_down()
            # controller update will put value back to 0 ?
            return False
        
        if path == '/Triggers/ChainOut':
            self.controller.trigger_chain_out()
            # controller update will put value back to 0 ?
            return False
        
        if path == '/Triggers/AnchorUp':
            self.controller.trigger_anchor_up()
            # controller update will put value back to 0 ?
            return False

        if path == '/Triggers/MuteAlarm':
            self.controller.trigger_mute_alarm()
            # controller update will put value back to 0 ?
            return False
        
        if path == '/Triggers/MooringMode':
            self.controller.trigger_mooring_mode()
            # controller update will put value back to 0 ?
            return False
        
        if path == '/Triggers/DecreaseTolerance':
            self.controller.trigger_decrease_tolerance()
            # controller update will put value back to 0 ?
            return False

        if path == '/Triggers/IncreaseTolerance':
            self.controller.trigger_increase_tolerance()
            # controller update will put value back to 0 ?
            return False



    def _get_version(self):
        version_file_path = os.path.join(os.path.dirname(__file__), '..', 'VERSION')
        try:
            with open(version_file_path, 'r') as version_file:
                version = version_file.read().strip()
        except Exception:
            # Handle unexpected errors
            version = "unknown"

        return version
    
        


    def _on_sog(self, nmea_message):
        # {'canId': 167248387, 'prio': 2, 'src': 3, 'dst': 255, 'pgn': 129026, 'timestamp': '2025-05-16T13:51:59.279Z', 'fields': {'SID': 208, 'COG Reference': 'True', 'COG': 0.2787, 'SOG': 0.07}, 'description': 'COG & SOG, Rapid Update'}
        if "fields" not in nmea_message:
            return
        
        if "SOG" not in nmea_message["fields"]:
            return  # should not happen

        if "COG" not in nmea_message["fields"]:
            return  # should not happen
        
        self._vessels['self']['sog'] = nmea_message["fields"]["SOG"]  * 1.94384  # Convert m/s to knots
        self._vessels['self']['cog'] = nmea_message["fields"]["COG"]  * (180.0 / math.pi)


    def _on_heading(self, nmea_message):
        # {'canId': 167248387, 'prio': 2, 'src': 3, 'dst': 255, 'pgn': 129026, 'timestamp': '2025-05-16T13:51:59.279Z', 'fields': {'SID': 208, 'COG Reference': 'True', 'COG': 0.2787, 'SOG': 0.07}, 'description': 'COG & SOG, Rapid Update'}
        if "fields" not in nmea_message:
            return
        
        if "Heading" not in nmea_message["fields"]:
            return  # should not happen
        
        self._vessels['self']['heading'] = nmea_message["fields"]["Heading"]  * (180.0 / math.pi)



    def _on_depth(self, nmea_message):
        # {"canId":234162979,"prio":3,"src":35,"dst":255,"pgn":128267,"timestamp":"2025-06-30T14:03:17.611Z","fields":{"Depth":6,"Offset":0,"Range":140},"description":"Water Depth","data":[255,88,2,0,0,0,0,14]}
        if "fields" not in nmea_message:
            return
        
        if "Depth" not in nmea_message["fields"]:
            return  # should not happen

        if "Offset" not in nmea_message["fields"]:
            return  # should not happen
        
        # TODO XXX : test that
        depth = float(nmea_message["fields"]["Depth"])
        if float(nmea_message["fields"]["Offset"]) != 0:
            depth += float(nmea_message["fields"]["Offset"])
        
        self._last_depth = depth


    def _on_wind(self, nmea_message):
        # {'canId': 167576065, 'prio': 2, 'src': 1, 'dst': 255, 'pgn': 130306, 'timestamp': '2025-06-30T19:43:50.240Z', 'fields': {'Wind Speed': 1.96, 'Wind Angle': 6.22, 'Reference': 'Apparent'}, 'description': 'Wind Data', 'data': bytearray(b'\xff\xc4\x00\xf8\xf2\xfa\xff\xff')}
        if "fields" not in nmea_message:
            return
        
        if "Reference" not in nmea_message["fields"]:
            return  # should not happen

        if "Wind Speed" not in nmea_message["fields"]:
            return  # should not happen
        
        if "Wind Angle" not in nmea_message["fields"]:
            return  # should not happen
        

        if  nmea_message["fields"]["Reference"] != "Apparent":
            return

        self._last_aws = nmea_message["fields"]["Wind Speed"] * 1.94384  # Convert m/s to knots
        self._last_awa = nmea_message["fields"]["Wind Angle"] * (180.0 / math.pi)



    def _create_vessel(self, mmsi):
        """Create a new vessel with the given MMSI"""
        if mmsi in self._vessels:
            return self._vessels[mmsi]
        
        # Vessel Info
        self._dbus_service.add_path('/Vessels/'+ mmsi +'/Latitude', "", "Current latitude", writeable=False)
        self._dbus_service.add_path('/Vessels/'+ mmsi +'/Longitude', "", "Current longitude", writeable=False)
        self._dbus_service.add_path('/Vessels/'+ mmsi +'/SOG', "", "Speed over ground (knots)", writeable=False)
        self._dbus_service.add_path('/Vessels/'+ mmsi +'/COG', "", "Course over ground (deg)", writeable=False)
        self._dbus_service.add_path('/Vessels/'+ mmsi +'/Heading', "", "Heading (deg)", writeable=False)
        self._dbus_service.add_path('/Vessels/'+ mmsi +'/Beam', "", "Beam (m)", writeable=False)
        self._dbus_service.add_path('/Vessels/'+ mmsi +'/Length', "", "Length (m)", writeable=False)
        self._dbus_service.add_path('/Vessels/'+ mmsi +'/Tracks', "", "Tracks", writeable=False)
        
        vessel = {
            'mmsi': mmsi,
            'latitude': "",
            'longitude': "",
            'sog': "",
            'cog': "",
            'tracks': deque(maxlen=self._settings['NumberOfTracks']),  # Keep last 100 tracks
            'distance': 0,  # Distance to anchor
            'beam': "",
            'length': "",
            'heading': "",
        }
        self._vessels[mmsi] = vessel
        return vessel


    def _remove_vessel(self, mmsi):
        """Remove a vessel with the given MMSI"""
        if mmsi in self._vessels:
            del self._vessels[mmsi]
            # Remove paths from dbus service
            del self._dbus_service['/Vessels/' + mmsi + '/Latitude']
            del self._dbus_service['/Vessels/' + mmsi + '/Longitude']
            del self._dbus_service['/Vessels/' + mmsi + '/SOG']
            del self._dbus_service['/Vessels/' + mmsi + '/COG']
            del self._dbus_service['/Vessels/' + mmsi + '/Heading']
            del self._dbus_service['/Vessels/' + mmsi + '/Beam']
            del self._dbus_service['/Vessels/' + mmsi + '/Length']
            del self._dbus_service['/Vessels/' + mmsi + '/Tracks']


    def _write_vessel_info(self, mmsi):
        """Write the vessel info to the dbus service"""

        if mmsi not in self._vessels:
            return
        
        vessel = self._vessels[mmsi]

        now = int(time.time())
        # Only add if empty or at least 30 seconds since the last in the queue
        tracks = vessel['tracks']
        if not tracks or (now - tracks[-1]['timestamp'] >= self._settings['TracksInterval']):
            entry = {
                'latitude': vessel['latitude'],
                'longitude': vessel['longitude'],
                'timestamp': now
            }
            tracks.append(entry)
        
        self._dbus_service['/Vessels/' + mmsi + '/Latitude'] = vessel['latitude']
        self._dbus_service['/Vessels/' + mmsi + '/Longitude'] = vessel['longitude']
        self._dbus_service['/Vessels/' + mmsi + '/SOG'] = vessel['sog']
        self._dbus_service['/Vessels/' + mmsi + '/COG'] = vessel['cog']
        self._dbus_service['/Vessels/' + mmsi + '/Heading'] = vessel['heading']
        self._dbus_service['/Vessels/' + mmsi + '/Beam'] = vessel['beam']
        self._dbus_service['/Vessels/' + mmsi + '/Length'] = vessel['length']
        self._dbus_service['/Vessels/' + mmsi + '/Tracks'] = json.dumps(list(vessel['tracks']))



    def _on_ais_message(self, nmea_message):
        # {"canId":301469618,"prio":4,"src":178,"dst":255,"pgn":129039,"timestamp":"2025-07-01T16:48:46.066Z","input":[],"fields":{"Message ID":"Standard Class B position report","Repeat Indicator":"Initial","User ID":9221639,"Longitude":-61.3895,"Latitude":12.5272,"Position Accuracy":"Low","RAIM":"not in use","Time Stamp":"43","COG":6.1994,"SOG":0.05,"AIS Transceiver information":"Channel B VDL reception","Heading":6.1959,"Regional Application B":0,"Unit type":"SOTDMA","Integrated Display":"No","DSC":"No","Band":"Top 525 kHz of marine band","Can handle Msg 22":"No","AIS mode":"Autonomous","AIS communication state":"SOTDMA"},"description":"AIS Class B Position Report"}}
        # {'canId': 301469483, 'prio': 4, 'src': 43, 'dst': 255, 'pgn': 129039, 'timestamp': '2025-07-16T12:14:00.145Z', 'input': [], 'fields': {'Message ID': 'Standard Class B position report', 'Repeat Indicator': 'Initial', 'User ID': 316033362, 'Longitude': -61.7400512, 'Latitude': 12.010176, 'Position Accuracy': 'High', 'RAIM': 'in use', 'Time Stamp': '59', 'COG': 6.2383, 'SOG': 0, 'Communication State': 393222, 'AIS Transceiver information': 'Channel A VDL reception', 'Regional Application': 0, 'Regional Application B': 0, 'Unit type': 'CS', 'Integrated Display': 'No', 'DSC': 'Yes', 'Band': 'Entire marine band', 'Can handle Msg 22': 'Yes', 'AIS mode': 'Autonomous', 'AIS communication state': 'ITDMA'}, 'description': 'AIS Class B Position Report'}
        # {'canId': 435884587, 'prio': 6, 'src': 43, 'dst': 255, 'pgn': 129810, 'timestamp': '2025-07-16T13:37:27.799Z', 'input': [], 'fields': {'Message ID': 'Static data report', 'Repeat Indicator': 'Initial', 'User ID': 378150000, 'Type of ship': 'Sailing', 'Vendor ID': 'FECD', 'Callsign': 'ZJL6809', 'Length': 24, 'Beam': 5, 'Position reference from Starboard': 1, 'Position reference from Bow': 9, 'Spare': 0, 'Sequence ID': 0}, 'description': 'AIS Class B static data (msg 24 Part B)'}
        # {"canId":435884331,"prio":6,"src":43,"dst":255,"pgn":129809,"timestamp":"2025-07-16T13:37:28.565Z","input":[],"fields":{"Message ID":"Static data report","Repeat Indicator":"Initial","User ID":316038742,"Name":"LA DOLCE VITA, EH"},"description":"AIS Class B static data (msg 24 Part A)"}}

        """Handle AIS messages to update vessels"""
        if "fields" not in nmea_message:
            return
        
        if "User ID" not in nmea_message["fields"]:
            return
        
        if "Longitude" not in nmea_message["fields"]:
            return 
        
        if "Latitude" not in nmea_message["fields"]:
            return
        
        if "COG" not in nmea_message["fields"]:
            return
        
        if "SOG" not in nmea_message["fields"]:
            return

        #if "Heading" not in nmea_message["fields"]:
        #    return

        if self.controller is None:
            return
        
        gps_position = self.controller.get_gps_position()
        if gps_position is None:
            return
        
        mmsi = str(nmea_message["fields"]["User ID"])
        longitude = nmea_message["fields"]["Longitude"]
        latitude = nmea_message["fields"]["Latitude"]   

        try:
            distance = geodesic((latitude, longitude), (gps_position.latitude, gps_position.longitude)).meters
        except (ValueError, Exception):
            logger.debug(f"Invalid coordinates for vessel {mmsi}: lat={latitude}, lon={longitude}")
            return  # Ignore vessels with invalid coordinates

        if distance < self._ais_self_distance_threshold:
            # this is self. save MMSI in settings to fetch 
            logger.debug(f"Ignoring vessel {mmsi} at distance {distance} meters, self ?")
            return


        if distance > self._settings['DistanceToVessel']:
            logger.debug(f"Ignoring vessel {mmsi} at distance {distance} meters, too far away")
            return  # Ignore vessels that are too far away
        
        if len(self._vessels) > self._settings['MaxVessels']:   # > and not >= because we always have self vessel in the list 
            # We have too many vessels, check if we need to replace one
            farther_vessel_mmsi = max(self._vessels.keys(), key=lambda vessel_mmsi: self._vessels[vessel_mmsi]['distance'])
            if farther_vessel_mmsi == 'self':
                return # should never happen, but just in case
            
            farther_vessel = self._vessels[farther_vessel_mmsi]
            if farther_vessel['distance'] < distance:
                logger.debug(f"Ignoring vessel {mmsi} at distance {distance} meters, too many vessels already")
                return   
            else:
                # Remove the farthest vessel to replace with this one
                self._remove_vessel(farther_vessel['mmsi'])
                logger.debug(f"Removed vessel {farther_vessel['mmsi']} at distance {farther_vessel['distance']} meters to add {mmsi} at distance {distance}")
            
        # Create or update vessel info
        vessel = self._create_vessel(mmsi)
        vessel['latitude'] = latitude
        vessel['longitude'] = longitude
        vessel['sog'] = nmea_message["fields"]["SOG"]
        vessel['cog'] = nmea_message["fields"]["COG"] * (180.0 / math.pi)  # Convert radians to degrees
        vessel['heading'] = "" # nmea_message["fields"]["Heading"] * (180.0 / math.pi)  # Convert radians to degrees
        vessel['distance'] = distance   # keep distance for easier pruning


    def _on_ais_extended_message(self, nmea_message):
        # PGN 129810: AIS Class B static data (msg 24 Part B)
        # {'canId': 435884587, 'prio': 6, 'src': 43, 'dst': 255, 'pgn': 129810, 'timestamp': '2025-07-16T13:37:27.799Z', 'input': [], 'fields': {'Message ID': 'Static data report', 'Repeat Indicator': 'Initial', 'User ID': 378150000, 'Type of ship': 'Sailing', 'Vendor ID': 'FECD', 'Callsign': 'ZJL6809', 'Length': 24, 'Beam': 5, 'Position reference from Starboard': 1, 'Position reference from Bow': 9, 'Spare': 0, 'Sequence ID': 0}, 'description': 'AIS Class B static data (msg 24 Part B)'}
        
        """Handle AIS extended messages (PGN 129810) to update vessel beam and length"""
        if "fields" not in nmea_message:
            return
        
        if "User ID" not in nmea_message["fields"]:
            return
        
        mmsi = str(nmea_message["fields"]["User ID"])
        
        # Only process if vessel already exists in our list
        if mmsi not in self._vessels:
            return
        
        # Check for required fields
        if "Beam" not in nmea_message["fields"]:
            return
        
        if "Length" not in nmea_message["fields"]:
            return
        
        # Update vessel with beam and length data
        vessel = self._vessels[mmsi]
        vessel['beam'] = nmea_message["fields"]["Beam"]
        vessel['length'] = nmea_message["fields"]["Length"]
        
        logger.debug(f"Updated vessel {mmsi} with beam={vessel['beam']}m, length={vessel['length']}m")



    def _prune_vessels(self):
        """Prune vessels that are too far away"""
        gps_position = self.controller.get_gps_position()
        if gps_position is None:
            return

        now = int(time.time())
        
        for mmsi in list(self._vessels.keys()):
            if mmsi == 'self':
                continue

            vessel = self._vessels[mmsi]

            tracks = vessel['tracks']
            if (len(tracks) > 0 and now - tracks[-1]['timestamp'] >= self._settings['PruneInterval']):
                # If the last track is older than the prune interval, remove the vessel
                self._remove_vessel(mmsi)
                continue

            # If the vessel is too far away, remove it
            if vessel['distance'] > self._settings['DistanceToVessel']:
                self._remove_vessel(mmsi)


if __name__ == "__main__":
    import sys
    import os

    from nmea_bridge import NMEABridge
    from utils import find_n2k_can

    from gi.repository import GLib
    from dbus.mainloop.glib import DBusGMainLoop
    import dbus
    from settingsdevice import SettingsDevice
    from unittest.mock import MagicMock

    logging.basicConfig(level=logging.DEBUG)
    # Have a mainloop, so we can send/receive asynchronous calls to and from dbus
    DBusGMainLoop(set_as_default=True)

    bus = dbus.SessionBus() if 'DBUS_SESSION_BUS_ADDRESS' in os.environ else dbus.SystemBus()

    can_id = find_n2k_can(bus)
    bridge = NMEABridge(can_id)
   
    dbus_connector = DBusConnector(lambda: GLib, lambda settings, cb: SettingsDevice(bus, settings, cb), bridge, "com.victronenergy.anchoralarm-test")

    controller = MagicMock()
    controller.trigger_anchor_down  = MagicMock(side_effect=lambda: logger.info("Trigger anchor down"))
    controller.trigger_anchor_up    = MagicMock(side_effect=lambda: logger.info("Trigger anchor up"))
    controller.trigger_chain_out    = MagicMock(side_effect=lambda: logger.info("Trigger chain out"))
    controller.trigger_mute_alarm   = MagicMock(side_effect=lambda: logger.info("Trigger mute alarm"))
    dbus_connector.set_controller(controller)

    # code to test notifications to Cerbo
    """
    state_disabled = AnchorAlarmState('DISABLED', 'Anchor alarm disabled',"short message", 'info', False, {})
    dbus_connector.on_state_changed(state_disabled)
    state_dragging = AnchorAlarmState('ALARM_DRAGGING', 'Anchor dragging !',"short message", 'emergency', False, {'drop_point': GPSPosition(10, 11), 'radius': 12})
    dbus_connector.on_state_changed(state_dragging)
    """

	# Start and run the mainloop
    #logger.info("Starting mainloop, responding only on events")
    mainloop = GLib.MainLoop()
    mainloop.run()
