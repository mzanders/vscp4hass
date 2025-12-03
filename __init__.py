from homeassistant.const import (EVENT_HOMEASSISTANT_STOP,
                                 CONF_HOST,
                                 CONF_PORT,
                                 CONF_USERNAME,
                                 CONF_PASSWORD,
                                 CONF_DISCOVERY)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant

from .gateway import Gateway
from .light import vscpLight
from .binary_sensor import vscpBinarySensor
import homeassistant.helpers.config_validation as cv
from .const import (DOMAIN, DEFAULT_HOST, DEFAULT_PORT, GATEWAY, SCANNER, SCANNER_TASK,
                    SVC_PRIORITY, SVC_TYPE, SVC_CLASS, SVC_DATA)
import voluptuous as vol
from .channel import channel_reg
import asyncio
from .vscp.event import Event

import logging
logger = logging.getLogger(__name__)

"""Support for VSCP in HASS."""

async def async_do_discovery(scanner: Gateway, updater: Gateway):
    await scanner.connect()
    await scanner.scan(updater)
    await scanner.close()

SERVICE_SCHEMA = vol.Schema(
    {
        vol.Required(SVC_PRIORITY): int,
        vol.Required(SVC_CLASS): int,
        vol.Required(SVC_TYPE): int,
        vol.Required(SVC_DATA): cv.string
    }
)

# -------------------------------
# Config Entry setup
# -------------------------------
async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry):
    """Set up VSCP via Config Entry (UI)."""
    host = entry.data.get(CONF_HOST)
    port = entry.data.get(CONF_PORT)
    user = entry.data.get(CONF_USERNAME)
    password = entry.data.get(CONF_PASSWORD)

    hass.data.setdefault(DOMAIN, {})

    gw = Gateway(host=host, port=port, user=user, password=password)
    scanner = Gateway(host=host, port=port, user=user, password=password)
    await gw.connect()
    await gw.start_update()
    hass.data[DOMAIN][GATEWAY] = gw
    hass.data[DOMAIN][SCANNER] = scanner

    # Close gracefully on HA stop
    async def on_hass_stop(event):
        await gw.close()
        task = hass.data[DOMAIN].get(SCANNER_TASK)
        if task:
            task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                pass

    hass.bus.async_listen_once(EVENT_HOMEASSISTANT_STOP, on_hass_stop)

    # Register send_event service
    async def handle_send_event(call):
        await gw.send(
            Event(
                vscp_class=call.data.get(SVC_CLASS),
                vscp_type=call.data.get(SVC_TYPE),
                head=call.data.get(SVC_PRIORITY) * 32,
                data=bytearray([int(x, 0) for x in call.data.get(SVC_DATA).split(",")])
            )
        )

    hass.services.async_register(DOMAIN, "send_event", handle_send_event, SERVICE_SCHEMA)

    await hass.config_entries.async_forward_entry_setups(entry, ["light", "binary_sensor"])
    hass.data[DOMAIN][SCANNER_TASK] = asyncio.create_task(async_do_discovery(scanner, gw))

    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry):
    """Unload VSCP integration (Config Entry)."""
    gw = hass.data[DOMAIN].get(GATEWAY)
    if gw:
        await gw.close()

    # Cancel scanner task
    task = hass.data[DOMAIN].get(SCANNER_TASK)
    if task:
        task.cancel()
        try:
            await task
        except asyncio.CancelledError:
            pass

    unload_ok = True
    for platform in ["light", "binary_sensor"]:
        result = await hass.config_entries.async_forward_entry_unload(entry, platform)
        unload_ok = unload_ok and result

    hass.data[DOMAIN].pop(GATEWAY, None)
    hass.data[DOMAIN].pop(SCANNER, None)
    hass.data[DOMAIN].pop(SCANNER_TASK, None)

    return unload_ok