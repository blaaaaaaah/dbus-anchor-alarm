#!/usr/bin/env python3

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


from dbus_connector import DBusConnector
from nmea_alert_connector import NMEAAlertConnector
from nmea_ydab_connector import NMEAYDABConnector
from nmea_sog_rpm_connector import NMEASOGRPMConnector


from anchor_alarm_controller import AnchorAlarmController
from nmea_bridge import NMEABridge


from gi.repository import GLib
import dbus
from settingsdevice import SettingsDevice

from gps_provider import GPSProvider


class DbusAnchorAlarmService(object):
    def __init__(self):
        
        self._gps_provider = GPSProvider()
        self._nmea_bridge  = NMEABridge()

        self._initStateMachine()


    def _initStateMachine(self):
        bus = dbus.SessionBus() if 'DBUS_SESSION_BUS_ADDRESS' in os.environ else dbus.SystemBus()

        self._alarm_controller = AnchorAlarmController(lambda: GLib, lambda settings, cb: SettingsDevice(bus, settings, cb), self._gps_provider)

        dbus_connector = DBusConnector(lambda: GLib, lambda settings, cb: SettingsDevice(bus, settings, cb))
        nmea_alert_connector = NMEAAlertConnector(lambda: GLib, lambda settings, cb: SettingsDevice(bus, settings, cb), self._nmea_bridge)
        nmea_ydab_connector = NMEAYDABConnector(lambda: GLib, lambda settings, cb: SettingsDevice(bus, settings, cb), self._nmea_bridge)
        nmea_sog_rpm_connector = NMEASOGRPMConnector(lambda: GLib, lambda settings, cb: SettingsDevice(bus, settings, cb), self._nmea_bridge)

        # TODO XXX move registration of connectors elsewhere ? 
        self._alarm_controller.register_connector(dbus_connector)
        self._alarm_controller.register_connector(nmea_alert_connector)
        self._alarm_controller.register_connector(nmea_ydab_connector)
        self._alarm_controller.register_connector(nmea_sog_rpm_connector)




# TODO XXX : how to launch the service ?
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
