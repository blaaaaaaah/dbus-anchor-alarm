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
import json

import logging
logger = logging.getLogger(__name__)

sys.path.insert(1, os.path.join(sys.path[0], '..'))


from abstract_connector import AbstractConnector
from anchor_alarm_controller import AnchorAlarmController
from anchor_alarm_controller import GPSPosition
from anchor_alarm_model import AnchorAlarmState

# our own packages
sys.path.insert(1, os.path.join(os.path.dirname(__file__), '../ext/velib_python'))


class DBusConnector(AbstractConnector):
    def __init__(self, timer_provider, settings_provider, service_name="com.victronenergy.anchoralarm"):
        super().__init__(timer_provider, settings_provider)

        self._timer_ids = {
            'anchor_up': None,
            'anchor_down': None,
            'chain_out': None,
            'mute_alarm': None,

            'show_error_timeout': None
        }

        self._previous_system_name = None
        self._system_name_error_duration = 15000

        self._init_settings()
        
        self._update_digital_input_names()

        self._init_dbus_monitor()
        self._init_dbus_service(service_name)
        
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

        # publish data on the service for other people to consume (MTTQ, ..)
        self._dbus_service.add_path('/State', 'DISABLED', "State of the anchor alarm")
        self._dbus_service.add_path('/Message', '', "Description of the state")
        self._dbus_service.add_path('/Level', '', "Info, Warning, Alarm or Emergency")
        self._dbus_service.add_path('/Muted', 0, "Is alarm muted")
        self._dbus_service.add_path('/Alarm', 0, "Is alarm on")
        self._dbus_service.add_path('/Params', '', "Various params (radius, current radius, tolerance, ..)")

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
        self._dbus_service['/State']    = current_state.state
        self._dbus_service['/Message']  = current_state.message
        self._dbus_service['/Level']    = current_state.level
        self._dbus_service['/Muted']    = 1 if current_state.muted else 0
        self._dbus_service['/Params']   = json.dumps(current_state.params)

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
                and self._dbus_service['/State'] in ['ALARM_DRAGGING', 'ALARM_NO_GPS']):

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


if __name__ == "__main__":
    import sys
    import os

    from gi.repository import GLib
    from dbus.mainloop.glib import DBusGMainLoop
    import dbus
    from settingsdevice import SettingsDevice
    from unittest.mock import MagicMock

    logging.basicConfig(level=logging.DEBUG)
    # Have a mainloop, so we can send/receive asynchronous calls to and from dbus
    DBusGMainLoop(set_as_default=True)

    from ve_utils import exit_on_error
   
    bus = dbus.SessionBus() if 'DBUS_SESSION_BUS_ADDRESS' in os.environ else dbus.SystemBus()
    dbus_connector = DBusConnector(lambda: GLib, lambda settings, cb: SettingsDevice(bus, settings, cb), "com.victronenergy.anchoralarm-test")

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
