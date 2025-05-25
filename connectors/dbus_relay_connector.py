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


class DBusRelayConnector(AbstractConnector):
    def __init__(self, timer_provider, settings_provider):
        super().__init__(timer_provider, settings_provider)

        self._timer_ids = {
       
        }

        self._init_settings()
        
        self._init_dbus_monitor()
        
    def _init_settings(self):
        # create the setting that are needed
        settingsList = {
            # Use or not the relay when the alarm is on
            "Enabled":            ["/Settings/AnchorAlarm/Relay/Enabled", 0, 0, 1],

            # Which relay to use. Default to 1 because 0 is usually reserved for generator and victron's stuff
            # Connector will verify that Relay mode is on "manual" but won't set it automatically
            "RelayNumber":        ["/Settings/AnchorAlarm/Relay/Number", 1, 0, 1],

            # Should the relay be inverted ?
            "Inverted":           ["/Settings/AnchorAlarm/Relay/Inverted", 0, 0, 1],

        }

        self._settings = self._settings_provider(settingsList, self._on_setting_changed)

    
    def _init_dbus_monitor(self):
        # listen to all 4 digital inputs so we don't have to recreate/update the dbus monitor

        dummy = {'code': None, 'whenToLog': 'configChange', 'accessLevel': None}
        
        monitorlist = {
            'com.victronenergy.system': {
                '/Relay/0/State': dummy,	
                '/Relay/1/State': dummy, 
            }, 
            'com.victronenergy.settings': {
                '/Settings/Relay/1/Function': dummy,
            }
        }

        self._alarm_monitor = self._create_dbus_monitor(monitorlist, self._on_monitor_changed, deviceAddedCallback=None, deviceRemovedCallback=None)

    def _create_dbus_monitor(self, *args, **kwargs):
        from dbusmonitor import DbusMonitor
        return DbusMonitor(*args, **kwargs)


    def on_state_changed(self, current_state:AnchorAlarmState):
        """Called by controller when state changed"""
        logger.info("On state changed "+ current_state.state)


        alarm_state = current_state.state in ['ALARM_DRAGGING', 'ALARM_NO_GPS']

        if self._settings['Enabled'] == 0:
            return
        
        relay_function = self._alarm_monitor.get_value("com.victronenergy.settings", '/Settings/Relay/'+ str(self._settings['RelayNumber']) +'/Function')
        if relay_function != 2: # only works if relay is in mode "Manual"
            return

        if self._settings["Inverted"]:
            alarm_state = not alarm_state

        relay_state = 1 if alarm_state else 0

        # toggle relay state
        self._alarm_monitor.set_value("com.victronenergy.system", '/Relay/'+ str(self._settings['RelayNumber']) +'/State', relay_state)


    def update_state(self, current_state:AnchorAlarmState):
        """Called by controller every second with updated state"""
        pass

    def _on_setting_changed(self, path, old_value, new_value):
        # just recompute all names
        pass
        

    def _on_monitor_changed(self, dbusServiceName, dbusPath, dict, changes, deviceInstance):
        # controller is not set yet
        if self.controller is None:
            return
        
    


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
    from utils import handle_stdin

   
    bus = dbus.SessionBus() if 'DBUS_SESSION_BUS_ADDRESS' in os.environ else dbus.SystemBus()
    dbus_connector = DBusRelayConnector(lambda: GLib, lambda settings, cb: SettingsDevice(bus, settings, cb))

    controller = MagicMock()
    controller.trigger_anchor_down  = MagicMock(side_effect=lambda: logger.info("Trigger anchor down"))
    controller.trigger_anchor_up    = MagicMock(side_effect=lambda: logger.info("Trigger anchor up"))
    controller.trigger_chain_out    = MagicMock(side_effect=lambda: logger.info("Trigger chain out"))
    controller.trigger_mute_alarm   = MagicMock(side_effect=lambda: logger.info("Trigger mute alarm"))
    controller.trigger_mooring_mode = MagicMock(side_effect=lambda: logger.info("Trigger mute alarm"))
    dbus_connector.set_controller(controller)

    print("DBUS Relay connector test program. Type : \ndisabled\ndrop\nin_radius\ndragging\nmuted\nexit to exit\nRelay state will be displayed on screen and can also be seen with dbus-spy on platform/Relay/1/State")

    def handle_command(command, text):

        # AnchorAlarmState = namedtuple('AnchorAlarmState', ['state', 'message','short_message', 'level', 'muted', 'params'])
        state_drop_point_set = AnchorAlarmState('DROP_POINT_SET', 'Drop point set, please do blablala',"short message", 'info', False, {'drop_point': GPSPosition(10, 11)})
        state_in_radius = AnchorAlarmState('IN_RADIUS', 'boat in radius',"short message", 'info', False, {'drop_point': GPSPosition(10, 11), 'radius': 12})
        state_dragging = AnchorAlarmState('ALARM_DRAGGING', 'Anchor dragging !',"short message", 'emergency', False, {'drop_point': GPSPosition(10, 11), 'radius': 12})
        state_dragging_muted = AnchorAlarmState('ALARM_DRAGGING_MUTED', 'Anchor dragging ! (muted)',"short message", 'emergency', True, {'drop_point': GPSPosition(10, 11), 'radius': 12})
        state_disabled = AnchorAlarmState('DISABLED', 'Anchor alarm disabled', "short message",'info', False, {})

        if command == "disabled":
            dbus_connector.on_state_changed(state_disabled)
        elif command == "drop":
            dbus_connector.on_state_changed(state_drop_point_set)
        elif command == "in_radius":
            dbus_connector.on_state_changed(state_in_radius)
        elif command == "dragging":
            dbus_connector.on_state_changed(state_dragging)
        elif command == "muted":
            dbus_connector.on_state_changed(state_dragging_muted)
        else:
            print("Unknown command "+ command)


    handle_stdin(handle_command)