class Guid:
    def __init__(self, input=None):
        if input == None:
            self.guid_d = None
            return
        if not isinstance(input, (bytearray, bytes)):
            raise ValueError('input has to be bytearray or bytes')
        if len(input) != 16:
            raise ValueError('input has to be 16 bytes')
        self.guid_d = bytearray(input)

    def __repr__(self):
        if self.guid_d == None:
            return ''
        else:
            sa = [format("%02X" % a) for a in self.guid_d]
            return ( ":" . join(sa))

    @classmethod
    def valid(cls, inst):
        if not isinstance(inst, Guid):
            raise ValueError('not a guid class')
        if len(inst.guid_d) != 16:
            raise ValueError('guid has to be 16 bytes')

    @classmethod
    def from_string(cls, guidstr):
        if guidstr == '':
            return cls()
        else:
            return cls(bytes(int(z,16) for z in guidstr.split(':')))

    @classmethod
    def clear(cls):
        return cls(bytearray(16))

    @classmethod
    def set(cls):
        return cls(bytearray(b'/xFF')*16)

    @property
    def nickname(self):
        if self.guid_d == None:
            return None
        else:
            return self.guid_d[15]

    @nickname.setter
    def nickname(self, value):
        if value > 255 or value < 0:
            raise ValueError
        self.guid_d[15] = value
