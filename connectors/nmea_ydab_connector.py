from collections import namedtuple
import sys
import os
sys.path.insert(1, os.path.join(sys.path[0], '..'))

from abstract_connector import AbstractConnector
from anchor_alarm_model import AnchorAlarmState


class NMEAYDABConnector(AbstractConnector):
    def __init__(self, timer_provider, settings_provider, nmea_bridge):
        super().__init__(timer_provider, settings_provider)

        self._timer_ids = {
            'config_command_timeout': None
        }

        self._init_settings()

        self._bridge = nmea_bridge
        self._bridge.add_pgn_handler(126998, self._on_config_command_acknowledged)
        self._bridge.add_pgn_handler(127502, self._on_ds_change)

    
    
    def _init_settings(self):
        # create the setting that are needed
        settingsList = {
            "NMEAAddress":          ["/Settings/AnchorAlarm/NMEA/YDAB/NMEAAddress", 67, 0, 254],
            "AlarmSoundID":         ["/Settings/AnchorAlarm/NMEA/YDAB/AlarmSoundID", 15, 1, 28],
            "AlarmVolume":          ["/Settings/AnchorAlarm/NMEA/YDAB/AlarmVolume", 100, 0, 100],
            "DSBank":               ["/Settings/AnchorAlarm/NMEA/YDAB/DSBank", 222, 0, 252],
            "DSDropPointSetChannel":["/Settings/AnchorAlarm/NMEA/YDAB/DSDropPointSetChannel", 10, 0, 16],
            "DSAlarmChannel":       ["/Settings/AnchorAlarm/NMEA/YDAB/DSAlarmChannel", 11, 0, 16],
            "DSAlarmMutedChannel":  ["/Settings/AnchorAlarm/NMEA/YDAB/DSAlarmMutedChannel", 12, 0, 16],
            "StartConfiguration":   ["/Settings/AnchorAlarm/NMEA/YDAB/StartConfiguration", False],
        }

        self._settings = self._settings_provider(settingsList, self._on_setting_changed)

    def _on_setting_changed(self, key, old_value, new_value):
        if key == "StartConfiguration":
            if new_value is False and self._queued_config_commands is not None and len(self._queued_config_commands) > 0:
                # we're sending commands, refuse the change
                self._settings['StartConfiguration'] = True # TODO XXX is this re-entrant ?

            if new_value is True: 
                self._send_init_config()    # TODO XXX : handle error ?





    def _on_ds_change(self, nmea_message):
        """Called when a new NMEA message arrives."""
        #self._log(f"Received NMEA message: {nmea_message}")

        if self.controller is None:
            return  # no controller yet, should never happend

        if nmea_message["src"] == self._settings['NMEAAddress'] \
            and "fields" in nmea_message and "Instance" in nmea_message["fields"] \
            and nmea_message['fields']["Instance"] == self._settings['DSBank']:
            # {"canId":233967171,"prio":3,"src":67,"dst":255,"pgn":127502,"timestamp":"2025-05-08T04:42:33.723Z","input":["2025-05-08T04:42:33.723Z,3,127502,67,255,8,00,ff,ff,3f,ff,ff,ff,ff"],"fields":{"Instance":0,"Switch12":"Off"},"description":"Switch Bank Control"}

            alarm_ds_channel = self._switch_name_for('ALARM')
            if alarm_ds_channel in nmea_message['fields'] and nmea_message['fields'][alarm_ds_channel] == 'Off':
                self.controller.trigger_mute_alarm()

            alarm_muted_ds_channel = self._switch_name_for('ALARM_MUTED')
            if alarm_muted_ds_channel in nmea_message['fields'] and nmea_message['fields'][alarm_muted_ds_channel] == 'Off':
                self.controller.trigger_chain_out()

            set_radius_ds_channel = self._switch_name_for('DROP_POINT_SET')
            if set_radius_ds_channel in nmea_message['fields'] and nmea_message['fields'][set_radius_ds_channel] == 'Off':
                self.controller.trigger_chain_out()
        


    def _log(self, msg):
        print(msg)

    # called when a state changes
    def on_state_changed(self, current_state:AnchorAlarmState):
        """Called by controller when state changed"""
        self._log("On state changed "+ current_state.state)

        if current_state.state == "DISABLED":
            # DISABLED, no led, no sound, not cancellable
            self._send_config_command("YD:LED 0")
            self._send_ds_command_for_state(None) # all off


        elif current_state.state == "DROP_POINT_SET":
            # DROP_POINT_SET, flashing led, no sound, activable
            self._send_ds_command_for_state('DROP_POINT_SET') # activate link 10

        
        elif current_state.state == "IN_RADIUS":
            # NO_ALARM, glowing led, no sound, not cancellable
            self._send_config_command("YD:LED 21")
            self._send_ds_command_for_state(None) # all off

        
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
        config_commands = [
            "YD:RESET",
            "YD:MODE DS",           # Set mode to DigitalSwitching

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
            self._settings['StartConfiguration'] = False
            self._send_config_finished_feedback()
        else:
            self._add_timer('config_command_timeout', self._on_config_command_timeout, 2000)
            next_command = self._queued_config_commands[0]  
            self._send_config_command(next_command)


    def _on_config_command_acknowledged(self, nmea_message):
        # {'canId': 435164739, 'prio': 6, 'src': 67, 'dst': 255, 'pgn': 126998, 'timestamp': '2025-05-13T20:44:33.321Z', 'input': [], 'fields': {'Installation Description #2': 'YD:LED 21 DONE', 'Manufacturer Information': 'Yacht Devices Ltd., www.yachtd.com'}, 'description': 'Configuration Information'}
        if "src" in nmea_message and nmea_message["src"] == self._settings['NMEAAddress'] \
            and 'fields' in  nmea_message and "Installation Description #2" in nmea_message['fields']:
            acknowledged_command = nmea_message['fields']["Installation Description #2"].removesuffix(" DONE")

            if self._queued_config_commands is not None and self._queued_config_commands[0] == acknowledged_command:
                self._queued_config_commands.pop(0)
                self._remove_timer('config_command_timeout')
                self._send_next_config_command()                    
            else:
                self._queued_config_commands = None
                self._settings['StartConfiguration'] = False

                # TODO XXX : yield error in whatever way

        
    def _on_config_command_timeout(self):
        # we couldn't get an ack, maybe the YDAB NMEA address is wrong ?
        self._queued_config_commands = None
        self._settings['StartConfiguration'] = False
        # TODO XXX : yield error in whatever way

    def _send_config_finished_feedback(self):
        # send sound
        self._send_config_command("YD:PLAY 6")
        self._add_timer('config_command_timeout', lambda: self._send_config_command("YD:PLAY 0"), 1000)



    def _timer_provider(self):
        from gi.repository import GLib
        return GLib







