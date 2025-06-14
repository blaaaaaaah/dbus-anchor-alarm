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

import json
import uuid
from subprocess import Popen, PIPE
from gi.repository import GLib

import logging
logger = logging.getLogger(__name__)

from utils import exit_on_error, handle_stdin, find_n2k_can
import os

class NMEABridge:

    def __init__(self, can_id = "can0", js_gateway_path=None, max_restart_attempts=3, ready_timeout=30):
        if js_gateway_path is None:
            js_gateway_path = os.path.join(os.path.dirname(__file__), 'nmea_bridge.js') # assume same folder

        self._can_id = can_id

        self._js_gateway_path = js_gateway_path
        self._max_restart_attempts = max_restart_attempts

        self._nodejs_process = None
        self._watch_id = None
        self._err_id = None
        self._restart_attempts = 0

        self._ready = False
        self._ready_timeout = ready_timeout
        self._ready_timeout_id = None

        self._queue = []

        self._handlers = {}

        self.error_handler = None
        self._unrecoverable_error = False
        self._was_once_ready = False

        self._start_nodejs_process()
        GLib.timeout_add_seconds(1, exit_on_error, self._check_process_status)


    def send_nmea(self, nmea_message):
        """Sends an NMEA message to the Node.js process."""
        command = {
            "id": str(uuid.uuid4()),
            "command": "sendPGN",
            "message": nmea_message
        }
        self._send_command(command)


    def add_pgn_handler(self, pgn, handler):
        """Sets NMEA filters."""
        if pgn not in self._handlers:
            self._handlers[pgn] = []

        self._handlers[pgn].append(handler)
        self._send_filters()
        

    def _send_filters(self):
        filters = list(self._handlers.keys())
        if len(filters):
            command = {
                "id": str(uuid.uuid4()),
                "command": "filterPGN",
                "filter": filters
            }
            self._send_command(command)


    def _init_can(self, can_id):
        command = {
                "id": str(uuid.uuid4()),
                "command": "initCAN",
                "canId": can_id
            }
        self._send_command(command, True)


    def _on_init_can(self, can_id, error):
        if error is None:
            logger.info("Found CAN device "+ can_id)
        else:
            logger.error(error)
            self._unrecoverable_error = True
            self._stop_nodejs_process()
            if self.error_handler is not None:
                self.error_handler("Unable to start NMEA bridge (initCAN)")

    # process and communication handling

    def _start_nodejs_process(self):
        """Starts the Node.js process."""
        self._ready = False
        try:

            if self._watch_id is not None:
                GLib.source_remove(self._watch_id)

            if self._err_id is not None:
                GLib.source_remove(self._err_id)

            self._nodejs_process = Popen(
                ['node', self._js_gateway_path],
                stdin=PIPE, stdout=PIPE, stderr=PIPE, text=True
            )

#            GLib.io_add_watch(self._nodejs_process.stdout, GLib.IO_HUP, self._check_process_status) # TODO XXX : doens't work
            
            self._watch_id = GLib.io_add_watch(self._nodejs_process.stdout, GLib.IO_IN, self._on_stdout_data)
            self._err_id = GLib.io_add_watch(self._nodejs_process.stderr, GLib.IO_IN, self._on_stderr_data)

            logger.info("Node.js process started, waiting for ready")

            self._send_filters()   

            if self._ready_timeout_id:
                GLib.source_remove(self._ready_timeout_id)

            self._ready_timeout_id = GLib.timeout_add(self._ready_timeout*1000, exit_on_error, self._on_ready_timeout)

            self._init_can(self._can_id)      

        except Exception as e:
            logger.info(f"Failed to start Node.js process: {e}")
            
            self._unrecoverable_error = True
            if self.error_handler is not None:
                self.error_handler("Unable to start NMEA bridge (NodeJS)")

            self._stop_nodejs_process()

    def _on_ready_timeout(self):
        logger.error("Timeout while waiting for ready")
        self._ready_timeout_id = None
        
        if self._nodejs_process:
            self._nodejs_process.terminate()
        
        self._check_process_status()
        return False

    def _stop_nodejs_process(self):
        """Stops the Node.js process."""
        if self._nodejs_process:
            self._nodejs_process.terminate()
            self._nodejs_process = None
            logger.info("Node.js process stopped")

    def _on_stdout_data(self, source, condition):
        """Handles stdout data from the Node.js process."""
        if condition == GLib.IO_IN:
            line = source.readline().strip()
            if line:
                self._handle_nodejs_message(line)
            return True
        
        return False
    
    def _on_stderr_data(self, source, condition):
        """Handles stderr data from the Node.js process."""
        if condition == GLib.IO_IN:
            line = source.readline().strip()
            if line:
                logger.error("STDERR " + line)

            return True
        
        return False

    def _check_process_status(self, source=None, condition=None):
        """Checks if the Node.js process is still running and restarts if it crashes."""
        if self._nodejs_process and self._nodejs_process.poll() is not None:
            logger.info("Node.js process crashed")
            self._restart_attempts += 1
            if self._restart_attempts <= self._max_restart_attempts:
                logger.info(f"Attempting to restart Node.js process (Attempt {self._restart_attempts}/{self._max_restart_attempts})...")
                self._start_nodejs_process()
            else:
                logger.info("Max restart attempts reached. Exiting.")
                self._stop_nodejs_process()

                self._unrecoverable_error = True
                if self.error_handler is not None:
                    if self._was_once_ready:
                        self.error_handler("Lost connection to NMEA bridge")
                    else:
                        self.error_handler("Unable to start NMEA bridge")
                
                #from os import _exit as os_exit
                #os_exit(1)
                return False

        return True

    def _handle_nodejs_message(self, message):
        """Handles messages from the Node.js process."""
        logger.debug("received "+ message)

        try:
            data = json.loads(message)
            if data.get("event") == "on_initCAN":
                self._on_init_can(data.get("canId"), data.get("error"))

            elif data.get("event") == "on_bridge_ready":
                if self._ready_timeout_id:
                    GLib.source_remove(self._ready_timeout_id)

                self._on_bridge_ready()

            elif data.get("event") == "on_NMEA_message":
                self._on_nmea_message(data.get("message"))

            elif data.get("event") == "on_sendPGN":
                logger.debug(f"NMEA message sent: {data}")

            elif data.get("event") == "on_filterPGN":
                logger.debug(f"Filters updated: {data}")
            
            elif data.get("event") == "on_error":
                logger.error(f"got error from NodeJS: {data}")
                

        except json.JSONDecodeError:
            logger.error(f"Invalid JSON from Node.js: {message}")


    def _send_command(self, command, force=False):
        """Sends a command to the Node.js process."""
        self._check_process_status()

        # do not accept any more commands if we're in an unrecoverable state
        if self._unrecoverable_error:
            logger.debug("In unrecoverable state, ignoring command "+ json.dumps(command))
            return

        if self._ready or force:
            try:
                # TODO XXX : make sure \n are escaped !
                self._nodejs_process.stdin.write(json.dumps(command) + "\n")
                self._nodejs_process.stdin.flush()
                logger.debug("sent "+ json.dumps(command))
            except Exception as e:
                logger.error(f"Failed to send command: {e}")
                self._check_process_status()
                
        else:
            logger.debug(f"Queuing: {command}")
            self._queue.append(command)


    def _on_nmea_message(self, message):
        pgn = message['pgn']

        # adding raw PGN data to the message
        # "data":{"type":"Buffer","data":[19,153,4,5,0,0,1,0]}
        if "data" in message and "data" in message['data']:
            message['data'] = bytearray(message['data']['data'])
        else:
            message['data'] = []

        if pgn in self._handlers:
            for handler in self._handlers[pgn]:
                handler(message)

    def _on_bridge_ready(self):
        logger.info("NMEA Bridge ready, flushing queued commands")
        while len(self._queue) > 0:
            self._send_command(self._queue.pop(0), True)

        # only set _ready to True after we flushed other commands to keep correct order
        self._ready = True
        self._was_once_ready = True



if __name__ == '__main__':

    logging.basicConfig(level=logging.DEBUG)

    import dbus
    dbus = dbus.SessionBus() if 'DBUS_SESSION_BUS_ADDRESS' in os.environ else dbus.SystemBus()	
    can_id = find_n2k_can(dbus)

    YDAB_ADDRESS = 67
    bridge = NMEABridge(can_id)

    bridge.error_handler = lambda msg: print("error_handler: "+ msg)

    # alert ack pgn
    bridge.add_pgn_handler(126984, print)

    # ydab config ack
    bridge.add_pgn_handler(126998, print)

    # ydab digital switching event
    bridge.add_pgn_handler(127502, print)

    

    print("NMEA Bridge test program. Enter show:text to send Alert PGN.\nhide to hide message.\nyd:command to send YDAB command\nds:BankInstance,BankChannel,On|Off to send a DigitalSwitching command\nfilter:<PGN> to filter and print received PGNS\nraw:{JSON object with at least pgn and fields parameter} to send a raw message\nkill to kill the underlying nodeJS program\nexit to exit\n")

    def handle_command(command, text):
        mapping = {
            'caution': "Caution",
            'warning': "Warning",
            'alarm': 'Alarm',
            'emergency': 'Emergency Alarm'
        }

        if command in ['show', 'caution', 'warning', 'alarm', 'emergency']:
            type = 'Caution' if command == "show" else mapping[command]
            bridge.send_nmea({
                "pgn": 126983,
                "Alert ID": 123,
                "Alert Type": type,
                "Alert State": "Active",
                "Alert Category": "Technical",
                "Alert System": 5,
                "Alert Sub-System": 0,
                "Data Source Network ID NAME": 123,
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
            })

            bridge.send_nmea({
                "pgn": 126985,
                "Alert ID": 123,
                "Alert Type": type,
                "Alert Category": "Technical",
                "Alert System": 5,
                "Alert Sub-System": 0,
                "Data Source Network ID NAME": 123,
                "Data Source Instance": 0,
                "Data Source Index-Source": 0,
                "Alert Occurrence Number": 0,
                "Language ID": 0,
                "Alert Text Description": text
            })


        elif command == "hide":

            type = 'Caution' if text is None else mapping[text]
            bridge.send_nmea({
                "pgn": 126983,
                "Alert ID": 123,
                "Alert Type": type,
                "Alert State": "Normal",
                "Alert Category": "Technical",
                "Alert System": 5,
                "Alert Sub-System": 0,
                "Data Source Network ID NAME": 123,
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
            })

        elif command == "yd":
            bridge.send_nmea({
                "prio":3,
                "dst":YDAB_ADDRESS,
                "pgn":126208,
                "fields":{
                    "Function Code":"Command",
                    "PGN":126998,
                    "Number of Parameters":1,
                    "list":[{
                        "Parameter":2,
                        "Value": "YD:"+text}]
                },
                "description":"NMEA - Command group function"
            })

        elif command == "yd":
                bridge.send_nmea({
                    "prio":3,
                    "dst": 67,
                    "pgn":126208,
                    "fields":{
                        "Function Code":"Command",
                        "PGN":126998,
                        "Number of Parameters":1,
                        "list":[{
                            "Parameter":2,
                            "Value": "yd:"+text}]
                    },
                    "description":"NMEA - Command group function"
                })
        
        elif command == "ds":
            if len(text) == 0:
                print("No arguments for ds: command")
                return True
            
            parts = text.split(":")
            if len(parts) != 3:
                print("Wrong arguments count ds: command")
                return True
            
            bridge.send_nmea({
                "pgn":127502,
                "fields": {
                    "Instance": parts[0],
                    "Switch"+ parts[1]:parts[2]
                },
                "description":"Switch Bank Control"
            })

        elif command == "raw":
            if len(text) == 0:
                print("No arguments for raw: command. 'pgn' and 'fields' params need to be in the JSON stringified object")
                return True
            try:
                nmea_message = json.loads(text)
                bridge.send_nmea(nmea_message)
            except Exception as e:
                print("Unable to decode JSON", e)

        elif command == "filter":
            bridge.add_pgn_handler(int(text), print)

        elif command == "kill":
            bridge._nodejs_process.terminate()

        else:
            print("Unknown command "+ command)


    handle_stdin(handle_command)