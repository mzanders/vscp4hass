# VSCP4HASS - framework to integrate VSCP nodes easily into Home Assistant

https://www.vscp.org
https://www.home-assistant.io

## Installation

Copy or link this folder to `<config_dir>/custom_components/vscp/` for HASS.

Add the following entry in your `configuration.yaml`:

```yaml
vscp:
    host: HOST_HERE
    port: PORT_HERE
```

## Objective
VSCP4HASS defines a standardized interface to VSCP nodes to implement generic
entities that are defined in HASS. This allows easy expansion of a VSCP4HASS
network without any configuration change on the HASS side by using a discovery
mechanism.

TODO: in the future, manual addition of HASS entities which are tied to VSCP 
events is foreseen!!

The goals of VSCP4HASS are:
- all configuration data is contained in the nodes, no separate config files are
  required to describe/interface the system
- HASS doesn't need to look up register addresses in the VSCP MDF
- everything can be discovered on the initiative of HASS
- changes on the VSCP network are automatically propagated to HASS
- The VSCP event matching the most with the targeted function is used where
  possible and practical.

VSCP4HASS uses asyncio interfaces exclusively. It uses an external Python module
to communicate with a vscpd compatible instance.

## VSCP features used
The following features of VSCP are used in order to meet the objectives above:
- "who's there" events are used to scan the bus and gather GUID's after starting.
- Extended page register reads are used to read the device registers.
- The standard device family code (starting address 0x9B) is set to "HASS" in
  UTF-8 encoding, this allows VSCP4HASS to scan a bus looking for compatible
  devices. Standard device type is set to all 0's and reserved for future use.
- The number of pages in a VSCP4HASS node (register address 0x99 - deprecated by
  VSCP) identifies the number of channels available on that node. Zero based.
- Each channel is mapped to a single page of registers, starting from 0x0000.
- The GUID for each node together with the channel number acts as the unique ID
  towards HASS.
- Node heartbeats (CLASS1.Information, type 0x09) are used to determine if a
  node is still connected.
- New node online messages (CLASS1.Protocol, type 0x02) are used to enable new
  or reconfigure existing nodes (ie after an external configuration change, a
  reset should be forced on the node to refresh the status in HASS).

The first 32 (0x20) registers for each channel/page are defined for use by
VSCP4HASS. The remainder of the page is available to implement other
functionalities. VSCP4HASS considers all registers as read-only. Configuration
of the registers (using the MDF) has to happen with external tools.

The first 2 registers of each channel act as an entity identifier, encoded as a
2 bytes of ASCII code.
Next is an enable register. If the channel is disabled, it will not be loaded
into HASS.
Further registers up to 0x0F define entity-dependent behaviour.
Each channel can optionally have a configured name (max 16 bytes), depending on
available non-volatile memory capacity in the node. Null-terminated in UTF-8.

The remaining registers (0x20-0x7F) are free to be used by the implementer.
For instance when implementing a binary sensor which receives push button
status, one might have it automatically send turn on/off events to a light. 
Other examples are polarity inversions, built-in timers etc.

## Home Assistant entities definitions
### Light
https://developers.home-assistant.io/docs/core/entity/light
Light entities are input/output devices which control physical lights.
Some advanced features are currently not supported (like effects) but might
be added in the future.

VSCP registers:
    0x00-0x01: Identifier: "LI"
    0x02: Enable (0=disabled)
    0x03: capabilities flags
      encoded as (currently identical as in HASS):
      * 0x01: support brightness
      * 0x02: support color temperature (NOT IMPLEMENTED, always 0)
      * 0x04: support effect (NOT IMPLEMENTED, always 0)
      * 0x08: support flash
      * 0x10: support color (NOT IMPLEMENTED, always 0)
      * 0x20: support transition (NOT IMPLEMENTED, always 0)
      * 0x40: support white value (NOT IMPLEMENTED, always 0)
    0x04: State (1=on)
    0x05: VSCP zone for this light
    0x06: VSCP subzone for this light
    0x07: brightness value, 0-255
    0x08-0x0F: reserved for future use
    0x10-0x1F: light name, null terminated (all 0's if not used)

VSCP events:
    CLASS1.CONTROL, 0x1E - Type=0x05: TurnOn
      Sent from HASS to the zone/subzone (as read from the registers) 
      to turn on. Data byte 0 indicates flashing mode: 
         0=no flashing
         1=short flash
         2=long flash
    CLASS1.CONTROL, 0x1E - Type=0x07: TurnOff
      Sent from HASS to the zone/subzone (from registers) to turn off, data
      byte 0 not used
    CLASS1.CONTROL, 0x1E - Type=0x16: Change level
      Sent from HASS to the zone/subzone to set dimmer value (0-255)
      Note: this is used as opposed to the command "Dim lamp(s)"
    CLASS1.INFORMATION, 0x14 - Type=0x03: On
      Sent from the VSCP node when the light turns on. Data byte 0 is the
      channel number of the VSCP node. Zone/subzone is ignored.
    CLASS1.INFORMATION, 0x14 - Type=0x04 Off
      Sent from the VSCP node when the light turns off. Data byte 0 is the
      channel number of the VSCP node. Zone/subzone is ignored.
    CLASS1.INFORMATION, 0x14 - Type=0x28 Level Changed
      Sent from the VSCP node supporting brightness control to indicate its
      new brightness level (0-255).
      NOTE: the event data is NOT conforming to the VSCP spec, instead:
         byte 0 = index of the channel
         byte 1 = zone
         byte 2 = subzone
         byte 3 = new level

### Binary sensor
https://developers.home-assistant.io/docs/core/entity/binary-sensor
Binary sensors are input-only devices and only have an ON or OFF state. 
Device classes are defined for sensors of a specific type, so they can be
displayed with an appropriate icon in the HASS frontend. VSCP4HASS defines
how each of those classes is implemented on VSCP.

VSCP registers:
    0x00-0x01: Identifier: "BS"
    0x02: Enabled (0=disable)
    0x03: State (1=on)
    0x04: Class ID
    0x05-0x0F: reserved for future use
    0x10-0x1F: binary sensor name, null terminated (all 0's if not used)

VSCP events:
    The events from the table below are used for the respective class ID's
    in each channel. Byte 0 always indicates the channel of the node which
    is reporting the status. Zone/subzone information is ignored in VSCP4HASS
    and can be used for other purposes.

Class ID - Class - VSCP event mapping - Work-in-progress

This is a suggested mapping between HASS device classes and VSCP events.
For now, only info ON and OFF events are used.

| Class ID | HASS Device Class | VSCP Class  | ON event type       | OFF event type     | Notes                                           |
|----------|-------------------|-------------|-------------------- |--------------------|-------------------------------------------------|
| 0x00     | generic           | 0x20 - info | 0x03 - ON           | 0x04 - OFF         |                                                 |
| 0x01     | battery           | 0x20 - info | 0x0A - Below limit  | 0x0B - Above limit | VSCP: add battery empty & OK events?            |
| 0x02     | battery_charging  | 0x20 - info | 0x03 - ON           | 0x04 - OFF         | VSCP: maybe too specific to add charge events?  |
| 0x03     | cold              | 0x02 - secu | 0x0C - Frost        | ???                | VSCP: no 'inactive' event                       |
| 0x04     | connectivity      | 0x20 - info | 0x51 - Connect      | 0x52 - Disconnect  |                                                 |
| 0x05     | door              | 0x02 - secu | 0x09 - Door contact | ???                | VSCP: no 'inactive' event                       |
| 0x06     | garage_door       | 0x20 - info | 0x07 - Opened       | 0x08 - Closed      |                                                 |
| 0x07     | gas               | 0x02 - secu | ???                 | ???                | VSCP: add generic gas sensor in security?       |
| 0x08     | heat              | 0x02 - secu | 0x07 - Heat sensor  | ???                | VSCP: no 'inactive' event                       |
| 0x08     | light             | 0x20 - info | 0x03 - ON           | 0x04 - OFF         |                                                 |
| 0x09     | lock              | 0x20 - info | 0x4B - Lock         | 0x4C - Unlock      |                                                 |
| 0x0A     | moisture          | 0x02 - secu | 0x10 - Water        | ???                | VSCP: no 'inactive' event                       |
| 0x0B     | motion            | 0x02 - secu | 0x01 - Motion       | ???                | VSCP: no 'inactive' event                       |
| 0x0C     | moving            | 0x20 - info | 0x03 - ON           | 0x04 - OFF         | VSCP: add 'in-motion' events?                   |
| 0x0D     | occupancy         | 0x20 - info | 0x54 - Enter        | 0x55 - Exit        |                                                 |
| 0x0E     | opening           | 0x20 - info | 0x07 - Opened       | 0x08 - Closed      |                                                 |
| 0x0F     | plug              | 0x20 - info | 0x03 - ON           | 0x04 - OFF         |                                                 |
| 0x10     | power             | 0x20 - info | 0x03 - ON           | 0x04 - OFF         |                                                 |
| 0x11     | presence          | 0x20 - info | 0x54 - Enter        | 0x55 - Exit        |                                                 |
| 0x12     | problem           | 0x20 - info | 0x29 - Warning      | ???                | VSCP: no 'inactive' event                       |
| 0x13     | safety            | 0x02 - secu | 0x00 - Generic      | ???                | VSCP: no 'inactive' event                       |
| 0x14     | smoke             | 0x02 - secu | 0x06 - Smoke sensor | ???                | VSCP: no 'inactive' event                       |
| 0x15     | sound             | 0x02 - secu | 0x12 - Noise        | ???                | VSCP: no 'inactive' event                       |
| 0x16     | vibration         | 0x02 - secu | 0x05 - Shock        | ???                | VSCP: no 'inactive' event                       |
| 0x17     | window            | 0x02 - secu | 0x0A - Window       | ???                | VSCP: no 'inactive' event                       |


### Sensor
https://developers.home-assistant.io/docs/core/entity/sensor
Sensors are read-only devices which report the magnitude for a physical
property. Just like binary sensors, HASS defines device classes to report
these values using appropriate representations. In addition, the unit being
reported by VSCP is provided to HASS (TBD if this is required, it seems that
unit handling is not really dealt with in HASS).

VSCP registers:
    0x00-0x01: Identifier: "SE"
    0x02: Enabled (0=disable)
    0x03: Class ID
    0x04: Sensor ID
    0x05: Generic
    0x10-0x1F: binary sensor name, null terminated (all 0's if not used)

VSCP events:
    The CLASS1.MEASUREZONE is used to transmit measurement data. Byte 0 always
    indicates	which channel of the node is reporting the value. Byte 1/2
    (zone/subzone) is ignored by VSCP4HASS. The datacoding in byte 3 has 2 4bit
    nibbles:
	bit 0-3: VSCP unit ID for the value, as defined in VSCP spec
	bit 4-7: Value encoding format as in VSCP:
				0b0000: set of bits
				0b0001: byte
				0b0010: string (only 4chars..)
				0b0011: signed integer
				0x0100: normalized signed integer
				0x0101: 32bit IEE754 float
				0x1011: unsigned integer
				0x1100: normalized unsigned integer			

Class ID - Event - Unit mapping - Work-in-progress

CLASS1.MEASUREMENTZONE (0x41) is used for all the sensor inputs. The mapping of
class ID's to events is as follows:

| Class ID | HASS device Class | VSCP event type         | Unit          | Notes                       |
|----------|-------------------|-------------------------|---------------|-----------------------------|
| 0x00     | generic           | 0x00 - General Event    | No units      |                             |
| 0x01     | humidity          | 0x23 - Damp/moist       | 0-100%        | Relative humidity           |
| 0x02     | illuminance       | 0x18 - Luminous Flux    | Lumen         | HASS mixes two types        |
| 0x03     | signal_strength   | not supported!          | dB, dBm       | VSCP: add in spec?          |
| 0x04     | temperature       | 0x06 - Temperature      | K, °C, F      |                             |
| 0x05     | timestamp         | 0x04 - Time             | Seconds       | Unix epoch                  |
| 0x06     | power             | 0x0E - Power            | Watt          |                             |
| 0x07     | pressure          | 0x0C - Pressure         | Pa, Bar, Psi  |                             |
| 0x08     | current           | 0x05 - Electric current | A             |                             |
| 0x09     | energy            | 0x0D - Energy           | J, kWh, Wh    | VSCP: extend units in spec? |
| 0x0A     | power_factor      | not supported!          | 0.0-1.0       | VSCP: add in spec?          |
| 0x0B     | voltage           | 0x10 - Voltage          | V             |                             |


