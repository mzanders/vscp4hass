import logging
import struct
import voluptuous as vol
import homeassistant.helpers.config_validation as cv
from homeassistant.const import (CONF_NAME, CONF_ZONE)


from homeassistant.components.light import (
    ATTR_BRIGHTNESS,
    ATTR_FLASH,
    LightEntity,
    LightEntityFeature
)

from .channel import Channel

from .const import (DOMAIN, GATEWAY, SCANNER, CONF_SUBZONE)

from .vscp.event import Event
from .vscp.const import (
    CLASS_CONTROL,
    CLASS_INFORMATION,
    EVENT_INFORMATION_ON,
    EVENT_INFORMATION_OFF,
    EVENT_INFORMATION_LEVEL,
    EVENT_CONTROL_TURN_ON,
    EVENT_CONTROL_TURN_OFF,
    EVENT_CHANGE_LEVEL,
)

from .vscp.util import read_reg

logger = logging.getLogger(__name__)
IDENTIFIER = 'LI'

async def async_setup_entry(hass, entry, async_add_entities):
    # Register a callback so nodes can add entities dynamically
    async def add_new_channel(channel):
        logger.debug("Add VSCP light via discovery: %s", channel._name)
        async_add_entities([channel])

    hass.data[DOMAIN][SCANNER].register_entity_callback(IDENTIFIER, add_new_channel)

    async_add_entities([])


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
        self._name = registers[16:33].decode(errors="ignore").rstrip("\x00")
        self.entity_id = "light.vscp.{}.{}".format(self._node.guid, self._channel)
        return self

    async def async_added_to_hass(self):
        await super().async_added_to_hass()
        await self._node.updater.sub_ch_event(
            self._node.nickname,
            self._channel,
            CLASS_INFORMATION,
            EVENT_INFORMATION_ON,
            self._handle_onoff_event,
        )
        await self._node.updater.sub_ch_event(
            self._node.nickname,
            self._channel,
            CLASS_INFORMATION,
            EVENT_INFORMATION_OFF,
            self._handle_onoff_event,
        )
        if self._supports_brightness:
            await self._node.updater.sub_ch_event(
                self._node.nickname,
                self._channel,
                CLASS_INFORMATION,
                EVENT_INFORMATION_LEVEL,
                self._handle_level_event,
            )

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
    def supported_color_modes(self):
        modes = set()
        if self._supports_brightness:
            modes.add("brightness")
        else:
            modes.add("onoff")
        return modes

    @property
    def color_mode(self):
        if self._supports_brightness:
            return "brightness"
        return "onoff"

    @property
    def supported_features(self) -> LightEntityFeature:
        features = LightEntityFeature(0)
        if self._supports_flash:
            features |= LightEntityFeature.FLASH
        return features

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
        await self._node.updater.send(ev)

        if self._supports_brightness and ATTR_BRIGHTNESS in kwargs:
            brightness = kwargs[ATTR_BRIGHTNESS]
            if brightness > 255:
                brightness = 255
            if brightness < 0:
                brightness = 0

            ev = Event(vscp_class=CLASS_CONTROL,
                       vscp_type=EVENT_CHANGE_LEVEL,
                       data=struct.pack('>BBB', brightness, self._zone, self._subzone))
            await self._node.updater.send(ev)

    async def async_turn_off(self, **kwargs):
        """Instruct the light to turn off."""
        logger.debug('Turning off {}'.format(self.name))
        ev = Event(vscp_class=CLASS_CONTROL,
                   vscp_type=EVENT_CONTROL_TURN_OFF,
                   data=struct.pack('>BBB', 0, self._zone, self._subzone))
        await self._node.updater.send(ev)

    async def _handle_onoff_event(self, event):
        logger.debug('Got on/off for {}'.format(self.name))
        self._state = (event.vscp_type == EVENT_INFORMATION_ON)
        self.async_schedule_update_ha_state()

    async def _handle_level_event(self, event):
        self._brightness = struct.unpack('>BBBB', event.data)[3]
        self.async_schedule_update_ha_state()
