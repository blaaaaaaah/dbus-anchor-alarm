dbus-anchor-alarm is a boat anchor watch alarm that runs as a native python service on Victron's Cerbo.

It supports :
 - Cerbo's digital input for various triggers : anchor up, anchor down, set radius, mute alarm, mooring ball mode
 - Cerbo's relays for triggering external buzzer or alarm
 - Cerbo's Alarm/Notification system through specified Digital Input
 - Anchor alarm feedback on Cerbo's main screen using Cerbo's system name
 - NMEA for Digital switching triggers, feedback on chart plotters, engines RPM and Speed Over Ground PGN for automatic safe radius definition
 - Yacht Device YDAB-01 NMEA Alarm Button
 - Cerbo's DBUS for integration through MQTT or Node-red
 - Cerbo's settings service for configuration through MQTT, dbus-spy or node-red
 - Out of radius alarm, no gps alarm, muting the alarm, increasing and decreasing the radius tolerance


![Cerbo Main screen](/doc/cerbo-main-screen.png)
![Cerbo Main with Alarm](/doc/cerbo-main-screen-dragging.png)
![Cerbo Notification](/doc/cerbo-alarm-notification.png)


# Usage

Controlling the anchor alarm will depend on your hardware setup, but the steps are the same :
- By default, state will be `DISABLED`.
- **Drop your anchor** and tell the system by wiring your windlass DOWN solenoid contactor to the Cerbo, a button, or using a virtual Digital Switching button on your chart plotter. Anchor alarm will fetch GPS position and go to `DROP_POINT_SET` state and emit a feedback message on the NMEA network.
- **Let your chain out**, attach the bridle and tell the system by having your engines on the NMEA network (3 seconds at 1700 RPM with Speed over ground of 0), using a physical button wired to a digital input or a virtual digital switching button on your chart plotter. Anchor alarm will fetch current GPS position, calculate safe radius and go to `IN_RADIUS` state, emit a feedback message on the NMEA network.
- **When raising anchor**, tell the system by wiring your windlass UP solenoid contactor to the Cerbo, a button, or using a virtual Digital Switching button on your chart plotter. Anchor alarm will go to `DISABLED` state and emit a feedback message on the NMEA network.

When active, the anchor alarm will monitor the GPS position every second. If the position is outside the safe radius + a default 15 meters tolerance, it will go to `ALARM_DRAGGING` state and :
 - emit a Emergency feedback on the NMEA network
 - open the Cerbo's relay if configured in settings
 - trigger a YachtDevice YDAB-01 alarm if present
 - trigger a Cerbo alarm/notification if configured
 
 The same will happen if there's no GPS position for more than 30 secs (going to `ALARM_NO_GPS` state).

 If, for some reason, the boat is going back to safe radius, the alarm will **NOT** be cleared.

 When an alarm is active, the alarm can be muted for 30 seconds by :
 - acknowledging the alarm on the Cerbo's screen
 - acknowleding the Emergency NMEA message displayed on the chartplotter,
 - pressing the YDAB-01 button
 - activating the appropriate Cerbo's digital input
 
The state of the alarm will go to `ALARM_DRAGGING_MUTED` or `ALARM_NO_GPS_MUTED` accordingly.

When the dragging alarm is active (whether it's muted or not) the tolerance can be increased (either by Digital Switching, changing settings, ..) and the anchor alarm will take this new parameter into account. If with the new tolerance, the boat is back in safe radius, the state will go back to `IN_RADIUS` and the alarm will be canceled


The alarm can also be cleared by raising the anchor and disabling the anchor alarm.




# Setup

## Typical hardware setup :

The typical setup requires the Cerbo to be connected to the NMEA 2000 network using the Victron VE.Can to NMEA 2000 micro-C male cable (https://www.victronenergy.com/cables/ve-can-to-nmea2000-micro-c-male) and having a constant GPS source on the NMEA network (like dedicated NMEA2000 GPS device). 

Having the Cerbo connected to the NMEA 2000 network will also allow feedback on the chartplotter as well as NMEA Digital Switching support for controlling the anchor alarm.

The windlass solenoid can be connected using intermediate relays to the Cerbo's digital inputs for anchor down (saving anchor GPS position when dropping) and anchor up (disabling anchor alarm). Setting the safe anchor radius could be done with the chartplotter's digital switching capability.

The Cerbo's integrated relay can be connected to a buzzer.


## Extended hardware setup :

The engines can be connected to the NMEA 2000 network (using for example YachtDevice YDAB-04 dongle) so that the anchor alarm can deduct the safe radius automatically if the Speed Over Ground is 0, engines' RPM is > 1700 for more than 3 seconds

A YachtDevice YDAB-01 Alarm button can be added to the NMEA 2000 network to support visual feedback, alarm sound and mute alarm button


## Minimal hardware setup :

The anchor alarm only really needs a constant GPS source. It can be provided by a compatible GPS USB dongle connected direclty to the Cerbo or custom hardware running Venus OS. It can be controlled by Digital inputs using buttons and alarm feedback triggered by the Cerbo's relay.


# Installation

## Manual installation

1. Enable SSH on your Cerbo (https://www.victronenergy.com/live/ccgx:root_access)

2. Clone this repository.
Edit `deploy.sh` to match your Cerbo's IP address. It must be reacheable from your computer
Make `deploy.sh` executable
Run `./deploy.sh` (it will create a VERSION file containing the current git revision and rsync the content of the folder to the Cerbo's `/data/dbus-anchor-alarm` folder)

```
chmod u+z deploy.sh
./deploy.sh
```

3. SSH into your Cerbo, go to `/data/dbus-anchor-alarm`, make sure `setup.sh` is executable and run it
```
ssh root@<your cerbo ip>
cd /data/dbus-anchor-alarm
chmod u+x setup.sh
./setup.sh
```

`setup.sh` will : 
- make sure that all required files are executable, 
- create a symbolic link in `/opt/victronenergy/service/dbus-anchor-alarm` for service installation
- create a symbolic link to `/usr/lib/node_modules/signalk-server/node_modules/` for CanBoatJS dependency
- create or update a `rc.local` file in `/data/` containing those 2 symlinks to survive firmware upgrades

4. Start the service by either rebooting the device (and making sure the service starts on startup, re-arming the anchor alarm if needed) or by running :
`cd /opt/victronenergy/services`
`svc -u dbus-anchor-alarm`

(stop the service by running `svc -d dbus-anchor-alarm`)


## Automatic installation

Not yet implemented. Target is to use InstallHelper and/or a one-liner wget bash command




# General configuration


## How to change configuration values


There is no dedicated user interface on the Cerbo GX for changing settings. The easier is to ssh into the Cerbo GX and run `dbus-spy` (https://github.com/victronenergy/dbus-spy) that is installed by default on the Cerbo and navigate to the `com.victronenergy.settings` service.

![dbus-spy](/doc/dbus-spy.png)


You can also use Node Red (https://www.victronenergy.com/live/venus-os:large) with a Victron Custom Control Node.
Use the `com.victronenergy.settings` as `Custom` field and the appropriate `/Settings/AnchorAlarm/XXX` as `Measurement`

![Node red](/doc/node-red.png)


## Configuration


| Configuration parameter | Default Value | Description |
| ----------------------- | ------------- | ----------- |
| Settings/AnchorAlarm/FeedbackUseSystemName  | 0 | Should the anchor alarm override the System Name to display feedback on the Cerbo's GX main screen instead of boat name |
| Settings/AnchorAlarm/Last/Active  | 0 | Is the  anchor alarm active ? Used when the system reboots to re-arm anchor alarm if needed |
| Settings/AnchorAlarm/Last/Position/Latitude  | 0 | Last anchor latitude. Used when the system reboots to re-arm anchor alarm if needed |
| Settings/AnchorAlarm/Last/Position/Longitude  | 0 | Last anchor longitude. Used when the system reboots to re-arm anchor alarm if needed |
| Settings/AnchorAlarm/Last/Radius  | 0 | Last alarm safe radius. Used when the system reboots to re-arm anchor alarm if needed |
| Settings/AnchorAlarm/MooringRadius  | 15 | Default safe radius used when enabling Mooring ball mode |
| Settings/AnchorAlarm/MuteDuration  | 30 | Mute duration used when muting alarm |
| Settings/AnchorAlarm/NoGPSCountThreshold  | 30 | Acceptable time without GPS before triggering NO_GPS alarm |
| Settings/AnchorAlarm/RadiusTolerance  | 15 | Acceptable radius tolerance when anchor alarm is enabled. It will add this number in meters to the saved safe radius to check the boat is in the safe area or is dragging |


Note: Settings/AnchorAlarm/Last/XXX can be modified by user integration, anchor alarm will monitor the "Active" settings. Setting it to 0 will disable the anchor alarm, setting it to 1 will reset the anchor alarm state with the Settings/AnchorAlarm/Last/XXX parameters




# Anchor Alarm connectors


## NMEA 2000 

NMEA 2000 connectivity will allow the anchor alarm to emit NMEA Alerts for feedback (info and alarms) (PGN 126983, 126984 126985), get GPS position (in most cases), be controlled and give feedback through Digital Switching from chart plotter (PGN 127501, 127502), read engines RPM and Speed Over Ground (SOG) for automatic radius calculation (PGN 129026, 127488).

### Wiring

Use the Victron VE.Can to NMEA 2000 micro-C male cable (https://www.victronenergy.com/cables/ve-can-to-nmea2000-micro-c-male) to connect your Cerbo to the NMEA2000 backbone. You might need an additional NMEA T connector.

### Configuration

| Configuration parameter | Default Value | Description |
| ----------------------- | ------------- | ----------- |
| Settings/AnchorAlarm/NMEA/Alert/AutoAcknowledgeInterval  | 15 | Default duration before an "info" NMEA feedback message is automatically acknowledged |
| Settings/AnchorAlarm/NMEA/DigitalSwitching/DSBank  | 221 | Digital Switching Bank used to advertise anchor alarm switches. |
| Settings/AnchorAlarm/NMEA/DigitalSwitching/AdvertiseInterval  | 5 | Default interval in seconds between each advertise on the NMEA network of the switches status  |
| Settings/AnchorAlarm/NMEA/DigitalSwitching/AnchorDownChannel  | 1 | Channel used for Anchor Down event |
| Settings/AnchorAlarm/NMEA/DigitalSwitching/AnchorChainOutChannel  | 2 | Channel used for Chain Out event |
| Settings/AnchorAlarm/NMEA/DigitalSwitching/AnchorUpChannel  | 3 | Channel used for Anchor Up event |
| Settings/AnchorAlarm/NMEA/DigitalSwitching/MuteAlarmChannel  | 4 | Channel used for MuteAlarmChannel event |
| Settings/AnchorAlarm/NMEA/DigitalSwitching/MooringModeChannel  | 5 | Channel used for MooringModeChannel event |
| Settings/AnchorAlarm/NMEA/DigitalSwitching/DecreaseToleranceChannel  | 6 | Channel used for Decreasing the tolerance by 5m |
| Settings/AnchorAlarm/NMEA/DigitalSwitching/IncreaseToleranceChannel  | 7 | Channel used for Increasing the tolerance by 5m |
| Settings/AnchorAlarm/NMEA/DigitalSwitching/DisabledFeedbackChannel  | 11 | Feedback channel for disabled state. Won't take any input, only a feedback channel |
| Settings/AnchorAlarm/NMEA/DigitalSwitching/DropPointSetFeedbackChannel  | 12 | Feedback channel for drop point set state. Won't take any input, only a feedback channel |
| Settings/AnchorAlarm/NMEA/DigitalSwitching/InRadiusFeedbackChannel  | 13 | Feedback channel for in radius state. Won't take any input, only a feedback channel |
| Settings/AnchorAlarm/NMEA/DigitalSwitching/AlarmDraggingFeedbackChannel  | 14 | Feedback channel for alarm dragging state. Won't take any input, only a feedback channel |
| Settings/AnchorAlarm/NMEA/DigitalSwitching/AlarmDraggingMutedFeedbackChannel  | 15 | Feedback channel for alarm dragging muted state. Won't take any input, only a feedback channel |
| Settings/AnchorAlarm/NMEA/DigitalSwitching/AlarmNoGPSFeedbackChannel  | 16 | Feedback channel for alarm no gps state. Won't take any input, only a feedback channel |
| Settings/AnchorAlarm/NMEA/DigitalSwitching/AlarmNoGPSMutedFeedbackChannel  | 17 | Feedback channel for alarm no gps muted state. Won't take any input, only a feedback channel |


### Configuring Digital Switching on Garmin Chartplotter

Those are the steps to configure the Digital Switching on a Garmin GPSMap chartplotter, but steps should be fairly similar.

On Garmin chartplotters, the switches will have a default name of "Switch <bank id>*28+<channel>", so the anchor down switch will be called "Switch 6189".

TODO XXX : add screenshots and steps



## Digital inputs

Cerbo's Digital Input can be used to connect the boat's windlass solenoid input or any other physical buttons to control the anchor alarm. A minimum input duration can be specified.

In order to use a Digital Input, you first need enable the digital input on the Cerbo's GX touchscreen in Settings, IO, Digital inputs, Digital input [0-4] and set "Bilge pump". 



### Windlass wiring

Use 2 DC relays between the windlass' solenoid UP and DOWN **INPUTS** (remote, foot switches, ...) and 2 Cerbo's available digital inputs

You can use a DIN rail mounted relay or a simple Bosch car relay (https://www.amazon.com/Bosch-0332019150-Mini-Relay/dp/B004Z0W1LM). 

**/!\\** Make sure to use the appropriate voltage for the relay's coil, some windlasses controls are 24v instead of 12v.

On a typical Bosch relay, connect pins 85 and 86 in **parallel** of the windlass' solenoid input side (where the remote and/or foot switches are connected).

Connect pins 30 and 87 to the digital input of the Cerbo. Before connecting to the Cerbo, make sure the relay is working when activating the windlass and that **NO POWER** is going to pins 30 and 87 since it would **DESTROY** your Cerbo. 

### Configuration

By default, Digital Input number 1 is Anchor UP, Digital Input Number 2 is Anchor DOWN with a default input time of 3 seconds.

The following events can be associated with a digital input : 
- AnchorDown when anchor is dropped, will save the anchor GPS position
- AnchorUp when anchor is raised, will disable anchor alarm
- ChainOut when safe radius must be calculated and anchor alarm armed
- MooringMode when taking a mooring ball. Will save the current GPS position as mooring ball position and arm the anchor alarm with a default 15m radius
- MuteAlarm when alarm must be muted

Each event can have a minimal digital input duration, mainly to prevent a short windlass movement to enable or disable the anchor alarm.

| Configuration parameter | Default Value | Description |
| ----------------------- | ------------- | ----------- |
| Settings/AnchorAlarm/DigitalInputs/AnchorDown/DigitalInputNumber  | 2 | Digital input number associated with Anchor Down event. Use 0 to disable. |
| Settings/AnchorAlarm/DigitalInputs/AnchorDown/DigitalInputDuration | 3 | Minimal duration of the digital input before triggering the Anchor Down event. |
| Settings/AnchorAlarm/DigitalInputs/AnchorUp/DigitalInputNumber  | 1 | Digital input number associated with Anchor Up event. Use 0 to disable. |
| Settings/AnchorAlarm/DigitalInputs/AnchorUp/DigitalInputDuration | 3 | Minimal duration of the digital input before triggering the Anchor Up event. |
| Settings/AnchorAlarm/DigitalInputs/ChainOut/DigitalInputNumber  | 0 | Digital input number associated with Chain Out event. Use 0 to disable. |
| Settings/AnchorAlarm/DigitalInputs/ChainOut/DigitalInputDuration | 0 | Minimal duration of the digital input before triggering the Chain Out event. |
| Settings/AnchorAlarm/DigitalInputs/MooringMode/DigitalInputNumber  | 0 | Digital input number associated with MooringMode event. Use 0 to disable. |
| Settings/AnchorAlarm/DigitalInputs/MooringMode/DigitalInputDuration | 0 | Minimal duration of the digital input before triggering the MooringMode event. |
| Settings/AnchorAlarm/DigitalInputs/MuteAlarm/DigitalInputNumber  | 0 | Digital input number associated with MuteAlarm event. Use 0 to disable. |
| Settings/AnchorAlarm/DigitalInputs/MuteAlarm/DigitalInputDuration | 0 | Minimal duration of the digital input before triggering the MuteAlarm event. |


## Engine gateway 

It will allow the anchor alarm to monitor engine(s) RPM and automatically set the anchor alarm when RPM > 1700 and Speed Over Ground (SOG) is 0 for more than 3 seconds, usually the sign that the anchor is well set, holding and not dragging.

### YachtDevice YDAB-4 gateway wiring 

You can use the Yacht Device YDAB-4 engine gateway (https://www.yachtd.com/products/engine_gateway.html) to advertise your engine date on the NMEA 2000 network.

Make sure to order the gateway with the appropriate adaptor cable that matches your engine brand and model.

In case of Yanmar engines (and maybe others), the YDAB-04 can be connected on a usually free debug connector on the engine side. However, it might be more pratical in your situration to have the YDAB-04 engine gateway near the engine control panels and NMEA backbone and might need to use a Yanmar Y splitter harness cable on the control panel side.

### Configuration

| Configuration parameter | Default Value | Description |
| ----------------------- | ------------- | ----------- |
| Settings/AnchorAlarm/NMEA/SOGRPM/Duration  | 3 | Duration for which the specified conditions need to be met (RPM and SpeedOverGround) before triggering the ChainOut event and arming the anchor alarm |
| Settings/AnchorAlarm/NMEA/SOGRPM/NumberOfEngines  | 2 | Number of engines to be monitored |
| Settings/AnchorAlarm/NMEA/SOGRPM/RPM  | 2 | Minimum RPM value for engine(s) to reach to be able to trigger the ChainOut event |
| Settings/AnchorAlarm/NMEA/SOGRPM/SOG  | 0.3 | Maximum SOG value to be able to trigger the ChainOut event. Default is 0.3 because in windy conditions the boat could slighlty rock from side to side and having a strict 0.0 SOG might be difficult to achieve for multiple seconds |



## YachtDevice YDAB-01 Alarm Button

You can use the YachtDevice YDAB-01 Alarm Button (https://www.yachtd.com/products/alarm_button.html) to provide instantaneous visual feedback of the state of the alarm, having the YDAB play a loud alarm sound when dragging, and a physical button to mute the alarm and reset the radius.

### YDAB-01 wiring

Connect the YDAB-01 to the NMEA backbone (using a NMEA T connector), add any (non provided) small loudspeaker(s) (https://www.amazon.com/Gikfun-Speaker-Stereo-Loudspeaker-Arduino/dp/B01CHYIU26) and wire and install the provided button.

It will allow the anchor alarm to play a loud alarm when needed and show the appropriate visual feedback :
- In DISABLED state, LED will be off and no sound played. Pressing the button will have no effect.
- In DROP_POINT_SET state (after anchor was dropped), LED will be in a blinking state and no sound played. Pressing the button will have no effect.
- In IN_RADIUS state, LED will be glowing slowly.  Pressing the button will have no effect.
- In ALARM_DRAGGING state, LED will be blinking rapidely and an alarm sound will be played. Pressing the button will mute the alarm for 30 secs
- In ALARM_DRAGGING_MUTED state, LED will be blinking rapidely and no alarm sound will be played. Pressing the button will reset the radius and alarm will go to IN_RADIUS state again.
- In ALARM_NO_GPS state, LED will be blinking rapidely and an alarm sound will be played. Pressing the button will mute the alarm for 30 secs.
- In ALARM_NO_GPS_MUTED state, LED will be blinking rapidely and no alarm sound will be played. Pressing the button will have no effect.


### Configuration

| Configuration parameter | Default Value | Description |
| ----------------------- | ------------- | ----------- |
| Settings/AnchorAlarm/NMEA/YDAB/AlarmSoundID  | 15 | Sound ID to use when in Alarm state. |
| Settings/AnchorAlarm/NMEA/YDAB/AlarmVolume  | 100 | Alarm volume to use. 0-100 |
| Settings/AnchorAlarm/NMEA/YDAB/DSDropPointSetChannel  | 10 | Digital Switching channel for Drop point set state to use. Only change if conflicting with existing configuration |
| Settings/AnchorAlarm/NMEA/YDAB/DSAlarmChannel  | 11 | Digital Switching channel for Alarm state to use. Only change if conflicting with existing configuration |
| Settings/AnchorAlarm/NMEA/YDAB/DSAlarmMutedChannel  | 12 | Digital Switching channel for Alarm Muted state to use. Only change if conflicting with existing configuration |
| Settings/AnchorAlarm/NMEA/YDAB/DSBank  | 222 | Digital Switching Bank number to use. Only change if conflicting with existing configuration |
| Settings/AnchorAlarm/NMEA/YDAB/NMEAAddress  | 0 | NMEA Address of the YDAB-01. Use 0 to disable. To find the address, on the Cerbo GX touchscreen, go to Settings, Services, VE.Can port, Devices, YDAB-01, Network Address |
| Settings/AnchorAlarm/NMEA/YDAB/StartConfiguration  | 0 | Write 1 to start the configuration process of the YDAB-01. If it succeeds, it will play a cheerful chime. If not, an error will be reported on chartplotter and a |


## Cerbo GX relays

You can use the Cerbo GX integrated relay to activate a buzzer or load when the alarm goes off.

### Wiring

Depending on the load consumption, you might need to use an intermediate relay. Refer to the Cerbo documentation for more details

### Configuration
| Settings/AnchorAlarm/Relay/Enabled  | 0 | Is the functionnality enabled ? |
| Settings/AnchorAlarm/Relay/Inverted  | 0 | Is the functionnality inverted (NC instead of NO) ? |
| Settings/AnchorAlarm/Relay/Number  | 1 | Number of the relay. The 0 relay is used by victron for generator start/stop etc and shouldn't be used |







# Technical 

## Overview

The anchor alarm is built around anchor_alarm_model.py which is the anchor alarm state machine.
It's controlled by anchor_alarm_controller.py which wires the model to the connectors.
The connectors connects the anchor alarm to the external world : DBUS, NMEA feedback, Digital switching support, ..
anchor_alarm_service.py is the main entry point
gps_provider.py will monitor the Cerbo's DBUS gps path to fetch current GPS position
nmea_bridge.py will launch a Node.JS process that will use CanBoatJS to communicate over the NMEA network


## GPS

The GPS position is fetched by monitoring the com.victronenergy.gps dbus service. The Victron Cerbo is responsible of creating and populating this service from NMEA 2000 source, physically connected GPS USB device, ... Once one of the GPS service instance will get a GPS fix, the anchor alarm will use this service. If there's not GPS position available for more than 30 seconds, the anchor alarm will trigger an alarm.


## DBUS paths

The anchor alarm advertises its state on DBUS. You can retrieve and interact with it using dbus-spy or MQTT.
dbus-spy is a tool installed on the Cerbo to view current DBUS state. SSH into your Cerbo (https://www.victronenergy.com/live/ccgx:root_access) and simply type dbus-spy

| path | Description | 
| ---- | ----------- |
| Alarm | 0 or 1. 1 if currently in Alarm state |
| Connected | 1. Mandatory victron path |
| DeviceInstance | 0. Mandatory victron path |
| FirmwareVersion | 0. Mandatory victron path |
| HardwareVersion | 0. Mandatory victron path |
| Level | info, warning, error, emergency. Regular feedback is info. Alarm dragging feedback is emergency |
| Message | Current text feedback of the anchor alarm state. Updated every second |
| Mgmt/Connection | -. Mandatory victron path |
| Mgmt/ProcessName | /data/dbus-anchor-alarm/anchor_alarm_service.py. Mandatory victron path. Path to the main anchor alarm python file |
| Mgmt/ProcessVersion | Git revision of the current running version |
| Muted | 0 or 1. 1 if currently in Alarm Muted state |
| Params | JSON string containing all anchor alarm context : state, anchor drop point GPS coordinates, radius threshold, current radius, ... |
| ProductId | 0. Mandatory victron path |
| ProductName | Anchor Alarm. Mandatory victron path |
| State | DISABLED, DROP_POINT_SET, IN_RADIUS, ALARM_DRAGGING, ALARM_DRAGGING_MUTED, ALARM_NO_GPS, ALARM_NO_GPS_MUTED. Current state of the anchor alarm |
| Triggers/AnchorDown | Write 1 when in DISABLED state to trigger AnchorDown event that will save current GPS position and change state to DROP_POINT_SET. |
| Triggers/AnchorUp | Write 1 in any state to triggers AnchorUp event that disable anchor alarm and change state to DISABLED |
| Triggers/ChainOut | Write 1 when in DROP_POINT_SET state to trigger ChainOut event that will calculate safe radius and change state to IN_RADIUS. |
| Triggers/DecreaseTolerance | Write 1 to decrease the radius tolerance by 5 meters. Min is 0 |
| Triggers/IncreaseTolerance | Write 1 to increase the radius tolerance by 5 meters. Max is 50 |
| Triggers/MooringMode | Write 1 when in DISABLED state to save current GPS position, set radius to 15m and change state to IN_RADIUS. |
| Triggers/MuteAlarm | Write 1 when in ALARM_DRAGGING or ALARM_NO_GPS state to mute the alarm for 30 seconds and change state to ALARM_DRAGGING_MUTED or ALARM_NO_GPS_MUTED |


Note: A dbus-spy bug will prevent to write 1 multiple times to Triggers/*. 
Use dbus -y com.victronenergy.anchoralarm /Triggers/AnchorDown SetValue %1 instead for testing





