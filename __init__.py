from homeassistant.const import (EVENT_HOMEASSISTANT_STOP,
                                 CONF_HOST,
                                 CONF_PORT,
                                 CONF_USERNAME,
                                 CONF_PASSWORD,
                                 CONF_DISCOVERY)

from .gateway import Gateway
from .light import vscpLight
from .binary_sensor import vscpBinarySensor
import homeassistant.helpers.config_validation as cv
from .const import (DOMAIN, DEFAULT_HOST, DEFAULT_PORT)
import voluptuous as vol

"""Support for VSCP in HASS."""

CONFIG_SCHEMA = vol.Schema(
    {
        DOMAIN: vol.Schema(
            {
                vol.Required(CONF_HOST): cv.string,
                vol.Optional(CONF_PORT, default=DEFAULT_PORT): cv.port,
                vol.Optional(CONF_USERNAME): cv.string,
                vol.Optional(CONF_PASSWORD): cv.string,
                vol.Optional(CONF_DISCOVERY, default=True): cv.boolean
            }
        )
    },
    extra=vol.ALLOW_EXTRA
)

async def async_setup(hass, config):
    """controller setup code"""
    conf = config.get(DOMAIN)
    host = conf.get(CONF_HOST)
    port = conf.get(CONF_PORT)
    user = conf.get(CONF_USERNAME)
    password = conf.get(CONF_PASSWORD)

    gw = Gateway(host=host, port=port, user=user, password=password)
    await gw.connect()

    if conf.get(CONF_DISCOVERY):
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
