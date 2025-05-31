# dbus-anchor-alarm

A comprehensive boat anchor watch alarm for Victron Cerbo, with deep integration via D-Bus, NMEA 2000, digital inputs, relays, and more.

**dbus-anchor-alarm** runs as a Python service for Victron Cerbo GX running Venus OS.  
It monitors your anchor position, integrates with NMEA 2000 and Cerbo’s digital inputs/relays, provides alarms and notifications, and is highly configurable.

---

## Features

- Native Python service for Victron Cerbo
- Supports:
  - Anchoring mode and mooring ball mode
  - Digital inputs (anchor up/down, set radius, mute alarm, mooring ball mode)
  - Cerbo relays for buzzers/alarms
  - Alarm/notification on Cerbo GX
  - Feedback on Cerbo’s main screen (using system name)
  - NMEA 2000 digital switching triggers and feedback
  - Engine RPM and Speed Over Ground PGN for auto safe radius
  - YachtDevice YDAB-01 NMEA Alarm Button support
  - MQTT and Node-RED via D-Bus
  - Settings management via MQTT, dbus-spy, or Node-RED
  - Out-of-radius, no-GPS, muting, and radius tolerance adjustment

---



![Cerbo Main screen](/doc/main-combined.png)


---

> **Disclaimer:**  
> This anchor alarm is provided as an aid for monitoring your boat's position, but it is **not** a substitute for proper seamanship or safe mooring practices. **Never rely solely on this alarm for the safety of your vessel, crew, or others.** The authors and contributors of this project cannot be held responsible for any loss, damage, or injury resulting from the use of this software. Always use multiple means to ensure your vessel is safely moored.

---

## Table of Contents

- [Overview](#dbus-anchor-alarm)
- [Features](#features)
- [Anchoring Mode](#anchoring-mode)
- [Mooring Mode](#mooring-mode)
- [Hardware Setup](#hardware-setup)
  - [Typical Hardware Setup](#typical-hardware-setup)
  - [Extended Hardware Setup](#extended-hardware-setup)
  - [Minimal Hardware Setup](#minimal-hardware-setup)
- [Installation](#installation)
  - [Manual Installation](#manual-installation)
  - [Automatic Installation](#automatic-installation)
- [Configuration](#configuration)
  - [How to Change Configuration Values](#how-to-change-configuration-values)
  - [General Anchor Alarm Parameters](#general-anchor-alarm-parameters)
- [Anchor Alarm Connectors](#anchor-alarm-connectors)
  - [NMEA 2000 & Digital Switching](#nmea-2000--digital-switching)
  - [Digital Inputs (Windlass, Buttons, etc.)](#digital-inputs-windlass-buttons-etc)
  - [Engine Gateway / NMEA SOG+RPM](#engine-gateway--nmea-sogrpm)
  - [YachtDevice YDAB-01 Alarm Button](#yachtdevice-ydab-01-alarm-button)
  - [Cerbo GX Integrated Relays](#cerbo-gx-integrated-relays)
- [Technical Details](#technical-details)
  - [Overview](#technical-overview)
  - [GPS](#gps)
  - [DBUS Paths](#dbus-paths)
- [Garmin GPSMAP 1243 Digital Switching integration](#garmin-gpsmap-1243-digital-switching-integration)
  - [Setting up Digital Switches](#setting-up-digital-switches)
  - [Setting up Anchoring Screen](#setting-up-anchoring-screen)
- [License](#license)

---

## Anchoring Mode

**Anchoring Mode** is the standard mode of the anchor alarm. The system watches your position relative to the saved anchor drop point and triggers alarms if you drift outside the safe radius.

### How to Use Anchoring Mode

1. **Anchor Drop:**  
   - Trigger the anchor drop event automatically by wiring windlass DOWN solenoid to a digital input, use a physical button, or a virtual NMEA digital switching button.
   - The system saves the current GPS position as the anchor point.

2. **Chain Out (Set Safe Radius):**  
   - Let out your anchor chain and attach bridle. Inform the system either automatically (using engine RPM/SOG via NMEA), via a button, or another digital switching trigger.
   - The system calculates and sets the safe radius and starts monitoring.

3. **Alarm Monitoring:**  
   - While active, the system continuously monitors GPS.
   - If the vessel moves outside the safe radius plus any configured tolerance or if GPS is lost for more than 30 seconds, it can :
     - Send emergency feedback to the NMEA network
     - Activate configured Cerbo relay(s)
     - Trigger a YDAB-01 alarm if present
     - Display a notification/alarm on Cerbo
   - If the boat returns to the safe radius, the alarm is **not** cleared automatically; it must be reset by the user.

4. **Alarm Muting:**  
   - While in an alarm state, it can be muted for 30 seconds by:
     - Acknowledging on the Cerbo screen
     - Acknowledging the emergency NMEA message on a chartplotter
     - Pressing the YDAB-01 button
     - Activating the designated Cerbo digital input

5. **Tolerance Adjustment:**  
   - You can increase or decrease the radius tolerance via digital switching or settings; the new value is taken into account immediately. If with the new tolerance, the boat is back in safe radius, the alarm will be cleared.
   - When the dragging alarm is active, you can also set a new safe radius as per step 2.

6. **Anchor Up (Disarm Alarm):**  
   - When raising the anchor, trigger the anchor up event using the windlass UP solenoid wired to a didital input, a button, or digital switching. This disables the anchor alarm.



---

## Mooring Mode

**Mooring Mode** is a special operating mode for situations where the boat is attached to a fixed object such as a mooring ball or buoy, rather than anchored. It monitors your position relative to the mooring point and triggers an alarm if you move outside the defined radius.

### How to Use Mooring Mode

1. **Activation:**  
   - Trigger the "Mooring Mode" event using:
     - A physical button wired to a digital input configured for Mooring Mode
     - A virtual Digital Switching button on your chartplotter
     - Programmatically via D-Bus or MQTT

2. **Setting the Mooring Point:**  
   - When Mooring Mode is activated, the system saves the current GPS position as the mooring location.
   - The anchor alarm arms and uses the radius defined by `Settings/AnchorAlarm/MooringRadius` (default: 15 meters).

3. **Monitoring:**  
   - The alarm system monitors your position relative to the mooring point.
   - If the vessel moves outside the mooring radius plus any configured tolerance, an alarm is triggered just as with the anchor alarm.
   - Alarm feedback and muting work identically to Anchoring Mode.

4. **Disarming Mooring Mode:**  
   - To exit mooring mode and disarm the alarm, trigger the "Anchor Up" event (e.g., by raising the anchor or pressing the corresponding button).

**Typical Use Cases:**
- When picking up a mooring ball instead of anchoring
- When tying to a fixed buoy or dock and you want to monitor for unexpected movement

---

## Hardware Setup

### Typical Hardware Setup

- **Cerbo to NMEA 2000:**  
  Use Victron VE.Can to NMEA 2000 micro-C male cable  
  ([see Victron docs](https://www.victronenergy.com/cables/ve-can-to-nmea2000-micro-c-male))
- **Windlass Solenoids:**  
  Connect via relays to Cerbo digital inputs for anchor down (saving anchor GPS position) and anchor up (disabling anchor alarm).
- **Cerbo Integrated Relay:**  
  Can be connected to a buzzer.

### Extended Hardware Setup

- **Engines on NMEA 2000:**  
  Use YachtDevice YDAB-04 or similar. Allows auto arm/disarm based on engine RPM/SOG.
- **YachtDevice YDAB-01:**  
  For instant alarm feedback and mute control.

### Minimal Hardware Setup

- Only requires a constant GPS source (USB dongle or NMEA or any supported GPS source).  
  Can be controlled via MQTT, D-Bus, or Node-RED.

---

## Installation

### Manual Installation

1. **Enable SSH on Cerbo:**  
   [Enable root access](https://www.victronenergy.com/live/ccgx:root_access)
2. **Clone repository and edit `deploy.sh`** for your Cerbo’s IP.
3. **Make `deploy.sh` executable and run:**
   ```bash
   chmod u+x deploy.sh
   ./deploy.sh
   ```
   - This creates a VERSION file and rsyncs the folder to Cerbo’s `/data/dbus-anchor-alarm`.
4. **SSH into Cerbo and run setup:**
   ```bash
   ssh root@<your_cerbo_ip>
   cd /data/dbus-anchor-alarm
   chmod u+x setup.sh
   ./setup.sh
   ```
   - Ensures all files are executable
   - Creates symlinks for service and dependencies
   - Updates `/data/rc.local` for persistence
5. **Start the service:**
   ```bash
   cd /opt/victronenergy/services
   svc -u dbus-anchor-alarm
   ```
   - Stop: `svc -d dbus-anchor-alarm`

### Automatic Installation

_Not implemented yet. Planned: InstallHelper or wget one-liner._

---

## Configuration

### How to Change Configuration Values

- **No Cerbo GX UI:**  
  Use SSH and [dbus-spy](https://github.com/victronenergy/dbus-spy), Node-RED or MQTT.
- **dbus-spy:**  
  After SSH-ing into your Cerbo and starting `dbus-spy`, make sure to navigate to the **`com.victronenergy.settings`** section.  
  All `dbus-anchor-alarm` settings are located under this section, typically at paths like `/Settings/AnchorAlarm/XXX`.  
  This is where you can view and modify every configuration parameter relevant to the anchor alarm.
- **Node-RED:**  
  Use Victron Custom Control Node with `com.victronenergy.settings` and `/Settings/AnchorAlarm/XXX`.

- **MQTT:**
  Connect to the DBUS using MQTT by enabling MQTT in the Cerbo settings and connecting to it usint MQTT Explorer or equivalent and connect on port 1883. Do not forget to publish R/<your cerbo id>/keepalive to get notified of values.

![dbus-spy](/doc/dbus-spy.png)
![Node red](/doc/node-red.png)
![MQTT](/doc/mqtt.png)

---

### General Anchor Alarm Parameters

| Parameter | Default | Description |
|---|---|---|
| Settings/AnchorAlarm/FeedbackUseSystemName | 0 | Override Cerbo GX system name for feedback |
| Settings/AnchorAlarm/Last/Active | 0 | Is the anchor alarm active? Used to re-arm after reboot |
| Settings/AnchorAlarm/Last/Position/Latitude | 0 | Last anchor latitude (for reboot re-arm) |
| Settings/AnchorAlarm/Last/Position/Longitude | 0 | Last anchor longitude |
| Settings/AnchorAlarm/Last/Radius | 0 | Last safe radius |
| Settings/AnchorAlarm/MooringRadius | 15 | Default radius for mooring ball mode (meters) |
| Settings/AnchorAlarm/MuteDuration | 30 | Mute time (seconds) |
| Settings/AnchorAlarm/NoGPSCountThreshold | 30 | Time without GPS before alarm (seconds) |
| Settings/AnchorAlarm/RadiusTolerance | 15 | Tolerance added to safe radius (meters) |

---

## Anchor Alarm Connectors

### NMEA 2000 & Digital Switching

**Description:**  
Integrates with the NMEA 2000 backbone for anchor alarm triggers, feedback, and digital switching events. Enables chartplotter control, feedback, and allows for use with digital switching-capable devices.

**Wiring:**  
Connect the Cerbo to the NMEA 2000 backbone using the Victron VE.Can to NMEA 2000 micro-C male cable.  
You may need an additional T-connector if your NMEA backbone does not have a free slot.

**Configuration Parameters:**

| Parameter | Default | Description |
|---|---|---|
| Settings/AnchorAlarm/NMEA/Alert/AutoAcknowledgeInterval | 15 | Duration before "info" NMEA feedback auto-acknowledges (seconds) |
| Settings/AnchorAlarm/NMEA/DigitalSwitching/DSBank | 221 | Digital Switching Bank used for anchor alarm switches |
| Settings/AnchorAlarm/NMEA/DigitalSwitching/AdvertiseInterval | 5 | Interval between NMEA switch status broadcasts (seconds) |
| Settings/AnchorAlarm/NMEA/DigitalSwitching/AnchorDownChannel | 1 | Channel for Anchor Down event |
| Settings/AnchorAlarm/NMEA/DigitalSwitching/AnchorChainOutChannel | 2 | Channel for Chain Out event |
| Settings/AnchorAlarm/NMEA/DigitalSwitching/AnchorUpChannel | 3 | Channel for Anchor Up event |
| Settings/AnchorAlarm/NMEA/DigitalSwitching/MuteAlarmChannel | 4 | Channel for MuteAlarm event |
| Settings/AnchorAlarm/NMEA/DigitalSwitching/MooringModeChannel | 5 | Channel for Mooring Mode event |
| Settings/AnchorAlarm/NMEA/DigitalSwitching/DecreaseToleranceChannel | 6 | Channel for decreasing tolerance by 5m |
| Settings/AnchorAlarm/NMEA/DigitalSwitching/IncreaseToleranceChannel | 7 | Channel for increasing tolerance by 5m |
| Settings/AnchorAlarm/NMEA/DigitalSwitching/DisabledFeedbackChannel | 11 | Feedback channel: disabled state (no input) |
| Settings/AnchorAlarm/NMEA/DigitalSwitching/DropPointSetFeedbackChannel | 12 | Feedback channel: drop point set (no input) |
| Settings/AnchorAlarm/NMEA/DigitalSwitching/InRadiusFeedbackChannel | 13 | Feedback channel: in radius (no input) |
| Settings/AnchorAlarm/NMEA/DigitalSwitching/AlarmDraggingFeedbackChannel | 14 | Feedback channel: alarm dragging (no input) |
| Settings/AnchorAlarm/NMEA/DigitalSwitching/AlarmDraggingMutedFeedbackChannel | 15 | Feedback channel: alarm dragging muted (no input) |
| Settings/AnchorAlarm/NMEA/DigitalSwitching/AlarmNoGPSFeedbackChannel | 16 | Feedback channel: alarm no GPS (no input) |
| Settings/AnchorAlarm/NMEA/DigitalSwitching/AlarmNoGPSMutedFeedbackChannel | 17 | Feedback channel: alarm no GPS muted (no input) |


---

### Digital Inputs (Windlass, Buttons, etc.)

**Description:**  
Allows connection of windlass solenoids or physical buttons to Cerbo digital inputs for controlling anchor up/down, chain out, mooring mode, or muting the alarm.

**Wiring:**  
- Use 2 DC relays between the windlass' solenoid UP and DOWN inputs (remote, foot switches, etc.) and 2 Cerbo digital inputs.
- Use DIN rail or Bosch car relay ([Bosch Mini Relay](https://www.amazon.com/Bosch-0332019150-Mini-Relay/dp/B004Z0W1LM)).
- Ensure relay coil voltage matches windlass control (12V/24V).
- **Relay Wiring:**  
  - Connect pins 85/86 in parallel to windlass solenoid input side.
  - Connect pins 30/87 to Cerbo digital input.  
    (Before connecting, verify relay operation and ensure **NO POWER** goes to pins 30/87.)

**TODO:** Add wiring diagram


**Configuration Parameters:**

| Parameter | Default | Description |
|---|---|---|
| Settings/AnchorAlarm/DigitalInputs/AnchorDown/DigitalInputNumber | 2 | Digital input number for Anchor Down event (0=disable) |
| Settings/AnchorAlarm/DigitalInputs/AnchorDown/DigitalInputDuration | 3 | Min duration for Anchor Down event (seconds) |
| Settings/AnchorAlarm/DigitalInputs/AnchorUp/DigitalInputNumber | 1 | Digital input number for Anchor Up event (0=disable) |
| Settings/AnchorAlarm/DigitalInputs/AnchorUp/DigitalInputDuration | 3 | Min duration for Anchor Up event (seconds) |
| Settings/AnchorAlarm/DigitalInputs/ChainOut/DigitalInputNumber | 0 | Digital input number for Chain Out event (0=disable) |
| Settings/AnchorAlarm/DigitalInputs/ChainOut/DigitalInputDuration | 0 | Min duration for Chain Out event (seconds) |
| Settings/AnchorAlarm/DigitalInputs/MooringMode/DigitalInputNumber | 0 | Digital input number for Mooring Mode event (0=disable) |
| Settings/AnchorAlarm/DigitalInputs/MooringMode/DigitalInputDuration | 0 | Min duration for Mooring Mode event (seconds) |
| Settings/AnchorAlarm/DigitalInputs/MuteAlarm/DigitalInputNumber | 0 | Digital input number for MuteAlarm event (0=disable) |
| Settings/AnchorAlarm/DigitalInputs/MuteAlarm/DigitalInputDuration | 0 | Min duration for MuteAlarm event (seconds) |

**Typical setup:**  
- Digital Input 1: Anchor UP  
- Digital Input 2: Anchor DOWN (default input time: 3s)

Each event can have a minimal digital input duration to avoid accidental triggers.

---

### Engine Gateway / NMEA SOG+RPM

**Description:**  
Supports auto-arm of the anchor alarm based on engine RPM and Speed Over Ground via the NMEA 2000 network (e.g., with YachtDevice YDAB-04 engine gateway).

**Wiring:**  
- Use a YachtDevice YDAB-04 or other NMEA 2000 compatible engine gateway that provides RPM PGN (127488).
- Make sure to order the gateway with the correct adapter for your engine brand/model.
- For Yanmar engines (and maybe others), the YDAB-04 can be connected on a usually free debug connector on the engine side.  However, it might be more pratical in your situration to have the YDAB-04 engine gateway near the engine control panels and NMEA backbone and might need to use a Yanmar Y splitter harness cable on the control panel side.


**Configuration Parameters:**

| Parameter | Default | Description |
|---|---|---|
| Settings/AnchorAlarm/NMEA/SOGRPM/Duration | 3 | Duration (seconds) for RPM/SOG condition before ChainOut event triggers |
| Settings/AnchorAlarm/NMEA/SOGRPM/NumberOfEngines | 2 | Number of engines to monitor |
| Settings/AnchorAlarm/NMEA/SOGRPM/RPM | 2 | Minimum RPM for ChainOut event |
| Settings/AnchorAlarm/NMEA/SOGRPM/SOG | 0.3 | Maximum SOG (knots) for ChainOut event (default 0.3) |

---

### YachtDevice YDAB-01 Alarm Button

**Description:**  
Provides visual/audible feedback and mute control for the anchor alarm via a dedicated NMEA 2000 device.

**Wiring:**  
- Connect the YDAB-01 to the NMEA 2000 backbone using a T connector.
- Add small loudspeakers as needed ([example](https://www.amazon.com/Gikfun-Speaker-Stereo-Loudspeaker-Arduino/dp/B01CHYIU26)).

**Feedback states:**  
- DISABLED: LED off, no sound
- DROP_POINT_SET: LED blinking, no sound
- IN_RADIUS: LED slow glow
- ALARM_DRAGGING: LED fast blink, alarm sound
- ALARM_DRAGGING_MUTED: LED fast blink, no sound
- ALARM_NO_GPS: LED fast blink, alarm sound
- ALARM_NO_GPS_MUTED: LED fast blink, no sound

**Configuration Parameters:**

| Parameter | Default | Description |
|---|---|---|
| Settings/AnchorAlarm/NMEA/YDAB/AlarmSoundID | 15 | Sound ID for alarm state |
| Settings/AnchorAlarm/NMEA/YDAB/AlarmVolume | 100 | Alarm volume (0-100) |
| Settings/AnchorAlarm/NMEA/YDAB/DSDropPointSetChannel | 10 | Digital Switching channel: Drop Point Set |
| Settings/AnchorAlarm/NMEA/YDAB/DSAlarmChannel | 11 | Digital Switching channel: Alarm |
| Settings/AnchorAlarm/NMEA/YDAB/DSAlarmMutedChannel | 12 | Digital Switching channel: Alarm Muted |
| Settings/AnchorAlarm/NMEA/YDAB/DSBank | 222 | Digital Switching Bank number |
| Settings/AnchorAlarm/NMEA/YDAB/NMEAAddress | 0 | NMEA Address of the YDAB-01 (0=disable) |
| Settings/AnchorAlarm/NMEA/YDAB/StartConfiguration | 0 | Write 1 to start YDAB-01 configuration |

Note : To start configuration of the YDAB-01 device, write 1 in Settings/AnchorAlarm/NMEA/YDAB/StartConfiguration using `dbus-spy`, Nore-Red or MQTT.  If it succeeds, it will play a cheerful chime. If not, an error will be reported on chartplotter and the Cerbo notification system.

---

### Cerbo GX Integrated Relays

**Description:**  
Allows the anchor alarm to drive a physical relay for a buzzer, alarm, or external load.

**Wiring:**  
- Use the Cerbo integrated relay output.
- For high load applications, use an intermediate relay as described in Cerbo documentation.

**Configuration Parameters:**

| Parameter | Default | Description |
|---|---|---|
| Settings/AnchorAlarm/Relay/Enabled | 0 | Is relay output enabled? |
| Settings/AnchorAlarm/Relay/Inverted | 0 | Inverted logic (NC instead of NO)? |
| Settings/AnchorAlarm/Relay/Number | 1 | Relay number (avoid 0: used by Victron for generator and other standard applications) |

---

## Technical Details

### Code Overview

- `anchor_alarm_model.py`: State machine
- `anchor_alarm_controller.py`: Connects state machine to hardware/NMEA/DBUS
- `anchor_alarm_service.py`: Main entry point
- `gps_provider.py`: Monitors GPS from D-Bus
- `nmea_bridge.py`: Node.js bridge for NMEA

### GPS

- The GPS position is fetched by monitoring the com.victronenergy.gps dbus service. 
- The Victron Cerbo is responsible of creating and populating this service from NMEA 2000 source, physically connected GPS USB device, ... 
- Once one of the GPS service instance will get a GPS fix, the anchor alarm will use this service. If there's not GPS position available for more than 30 seconds, the anchor alarm will trigger an alarm.

### DBUS Paths

- Alarm state and triggers available via D-Bus and MQTT.
- Use `dbus-spy` or MQTT for integration.

| Path                    | Description                                    |
|-------------------------|------------------------------------------------|
| Alarm                   | 0/1, in alarm state                            |
| Connected               | 1, mandatory path                              |
| DeviceInstance, FirmwareVersion, HardwareVersion, ProductId, ProductName | Victron mandatory paths |
| Level                   | info, warning, error, emergency                |
| Message                 | Current feedback text, updated every second    |
| Mgmt/Connection, Mgmt/ProcessName, Mgmt/ProcessVersion | Management info |
| Muted                   | 0/1, alarm muted state                         |
| Params                  | JSON string with all context                   |
| State                   | DISABLED, DROP_POINT_SET, IN_RADIUS, etc.      |
| Triggers/AnchorDown     | Write 1 to trigger event                       |
| Triggers/ChainOut       | Write 1 to trigger event                       |
| Triggers/AnchorUp       | Write 1 to trigger event                       |
| Triggers/DecreaseTolerance     | Write 1 to trigger event                |
| Triggers/IncreaseTolerance     | Write 1 to trigger event                |
| Triggers/MooringMode    | Write 1 to trigger event                       |
| Triggers/MuteAlarm      | Write 1 to trigger event                       |

> **Note:**  
> `dbus-spy` cannot write 1 multiple times to Triggers/*. Instead, use:
> ```
> dbus -y com.victronenergy.anchoralarm /Triggers/AnchorDown SetValue %1
> ```

---

# Garmin GPSMAP 1243 Digital Switching integration

## Setting up Digital Switches

On a Garmin GPSMAP 1243, to configure Digital Switching go to "Vessel" then "Switching", then "Setup".

![garmin-step-1](/doc/garmin-switching.png)

![garmin-step-2](/doc/garmin-switch-setup.png)

`dbus-anchor-alarm` switches will labeled `"Switch <bank id>*28+<channel>"` (e.g., Anchor Down: `Switch 6189`).

Use the "Configuration Switch" button to rename all appropriate buttons. The 7 first switches will be input buttons. The following will be status buttons to show the current state of the alarm. Refer to [NMEA 2000 & Digital Switching](#nmea-2000--digital-switching).


## Setting up Anchoring Screen

Once the switches names are configured, you can regroup the ones you would use the most in a Page.
Under SmartMode, create a new Layout, select 2 columns layout : 
 - Left column could be charts or camera, as big as possible
 - Right column would be switching page, as small as possbile. Select the page with your Anchor alarm control buttons
 - Overlay could be "Top" with SOG and Depth, on the left side to not be hidden by NMEA Alerts


![garmin-step-3](/doc/garmin-layout.png)



---

## License

MIT

---

