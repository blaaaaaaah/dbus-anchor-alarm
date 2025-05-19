from collections import namedtuple

import logging
import sys
import os
sys.path.insert(1, os.path.join(os.path.dirname(__file__), 'ext/velib_python'))

from gi.repository import GLib
from dbusmonitor import DbusMonitor
from dbus.mainloop.glib import DBusGMainLoop
import dbus

GPSPosition = namedtuple('GPSPosition', ['latitude', 'longitude'])

logger = logging.getLogger(__name__)

class GPSProvider(object):
    
    def __init__(self):
        dummy = {'code': None, 'whenToLog': 'configChange', 'accessLevel': None}
        dbus_tree = {'com.victronenergy.gps': {
                '/DeviceInstance': dummy,
				'/Fix': dummy,
				'/Position/Latitude': dummy,
				'/Position/Longitude': dummy
                }
            }
        
        self._gpses = set()
        self._current_service = None

        
        self._dbusmonitor = DbusMonitor(dbus_tree, valueChangedCallback=self._dbus_value_changed,
			deviceAddedCallback=self._device_added, deviceRemovedCallback=self._device_removed)
    
        for service, instance in self._dbusmonitor.get_service_list().items():
            self._device_added(service, instance)

    def get_gps_position(self):
        """Main public API, returns a GPSPosition namedtuple or None if no GPS is available"""

        if self._current_service is None:
            logger.info("No current GPS service, can't get GPS position")
            return None
        
        gps_position = GPSPosition(latitude=  self._dbusmonitor.get_value(self._current_service, '/Position/Latitude'), 
                                   longitude= self._dbusmonitor.get_value(self._current_service, '/Position/Longitude'))

        logger.debug("Found gps position "+ str(gps_position))
        return gps_position


    def _dbus_value_changed(self, dbusServiceName, dbusPath, dict, changes, deviceInstance):
#        logger.info("_dbus_value_changed called "+ dbusServiceName +"/"+dbusPath)
#        logger.info(dict)
#        logger.info(changes)
        pass

    def _device_added(self, service, instance):
        if service.startswith('com.victronenergy.gps.'):
            logger.info('found GPS service '+ service)
            self._gpses.add((instance, service))
            self._dbusmonitor.track_value(service, "/Fix", self.update)
            self.update()

    def _device_removed(self, service, instance):
        logger.info('GPS service '+ service + ' removed')
        self._gpses.discard((instance, service))
        self.update()
		

    def update(self, *args):
        for instance, service in sorted(self._gpses):
            fix = self._dbusmonitor.get_value(service, '/Fix')
            if fix:
                logger.info('got fixed GPS service on '+ service)
                self._current_service = service
                break
        else:
            logger.info('no GPS service found')
            self._current_service = None



def log_gps_position(provider):
    print (str(provider.get_gps_position()))
    return True


if __name__ == "__main__":

    logging.basicConfig(level=logging.DEBUG)
    # Have a mainloop, so we can send/receive asynchronous calls to and from dbus
    DBusGMainLoop(set_as_default=True)
    provider = GPSProvider()

    from ve_utils import exit_on_error
   
    GLib.timeout_add(1000, exit_on_error, log_gps_position, provider)
#    GLib.timeout_add(2000, log_gps_position, provider)
#    GLib.timeout_add(3000, log_gps_position, provider)

	# Start and run the mainloop
    logger.info("Starting mainloop, responding only on events")
    mainloop = GLib.MainLoop()
    mainloop.run()
