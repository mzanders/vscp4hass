import datetime
import dateutil.parser
from .guid import Guid

class Event:
    def __init__(self, vscp_class=0, vscp_type=0, data=bytearray(), obid=0,
            timestamp=0, head=0,dt=datetime.datetime.utcnow(),guid=Guid()):
        self.timestamp = timestamp
        self.head = head
        self.dt = dt
        self.guid = guid
        self.vscp_class = vscp_class
        self.vscp_type = vscp_type
        self.data = bytearray(data)
        self.obid = obid
        if not isinstance(self.dt, datetime.datetime):
            raise ValueError('invalid date/time')
        if self.vscp_class > 0xffff or self.vscp_class < 0:
            raise ValueError('invalid vscp_class')
        if self.vscp_type > 511 or self.vscp_type < 0:
            raise ValueError('invalid vscp_type')
        if not len(self.data)<64:
            raise ValueError('data too long')

    def __repr__(self):
        repr = f'{self.head},{self.vscp_class},{self.vscp_type},' \
               f'{self.obid},{self.dt.replace(microsecond=0).isoformat()},' \
               f'{self.timestamp},{self.guid}'
        if(len(self.data) > 0):
            repr += f',{",".join([str(b) for b in self.data])}'
        return repr

    @classmethod
    def from_string(cls,input):
        ev = input.split(',')
        head = int(ev[0],base=0)
        vscp_class = int(ev[1],base=0)
        vscp_type = int(ev[2],base=0)
        obid = int(ev[3],base=0)
        dt = dateutil.parser.parse(ev[4])
        timestamp = int(ev[5])
        guid_l = Guid.from_string(ev[6])
        data = bytearray(len(ev)-7)
        for i in range(7,len(ev)):
            data[i-7] = int(ev[i],base=0)
        return cls(vscp_class,vscp_type,data,obid,timestamp,head,dt,guid_l)

    @classmethod
    def from_string_list(cls, input):
        if type(input) is list:
            return [Event.from_string(x) for x in input]
        else:
            raise TypeError('input should be list of bytes')
