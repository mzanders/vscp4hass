import logging

from .channel import Channel
from .const import DOMAIN

from .vscp.const import (CLASS_INFORMATION, EVENT_INFORMATION_ON, EVENT_INFORMATION_OFF)
from .vscp.util import read_reg

from homeassistant.components.binary_sensor import (BinarySensorEntity)
from homeassistant.const import STATE_OFF, STATE_ON

_LOGGER = logging.getLogger(__name__)

IDENTIFIER = 'BS'


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
        async_add_entities(node.get_channels(IDENTIFIER))

    return True


class vscpBinarySensor(BinarySensorEntity, Channel):
    """Representation of an VSCP binary sensor."""
    @classmethod
    async def new(cls, node, channel):
        self = cls()
        self._node = node
        self._channel = channel

        registers = await read_reg(node.bus, node.nickname, channel, 0, 34)
        self._enabled = (registers[0x02] != 0x00)
        self._state = (registers[0x03] != 0x00)
        self._class_id = int(registers[0x04])
        self._name = registers[16:33].decode().rstrip('/x0')
        self.entity_id = "binary_sensor.vscp.{}.{}".format(self._node.guid, self._channel)

        await self._node.bus.sub_ch_event(node.nickname, channel, CLASS_INFORMATION, EVENT_INFORMATION_ON, self._handle_onoff_event)
        await self._node.bus.sub_ch_event(node.nickname, channel, CLASS_INFORMATION, EVENT_INFORMATION_OFF, self._handle_onoff_event)
        return self

    @property
    def is_on(self):
        return self._state

    @property
    def state(self):
        """Return the state of the sensor."""
        return STATE_ON if self._state else STATE_OFF

    @classmethod
    def identifier(cls):
        return IDENTIFIER

    @property
    def name(self):
        """Return the display name of this light."""
        return self._name

    # when a node goes offline, we can disable it's channels
    @property
    def available(self):
        return True

    @property
    def unique_id(self):
        return "BS-{}-{}".format(self._node.guid, self._channel)

    @property
    def should_poll(self):
        return False

    async def _handle_onoff_event(self, event):
        self._state = (event.vscp_type == EVENT_INFORMATION_ON)
        self.async_schedule_update_ha_state()

    @property
    def device_class(self):
        class_map = {
            0x01 : 'battery',
            0x02 : 'battery_charging',
            0x03 : 'cold',
            0x04 : 'connectivity',
            0x05 : 'door',
            0x06 : 'garage_door',
            0x07 : 'gas',
            0x08 : 'heat',
            0x08 : 'light',
            0x09 : 'lock',
            0x0A : 'moisture',
            0x0B : 'motion',
            0x0C : 'moving',
            0x0D : 'occupancy',
            0x0E : 'opening',
            0x0F : 'plug',
            0x10 : 'power',
            0x11 : 'presence',
            0x12 : 'problem',
            0x13 : 'safety',
            0x14 : 'smoke',
            0x15 : 'sound',
            0x16 : 'vibration',
            0x17 : 'window'
        }
        return class_map[self._class_id] if self._class_id in class_map else 'generic'
