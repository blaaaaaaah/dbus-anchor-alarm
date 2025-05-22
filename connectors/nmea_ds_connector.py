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


        self._init_settings()

        self._bridge = nmea_bridge
        self._bridge.add_pgn_handler(127502, self._on_ds_change)

        logger.debug("adding timer")
        self._add_timer('advertise_timer', self._advertise_ds, 2000, False)
    
    
    def _init_settings(self):
        # create the setting that are needed
        settingsList = {
            # Digital Switching Bank ID the anchor alarm must be registered with. Only change it if conflicts with existing configuration
            "DSBank":               ["/Settings/AnchorAlarm/NMEA/DigitalSwitching/DSBank", 221, 0, 252],

            # Digital Switching Channel to use to receive command to set the anchor drop point. Only change it if conflicts with existing configuration
            "AnchorDownChannel":  ["/Settings/AnchorAlarm/NMEA/DigitalSwitching/AnchorDownChannel", 1, 1, 28],

            # Digital Switching Channel to use to receive command to set the radius and enable anchor alarm. Only change it if conflicts with existing configuration
            "ChainOutChannel":       ["/Settings/AnchorAlarm/NMEA/DigitalSwitching/ChainOutChannel", 2, 1, 28],

            # Digital Switching Channel to use to receive command to set disable anchor alarm. Only change it if conflicts with existing configuration
            "AnchorUpChannel":          ["/Settings/AnchorAlarm/NMEA/DigitalSwitching/AnchorUpChannel", 3, 1, 28],

            # Digital Switching Channel to use to receive command to mute anchor alarm. Only change it if conflicts with existing configuration
            "MuteAlarmChannel":          ["/Settings/AnchorAlarm/NMEA/DigitalSwitching/MuteAlarmChannel", 4, 1, 28],
        }

        # not interested in settings changes
        self._settings = self._settings_provider(settingsList, None)        



    def _on_ds_change(self, nmea_message):
        """Called when a new NMEA message arrives."""
        logger.debug(f"Received NMEA message: {nmea_message}")

        if self.controller is None:
            return  # no controller yet, should never happend

        if "fields" in nmea_message and "Instance" in nmea_message["fields"] \
            and nmea_message['fields']["Instance"] == self._settings['DSBank']:
            # {"canId":233967171,"prio":3,"src":67,"dst":255,"pgn":127502,"timestamp":"2025-05-08T04:42:33.723Z","input":["2025-05-08T04:42:33.723Z,3,127502,67,255,8,00,ff,ff,3f,ff,ff,ff,ff"],"fields":{"Instance":0,"Switch12":"Off"},"description":"Switch Bank Control"}

            anchor_down_switch = "Switch"+ str(self._settings['AnchorDownChannel'])
            if anchor_down_switch in nmea_message['fields'] and nmea_message['fields'][anchor_down_switch] == 'On':
                logger.info("Received On command for channel "+ anchor_down_switch+ ", calling trigger_mute_alarm")
                self.controller.trigger_anchor_down()

            chain_out_switch = "Switch"+ str(self._settings['ChainOutChannel'])
            if chain_out_switch in nmea_message['fields'] and nmea_message['fields'][chain_out_switch] == 'On':
                logger.info("Received On command for channel "+ chain_out_switch+ ", calling trigger_chain_out")
                self.controller.trigger_chain_out()

            anchor_up_switch = "Switch"+ str(self._settings['AnchorUpChannel'])
            if anchor_up_switch in nmea_message['fields'] and nmea_message['fields'][anchor_up_switch] == 'On':
                logger.info("Received On command for channel "+ anchor_up_switch+ ", calling trigger_anchor_up")
                self.controller.trigger_anchor_up()

            mute_alarm_switch = "Switch"+ str(self._settings['MuteAlarmChannel'])
            if mute_alarm_switch in nmea_message['fields'] and nmea_message['fields'][mute_alarm_switch] == 'On':
                logger.info("Received On command for channel "+ mute_alarm_switch+ ", calling trigger_mute_alarm")
                self.controller.trigger_mute_alarm()
        
    # called when a state changes
    def on_state_changed(self, current_state:AnchorAlarmState):
        """Called by controller when state changed"""
        logger.info("On state changed "+ current_state.state)

        channel = None
        if current_state.state == "DROP_POINT_SET":
            channel = self._settings['AnchorDownChannel']
        elif current_state.state == "IN_RADIUS":
            channel = self._settings['ChainOutChannel']
        elif current_state.state in ["ALARM_DRAGGING_MUTED", 'ALARM_NO_GPS_MUTED']:
            channel = self._settings['MuteAlarmChannel']
        elif current_state.state == "DISABLED":
            channel = self._settings['AnchorUpChannel']

        if channel:
            # feedback might last less than a second is this calls arrives close to the advertise_timer
            # feedback will also be shown even if not triggered by DS switching. 
            self._advertise_ds(channel) 


    def _advertise_ds(self, on_channel=None):
        nmea_message = {
            'pgn': 127501, 
            'fields': {
                'Instance': self._settings['DSBank'], 
                'Indicator'+ str(self._settings['AnchorDownChannel']): 'Off', 
                'Indicator'+ str(self._settings['ChainOutChannel']): 'Off', 
                'Indicator'+ str(self._settings['AnchorUpChannel']): 'Off', 
                'Indicator'+ str(self._settings['MuteAlarmChannel']): 'Off', 
            }, 
            'description': 'Binary Switch Bank Status'
        }

        if on_channel:
            nmea_message['fields']['Indicator'+ str(on_channel)] = 'On'

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
    state_in_radius2 = AnchorAlarmState('IN_RADIUS', 'boat in radius 2',"short message", 'info', False, {'drop_point': GPSPosition(10, 11), 'radius': 12})
    state_in_radius3 = AnchorAlarmState('IN_RADIUS', 'boat in radius 3',"short message", 'info', False, {'drop_point': GPSPosition(10, 11), 'radius': 12})
    state_dragging = AnchorAlarmState('ALARM_DRAGGING', 'Anchor dragging !',"short message", 'emergency', False, {'drop_point': GPSPosition(10, 11), 'radius': 12})
    state_dragging_muted = AnchorAlarmState('ALARM_DRAGGING_MUTED', 'Anchor dragging ! (muted)',"short message", 'emergency', True, {'drop_point': GPSPosition(10, 11), 'radius': 12})
    state_disabled = AnchorAlarmState('DISABLED', 'Anchor alarm disabled',"short message", 'info', False, {})

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

    print("NMEA DS connector test program.\nType:\n alarm to simulate alarm state\nexit to exit\nWill display trigger_xxx when appropriate DS command is sent")

    def handle_command(command, text):

        if command == "alarm":
            nmea_ds_connector.on_state_changed(state_dragging)
        else:
            print("Unknown command "+ command)


    handle_stdin(handle_command)
