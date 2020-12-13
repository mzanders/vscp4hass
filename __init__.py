from homeassistant.const import EVENT_HOMEASSISTANT_STOP
from .gateway import Gateway
from .light import VSCP4HASSLight
from .binary_sensor import VSCP4HASSBinarySensor
from .const import VSCP4HASS_DOMAIN

"""Support for VSCP4HASS."""
DOMAIN = VSCP4HASS_DOMAIN


async def async_setup(hass, config):
    """controller setup code"""
    gw = Gateway()
    await gw.connect()
    await gw.scan()

    async def on_hass_stop(event):
        """Close connection when hass stops."""
        await gw.close()
    hass.bus.async_listen_once(EVENT_HOMEASSISTANT_STOP, on_hass_stop)

    hass.data[DOMAIN] = gw

    hass.helpers.discovery.load_platform('light', DOMAIN, {}, config)
    hass.helpers.discovery.load_platform('binary_sensor', DOMAIN, {}, config)

    await gw.start_update()
    return True
