from collections import namedtuple
import sys
import os
sys.path.insert(1, os.path.join(sys.path[0], '..'))

from abstract_connector import AbstractConnector
from anchor_alarm_model import AnchorAlarmState

import logging
logger = logging.getLogger(__name__)

class NMEAYDABConnector(AbstractConnector):
    def __init__(self, timer_provider, settings_provider, nmea_bridge):
        super().__init__(timer_provider, settings_provider)

        self._timer_ids = {
            'config_command_timeout': None
        }

        self._queued_config_commands = None

        self._init_settings()

        self._bridge = nmea_bridge
        self._bridge.add_pgn_handler(126998, self._on_config_command_acknowledged)
        self._bridge.add_pgn_handler(127502, self._on_ds_change)

    
    
    def _init_settings(self):
        # create the setting that are needed
        settingsList = {
            # NMEA Address of the YDAB-01 device. 
            # You can find it by going on the Cerbo in Settings/Services/VE.Can port/Devices/YDAB-01/Network Address
            "NMEAAddress":          ["/Settings/AnchorAlarm/NMEA/YDAB/NMEAAddress", 67, 0, 254],

            # Sound ID to be played when the alarm is activated
            "AlarmSoundID":         ["/Settings/AnchorAlarm/NMEA/YDAB/AlarmSoundID", 15, 1, 28],

            # Volume (0-100) the sound must be played at
            "AlarmVolume":          ["/Settings/AnchorAlarm/NMEA/YDAB/AlarmVolume", 100, 0, 100],

            # Digital Switching Bank ID the YDAB-1 must be registered with. Only change it if conflicts with existing configuration
            # Digital Switching is used to communicate with the physical button of the YDAB-01
            "DSBank":               ["/Settings/AnchorAlarm/NMEA/YDAB/DSBank", 222, 0, 252],

            # Digital Switching Channel to use to get feedback from the button to set the radius. Only change it if conflicts with existing configuration
            "DSDropPointSetChannel":["/Settings/AnchorAlarm/NMEA/YDAB/DSDropPointSetChannel", 10, 0, 16],

            # Digital Switching Channel to use to get feedback from the button when the alarm is activated. Only change it if conflicts with existing configuration
            "DSAlarmChannel":       ["/Settings/AnchorAlarm/NMEA/YDAB/DSAlarmChannel", 11, 0, 16],

            # Digital Switching Channel to use to get feedback from the button when the alarm is muted. Only change it if conflicts with existing configuration
            "DSAlarmMutedChannel":  ["/Settings/AnchorAlarm/NMEA/YDAB/DSAlarmMutedChannel", 12, 0, 16],

            # Set to 1 to initiate the configuration of the YDAB-01. NMEAddress must be set. 
            # Will go back to 0 when done (success AND error). Will play a chime sound upon success. 
            "StartConfiguration":   ["/Settings/AnchorAlarm/NMEA/YDAB/StartConfiguration", 0, 0, 1],
        }

        self._settings = self._settings_provider(settingsList, self._on_setting_changed)

    def _on_setting_changed(self, key, old_value, new_value):
        if key == "StartConfiguration":
            if new_value == 0 and self._queued_config_commands is not None and len(self._queued_config_commands) > 0:
                # we're sending commands, refuse the change
                self._settings['StartConfiguration'] = 1

            if new_value == 1: 
                self._send_init_config()





    def _on_ds_change(self, nmea_message):
        """Called when a new NMEA message arrives."""
        logger.debug(f"Received NMEA message: {nmea_message}")

        if self.controller is None:
            return  # no controller yet, should never happend

        if nmea_message["src"] == self._settings['NMEAAddress'] \
            and "fields" in nmea_message and "Instance" in nmea_message["fields"] \
            and nmea_message['fields']["Instance"] == self._settings['DSBank']:
            # {"canId":233967171,"prio":3,"src":67,"dst":255,"pgn":127502,"timestamp":"2025-05-08T04:42:33.723Z","input":["2025-05-08T04:42:33.723Z,3,127502,67,255,8,00,ff,ff,3f,ff,ff,ff,ff"],"fields":{"Instance":0,"Switch12":"Off"},"description":"Switch Bank Control"}

            alarm_ds_channel = self._switch_name_for('ALARM')
            if alarm_ds_channel in nmea_message['fields'] and nmea_message['fields'][alarm_ds_channel] == 'Off':
                logger.info("Received Off command for channel "+ alarm_ds_channel+ ", calling trigger_mute_alarm")
                self.controller.trigger_mute_alarm()

            alarm_muted_ds_channel = self._switch_name_for('ALARM_MUTED')
            if alarm_muted_ds_channel in nmea_message['fields'] and nmea_message['fields'][alarm_muted_ds_channel] == 'Off':
                logger.info("Received Off command for channel "+ alarm_muted_ds_channel+ ", calling trigger_chain_out")
                self.controller.trigger_chain_out()

            set_radius_ds_channel = self._switch_name_for('DROP_POINT_SET')
            if set_radius_ds_channel in nmea_message['fields'] and nmea_message['fields'][set_radius_ds_channel] == 'Off':
                logger.info("Received Off command for channel "+ set_radius_ds_channel+ ", calling trigger_chain_out")
                self.controller.trigger_chain_out()
        
    # called when a state changes
    def on_state_changed(self, current_state:AnchorAlarmState):
        """Called by controller when state changed"""
        logger.info("On state changed "+ current_state.state)

        if self._settings['NMEAAddress'] == 0:
            return

        if current_state.state == "DISABLED":
            # DISABLED, no led, no sound, not cancellable
            self._send_ds_command_for_state(None) # all off
            self._send_config_command("YD:LED 0")


        elif current_state.state == "DROP_POINT_SET":
            # DROP_POINT_SET, flashing led, no sound, activable
            self._send_ds_command_for_state('DROP_POINT_SET') # activate link 10

        
        elif current_state.state == "IN_RADIUS":
            # NO_ALARM, glowing led, no sound, not cancellable
            self._send_ds_command_for_state(None) # all off
            self._send_config_command("YD:LED 21")

        
        elif current_state.state == "ALARM_DRAGGING" or current_state.state == "ALARM_NO_GPS":
            # ALARM (no gps our outside radius), blinking led, sound, cancellable
            self._send_ds_command_for_state('ALARM') # activate link 11

        
        elif current_state.state == "ALARM_DRAGGING_MUTED" or current_state.state == "ALARM_NO__MUTED":
            # ALARM_MUTED, blinking led, no sound, cancellable
            self._send_ds_command_for_state('ALARM_MUTED') # activate link 12




    # called every second to update state
    def update_state(self, current_state:AnchorAlarmState):
        """Called by controller every second with updated state"""
        # nothing to do
        pass


    
    def _send_config_command(self, command):
        nmea_message = {
            "prio":3,
            "dst":self._settings['NMEAAddress'],
            "pgn":126208,
            "fields":{
                "Function Code":"Command",
                "PGN":126998,
                "Number of Parameters":1,
                "list":[{
                    "Parameter":2,
                    "Value": command}]
            },
            "description":"NMEA - Command group function"
        }

        logger.debug("Sending config command", nmea_message)
        self._bridge.send_nmea(nmea_message)


    def _send_ds_command_for_state(self, state):
        nmea_message = {
            "pgn":127502,
            "fields": {
                "Instance": self._settings['DSBank'],
                self._switch_name_for("DROP_POINT_SET"):"Off",
                self._switch_name_for("ALARM"):"Off",
                self._switch_name_for("ALARM_MUTED"):"Off",
            },
            "description":"Switch Bank Control"
        }

        if state is not None:
            nmea_message['fields'][self._switch_name_for(state)] = "On"

        logger.debug("Sending DS message", nmea_message)
        self._bridge.send_nmea(nmea_message)

    def _switch_name_for(self, state):
        mapping = {
            "DROP_POINT_SET":   "DSDropPointSetChannel",
            "ALARM":            "DSAlarmChannel",
            "ALARM_MUTED":      "DSAlarmMutedChannel",
        }
        channel = self._settings[mapping[state]]
        return "Switch"+ str(channel)


    def _send_init_config(self):
        if self._settings['NMEAAddress'] == 0:
            return
        
        config_commands = [
            "YD:RESET",
            "YD:MODE DS",           # Set mode to DigitalSwitching
            "YD:BANK "+ str(self._settings['DSBank']),

            # Disable button press channel activation
            "YD:CHANNEL 0",
            "YD:VOLUME "+ str(self._settings['AlarmVolume']),

            # Anchor Alarm DROP_POINT_SET, flashing led and no sound
            "YD:LINK "+ str(self._settings['DSDropPointSetChannel']) +" SOUND 0",
            "YD:LINK "+ str(self._settings['DSDropPointSetChannel']) +" LED 22",

            # Anchor Alarm ON, Rapid blink and sound
            "YD:LINK "+ str(self._settings['DSAlarmChannel'] )+" SOUND "+ str(self._settings['AlarmSoundID']),
            "YD:LINK "+ str(self._settings['DSAlarmChannel']) +" LED 10",

            # Anchor Alarm MUTED, Rapid blink and no sound
            "YD:LINK "+ str(self._settings['DSAlarmMutedChannel']) +" SOUND 0",
            "YD:LINK "+ str(self._settings['DSAlarmMutedChannel']) +" LED 10",
        ]

        self._queued_config_commands = config_commands
        self._send_next_config_command()
        

    def _send_next_config_command(self):
        if self._queued_config_commands is None:
            return
        
        if len(self._queued_config_commands) == 0:
            # last one, clear everything
            self._queued_config_commands = None
            self._settings['StartConfiguration'] = 0
            self._send_config_finished_feedback()
        else:
            self._add_timer('config_command_timeout', self._on_config_command_timeout, 10000)
            next_command = self._queued_config_commands[0]  
            self._send_config_command(next_command)


    def _on_config_command_acknowledged(self, nmea_message):
        # {'canId': 435164739, 'prio': 6, 'src': 67, 'dst': 255, 'pgn': 126998, 'timestamp': '2025-05-13T20:44:33.321Z', 'input': [], 'fields': {'Installation Description #2': 'YD:LED 21 DONE', 'Manufacturer Information': 'Yacht Devices Ltd., www.yachtd.com'}, 'description': 'Configuration Information'}
        if "src" in nmea_message and nmea_message["src"] != self._settings['NMEAAddress']:
            return # not YDAB talking to us
        
        if "fields" not in nmea_message:
            return # no fields, should not happen
        

        if self._queued_config_commands is None:
            return  # nothing to do

        if len(self._queued_config_commands) == 0:
            logger.error("should not happen ?")
            return
        
        expected_command = self._queued_config_commands[0]

        # YD:RESET will sometimes trigger a message with no "Installation Description #2" field or with "\u0000\u0000\u0000\u0000\u0000\u0000\u0000\u0000 DONE" as content
        # {"canId":435164739,"prio":6,"src":67,"dst":255,"pgn":126998,"timestamp":"2025-05-15T18:55:09.398Z","input":[],"fields":{"Installation Description #2":"YD:LED 0 DONE","Manufacturer Information":"Yacht Devices Ltd., www.yachtd.com"},"description":"Configuration Information"}
        # {"canId":435164739,"prio":6,"src":67,"dst":255,"pgn":126998,"timestamp":"2025-05-15T19:32:42.124Z","input":[],"fields":{"Manufacturer Information":"Yacht Devices Ltd., www.yachtd.com"},"description":"Configuration Information"}}

        if "Installation Description #2" not in nmea_message['fields'] or \
            nmea_message['fields']["Installation Description #2"] == "\u0000\u0000\u0000\u0000\u0000\u0000\u0000\u0000 DONE":
            nmea_message['fields']["Installation Description #2"] = "YD:RESET DONE"
        
        acknowledged_command = nmea_message['fields']["Installation Description #2"][:-len(" DONE")]

        if expected_command == acknowledged_command:
            self._queued_config_commands.pop(0)
            self._remove_timer('config_command_timeout')

            self._send_next_config_command()   
        else:
            logger.error("Unexpected acked command "+ acknowledged_command + ", expecting "+ expected_command +", stopping config process")
            self._queued_config_commands = None
            self._settings['StartConfiguration'] = 0

            # TODO XXX : yield error in whatever way

        
    def _on_config_command_timeout(self):
        # we couldn't get an ack, maybe the YDAB NMEA address is wrong ?
        logger.error("_on_config_command_timeout")
        self._queued_config_commands = None
        self._settings['StartConfiguration'] = 0
        # TODO XXX : yield error in whatever way

    def _send_config_finished_feedback(self):
        # send sound
        self._send_config_command("YD:PLAY 6")
        self._add_timer('config_command_timeout', lambda: self._send_config_command("YD:PLAY 0"), 1000)



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


    # TODO XXX : move that import somewhere
    GPSPosition = namedtuple('GPSPosition', ['latitude', 'longitude'])

    bridge = NMEABridge('../nmea_bridge.js')
    DBusGMainLoop(set_as_default=True)

    bus = dbus.SessionBus() if 'DBUS_SESSION_BUS_ADDRESS' in os.environ else dbus.SystemBus()
    nmea_alert_connector = NMEAYDABConnector(lambda: GLib, lambda settings, cb: SettingsDevice(bus, settings, cb), bridge)

    controller = MagicMock()
    controller.trigger_mute_alarm   = MagicMock(side_effect=lambda: print("trigger mute alarm"))
    controller.trigger_chain_out    = MagicMock(side_effect=lambda: print("trigger chain out"))
    nmea_alert_connector.set_controller(controller)

    print("NMEA YDAB connector test program. Type : \ndisabled\ndrop\nin_radius\nin_radius2\nin_radius3\ndragging\nmuted\nconf\nexit to exit\nWhen the button is pressed sent when dropped, trigger_chain_out should show on screen\nWhen the button is pressed sent when dragging, trigger_mute_alarm should show on screen\nconf will trigger a start configuration. You can also do this using settings in dbus-spy")

    def handle_command(command, text):

        # AnchorAlarmState = namedtuple('AnchorAlarmState', ['state', 'message', 'level', 'muted', 'params'])
        state_drop_point_set = AnchorAlarmState('DROP_POINT_SET', 'Drop point set, please do blablala',"short message", 'info', False, {'drop_point': GPSPosition(10, 11)})
        state_in_radius = AnchorAlarmState('IN_RADIUS', 'boat in radius',"short message", 'info', False, {'drop_point': GPSPosition(10, 11), 'radius': 12})
        state_in_radius2 = AnchorAlarmState('IN_RADIUS', 'boat in radius 2',"short message", 'info', False, {'drop_point': GPSPosition(10, 11), 'radius': 12})
        state_in_radius3 = AnchorAlarmState('IN_RADIUS', 'boat in radius 3',"short message", 'info', False, {'drop_point': GPSPosition(10, 11), 'radius': 12})
        state_dragging = AnchorAlarmState('ALARM_DRAGGING', 'Anchor dragging !',"short message", 'emergency', False, {'drop_point': GPSPosition(10, 11), 'radius': 12})
        state_dragging_muted = AnchorAlarmState('ALARM_DRAGGING_MUTED', 'Anchor dragging ! (muted)',"short message", 'emergency', True, {'drop_point': GPSPosition(10, 11), 'radius': 12})
        state_disabled = AnchorAlarmState('DISABLED', 'Anchor alarm disabled',"short message", 'info', False, {})

        if command == "disabled":
            nmea_alert_connector.on_state_changed(state_disabled)
        elif command == "drop":
            nmea_alert_connector.on_state_changed(state_drop_point_set)
        elif command == "in_radius":
            nmea_alert_connector.on_state_changed(state_in_radius)
        elif command == "in_radius2":
            nmea_alert_connector.update_state(state_in_radius2)
        elif command == "in_radius3":
            nmea_alert_connector.update_state(state_in_radius3)
        elif command == "dragging":
            nmea_alert_connector.on_state_changed(state_dragging)
        elif command == "muted":
            nmea_alert_connector.on_state_changed(state_dragging_muted)
        elif command == "conf":
            nmea_alert_connector._settings['StartConfiguration'] = 1
        else:
            print("Unknown command "+ command)


    handle_stdin(handle_command)
