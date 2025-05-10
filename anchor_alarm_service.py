
#!/usr/bin/env python3

"""
Service that will listen on com.victronenergy.gps and raise an alarm when outisde radius.
Can check on digital inputn for automaric enabling/disabling
Can
"""
from connectors.dbus_connector import DBusConnector
import logging
import sys
import os

from anchor_alarm_controller import AnchorAlarmController
from anchor_alarm_model import AnchorAlarmConfiguration
from nmea_bridge import NMEABridge

# our own packages
# use an established Victron service to maintain compatiblity
sys.path.insert(1, os.path.join('/opt/victronenergy/dbus-systemcalc-py', 'ext', 'velib_python'))

from connectors.nmea_alert_connector import NMEAAlertConnector
from gi.repository import GLib
import dbus
from settingsdevice import SettingsDevice

from gps_provider import GPSProvider


class DbusAnchorAlarmService(object):
    def __init__(self):
        
        self._initSettings()

        self._gps_provider = GPSProvider()
        self._nmea_bridge  = NMEABridge()

        self._initStateMachine()


    def _initSettings(self):
        # create the setting that are needed

        # addSetting(self, path, value, _min, _max, silent=False, callback=None)
        settingsList = {
            # configuration
            "Tolerance":            ["/Settings/Services/Anchoralarm/Configuration/RadiusTolerance", 15, 0, 512, False, self._on_setting_changed],
            "NoGPSCountThreshold":  ["/Settings/Services/Anchoralarm/Configuration/NoGPSCountThreshold", 30, 0, 300, False, self._on_setting_changed],
            "MuteDuration":         ["/Settings/Services/Anchoralarm/Configuration/MuteDuration", 30, 0, 300, False, self._on_setting_changed],   
        }
        self._dbusSettings = SettingsDevice(
            bus=dbus.SystemBus(),
            supportedSettings=settingsList,
            timeout=10,
            eventCallback=None,
        )


    def _initStateMachine(self):
        # TODO XXX : make sure conf is OK ?
        # TODO XXX : make sure dbus_settings is populated already ?


        bus = dbus.SessionBus() if 'DBUS_SESSION_BUS_ADDRESS' in os.environ else dbus.SystemBus()


        conf = AnchorAlarmConfiguration(self._dbusSettings["Tolerance"], self._dbusSettings["NoGPSCountThreshold"], self._dbusSettings["MuteDuration"])
        self._alarm_controller = AnchorAlarmController(conf, GLib, self._gps_provider)
        # TODO XXX : change to use same mechanisme as connectors for settings

        dbus_connector = DBusConnector(lambda: GLib, lambda settings, cb: SettingsDevice(bus, settings, cb))

        nmea_alert_connector = NMEAAlertConnector(lambda settings, cb: SettingsDevice(bus, settings, cb), self.nmea_bridge)


        # TODO XXX move registration of connectors elsewhere ? how to configure them ?
        self._alarm_controller.register_connector(dbus_connector)
        self._alarm_controller.register_connector(nmea_alert_connector)


    def _on_setting_changed(self, path, old_value, new_value):
        print("On setting changed "+ path + ' : '+ old_value +' replaced by '+ new_value)
        # TODO XXX : update controller !



# TODO XXX : how to launch the service ?
def main():
    logging.basicConfig(level=logging.DEBUG)

    from dbus.mainloop.glib import DBusGMainLoop
    # Have a mainloop, so we can send/receive asynchronous calls to and from dbus
    DBusGMainLoop(set_as_default=True)

    service = DbusAnchorAlarmService()


    logging.info('Connected to dbus, and switching over to GLib.MainLoop() (= event based)')
    mainloop = GLib.MainLoop()
    mainloop.run()


if __name__ == "__main__":
    main()
