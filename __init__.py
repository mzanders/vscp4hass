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
from .const import (DOMAIN, DEFAULT_HOST, DEFAULT_PORT, GATEWAY, SCANNER, SCANNER_TASK)
import voluptuous as vol
from .channel import channel_reg
import asyncio

import logging

logger = logging.getLogger(__name__)

"""Support for VSCP in HASS."""

CONFIG_SCHEMA = vol.Schema(
    {
        DOMAIN: vol.Schema(
            {
                vol.Required(CONF_HOST): cv.string,
                vol.Optional(CONF_PORT, default=DEFAULT_PORT): cv.port,
                vol.Optional(CONF_USERNAME): cv.string,
                vol.Optional(CONF_PASSWORD): cv.string,
                vol.Optional(CONF_DISCOVERY, default=False): cv.boolean
            }
        )
    },
    extra=vol.ALLOW_EXTRA
)


async def async_do_discovery(hass, config, updater):
    logger.info('Starting VSCP discovery for HASS nodes.')
    conf = config.get(DOMAIN)
    host = conf.get(CONF_HOST)
    port = conf.get(CONF_PORT)
    user = conf.get(CONF_USERNAME)
    password = conf.get(CONF_PASSWORD)

    scanner = Gateway(host=host, port=port, user=user, password=password)
    hass.data[DOMAIN][SCANNER] = scanner
    await scanner.connect()
    await scanner.scan(updater)

    hass.helpers.discovery.load_platform('light', DOMAIN, {}, config)
    hass.helpers.discovery.load_platform('binary_sensor', DOMAIN, {}, config)

    await scanner.close()


async def async_setup(hass, config):
    """controller setup code"""
    conf = config.get(DOMAIN)
    host = conf.get(CONF_HOST)
    port = conf.get(CONF_PORT)
    user = conf.get(CONF_USERNAME)
    password = conf.get(CONF_PASSWORD)

    hass.data[DOMAIN] = dict()

    gw = Gateway(host=host, port=port, user=user, password=password)
    await gw.connect()
    await gw.start_update()
    hass.data[DOMAIN][GATEWAY] = gw

    if conf.get(CONF_DISCOVERY):
        hass.data[DOMAIN][SCANNER_TASK] = asyncio.create_task(async_do_discovery(hass, config, gw))

    async def on_hass_stop(event):
        """Close connection when hass stops."""
        await gw.close()
        if SCANNER_TASK in hass.data[DOMAIN]:
            task = hass.data[DOMAIN][SCANNER_TASK]
            if task is not None:
                try:
                    task.cancel()
                except asyncio.CancelledError:
                    pass
                await task
    hass.bus.async_listen_once(EVENT_HOMEASSISTANT_STOP, on_hass_stop)

    hass.helpers.discovery.load_platform('light', DOMAIN, None, config)
    hass.helpers.discovery.load_platform('binary_sensor', DOMAIN, None, config)

    return True
