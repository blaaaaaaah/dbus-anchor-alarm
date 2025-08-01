#!/usr/bin/env python3

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


"""
Service that will listen on com.victronenergy.gps and raise an alarm when outisde radius.
Can check on digital inputn for automaric enabling/disabling
Can
"""

import logging
import sys
import os


sys.path.insert(1, os.path.join(os.path.dirname(__file__), 'ext/velib_python'))
sys.path.insert(1, os.path.join(os.path.dirname(__file__), 'connectors'))
sys.path.insert(1, os.path.join(os.path.dirname(__file__), 'gps_providers'))


from dbus_connector import DBusConnector
from nmea_alert_connector import NMEAAlertConnector
from nmea_ais_anchor_connector import NMEAAISAnchorConnector
from nmea_ydab_connector import NMEAYDABConnector
from nmea_sog_rpm_connector import NMEASOGRPMConnector
from nmea_ds_connector import NMEADSConnector
from dbus_relay_connector import DBusRelayConnector
from dbus_dwp_connector import DBusDWPConnector

from anchor_alarm_controller import AnchorAlarmController
from nmea_bridge import NMEABridge
from utils import find_n2k_can


from gi.repository import GLib
import dbus
from settingsdevice import SettingsDevice

from dbus_gps_provider import DBusGPSProvider
from nmea_gps_provider import NMEAGPSProvider


class DbusAnchorAlarmService(object):
    def __init__(self):
        # create the setting that are needed
        settingsList = {
            # If auto discovery of NMEA can device fails, you can force it. Reboot required
            "NNMEACanDevice":     ["/Settings/AnchorAlarm/NMEA/CanDevice", "auto", 0, 128]
        }

        bus = dbus.SessionBus() if 'DBUS_SESSION_BUS_ADDRESS' in os.environ else dbus.SystemBus()
        settings = SettingsDevice(bus, settingsList, None)

        can_id = settings['NNMEACanDevice']
        if can_id == "auto":
            can_id = find_n2k_can(bus)

        self._nmea_bridge  = NMEABridge(can_id)

        self._initStateMachine(bus)


    def _initStateMachine(self, bus):

        self._alarm_controller = AnchorAlarmController(lambda: GLib, lambda settings, cb: SettingsDevice(bus, settings, cb))
        
        self._nmea_bridge.error_handler = lambda msg: self._alarm_controller.trigger_show_message("error", msg)

        dbus_gps_provider = DBusGPSProvider(lambda: GLib)
        nmea_gps_provider = NMEAGPSProvider(lambda: GLib, self._nmea_bridge)

        self._alarm_controller.register_gps_provider(dbus_gps_provider)
        self._alarm_controller.register_gps_provider(nmea_gps_provider)

        # Create shared D-Bus service
        self._dbus_service = self._create_dbus_service()

        dbus_connector = DBusConnector(lambda: GLib, lambda settings, cb: SettingsDevice(bus, settings, cb), self._nmea_bridge, self._dbus_service)
        dbus_dwp_connector = DBusDWPConnector(lambda: GLib, lambda settings, cb: SettingsDevice(bus, settings, cb), self._dbus_service)
        nmea_alert_connector = NMEAAlertConnector(lambda: GLib, lambda settings, cb: SettingsDevice(bus, settings, cb), self._nmea_bridge)
        nmea_ais_anchor_connector = NMEAAISAnchorConnector(lambda: GLib, lambda settings, cb: SettingsDevice(bus, settings, cb), self._nmea_bridge)
        nmea_ydab_connector = NMEAYDABConnector(lambda: GLib, lambda settings, cb: SettingsDevice(bus, settings, cb), self._nmea_bridge)
        nmea_sog_rpm_connector = NMEASOGRPMConnector(lambda: GLib, lambda settings, cb: SettingsDevice(bus, settings, cb), self._nmea_bridge)
        nmea_ds_connector = NMEADSConnector(lambda: GLib, lambda settings, cb: SettingsDevice(bus, settings, cb), self._nmea_bridge)
        dbus_relay_connector = DBusRelayConnector(lambda: GLib, lambda settings, cb: SettingsDevice(bus, settings, cb))

        # Register D-Bus service after all connectors have added their paths
        self._dbus_service.register()


        self._alarm_controller.register_connector(dbus_connector)
        self._alarm_controller.register_connector(dbus_dwp_connector)
        self._alarm_controller.register_connector(nmea_alert_connector)
        self._alarm_controller.register_connector(nmea_ais_anchor_connector)
        self._alarm_controller.register_connector(nmea_ydab_connector)
        self._alarm_controller.register_connector(nmea_sog_rpm_connector)
        self._alarm_controller.register_connector(nmea_ds_connector)
        self._alarm_controller.register_connector(dbus_relay_connector)

    def _create_dbus_service(self):
        from vedbus import VeDbusService
        dbus_service = VeDbusService("com.victronenergy.anchoralarm", register=False)
        dbus_service.add_mandatory_paths(sys.argv[0], self._get_version(), None, 0, 0, 'Anchor Alarm', 0, 0, 1)

        return dbus_service        
        
    def _get_version(self):
        version_file_path = os.path.join(os.path.dirname(__file__), 'VERSION')
        try:
            with open(version_file_path, 'r') as version_file:
                return version_file.read().strip()
        except Exception:
            return "Unknown"


def main():
    from argparse import ArgumentParser
    parser = ArgumentParser(
                    prog='Anchor Alarm Service',
                    description='Will register on the victron DBUS and provide an anchor alarm',
                    epilog='Should be run as a service. run setup.sh to install it as a service')
    
    parser.add_argument('-v', '--verbose', action='store_true')
    args = parser.parse_args()
    log_level = logging.DEBUG if args.verbose else logging.INFO
    logging.basicConfig(level=log_level)

    from dbus.mainloop.glib import DBusGMainLoop
    # Have a mainloop, so we can send/receive asynchronous calls to and from dbus
    DBusGMainLoop(set_as_default=True)

    service = DbusAnchorAlarmService()


    logging.info('Connected to dbus, and switching over to GLib.MainLoop() (= event based)')
    mainloop = GLib.MainLoop()
    mainloop.run()


if __name__ == "__main__":
    main()
