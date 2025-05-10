import sys
import os
sys.path.insert(1, os.path.join(sys.path[0], '..'))


from abstract_connector import AbstractConnector
from anchor_alarm_controller import AnchorAlarmController
from anchor_alarm_controller import GPSPosition
from anchor_alarm_model import AnchorAlarmState


# our own packages
# use an established Victron service to maintain compatiblity
#sys.path.insert(1, os.path.join('/opt/victronenergy/dbus-systemcalc-py', 'ext', 'velib_python'))
sys.path.insert(1, os.path.join(os.path.dirname(__file__), '../ext/velib_python'))





class DBusConnector(AbstractConnector):
    def __init__(self, timer_provider, settings_provider):
        super().__init__(timer_provider, settings_provider)

        self._timer_ids = {
            'anchor_up': None,
            'anchor_down': None,
            'chain_out': None
        }

        self._init_settings()
        
        self._update_digital_input_names()

        self._init_dbus_monitor()
        self._init_dbus_service()
        
    def _init_settings(self):
        # create the setting that are needed
        settingsList = {
            # last state 
            "Latitude":             ["/Settings/AnchorAlarm/Last/Position/Latitude", None, 0.0, 128],
            "Longitude":            ["/Settings/AnchorAlarm/Last/Position/Longitude", None, 0.0, 128],
            "Radius":               ["/Settings/AnchorAlarm/Last/Radius", 0, 0, 256],

            
            "AnchorDownDigitalInputNumber":     ["/Settings/AnchorAlarm/Triggers/AnchorDown/DigitalInputNumber", 1, 0, 4],
            "AnchorDownDigitalInputDuration":   ["/Settings/AnchorAlarm/Triggers/AnchorDown/DigitalInputDuration", 3, 0, 30],

            "ChainOutDigitalInputNumber":       ["/Settings/AnchorAlarm/Triggers/ChainOut/DigitalInputNumber", 0, 0, 4],
            "ChainOutDigitalInputDuration":     ["/Settings/AnchorAlarm/Triggers/ChainOut/DigitalInputDuration", 0, 0, 30], 

            "AnchorUpDigitalInputNumber":       ["/Settings/AnchorAlarm/Triggers/AnchorUp/DigitalInputNumber", 2, 0, 4],
            "AnchorUpDigitalInputDuration":     ["/Settings/AnchorAlarm/Triggers/AnchorUp/DigitalInputDuration", 3, 0, 30], 

            "FeedbackDigitaInputNumber"  :      ["/Settings/AnchorAlarm/Triggers/Enable/DigitalInput", 1, 0, 4],    
            
        }

        self._settings = self._settings_provider(settingsList, self._on_setting_changed)

    
    def _init_dbus_monitor(self):
        # listen to all 4 digital inputs so we don't have to recreate/update the dbus monitor

        dummy = {'code': None, 'whenToLog': 'configChange', 'accessLevel': None}
        dummy_service = {'/Alarm': dummy, '/CustomName': dummy,	'/ProductName': dummy, '/State': dummy}
        monitorlist = {'com.victronenergy.digitalinput': dummy_service}

        # TODO XXX : add deviceAddedCallback handler in case of digitalinput service is loaded after us ?
        self._alarm_monitor = self._create_dbus_monitor(monitorlist, self._on_digitalinput_service_changed, deviceAddedCallback=None, deviceRemovedCallback=None)

    def _create_dbus_monitor(self, *args, **kwargs):
        from vedbus import DBusMonitor
        return DBusMonitor(*args, **kwargs)



    def _init_dbus_service(self):
        self._dbus_service = self._create_dbus_service("com.victronenergy.anchoralarm")
        self._dbus_service.add_mandatory_paths(__file__, '0.1', None, 0, 0, 'AnchorAlarm', 0, 0, 1)

        # publish data on the service for other people to consume (MTTQ, ..)
        self._dbus_service.add_path('/State', 'DISABLED', "State of the anchor alarm")
        self._dbus_service.add_path('/Message', '', "Description of the state")
        self._dbus_service.add_path('/Level', '', "Info, Warning, Alarm or Emergency")
        self._dbus_service.add_path('/Muted', False, "Is alarm muted")
        self._dbus_service.add_path('/Params', '', "Various params (radius, current radius, tolerance, ..)")

        # create trigger points for other people to manipulate state
        self._dbus_service.add_path('/Triggers/AnchorDown', 0, "Set 1 to trigger anchor down and define drop point", writeable=True, onchangecallback=self._on_service_changed)
        self._dbus_service.add_path('/Triggers/ChainOut',   0, "Set 1 to trigger chain out and set radius"         , writeable=True, onchangecallback=self._on_service_changed)
        self._dbus_service.add_path('/Triggers/AnchorUp',   0, "Set 1 to trigger anchor up and disable alarm"      , writeable=True, onchangecallback=self._on_service_changed)
        self._dbus_service.add_path('/Triggers/MuteAlarm',  0, "Set 1 to mute current alarm"                       , writeable=True, onchangecallback=self._on_service_changed)

        self._dbus_service.register()


    def _create_dbus_service(self, *args, **kwargs):
        from vedbus import VeDbusService
        return VeDbusService(*args, **kwargs)
    


    def set_controller(self, controller:AnchorAlarmController):
        """Controller has :
            - trigger_anchor_down
            - trigger_chain_out
            - trigger_anchor_up
            - trigger mute_alarm
        """
        super().set_controller(controller)

        if self._settings["Latitude"] and self._settings["Longitude"] and self._settings["Radius"]:
            # TODO XXX : check if lat/lont are valid ?
            drop_point = GPSPosition(self._settings["Latitude"], self._settings["Longitude"])
            self._controller.reset_state(drop_point, self._settings["Radius"])

    

    def on_state_changed(self, current_state:AnchorAlarmState):
        """Called by controller when state changed"""
        print("On state changed "+ current_state.state)

        if current_state.state == "IN_RADIUS":
            self._settings['Latitude']   = current_state.params['drop_point']['latitude']
            self._settings['Longitude']  = current_state.params['drop_point']['longitude']
            self._settings['Radius']     = current_state.params['radius']

        # update values on DBUS
        self.update_state(current_state)


        alarm_state = current_state.state in ['ALARM_DRAGGING', 'ALARM_NO_GPS'] 

        # update feedback alarm name so Cerbo shows correct alarm description
        self._alarm_monitor.set_value(self._feedback_digital_input, '/CustomName', current_state.message)
        self._alarm_monitor.set_value(self._feedback_digital_input, '/ProductName', current_state.message)

        # toggle alarm state
        self._alarm_monitor.set_value(self._feedback_digital_input, '/Alarm', alarm_state)


    def update_state(self, current_state:AnchorAlarmState):
        """Called by controller every second with updated state"""
        self._dbus_service['/State']    = current_state.state
        self._dbus_service['/Message']  = current_state.message
        self._dbus_service['/Level']    = current_state.level
        self._dbus_service['/Muted']    = current_state.muted
        self._dbus_service['/Params']   = current_state.params # TODO XXX as json string ?

        # TODO XXX : change also name of the feedback digital input ?
        #self._alarm_monitor.set_value(self._feedback_digital_input, '/CustomName', current_state.message)
        #self._alarm_monitor.set_value(self._feedback_digital_input, '/ProductName', current_state.message)


    def _on_setting_changed(self, path, old_value, new_value):
        # just recompute all names
        self._update_digital_input_names()
        

    def _update_digital_input_names(self):
        # com.victronenergy.digitalinput.input00 doesn't exist, so if any XXXDigitalInputNumber is 0, it will won't match a
        # a changed dbusPath and will be ignored 
        self._anchor_down_digital_input = 'com.victronenergy.digitalinput.input0' + str(self._settings['AnchorDownDigitalInputNumber'])
        self._chain_out_digital_input   = 'com.victronenergy.digitalinput.input0' + str(self._settings['ChainOutDigitalInputNumber'])
        self._anchor_up_digital_input   = 'com.victronenergy.digitalinput.input0' + str(self._settings['AnchorUpDigitalInputNumber'])
        self._feedback_digital_input    = 'com.victronenergy.digitalinput.input0' + str(self._settings['FeedbackDigitaInputNumber'])


    def _on_digitalinput_service_changed(self, dbusServiceName, dbusPath, dict, changes, deviceInstance):
        # controller is not set yet
        if self.controller is None:
            return
        
        # digital inputs states are pairs of ints. 0 is low, 1 is high, 2 is off, 3 is on and so on 
        # depending on input type in settings

        # mute alarm
        if ( dbusServiceName == self._feedback_digital_input 
                and dbusPath == '/Alarm'
                and changes['Value'] == 0 
                and self._dbus_service['/State'] in ['ALARM_DRAGGING', 'ALARM_NO_GPS']):

            self.controller.trigger_mute_alarm()

        # anchor_down digital input trigger
        if ( dbusServiceName == self._anchor_down_digital_input
                and dbusPath == '/State' ):
            
            if ( changes['Value'] % 2 == 1 ):
                self._add_timer('anchor_down', self.controller.trigger_anchor_down, int(self._settings['AnchorDownDigitalInputDuration'])*1000)
            else:
                self._remove_timer('anchor_down')


        # anchor up digital input trigger
        if ( dbusServiceName == self._anchor_up_digital_input
                and dbusPath == '/State' ):
            
            if ( changes['Value'] % 2 == 1 ):
                self._add_timer('anchor_up', self.controller.trigger_anchor_up, int(self._settings['AnchorUpDigitalInputDuration'])*1000)
            else:
                self._remove_timer('anchor_up')

        # chain out digital input trigger
        if ( dbusServiceName == self._chain_out_digital_input
                and dbusPath == '/State' ):
            
            if ( changes['Value'] % 2 == 1 ):
                self._add_timer('chain_out', self.controller.trigger_chain_out, int(self._settings['ChainOutDigitalInputDuration'])*1000)
            else:
                self._remove_timer('chain_out')


    def _on_service_changed(self, path, newvalue):
        if path == '/Triggers/AnchorDown':
            self.controller.trigger_anchor_down()
            # controller update will put value back to 0 ?
            return False
        
        if path == '/Triggers/ChainOut':
            self.controller.trigger_chain_out()
            # controller update will put value back to 0 ?
            return False
        
        if path == '/Triggers/AnchorUp':
            self.controller.trigger_anchor_up()
            # controller update will put value back to 0 ?
            return False

        if path == '/Triggers/MuteAlarm':
            self.controller.trigger_mute_alarm()
            # controller update will put value back to 0 ? setTimeout 0 ? setTimeout 1000 ?
            return False



    