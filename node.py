from .vscp.const import (STD_REG_STD_DEV,
                         STD_REG_PAGES,
                         STD_REG_UID)
from .vscp.util import write_reg, read_reg, read_std_reg
from .channel import channel_reg

CHANNEL_TYPE = 0
CHANNEL_TYPE_SIZE = 2

class Node:
    @classmethod
    async def new(cls, bus, nickname, guid=None, mdf=None):
        self = cls()
        self.bus = bus
        self.nickname = nickname
        self.guid = guid
        self.stddev = await read_std_reg(bus, nickname, STD_REG_STD_DEV)

        self.is_vscp4hass = True if self.stddev == b'HASS\0\0\0\0' else False

        if self.is_vscp4hass:
            self.channels = dict()
            for channel_type in channel_reg:
                self.channels[channel_type] = dict()

            for channel in range(256):
                channel_type = (await read_reg(bus, nickname, channel, CHANNEL_TYPE, num=CHANNEL_TYPE_SIZE)).decode("utf-8")
                if channel_type == b'\0\0'.decode("utf-8"):
                    break
                elif channel_type in channel_reg:
                    self.channels[channel_type][(nickname, channel)] = await channel_reg[channel_type].new(self, channel)

        return self

    def get_channels(self, identifier):
        if not self.is_vscp4hass:
            return list()

        return self.channels[identifier].values()
