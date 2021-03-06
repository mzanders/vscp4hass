from homeassistant.const import EVENT_HOMEASSISTANT_STOP
from .vscp.util import who_is_there
from .vscp.tcp import TCP
from .vscp.filter import Filter
from .node import Node


class DuplicateEvent(Exception):
    pass


class Gateway(TCP):
    """This class connects to the SWALI VSCP Gateway."""
    def __init__(self, *args, **kwargs):
        """Initialize a Gateway object"""
        super().__init__(*args, **kwargs)

        self.nodes = dict() # list of nodes
        self.ch = dict() # list of channels for each channel class
        self._channel_events = dict() # event sensitivity list, key = event type+guid+index, value = list of callbacks to call
        self._zone_events = dict()

    async def sub_ch_event(self, nickname, index, vscp_class, vscp_type, callback):
        key = (nickname, index, vscp_class, vscp_type)
        if key in self._channel_events:
            raise DuplicateEvent
        self._channel_events[key] = callback

    async def sub_zone_event(self, vscp_class, vscp_type, vscp_zone, vscp_subzone, callback):
        key = (vscp_zone, vscp_subzone, vscp_class, vscp_type)
        if key in self._zone_events:
            raise DuplicateEvent
        self._zone_events[key] = callback

    async def _process_event(self, event):
        if len(event.data) > 0:
            ch_key = (event.guid.nickname, event.data[0], event.vscp_class, event.vscp_type)
            if ch_key in self._channel_events:
                await self._channel_events[ch_key](event)  # do the callback

        if len(event.data) >= 2:
            print('got event!')
            zone_key = (event.data[1], event.data[2], event.vscp_class, event.vscp_type)
            if zone_key in self._zone_events:
                await self._zone_events[zone_key](event)  # do the callback

    async def start_update(self):
        await self.quitloop()
        flt = Filter(0,0,0,0,0,0)
        await self.setmask(flt)
        await self.setfilter(flt)
        await self.clrall()
        await self.rcvloop(self._process_event)

    async def scan(self, updater):
        """Scan a gateway for devices, build the channel lists"""
        await self.quitloop()

        for nickname in range(128):
            (guid, mdf) = await who_is_there(self, nickname)

            if (guid, mdf) != (None, None):
                node = await Node.new(self, nickname, guid, mdf, updater)
                self.nodes[nickname] = node
