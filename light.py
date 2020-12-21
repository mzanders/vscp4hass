import logging
import struct

from homeassistant.components.light import (
    ATTR_BRIGHTNESS,
    ATTR_FLASH,
    SUPPORT_BRIGHTNESS,
    SUPPORT_FLASH,
    LightEntity
)

from .channel import Channel

from .const import DOMAIN

from .vscp.event import Event
from .vscp.const import (CLASS_CONTROL, CLASS_INFORMATION,
                         EVENT_INFORMATION_ON, EVENT_INFORMATION_OFF, EVENT_INFORMATION_LEVEL,
                         EVENT_CONTROL_TURN_ON, EVENT_CONTROL_TURN_OFF, EVENT_CHANGE_LEVEL)

from .vscp.util import read_reg

logger = logging.getLogger(__name__)

IDENTIFIER = 'LI'


async def async_setup_platform(hass, config, async_add_entities, discovery_info=None):
    # Assign configuration variables.
    # The configuration check takes care they are present.
    #host = config[CONF_HOST]
    #username = config[CONF_USERNAME]
    #password = config.get(CONF_PASSWORD)
    if discovery_info is None:
        return

    # Setup connection with devices/cloud
    gw = hass.data[DOMAIN]

    for node in gw.nodes.values():
        async_add_entities([ch for ch in node.get_channels(IDENTIFIER) if ch.enabled])
    return True


class vscpLight(LightEntity, Channel):
    """Representation of a VSCP4HASS Light."""
    @classmethod
    async def new(cls, node, channel):
        self = cls()
        self._node = node
        self._channel = channel

        registers = await read_reg(node.bus, node.nickname, channel, 0, 34)
        self._enabled = (registers[0x03] != 0x00)
        self._supports_brightness = (registers[0x04] & 0x01 == 0x01)
        self._supports_flash = (registers[0x04] & 0x08 == 0x08)
        self._state = (registers[0x05] != 0x00)
        self._zone = int(registers[0x06])
        self._subzone = int(registers[0x07])
        self._brightness = int(registers[0x08])
        self._name = registers[16:33].decode().rstrip('/x0')
        self.entity_id = "light.vscp.{}.{}".format(self._node.guid, self._channel)
        return self

    async def async_added_to_hass(self):
        super().async_added_to_hass()
        await self._node.bus.sub_ch_event(self._node.nickname, self._channel, CLASS_INFORMATION, EVENT_INFORMATION_ON,
                                          self._handle_onoff_event)
        await self._node.bus.sub_ch_event(self._node.nickname, self._channel, CLASS_INFORMATION, EVENT_INFORMATION_OFF,
                                          self._handle_onoff_event)
        if self._supports_brightness:
            await self._node.bus.sub_ch_event(self._node.nickname, self._channel, CLASS_INFORMATION, EVENT_INFORMATION_LEVEL,
                                              self._handle_level_event)

    @property
    def enabled(self):
        return self._enabled

    @property
    def unique_id(self):
        return "LI-{}-{}".format(self._node.guid, self._channel)

    @property
    def name(self):
        """Return the display name of this light."""
        return self._name

    # when a node goes offline, we can disable it's channels
    @property
    def available(self):
        return True

    @property
    def should_poll(self):
        return False

    @classmethod
    def identifier(cls):
        return IDENTIFIER

    @property
    def supported_features(self):
        _c = 0
        if self._supports_brightness:
            _c |= SUPPORT_BRIGHTNESS
        if self._supports_flash:
            _c |= SUPPORT_FLASH
        return _c

    @property
    def brightness(self):
        return self._brightness

    @property
    def is_on(self):
        """Return true if light is on."""
        return self._state

    async def async_turn_on(self, **kwargs):
        """Instruct the light to turn on."""
        logger.debug('Turning on {}'.format(self.name))
        flash_cmd = 0
        if ATTR_FLASH in kwargs:
            if kwargs[ATTR_FLASH] == 'short':
                flash_cmd = 1
            if kwargs[ATTR_FLASH] == 'long':
                flash_cmd = 2

        ev = Event(vscp_class=CLASS_CONTROL,
                   vscp_type=EVENT_CONTROL_TURN_ON,
                   data=struct.pack('>BBB', flash_cmd, self._zone, self._subzone))
        await self._node.bus.send(ev)

        if self._supports_brightness and ATTR_BRIGHTNESS in kwargs:
            brightness = kwargs[ATTR_BRIGHTNESS]
            if brightness > 255:
                brightness = 255
            if brightness < 0:
                brightness = 0

            ev = Event(vscp_class=CLASS_CONTROL,
                       vscp_type=EVENT_CHANGE_LEVEL,
                       data=struct.pack('>BBB', brightness, self._zone, self._subzone))
            await self._node.bus.send(ev)

    async def async_turn_off(self, **kwargs):
        """Instruct the light to turn off."""
        logger.debug('Turning off {}'.format(self.name))
        ev = Event(vscp_class=CLASS_CONTROL,
                   vscp_type=EVENT_CONTROL_TURN_OFF,
                   data=struct.pack('>BBB', 0, self._zone, self._subzone))
        await self._node.bus.send(ev)

    @property
    def should_poll(self):
        return False

    async def _handle_onoff_event(self, event):
        logger.debug('Got on/off for {}'.format(self.name))
        self._state = (event.vscp_type == EVENT_INFORMATION_ON)
        self.async_schedule_update_ha_state()

    async def _handle_level_event(self, event):
        self._brightness = struct.unpack('>BBBB', event.data)[3]
        self.async_schedule_update_ha_state()
