import json
import uuid
from subprocess import Popen, PIPE
from gi.repository import GLib

import logging
logger = logging.getLogger(__name__)

from utils import exit_on_error, handle_stdin


class NMEABridge:

    def __init__(self, js_gateway_path="nmea_bridge.js", max_restart_attempts=5):
        self._js_gateway_path = js_gateway_path
        self._max_restart_attempts = max_restart_attempts

        self._nodejs_process = None
        self._watch_id = None
        self._err_id = None
        self._restart_attempts = 0

        self._ready = False
        self._queue = []

        self._handlers = {}

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

        except Exception as e:
            logger.info(f"Failed to start Node.js process: {e}")
            self._stop_nodejs_process()

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
                from os import _exit as os_exit
                os_exit(1)
                return False

        return True

    def _handle_nodejs_message(self, message):
        """Handles messages from the Node.js process."""
        logger.debug("received "+ message)

        try:
            data = json.loads(message)
            if data.get("event") == "on_bridge_ready":
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
        if pgn in self._handlers:
            for handler in self._handlers[pgn]:
                handler(message)

    def _on_bridge_ready(self):
        logger.info("NMEA Bridge ready, flushing queued commands")
        while len(self._queue) > 0:
            self._send_command(self._queue.pop(0), True)

        # only set _ready to True after we flushed other commands to keep correct order
        self._ready = True



if __name__ == '__main__':
    YDAB_ADDRESS = 67
    bridge = NMEABridge()

    # alert ack pgn
    bridge.add_pgn_handler(126984, print)

    # ydab config ack
    bridge.add_pgn_handler(126998, print)

    # ydab digital switching event
    bridge.add_pgn_handler(127502, print)

    

    print("NMEA Bridge test program. Enter show:text to send Alert PGN.\nhide to hide message.\nyd:command to send YDAB command\nds:BankInstance,BankChannel,On|Off to send a DigitalSwitching command\nfilter:<PGN> to filter and print received PGNS\nkill to kill the underlying nodeJS program\nexit to exit\n")

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

        elif command == "filter":
            bridge.add_pgn_handler(int(text), print)

        elif command == "kill":
            bridge._nodejs_process.terminate()

        else:
            print("Unknown command "+ command)


    handle_stdin(handle_command)