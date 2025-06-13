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

# Credits : heavily inspired/ported code from ttlappalainen and Paul/ando274
# see : https://github.com/ttlappalainen/NMEA2000/issues/128

from collections import namedtuple
import sys
import os

sys.path.insert(1, os.path.join(sys.path[0], '..'))

from abstract_connector import AbstractConnector
from anchor_alarm_model import AnchorAlarmState

import logging
logger = logging.getLogger(__name__)

class NMEARawPGN:
    def __init__(self, pgn, destination=255):
        self.pgn = pgn
        self.destination = destination
        self.data = []
    def Add2ByteUInt(self, val): self.data.extend(val.to_bytes(2, byteorder='big'))
    def AddByte(self, val): self.data.append(val & 0xFF)

    def __repr__(self): 
        bytes = ' '.join(f'{b:02x}' for b in self.data)
        return f"NMEARawPGN {self.pgn} : {bytes})"
    def __eq__(self, b):
        return hasattr(b, 'pgn') and self.pgn == b.pgn and self.destination == b.destination and self.data == b.data



class NMEADSConnector(AbstractConnector):
    def __init__(self, timer_provider, settings_provider, nmea_bridge):
        super().__init__(timer_provider, settings_provider)

        self._timer_ids = {
            'advertise_timer': None,
            'czone_handshake_heartbeat': None,
            'czone_state_heartbear': None
        }

        self._switches_status = {}

        self._CZONE_MESSAGE = 0x9927

        self._czone_handshake_done = False

        self._init_settings()

        self._bridge = nmea_bridge

        self._bridge.add_pgn_handler(127502,    self._on_ds_change)
        self._bridge.add_pgn_handler(65280,     self._on_czone_switch_change_request)
        self._bridge.add_pgn_handler(65290,     self._handle_czone_config_request)

        # not sure why this is needed
        # TODO XXX : test without and see what happends
        self._bridge.add_pgn_handler(65284,     self._on_czone_switch_heartbeat)


        # timers are initiated in on_settings_changed


    
    
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

            # Digital Switching Channel to use to receive command to set the anchor drop point. Set 0 to disable. With CZone enabled, only use values 1-8. Only change it if conflicts with existing configuration
            "AnchorDownChannel":                ["/Settings/AnchorAlarm/NMEA/DigitalSwitching/AnchorDownChannel", 1, 0, 28],

            # Digital Switching Channel to use to receive command to set the radius and enable anchor alarm. Set 0 to disable. With CZone enabled, only use values 1-8. Only change it if conflicts with existing configuration
            "ChainOutChannel":                  ["/Settings/AnchorAlarm/NMEA/DigitalSwitching/ChainOutChannel", 2, 0, 28],

            # Digital Switching Channel to use to receive command to set disable anchor alarm. Set 0 to disable. With CZone enabled, only use values 1-8. Only change it if conflicts with existing configuration
            "AnchorUpChannel":                  ["/Settings/AnchorAlarm/NMEA/DigitalSwitching/AnchorUpChannel", 3, 0, 28],

            # Digital Switching Channel to use to receive command to mute anchor alarm. Set 0 to disable. With CZone enabled, only use values 1-8. Only change it if conflicts with existing configuration
            "MuteAlarmChannel":                 ["/Settings/AnchorAlarm/NMEA/DigitalSwitching/MuteAlarmChannel", 4, 0, 28],

            # Digital Switching Channel to use to receive command to enable mooring mode. Set 0 to disable. With CZone enabled, only use values 1-8. Only change it if conflicts with existing configuration
            "MooringModeChannel":               ["/Settings/AnchorAlarm/NMEA/DigitalSwitching/MooringModeChannel", 5, 0, 28],

            # Digital Switching Channel to use to decrease tolerance by 5m. Set 0 to disable. With CZone enabled, only use values 1-8. Only change it if conflicts with existing configuration
            "DecreaseToleranceChannel":          ["/Settings/AnchorAlarm/NMEA/DigitalSwitching/DecreaseToleranceChannel", 6, 0, 28],

             # Digital Switching Channel to use to increase tolerance by 5m. Set 0 to disable. With CZone enabled, only use values 1-8. Only change it if conflicts with existing configuration
            "IncreaseToleranceChannel":          ["/Settings/AnchorAlarm/NMEA/CDigitalSwitchingZone/IncreaseToleranceChannel", 7, 0, 28],

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
        

            #
            #   CZone support configuration.
            #

            # CZone Serial number / 00260128
            "CZoneBank1SerialNumber":                    ["/Settings/AnchorAlarm/NMEA/DigitalSwitching/CZone/Bank1SerialNumber", "00260128", 0, 252],

            "CZoneBank2SerialNumber":                    ["/Settings/AnchorAlarm/NMEA/DigitalSwitching/CZone/Bank2SerialNumber", "00260126", 0, 252],

            # CZone address
            # TODO XXX : find max value
            # TODO XXX : is this the same as DSBank ?
            "CZoneDipSwitch":                    ["/Settings/AnchorAlarm/NMEA/DigitalSwitching/CZone/DipSwitch", 0, 0, 252],  
        }


        self._settings = self._settings_provider(self._settingsList, self._on_setting_changed)
        self._on_setting_changed(None, None, None)        



    def _czone_enabled(self):
        return self._settings['CZoneBank1SerialNumber'] != "" \
                and self._settings['CZoneBank2SerialNumber'] != "" \
                and self._settings['CZoneDipSwitch'] != 0



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
            self._add_timer('advertise_timer',          self._advertise_ds, self._settings['AdvertiseInterval']*1000, False)

            if self._czone_enabled():
                self._add_timer('czone_handshake_heartbeat',  self._czone_handshake_heartbeat, 500,  False)
                self._add_timer('czone_state_heartbear',      self._czone_switch_heartbeat,    2000, False)

    


    # Sends 65283 every 500ms
    def _czone_handshake_heartbeat(self):
        if self._czone_handshake_done:
            self._send_czone_switch_change_ack(1) # sends 65283
            self._send_czone_switch_change_ack(2) # sends 65283

        return True

    # Czone heartbeat messages
    def _czone_switch_heartbeat(self):
        self._send_czone_switch_heartbeat(1)    # sends 65284
        self._send_czone_switch_heartbeat(2)    # sends 65284

        self._czone_all_switches_state_advertise(1) # sends 130817
        self._czone_all_switches_state_advertise(2) # sends 130817
        return True
    

    # not sure why this is needed
    # TODO XXX : test without and see what happends
    # listens on 65284, handshake response ?
    def _on_czone_switch_heartbeat(self, nmea_message):
        if int.from_bytes(nmea_message.data[:2], byteorder="big") != self._CZONE_MESSAGE: 
            return  # not a CZone Message, ignore
        
        if nmea_message.data[5] != self._settings['CZoneDipSwitch']:
            return  # not our DipSwitch Message, ignore
        
        self._czone_handshake_done = True
    

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

            mooring_mode_switch = "Switch"+ str(self._settings['MooringModeChannel'])
            if mooring_mode_switch in nmea_message['fields'] and nmea_message['fields'][mooring_mode_switch] == 'On':
                logger.info("Received On command for channel "+ mooring_mode_switch+ ", calling trigger_mooring_mode")
                self._update_switch_status(self._settings['MooringModeChannel'], True)
                self.controller.trigger_mooring_mode()

            decrease_tolerance_switch = "Switch"+ str(self._settings['DecreaseToleranceChannel'])
            if decrease_tolerance_switch in nmea_message['fields'] and nmea_message['fields'][decrease_tolerance_switch] == 'On':
                logger.info("Received On command for channel "+ decrease_tolerance_switch+ ", calling trigger_decrease_tolerance")
                self._update_switch_status(self._settings['DecreaseToleranceChannel'], True)
                self.controller.trigger_decrease_tolerance()

            increase_tolerance_switch = "Switch"+ str(self._settings['IncreaseToleranceChannel'])
            if increase_tolerance_switch in nmea_message['fields'] and nmea_message['fields'][increase_tolerance_switch] == 'On':
                logger.info("Received On command for channel "+ increase_tolerance_switch+ ", calling trigger_increase_tolerance")
                self._update_switch_status(self._settings['IncreaseToleranceChannel'], True)
                self.controller.trigger_increase_tolerance()

            # advertise the switch change
            self._advertise_ds()    # sends 127501

            # sending 65283 acks for both banks
            self._send_czone_switch_change_ack(1)
            self._send_czone_switch_change_ack(2)

             
        
    # updates the state of a switch
    # if is ON and has a reset delay, will automatically set it back to OFF after delay
    # this is to show user input feedback on momentary switches
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

                self._send_czone_switch_change_ack(1)
                self._send_czone_switch_change_ack(2)
                self._send_czone_switch_heartbeat(1)
                self._send_czone_switch_heartbeat(2)

            self._add_timer('update_switch_'+ str(channel)+ '_status', lambda: reset_switch(channel), reset_delay)


    # called when a state changes
    def on_state_changed(self, current_state:AnchorAlarmState):
        """Called by controller when state changed"""
        logger.info("On state changed "+ current_state.state)

        self.update_state(current_state)

        # advertise the state change
        self._advertise_ds()



    # sends 127501, switch bank status
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



    # CZONE PGN 65280 somewhat equivalent of 127502
    # each channel change will be in a separate message
    # when byte 6 is 0x40, we need to send a 65283 change ack 
    def _on_czone_switch_change_request(self, nmea_message):
        if not self._czone_enabled:
            return 

        if int.from_bytes(nmea_message.data[:2], byteorder="big") != self._CZONE_MESSAGE: 
            return  # not a CZone Message, ignore
        
        if nmea_message.data[5] != self._settings['CZoneDipSwitch']:
            return  # not our DipSwitch Message, ignore

        # nmea_message.data[2] will be the channel number, starting at 0x05 (5) to 0x0c (12)
        # nmea_message.data[6] will be the switch value 0xf1 for one, 0xf2 for off, 0x04 for toggle
        channel = nmea_message.data[2] - 5
        switch_value = nmea_message.data[6]

        if switch_value in (0xf1, 0xf2, 0x04): 
            new_state = True

            if switch_value == 0x04:
                # toggle request, lookup current value and toggle it
                logger.debug("Got CZONE toggle request for channel "+ str(channel))
                if channel in self._switches_status and self._switches_status[channel]:
                    new_state = False
            else:
                new_state = switch_value == 0xf1
                logger.debug("Got CZONE switch change request for channel "+ str(channel) + " : "+ str(new_state))


            logger.debug("Updating channel "+ str(channel) + " with status "+ str(new_state))

            self._update_switch_status(channel, new_state) 

            if new_state:
                # got a toggle ON, trigger appropriate channel trigger
                if channel == self._settings['AnchorDownChannel']:
                    self.controller.trigger_anchor_down()
                elif channel == self._settings['ChainOutChannel']:
                    self.controller.trigger_chain_out()
                elif channel == self._settings['AnchorUpChannel']:
                    self.controller.trigger_anchor_up()
                elif channel == self._settings['MuteAlarmChannel']:
                    self.controller.trigger_mute_alarm()
                elif channel == self._settings['MooringModeChannel']:
                    self.controller.trigger_mooring_mode()
                elif channel == self._settings['DecreaseToleranceChannel']:
                    self.controller.trigger_decrease_tolerance()
                elif channel == self._settings['IncreaseToleranceChannel']:
                    self.controller.trigger_increase_tolerance()

            self._send_switch_bank_control_pgn(channel, new_state) # will send 127502
            self._advertise_ds() # will send 127501


        elif switch_value == 0x40:
            # end of change request, send czone 65283 ack
            bank_number = 1 if channel < 5 else 2
            self._send_czone_switch_change_ack(bank_number)



    


    # Sends CZONE 65280 Switch toggle PGN 65283 Ack
    def _send_czone_switch_change_ack(self, bank_number):
        if not self._czone_enabled():
            return 
        
        bank_serial_number = self._settings['CZoneBank1SerialNumber'] if bank_number == 1 else self._settings['CZoneBank2SerialNumber']
        
        czone_switch_ack_msg = NMEARawPGN(65283)
        czone_switch_ack_msg.Add2ByteUInt(self._CZONE_MESSAGE)
        czone_switch_ack_msg.AddByte(int(bank_serial_number))
        czone_switch_ack_msg.AddByte(self._get_czone_mfd_state(bank_number))
        czone_switch_ack_msg.Add2ByteUInt(0x0000)
        czone_switch_ack_msg.AddByte(0x00)
        czone_switch_ack_msg.AddByte(0x10)

        self._bridge.send_nmea(czone_switch_ack_msg)


    # returns a state byte with channels 1-4 or 5-8 status
    def _get_czone_mfd_state(self, bank_number):
        state = 0x00

        for channel in range(1, 5):
            bit_mapping = [0x01, 0x04, 0x10, 0x40]
            xor_value = bit_mapping[channel-1]

            if bank_number == 2: 
                channel = channel + 4

            # if swtich_status is True, flip the appropriate bit
            if channel in self._switches_status and self._switches_status[channel]:
                state ^= xor_value

        return state
    

    # sends a 127502 standard NMEA Switch Bank control
    def _send_switch_bank_control_pgn(self, channel, value):
        # {"canId":233967171,"prio":3,"src":67,"dst":255,"pgn":127502,"timestamp":"2025-05-08T04:42:33.723Z","input":["2025-05-08T04:42:33.723Z,3,127502,67,255,8,00,ff,ff,3f,ff,ff,ff,ff"],"fields":{"Instance":0,"Switch12":"Off"},"description":"Switch Bank Control"}
        nmea_message = {
            "pgn": 127502,
            "fields": {
                "Instance": self._settings['DSBank'],
                #"Switch12":"Off"
            },
            "description":"Switch Bank Control"
        }

        text_value =  "On" if value else "Off"
        nmea_message["fields"]["Switch"+ str(channel)] =text_value

        logger.debug("Sending 127502 with Switch"+str(channel)+ ": "+text_value)
        self._bridge.send_nmea(nmea_message) 



    # MFD sends a 65290 configuration request which we need to 
    # reply with our bank serial numbers
    def _handle_czone_config_request(self, nmea_message):
        if not self._czone_enabled():
            return 

        if int.from_bytes(nmea_message.data[:2], byteorder="big") != self._CZONE_MESSAGE: 
            return  # not a CZone Message, ignore
        
        if nmea_message.data[7] != self._settings['CZoneDipSwitch']:
            return  # not our DipSwitch Message, ignore

        czone_config = nmea_message.data[2]

        def get_auth_pgn(config_byte, serial):
            auth_nmea_message = NMEARawPGN(65290)
            auth_nmea_message.Add2ByteUInt(self._CZONE_MESSAGE)
            auth_nmea_message.AddByte(config_byte)
            auth_nmea_message.AddByte(config_byte)
            auth_nmea_message.AddByte(config_byte)
            auth_nmea_message.Add2ByteUInt(0x0000)
            auth_nmea_message.AddByte(int(serial))

            return auth_nmea_message

        self._bridge.send_nmea(get_auth_pgn(czone_config, self._settings['CZoneBank1SerialNumber']))
        self._bridge.send_nmea(get_auth_pgn(czone_config, self._settings['CZoneBank2SerialNumber']))

        self._czone_handshake_done = True


    # Sends CZone 65284 switch heart beat PGN
    def _send_czone_switch_heartbeat(self, bank_number):
        if not self._czone_enabled():
            return 
        
        heartbeat_nmea_message = NMEARawPGN(65284)
        heartbeat_nmea_message.Add2ByteUInt(self._CZONE_MESSAGE)
        if self._czone_handshake_done:
            serial = self._settings['CZoneBank1SerialNumber'] if bank_number == 1 else self._settings['CZoneBank2SerialNumber']
            heartbeat_nmea_message.AddByte(int(serial))
            heartbeat_nmea_message.AddByte(0x0f)
            heartbeat_nmea_message.AddByte(self._get_czone_mfd_state(bank_number))
        else:   # if handshake not done, send 0xff to ask for a 65290 config request
            heartbeat_nmea_message.AddByte(0xff)
            heartbeat_nmea_message.Add2ByteUInt(0x0f0f)

        heartbeat_nmea_message.Add2ByteUInt(0x0000)
        heartbeat_nmea_message.AddByte(0x00)

        self._bridge.send_nmea(heartbeat_nmea_message)






    def _czone_all_switches_state_advertise(self, bank_number):
        if not self._czone_enabled():
            return 
        
        state_nmea_message = NMEARawPGN(130817)
        state_nmea_message.Add2ByteUInt(self._CZONE_MESSAGE)
        state_nmea_message.AddByte(0x01)   # ?? maybe an "instance" value

        serial = self._settings['CZoneBank1SerialNumber'] if bank_number == 1 else self._settings['CZoneBank2SerialNumber']
        state_nmea_message.AddByte(int(serial))

        for channel in range(1, 5):
            if bank_number == 2: 
                channel = channel + 4

            # if swtich_status is True, set 1 else 0
            value = 0x01 if channel in self._switches_status and self._switches_status[channel] else 0x00
            state_nmea_message.AddByte(value)
            state_nmea_message.Add2ByteUInt(0x0000)

        state_nmea_message.AddByte(0x0)
        state_nmea_message.AddByte(0x0)
        state_nmea_message.AddByte(0x0)
        state_nmea_message.AddByte(0x0)
        state_nmea_message.AddByte(0x0)
        state_nmea_message.AddByte(0x0)

        logger.debug("Sending 130817 state message for bank "+ str(bank_number))
        self._bridge.send_nmea(state_nmea_message)













if __name__ == '__main__':

    from nmea_bridge import NMEABridge
    from utils import handle_stdin, find_n2k_can
    from gi.repository import GLib
    import dbus
    sys.path.insert(1, os.path.join(os.path.dirname(__file__), '../ext/velib_python'))

    from settingsdevice import SettingsDevice
    from unittest.mock import MagicMock
    from collections import namedtuple
    from dbus.mainloop.glib import DBusGMainLoop


    logging.basicConfig(level=logging.DEBUG)

    from abstract_gps_provider import GPSPosition
    
    DBusGMainLoop(set_as_default=True)

    bus = dbus.SessionBus() if 'DBUS_SESSION_BUS_ADDRESS' in os.environ else dbus.SystemBus()
    can_id = find_n2k_can(bus)
    bridge = NMEABridge(can_id)    

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

    def _mooring_mode():
        print("trigger mooring mode")
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
    controller.trigger_mooring_mode = MagicMock(side_effect=_mooring_mode)
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
