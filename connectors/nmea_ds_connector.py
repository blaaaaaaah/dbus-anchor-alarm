from collections import namedtuple
import sys
import os

sys.path.insert(1, os.path.join(sys.path[0], '..'))

from abstract_connector import AbstractConnector
from anchor_alarm_model import AnchorAlarmState

import logging
logger = logging.getLogger(__name__)

class NMEADSConnector(AbstractConnector):
    def __init__(self, timer_provider, settings_provider, nmea_bridge):
        super().__init__(timer_provider, settings_provider)

        self._timer_ids = {
            'advertise_timer': None
        }

        self._switches_status = {}

        self._init_settings()

        self._bridge = nmea_bridge
        self._bridge.add_pgn_handler(127502, self._on_ds_change)


    
    
    def _init_settings(self):
        # create the setting that are needed
        # store that to iterate over it in _on_settings_updated
        self._settingsList = {
            # Digital Switching Bank ID the anchor alarm must be registered with. Only change it if conflicts with existing configuration
            "DSBank":                           ["/Settings/AnchorAlarm/NMEA/DigitalSwitching/DSBank", 221, 0, 252],

            # How often, in seconds, the switches should be advertised. Set to 0 to disabled Digital Switching advertising. Only change it if conflicts with existing configuration
            "AdvertiseInterval":                ["/Settings/AnchorAlarm/NMEA/DigitalSwitching/AdvertiseInterval", 5, 0, 60],


            #
            # Digital Switching Channels : will take user inputs
            #
            # On Garmin chart plotter, it will give the name "Switch <bank id>*28+<channel>" by default
            #

            # Digital Switching Channel to use to receive command to set the anchor drop point. Set 0 to disable. Only change it if conflicts with existing configuration
            "AnchorDownChannel":                ["/Settings/AnchorAlarm/NMEA/DigitalSwitching/AnchorDownChannel", 1, 0, 28],

            # Digital Switching Channel to use to receive command to set the radius and enable anchor alarm. Set 0 to disable. Only change it if conflicts with existing configuration
            "ChainOutChannel":                  ["/Settings/AnchorAlarm/NMEA/DigitalSwitching/ChainOutChannel", 2, 0, 28],

            # Digital Switching Channel to use to receive command to set disable anchor alarm. Set 0 to disable. Only change it if conflicts with existing configuration
            "AnchorUpChannel":                  ["/Settings/AnchorAlarm/NMEA/DigitalSwitching/AnchorUpChannel", 3, 0, 28],

            # Digital Switching Channel to use to receive command to mute anchor alarm. Set 0 to disable. Only change it if conflicts with existing configuration
            "MuteAlarmChannel":                 ["/Settings/AnchorAlarm/NMEA/DigitalSwitching/MuteAlarmChannel", 4, 0, 28],


            #
            # Feedback channels. They won't listen on inputs but will show current anchor alamr state
            #

            # Feedback Channel to advertise the Disabled state. Set 0 to disable. Only change it if conflicts with existing configuration
            "DisabledFeedbackChannel":          ["/Settings/AnchorAlarm/NMEA/DigitalSwitching/DisabledFeedbackChannel", 11, 0, 28],

            # Feedback Channel to advertise the DropPointSet state. Set 0 to disable. Only change it if conflicts with existing configuration
            "DropPointSetFeedbackChannel":      ["/Settings/AnchorAlarm/NMEA/DigitalSwitching/DropPointSetFeedbackChannel", 12, 0, 28],

            # Feedback Channel to advertise the InRadius state. Set 0 to disable. Only change it if conflicts with existing configuration
            "InRadiusFeedbackChannel":          ["/Settings/AnchorAlarm/NMEA/DigitalSwitching/InRadiusFeedbackChannel", 13, 0, 28],

            # Feedback Channel to advertise the AlarmDragging state. Set 0 to disable. Only change it if conflicts with existing configuration
            "AlarmDraggingFeedbackChannel":     ["/Settings/AnchorAlarm/NMEA/DigitalSwitching/AlarmDraggingFeedbackChannel", 14, 0, 28],

            # Feedback Channel to advertise the AlarmDraggingMuted state. Set 0 to disable. Only change it if conflicts with existing configuration
            "AlarmDraggingMutedFeedbackChannel":["/Settings/AnchorAlarm/NMEA/DigitalSwitching/AlarmDraggingMutedFeedbackChannel", 15, 0, 28],

            # Feedback Channel to advertise the AlarmNoGPS state. Set 0 to disable. Only change it if conflicts with existing configuration
            "AlarmNoGPSFeedbackChannel":        ["/Settings/AnchorAlarm/NMEA/DigitalSwitching/AlarmNoGPSFeedbackChannel", 16, 0, 28],

            # Feedback Channel to advertise the AlarmNoGPSMuted state. Set 0 to disable. Only change it if conflicts with existing configuration
            "AlarmNoGPSMutedFeedbackChannel":   ["/Settings/AnchorAlarm/NMEA/DigitalSwitching/AlarmNoGPSMutedFeedbackChannel", 17, 0, 28],
        }


        self._settings = self._settings_provider(self._settingsList, self._on_setting_changed)
        self._on_setting_changed(None, None, None)        


    def _on_setting_changed(self, key, old_value, new_value):
        self._switches_status = {}  # just reset it when settings are changed
        for i in self._timer_ids:   # clear timers in case there's something running
            self._remove_timer(i)

        for name in self._settingsList:
            if "Channel" not in name:
                continue

            if self._settings[name] != 0:
                self._switches_status[self._settings[name]] = False

        self._remove_timer('advertise_timer')
        logger.debug("adding timer")
        if self._settings['AdvertiseInterval'] != 0:
            self._add_timer('advertise_timer', self._advertise_ds, self._settings['AdvertiseInterval']*1000, False)


    def _on_ds_change(self, nmea_message):
        """Called when a new Digital Switching NMEA message arrives."""
        logger.debug(f"Received 127502 NMEA message: {nmea_message}")

        if self.controller is None:
            return  # no controller yet, should never happend

        if "fields" in nmea_message and "Instance" in nmea_message["fields"] \
            and nmea_message['fields']["Instance"] == self._settings['DSBank']:
            # {"canId":233967171,"prio":3,"src":67,"dst":255,"pgn":127502,"timestamp":"2025-05-08T04:42:33.723Z","input":["2025-05-08T04:42:33.723Z,3,127502,67,255,8,00,ff,ff,3f,ff,ff,ff,ff"],"fields":{"Instance":0,"Switch12":"Off"},"description":"Switch Bank Control"}

            anchor_down_switch = "Switch"+ str(self._settings['AnchorDownChannel'])
            if anchor_down_switch in nmea_message['fields'] and nmea_message['fields'][anchor_down_switch] == 'On':
                logger.info("Received On command for channel "+ anchor_down_switch+ ", calling trigger_mute_alarm")
                self._update_switch_status(self._settings['AnchorDownChannel'], True)
                self.controller.trigger_anchor_down()

            chain_out_switch = "Switch"+ str(self._settings['ChainOutChannel'])
            if chain_out_switch in nmea_message['fields'] and nmea_message['fields'][chain_out_switch] == 'On':
                logger.info("Received On command for channel "+ chain_out_switch+ ", calling trigger_chain_out")
                self._update_switch_status(self._settings['ChainOutChannel'], True)
                self.controller.trigger_chain_out()

            anchor_up_switch = "Switch"+ str(self._settings['AnchorUpChannel'])
            if anchor_up_switch in nmea_message['fields'] and nmea_message['fields'][anchor_up_switch] == 'On':
                logger.info("Received On command for channel "+ anchor_up_switch+ ", calling trigger_anchor_up")
                self._update_switch_status(self._settings['AnchorUpChannel'], True)
                self.controller.trigger_anchor_up()

            mute_alarm_switch = "Switch"+ str(self._settings['MuteAlarmChannel'])
            if mute_alarm_switch in nmea_message['fields'] and nmea_message['fields'][mute_alarm_switch] == 'On':
                logger.info("Received On command for channel "+ mute_alarm_switch+ ", calling trigger_mute_alarm")
                self._update_switch_status(self._settings['MuteAlarmChannel'], True)
                self.controller.trigger_mute_alarm()

            # advertise the switch change
            self._advertise_ds()

        

    def _update_switch_status(self, channel, is_on, reset_delay=1000):
        if channel not in self._switches_status:
            return # should never happen
        
        if channel == 0:
            return

        self._switches_status[channel] = is_on
        if reset_delay is not None:
            def reset_switch(channel):
                self._update_switch_status(channel, False, None)
                self._advertise_ds()
            self._add_timer('update_switch_'+ str(channel)+ '_status', lambda: reset_switch(channel), reset_delay)


    # called when a state changes
    def on_state_changed(self, current_state:AnchorAlarmState):
        """Called by controller when state changed"""
        logger.info("On state changed "+ current_state.state)

        state_to_channel_mapping = {
            'DISABLED':             self._settings['DisabledFeedbackChannel'],
            'DROP_POINT_SET':       self._settings['DropPointSetFeedbackChannel'],
            'IN_RADIUS':            self._settings['InRadiusFeedbackChannel'],
            'ALARM_DRAGGING':       self._settings['AlarmDraggingFeedbackChannel'],
            'ALARM_DRAGGING_MUTED': self._settings['AlarmDraggingMutedFeedbackChannel'],
            'ALARM_NO_GPS':         self._settings['AlarmNoGPSFeedbackChannel'],
            'ALARM_NO_GPS_MUTED':   self._settings['AlarmNoGPSMutedFeedbackChannel'],
        }

        for state in state_to_channel_mapping:
            channel = state_to_channel_mapping[state]
            self._update_switch_status(channel, state == current_state.state, None)

        # advertise the state change
        self._advertise_ds()


    def _advertise_ds(self):
        if self._settings['AdvertiseInterval'] == 0:
            # do not advertise at all, stop timer
            return False
        
        if len(self._switches_status) == 0:
            # no switches to advertise, stop timer
            return False
        
        nmea_message = {
            'pgn': 127501, 
            'fields': {
                'Instance': self._settings['DSBank'], 
            }, 
            'description': 'Binary Switch Bank Status'
        }

        

        for channel in self._switches_status:
            nmea_message['fields']['Indicator'+ str(channel)] = 'On' if self._switches_status[channel] else 'Off'

        logger.debug("advertising switch bank", nmea_message)
        self._bridge.send_nmea(nmea_message)

        return True # we want to repeat that


    # called every second to update state
    def update_state(self, current_state:AnchorAlarmState):
        """Called by controller every second with updated state"""
        # nothing to do
        pass


    def _timer_provider(self):
        from gi.repository import GLib
        return GLib








if __name__ == '__main__':

    from nmea_bridge import NMEABridge
    from utils import handle_stdin
    from gi.repository import GLib
    import dbus
    sys.path.insert(1, os.path.join(os.path.dirname(__file__), '../ext/velib_python'))

    from settingsdevice import SettingsDevice
    from unittest.mock import MagicMock
    from collections import namedtuple
    from dbus.mainloop.glib import DBusGMainLoop


    logging.basicConfig(level=logging.DEBUG)

    # TODO XXX : move that import somewhere
    GPSPosition = namedtuple('GPSPosition', ['latitude', 'longitude'])

    bridge = NMEABridge('../nmea_bridge.js')
    DBusGMainLoop(set_as_default=True)

    bus = dbus.SessionBus() if 'DBUS_SESSION_BUS_ADDRESS' in os.environ else dbus.SystemBus()
    nmea_ds_connector = NMEADSConnector(lambda: GLib, lambda settings, cb: SettingsDevice(bus, settings, cb), bridge)


    state_drop_point_set = AnchorAlarmState('DROP_POINT_SET', 'Drop point set, please do blablala',"short message", 'info', False, {'drop_point': GPSPosition(10, 11)})
    state_in_radius = AnchorAlarmState('IN_RADIUS', 'boat in radius',"short message", 'info', False, {'drop_point': GPSPosition(10, 11), 'radius': 12})
    state_dragging = AnchorAlarmState('ALARM_DRAGGING', 'Anchor dragging !',"short message", 'emergency', False, {'drop_point': GPSPosition(10, 11), 'radius': 12})
    state_dragging_muted = AnchorAlarmState('ALARM_DRAGGING_MUTED', 'Anchor dragging ! (muted)',"short message", 'emergency', True, {'drop_point': GPSPosition(10, 11), 'radius': 12})
    state_disabled = AnchorAlarmState('DISABLED', 'Anchor alarm disabled',"short message", 'info', False, {})
    state_no_gps = AnchorAlarmState('ALARM_NO_GPS', 'alarm no gps',"short message", 'emergency', False, {})
    state_no_gps_muted = AnchorAlarmState('ALARM_NO_GPS_MUTED', 'alarm no gps',"short message", 'emergency', True, {})

    def _anchor_down():
        print("trigger anchor down")
        nmea_ds_connector.on_state_changed(state_drop_point_set)

    def _chain_out():
        print("trigger chain out")
        nmea_ds_connector.on_state_changed(state_in_radius)

    def _mute_alarm():
        print("trigger mute alarm")
        nmea_ds_connector.on_state_changed(state_dragging_muted)

    def _anchor_up():
        print("trigger anchor up")
        nmea_ds_connector.on_state_changed(state_disabled)

    controller = MagicMock()
    controller.trigger_anchor_down   = MagicMock(side_effect=_anchor_down)
    controller.trigger_anchor_up    = MagicMock(side_effect=_anchor_up)
    controller.trigger_mute_alarm   = MagicMock(side_effect=_mute_alarm)
    controller.trigger_chain_out    = MagicMock(side_effect=_chain_out)
    nmea_ds_connector.set_controller(controller)

    print("NMEA DS connector test program.\nType:\ndisabled to simulate DISABLED state\ndrop to simulate DROP_POINT_SET\nradius to simulate IN_RADIUS\ndragging to simulate ALARM_DRAGGING\ndragging_muted to simulate ALARM_DRAGING_MUTED\nnogps to simulate ALARM_NO_GPS\nnogps_muted to simulate ALARM_NO_GPS_MUTED\nexit to exit\nWill display trigger_xxx when appropriate DS command is sent and change state accordingly")

    def handle_command(command, text):
        if command == "disabled":
            nmea_ds_connector.on_state_changed(state_disabled)
        elif command == "drop":
            nmea_ds_connector.on_state_changed(state_drop_point_set)
        elif command == "radius":
            nmea_ds_connector.on_state_changed(state_in_radius)
        elif command == "dragging":
            nmea_ds_connector.on_state_changed(state_dragging)
        elif command == "dragging_muted":
            nmea_ds_connector.on_state_changed(state_dragging_muted)
        elif command == "nogps":
            nmea_ds_connector.on_state_changed(state_no_gps)
        elif command == "nogps_muted":
            nmea_ds_connector.on_state_changed(state_no_gps_muted)
        else:
            print("Unknown command "+ command)


    handle_stdin(handle_command)
