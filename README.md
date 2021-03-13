# VSCP4HASS - VSCP communication for Home Assistant

Please also refer to:  
https://www.vscp.org  
https://www.home-assistant.io

## Introduction
VSCP4HASS connects to a running (u)vscpd instance and uses the TCP interface
to communicate with VSCP nodes.

uvscpd can be found here: https://www.github.com/mzanders/uvscpd

VSCP4HASS uses asyncio interfaces exclusively. It uses an internal VSCP module to
handle the communication protocol. This is not in line with the guidelines for 
HASS integrations (the physical communication should be through a PyPi module).
As this extension is still considered under development, I prefer to keep it 
simple and stash everything together for now. In the future, I'll probably move
to an MQTT interface making the external module obsolete anyway.

VSCP4HASS provides:
- a service (vscp.send_event) to send 'raw' VSCP events from HASS
- a discovery service for 'standardised' VSCP HASS nodes for lights and binary
  sensors
- manual configuration of lights based on zones & subzones

The discovery service searches for all level 1 nodes on a segment with standard
device family code set to 'HASS'. These nodes have a modular & standardised register 
layout.  This allows VSCP4HASS to read the entire configuration from the nodes 
directly and avoids duplicating configuration information in the system.  
This method uses the node GUID and channel index to identify individual entities.

Example implementations of this standard device on CAN nodes can be found here:
https://www.github.com/mzanders/swali

To allow interfacing with existing VSCP networks and non-standardised nodes, 
manual entry of lights is also supported. In this case, the zone and subzone are 
used to control and monitor light entities. (Binary) sensor entities will be added
shortly.

## Installation

Copy, clone or link this folder to `<config_dir>/custom_components/vscp/` for your
HASS instance. Note that when running HASS in a container, soft-links will not work.

Add the following minimal configuration entry in your `configuration.yaml`:

```yaml
vscp:
  host: 127.0.0.1    # IP address of vscpd instance
```

**NOTE that this connection is NOT SECURED and should only be used on
localhost. So run (u)vscpd on the same host has HASS.** 

## Configuration
The full platform configuration is as follows:
```yaml
vscp:
  host: 127.0.0.1
  port: 8598
  username: your_user
  password: your_password
  discovery: false
```
The only required field is the host address. The port is defaulting to the default
(u)vscpd port.  
Username/password is also optional as uvscpd can be configured without. If the option
is not provided, the USER and PASSWORD TCP commands are not sent after connecting to
the server.  

Set discovery to 'true' if you want HASS to scan for standardised nodes on the segment.
It defaults to 'false'.

For manually entering lights in your `configuration.yaml` file, use:

```yaml
light:
  - platform: vscp
    entities:
      - name: red
        zone: 1
        subzone: 1
      - name: green
        zone: 1
        subzone: 2
        brightness: true
```
Duplicate entries for zone/subzone combinations are not allowed.
The brightness entry defaults to false. If true, it allows brightness control for that light.

Configuration entries are validated using voluptuous schema's, so you should
get a sensible error message when there's an error. (Although not for the duplicates
mentioned above...)

For adding debug information to the logs, add this to `configuration.yaml`:
```yaml
logger:
  default: warning
  logs:
    custom_components.vscp: debug
```


## Manual entity configuration
### Lights
These VSCP events are sent or processed for manually configured lights:
- **CLASS1.CONTROL, 0x1E - Type=0x05: TurnOn**  
  Sent from HASS to the zone/subzone to turn on.  
  Data byte 0 set to 0.

- **CLASS1.CONTROL, 0x1E - Type=0x07: TurnOff**  
  Sent from HASS to the zone/subzone to turn off.  
  Data byte 0 set to 0.
  
- **CLASS1.CONTROL, 0x1E - Type=0x16: Change level**    
  Sent from HASS to the zone/subzone to set dimmer value (0-255) when brightness control is enabled.
  *Note: this is used as opposed to the command "Dim lamp(s)"*
  
- **CLASS1.INFORMATION, 0x14 - Type=0x03: On**    
  Sent from the VSCP node when the light turns on.  
  Zone/subzone is used to identify the light.  
  Data byte 0 is ignored.
  
- **CLASS1.INFORMATION, 0x14 - Type=0x04: Off**    
  Sent from the VSCP node when the light turns off.  
  Zone/subzone is used to identify the light.  
  Data byte 0 is ignored.
  
- **CLASS1.INFORMATION, 0x14 - Type=0x28 Level Changed**    
  Sent from the VSCP node supporting brightness control to indicate its
  new brightness level (0-255).  
  NOTE: the event data is NOT conforming to the VSCP spec, instead:
  - byte 0 = index of the channel
  - byte 1 = zone
  - byte 2 = subzone
  - byte 3 = new level
  
## Discovery service for standardised entities

The following features of VSCP are used in the discovery process:
- "who's there" events are used to scan the bus and gather GUID's after starting.
- Extended page register reads are used to read the device registers.
- The standard device family code (starting address 0x9B) is set to "HASS" in
  UTF-8 encoding, this allows VSCP4HASS to scan a bus looking for compatible
  devices. Standard device type is set to all 0's and reserved for future use.
- Each channel is mapped to a single page of registers, starting from 0x0000.
- The GUID for each node together with the channel number acts as the unique ID
  towards HASS.
- Node heartbeats (CLASS1.Information, type 0x09) are used to determine if a
  node is still connected. (To be implemented!)
- New node online messages (CLASS1.Protocol, type 0x02) are used to enable new
  or reconfigure existing nodes (ie after an external configuration change, a
  reset should be forced on the node to refresh the status in HASS). 
  (To be implemented!)

The first 32 (0x20) registers for each channel/page are defined for use by
VSCP4HASS. The remainder of the page is available to implement other
functionalities. VSCP4HASS considers all registers as read-only. Configuration
of the registers (using the MDF) has to happen with external tools.

The first 2 registers of each channel act as an entity identifier, encoded as a
2 bytes of ASCII code. An entity identifier of all 0's marks the end of the
register map.  
Next is an enable register. If a light channel is disabled, it will not be loaded
into HASS.  
Further registers up to 0x0F define entity-dependent behaviour.
Each channel can optionally have a configured name (max 16 bytes), depending on
available non-volatile memory capacity in the node. Null-terminated in UTF-8.

The remaining registers of the page (0x20-0x7F) are free to be used by the 
implementer. For instance when implementing a binary sensor which receives push 
button status, one might have it also send turn on/off events to a light. 
Other examples are polarity inversions, built-in timers etc.

### Light
https://developers.home-assistant.io/docs/core/entity/light  
Light entities are input/output devices which control physical lights.
Some advanced features are currently not supported (like effects) but might
be added in the future.

#### VSCP registers:
- 0x00-0x01: Identifier: "LI"
- 0x02: Enable (0=disabled)
- 0x03: capabilities flags, encoded as (currently identical as in HASS):
  * 0x01: support brightness
  * 0x02: support color temperature (NOT IMPLEMENTED, always 0)
  * 0x04: support effect (NOT IMPLEMENTED, always 0)
  * 0x08: support flash
  * 0x10: support color (NOT IMPLEMENTED, always 0)
  * 0x20: support transition (NOT IMPLEMENTED, always 0)
  * 0x40: support white value (NOT IMPLEMENTED, always 0)
- 0x04: State (1=on)
- 0x05: VSCP zone for this light
- 0x06: VSCP subzone for this light
- 0x07: brightness value, 0-255
- 0x08-0x0F: reserved for future use
- 0x10-0x1F: light name, null terminated (all 0's if not used)

#### VSCP events:
- **CLASS1.CONTROL, 0x1E - Type=0x05: TurnOn**  
  Sent from HASS to the zone/subzone (as read from the registers) 
  to turn on. Data byte 0 indicates flashing mode: 
  - 0=no flashing
  - 1=short flash
  - 2=long flash

- **CLASS1.CONTROL, 0x1E - Type=0x07: TurnOff**  
  Sent from HASS to the zone/subzone (from registers) to turn off, data
  byte 0 not used

- **CLASS1.CONTROL, 0x1E - Type=0x16: Change level**    
  Sent from HASS to the zone/subzone to set dimmer value (0-255)    
  *Note: this is used as opposed to the command "Dim lamp(s)"*

- **CLASS1.INFORMATION, 0x14 - Type=0x03: On**    
  Sent from the VSCP node when the light turns on. Data byte 0 is the
  channel number of the VSCP node. Zone/subzone is ignored.
  
- **CLASS1.INFORMATION, 0x14 - Type=0x04 Off**    
  Sent from the VSCP node when the light turns off. Data byte 0 is the
  channel number of the VSCP node. Zone/subzone is ignored.
  
- **CLASS1.INFORMATION, 0x14 - Type=0x28 Level Changed**    
  Sent from the VSCP node supporting brightness control to indicate its
  new brightness level (0-255).  
  NOTE: the event data is NOT conforming to the VSCP spec, instead:
  - byte 0 = index of the channel
  - byte 1 = zone
  - byte 2 = subzone
  - byte 3 = new level

### Binary sensor
https://developers.home-assistant.io/docs/core/entity/binary-sensor  
Binary sensors are input-only devices and only have an ON or OFF state. 
Device classes are defined for sensors of a specific type, so they can be
displayed with an appropriate icon in the HASS frontend.

#### VSCP registers:
- 0x00-0x01: Identifier: "BS"
- 0x02: Enabled (0=disable)
- 0x03: State (1=on)
- 0x04: Class ID - see below
- 0x05-0x0F: reserved for future use
- 0x10-0x1F: binary sensor name, null terminated (all 0's if not used)

#### Class ID mapping:
| Class ID | HASS Device Class |
|----------|-------------------|
| 0x00     | generic           |
| 0x01     | battery           |
| 0x02     | battery_charging  |
| 0x03     | cold              |
| 0x04     | connectivity      |
| 0x05     | door              |
| 0x06     | garage_door       |
| 0x07     | gas               |
| 0x08     | heat              |
| 0x08     | light             |
| 0x09     | lock              |
| 0x0A     | moisture          |
| 0x0B     | motion            |
| 0x0C     | moving            |
| 0x0D     | occupancy         |
| 0x0E     | opening           |
| 0x0F     | plug              |
| 0x10     | power             |
| 0x11     | presence          |
| 0x12     | problem           |
| 0x13     | safety            |
| 0x14     | smoke             |
| 0x15     | sound             |
| 0x16     | vibration         |
| 0x17     | window            |

#### VSCP events:  

- **CLASS1.INFORMATION, 0x14 - Type=0x03: On**    
  Sent from the VSCP node when the sensor turns on. Data byte 0 is the
  channel number of the VSCP node. Zone/subzone is ignored.
  
- **CLASS1.INFORMATION, 0x14 - Type=0x04 Off**    
  Sent from the VSCP node when the sensor turns off. Data byte 0 is the
  channel number of the VSCP node. Zone/subzone is ignored.
