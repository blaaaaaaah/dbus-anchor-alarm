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
sys.path.insert(1, os.path.join(sys.path[0], '..'))

from abstract_connector import AbstractConnector
from anchor_alarm_model import AnchorAlarmState

import logging
logger = logging.getLogger(__name__)

class NMEAAlertConnector(AbstractConnector):
    def __init__(self, timer_provider, settings_provider, nmea_bridge):
        super().__init__(timer_provider, settings_provider)
        
        self._init_settings()

        # TODO XXX : move to settings ?
        self._ALERT_ID = "54321"
        self._NETWORK_ID = "54321"

        # "Emergency Alarm" | "Alarm" | "Warning" | "Caution"
        self._types_states = [
            {"type": "Caution",           "state": "Normal"},
            {"type": "Warning",           "state": "Normal"},
            {"type": "Alarm",             "state": "Normal"},
            {"type": "Emergency Alarm",   "state": "Normal"}
        ]
        self._timer_ids = {
            'Caution': None,
            'Warning': None,
            'Alarm':   None,
            'Emergency Alarm': None
        }

        self._bridge = nmea_bridge
        self._bridge.add_pgn_handler(126984, self._on_nmea_message)


    def _init_settings(self):
        # create the setting that are needed
        settingsList = {
            # Duration an info (Caution) message will be automatically dismissed after
            "AutoAcknowledgeInterval":     ["/Settings/AnchorAlarm/NMEA/Alert/AutoAcknowledgeInterval", 5, 1, 90]
        }

        # we don't care about getting notified if settings are updated
        self._settings = self._settings_provider(settingsList, None)


    def _on_nmea_message(self, nmea_message):
        """Called when a new NMEA message arrives."""
        logger.debug(f"Received NMEA message: {nmea_message}")
        # {'canId': 166725639, 'prio': 2, 'src': 7, 'dst': 255, 'pgn': 126984, 'timestamp': '2025-05-15T18:15:00.974Z', 'input': [], 'fields': {'Alert Type': 'Caution', 'Alert Category': 'Technical', 'Alert System': 5, 'Alert Sub-System': 0, 'Alert ID': 54321, 'Data Source Network ID NAME': 54321, 'Data Source Instance': 0, 'Data Source Index-Source': 0, 'Alert Occurrence Number': 0, 'Acknowledge Source Network ID NAME': 13902754986684846000, 'Response Command': 'Acknowledge', 'Reserved1': 0}, 'description': 'Alert Response'}
        # {'canId': 166725639, 'prio': 2, 'src': 7, 'dst': 255, 'pgn': 126984, 'timestamp': '2025-05-15T18:31:09.659Z', 'input': [], 'fields': {'Alert Type': 'Emergency Alarm', 'Alert Category': 'Technical', 'Alert System': 5, 'Alert Sub-System': 0, 'Alert ID': 54321, 'Data Source Network ID NAME': 54321, 'Data Source Instance': 0, 'Data Source Index-Source': 0, 'Alert Occurrence Number': 0, 'Acknowledge Source Network ID NAME': 13902754986684846000, 'Response Command': 'Acknowledge', 'Reserved1': 0}, 'description': 'Alert Response'}

        if nmea_message['pgn'] == 126984 and "fields" in nmea_message and \
            "Data Source Network ID NAME" in nmea_message["fields"] and  str(nmea_message["fields"]["Data Source Network ID NAME"]) == self._NETWORK_ID and \
            'Alert ID' in nmea_message["fields"] and  str(nmea_message["fields"]['Alert ID']) == self._ALERT_ID and 'Alert Type' in nmea_message["fields"]:
            # set back state for type to Normal

            t = next(item for item in self._types_states if item["type"] == nmea_message["fields"]['Alert Type'])
            t['state'] = 'Normal'

            # TODO XXX : multiple devices on nmea bus will send this message as broadcast, make sure to not call mute multiple times ?
            if self.controller is not None and nmea_message["fields"]['Alert Type'] == "Emergency Alarm":
                self.controller.trigger_mute_alarm()

    # called when a state changes
    def on_state_changed(self, current_state:AnchorAlarmState):
        """Called by controller when state changed"""
        logger.info("On state changed "+ current_state.state)

        #"Alert Type"" = "Emergency Alarm" | "Alarm" | "Warning" | "Caution"
        type = self._type_for_alarm_state(current_state.level)


        # new type, we want to clear old messages
        if current_state.muted:
            self._clear_alerts_except(None) # clear all 
        else:
            self._clear_alerts_except(type)


        # if we're in a muted state, Active state has been cancelled by _clear_alerts()
        if not current_state.muted:
            self._send_alert_payload(type, "Active")

            #auto aknowledge only Caution type
            if type == "Caution":
                self._add_timer('Caution', lambda: self._send_alert_payload("Caution", "Normal"), self._settings['AutoAcknowledgeInterval']*1000)



        # update values on NMEA BUS
        # TODO XXX : should this be called BEFORE or AFTER the _send_alert_payload ?
        self.update_state(current_state)


    # called every second to update state
    def update_state(self, current_state:AnchorAlarmState):
        """Called by controller every second with updated state"""
       
       # TODO XXX : do not send a message every second when nothing is happening
        type = self._type_for_alarm_state(current_state.level)
        self._send_alert_text_message(type, current_state.message)


    # shows a specific message. Will be auto acknowledged
    def show_message(self, level, message):
        type = self._type_for_alarm_state(level)

        self._send_alert_payload(type, "Active")
        self._send_alert_text_message(type, message)

        if type == "Caution":
            self._add_timer('Caution', lambda: self._send_alert_payload("Caution", "Normal"), self._settings['AutoAcknowledgeInterval']*1000)


    def _type_for_alarm_state(self, current_state_level):
        # level = info | warning | error | emergency
        mapping = {
            "emergency": "Emergency Alarm",
            "error": "Alarm",
            "warning": "Warning",
            "info": "Caution"
        }

        return mapping.get(current_state_level, "Caution")

    def _clear_alerts_except(self, type):
        for t in self._types_states:            
            if t['state'] == "Active" and t['type'] != type:
                if self._timer_ids[t['type']] is not None:
                    self._remove_timer(t['type'])   # clear auto acknowledge.  

                self._send_alert_payload(t['type'], "Normal")
                              

    def _send_alert_payload(self, type, state):
        # update type's state
        t = next(item for item in self._types_states if item["type"] == type)
        t['state'] = state

        nmea_message = {
            "pgn": 126983,
            "Alert ID": self._ALERT_ID,
            "Alert Type": type,
            "Alert State": state,
            "Alert Category": "Technical",
            "Alert System": 5,
            "Alert Sub-System": 0,
            "Data Source Network ID NAME": self._NETWORK_ID,
            "Data Source Instance": 0,
            "Data Source Index-Source": 0,
            "Alert Occurrence Number": 0,
            "Temporary Silence Status": 0,
            "Acknowledge Status": 0,
            "Escalation Status": 0,
            "Temporary Silence Support": 0,
            "Acknowledge Support": 1,
            "Escalation Support": 0,
            "Trigger Condition": 2,
            "Threshold Status": 1,
            "Alert Priority": 0
        }

        logger.debug("Sending alert payload", nmea_message)
        self._bridge.send_nmea(nmea_message)

    def _send_alert_text_message(self, type, message):
        nmea_message = {
            "pgn": 126985,
            "Alert ID": self._ALERT_ID,
            "Alert Type": type,
            "Alert Category": "Technical",
            "Alert System": 5,
            "Alert Sub-System": 0,
            "Data Source Network ID NAME": self._NETWORK_ID,
            "Data Source Instance": 0,
            "Data Source Index-Source": 0,
            "Alert Occurrence Number": 0,
            "Language ID": 0,
            "Alert Text Description": message
        }

        logger.debug("Sending alert text", nmea_message)
        self._bridge.send_nmea(nmea_message)








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


    from abstract_gps_provider import GPSPosition

    bridge = NMEABridge()
    DBusGMainLoop(set_as_default=True)

    bus = dbus.SessionBus() if 'DBUS_SESSION_BUS_ADDRESS' in os.environ else dbus.SystemBus()
    nmea_alert_connector = NMEAAlertConnector(lambda: GLib, lambda settings, cb: SettingsDevice(bus, settings, cb), bridge)

    controller = MagicMock()
    controller.trigger_mute_alarm   = MagicMock(side_effect=lambda: print("trigger mute alarm"))
    nmea_alert_connector.set_controller(controller)

    print("NMEA Alert connector test program. Type : \ndisabled\ndrop\nin_radius\nin_radius2\nin_radius3\ndragging\nmuted\nexit to exit\nWhen the alert message sent by dragging is acknoweledge, trigger_mute_alarm should show in screen")

    def handle_command(command, text):

        # AnchorAlarmState = namedtuple('AnchorAlarmState', ['state', 'message','short_message', 'level', 'muted', 'params'])
        state_drop_point_set = AnchorAlarmState('DROP_POINT_SET', 'Drop point set, please do blablala',"short message", 'info', False, {'drop_point': GPSPosition(10, 11)})
        state_in_radius = AnchorAlarmState('IN_RADIUS', 'boat in radius',"short message", 'info', False, {'drop_point': GPSPosition(10, 11), 'radius': 12})
        state_in_radius2 = AnchorAlarmState('IN_RADIUS', 'boat in radius 2',"short message", 'info', False, {'drop_point': GPSPosition(10, 11), 'radius': 12})
        state_in_radius3 = AnchorAlarmState('IN_RADIUS', 'boat in radius 3',"short message", 'info', False, {'drop_point': GPSPosition(10, 11), 'radius': 12})
        state_dragging = AnchorAlarmState('ALARM_DRAGGING', 'Anchor dragging !',"short message", 'emergency', False, {'drop_point': GPSPosition(10, 11), 'radius': 12})
        state_dragging_muted = AnchorAlarmState('ALARM_DRAGGING_MUTED', 'Anchor dragging ! (muted)',"short message", 'emergency', True, {'drop_point': GPSPosition(10, 11), 'radius': 12})
        state_disabled = AnchorAlarmState('DISABLED', 'Anchor alarm disabled', "short message",'info', False, {})

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
        else:
            print("Unknown command "+ command)


    handle_stdin(handle_command)