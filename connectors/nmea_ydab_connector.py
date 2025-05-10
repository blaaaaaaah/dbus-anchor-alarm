from collections import namedtuple
import sys
import os
sys.path.insert(1, os.path.join(sys.path[0], '..'))

from abstract_connector import AbstractConnector
from anchor_alarm_model import AnchorAlarmState

YDABConfig = namedtuple('YDABConfig', ['nmea_address', 'alarm_sound_id', 'ds_bank', 'alarm_channel', 'alarm_muted_channel', 'set_radius_channel'], [67, 15, 0, 11, 12, 10])

class NMEAYDABConnector(AbstractConnector):
    def __init__(self, timer_provider, nmea_bridge, ydab_nmea_address = 67):
        super().__init__(timer_provider)


        # TODO XXX : make that configurable from settings and handle update
        self._ydab_nmea_address = ydab_nmea_address
        self._alarm_sound_id = 15
        self._ds_bank = 0
        self._ds_channels = {
            'ALARM': 10,
            'ALARM_MUTED': 11,
            'SET_RADIUS': 12,
        }

        self._timer_ids = {
            'config_command_timeout': None
        }

        self._bridge = nmea_bridge
        self._bridge.add_pgn_handler(126998, self._on_config_command_acknowledged)
        self._bridge.add_pgn_handler(127502, self._on_ds_change)

        # TODO XXX : create dbus_settings for that
        # TODO XXX : init config each time ?
        # TODO XXX : upon reset state, we could send conflicting/out of sequence messages where init config is sent and state reset
        #self._send_init_config()



    def _on_ds_change(self, nmea_message):
        """Called when a new NMEA message arrives."""
        #self._log(f"Received NMEA message: {nmea_message}")

        if nmea_message["src"] == self._ydab_nmea_address and nmea_message["fields"] is not None and nmea_message["fields"]["instance"] == self._ds_bank:
            # {"canId":233967171,"prio":3,"src":67,"dst":255,"pgn":127502,"timestamp":"2025-05-08T04:42:33.723Z","input":["2025-05-08T04:42:33.723Z,3,127502,67,255,8,00,ff,ff,3f,ff,ff,ff,ff"],"fields":{"Instance":0,"Switch12":"Off"},"description":"Switch Bank Control"}

            alarm_ds_channel = self._switch_name_for('ALARM')
            if nmea_message['fields'] and nmea_message['fields'][alarm_ds_channel] is not None and nmea_message['fields'][alarm_ds_channel] == 'Off':
                self.controller.trigger_mute_alarm()

            alarm_muted_ds_channel = self._switch_name_for('ALARM_MUTED')
            if nmea_message['fields'] and nmea_message['fields'][alarm_muted_ds_channel] is not None and nmea_message['fields'][alarm_muted_ds_channel] == 'Off':
                self.controller.trigger_chain_out()

            set_radius_ds_channel = self._switch_name_for('SET_RADIUS')
            if nmea_message['fields'] and nmea_message['fields'][set_radius_ds_channel] is not None and nmea_message['fields'][set_radius_ds_channel] == 'Off':
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
            self._send_ds_command_for_state('SET_RADIUS') # activate link 12

        
        elif current_state.state == "IN_RADIUS":
            # NO_ALARM, glowing led, no sound, not cancellable
            self._send_config_command("YD:LED 21")
            self._send_ds_command_for_state(None) # all off

        
        elif current_state.state == "ALARM_DRAGGING" or current_state.state == "ALARM_NO_GPS":
            # ALARM (no gps our outside radius), blinking led, sound, cancellable
            self._send_ds_command_for_state('ALARM') # activate link 10

        
        elif current_state.state == "ALARM_DRAGGING_MUTED" or current_state.state == "ALARM_NO__MUTED":
            # ALARM_MUTED, blinking led, no sound, cancellable
            self._send_ds_command_for_state('ALARM_MUTED') # activate link 11




    # called every second to update state
    def update_state(self, current_state:AnchorAlarmState):
        """Called by controller every second with updated state"""
        # nothing to do
        pass


    
    def _send_config_command(self, command):
        nmea_message = {
            "prio":3,
            "dst":self._ydab_nmea_address,
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
                "Instance":0,
                self._switch_name_for("SET_RADIUS"):"Off",
                self._switch_name_for("ALARM"):"Off",
                self._switch_name_for("ALARM_MUTED"):"Off",
            },
            "description":"Switch Bank Control"
        }

        if state is not None:
            nmea_message['fields'][self._switch_name_for(state)] = "On"

        self._bridge.send_nmea(nmea_message)

    def _switch_name_for(self, state):
        return "Switch"+ self._ds_channels[state]


    def _send_init_config(self):
        config_commands = [
            "YD_RESET",
            "YD:MODE DS",           # Set mode to DigitalSwitching
            # TODO XXX : is this one really needed ?
            #"YD:PGN 127501 500",    # Set transmission interval for PGN 127501 (Binary Status Report) 

            # Disable button press channel activation
            "YD:CHANNEL 0",

            # Anchor Alarm ON, Rapid blink and sound
            "YD:LINK "+ self._ds_channels['ALARM'] +" SOUND "+ self._alarm_sound_id,
            "YD:LINK "+ self._ds_channels['ALARM'] +" LED 10",

            # Anchor Alarm MUTED, Rapid blink and no sound
            "YD:LINK "+ self._ds_channels['ALARM_MUTED'] +" SOUND 0",
            "YD:LINK "+ self._ds_channels['ALARM_MUTED'] +" LED 10",

            # Anchor Alarm SET_RADIUS, flashing led and no sound
            "YD:LINK "+ self._ds_channels['SET_RADIUS'] +" SOUND 0",
            "YD:LINK "+ self._ds_channels['SET_RADIUS'] +" LED 22",
        ]

        self._queued_config_commands = config_commands
        

    def _send_next_config_command(self):
        if self._queued_config_commands is None:
            return
        
        self._add_timer('config_command_timeout', self._on_config_command_timeout, 1000)

        next_command = self._queued_config_commands[0]  
        self._send_config_command(next_command)


    def _on_config_command_acknowledged(self, nmea_message):
        if nmea_message["src"] == self._ydab_nmea_address and nmea_message['fields'] is not None and nmea_message['fields']["Installation Description #2"] is not None:
            acknowledged_command = nmea_message["Installation Description #2"].removesuffix(" DONE")
            current_command = self._queued_config_commands[0]

            if current_command == acknowledged_command:
                self._queued_config_commands.pop(0)
                self._remove_timer('config_command_timeout')
                self._send_next_config_command()                    
            else:
                self._queued_config_commands = None
                # TODO XXX : yield error in whatever way

        
    def _on_config_command_timeout(self):
        # we couldn't get an ack, maybe the YDAB NMEA address is wrong ?
        self._queued_config_commands = None
        # TODO XXX : yield error in whatever way





    def _timer_provider(self):
        from gi.repository import GLib
        return GLib







