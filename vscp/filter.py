from .guid import Guid

class Filter():
    def __init__(self, priority, mask_priority, event_class, mask_class,
                 type, mask_type, guid=Guid.clear(), mask_guid=Guid.clear()):
        self.priority = priority
        self.mask_priority = mask_priority
        self.event_class = event_class
        self.mask_class = mask_class
        self.type = type
        self.mask_type = mask_type
        self.guid = guid
        self.mask_guid = mask_guid
        if self.priority not in range(0,7):
            raise ValueError('0 <= priority <= 7')
        if self.mask_priority not in range(0,8):
            raise ValueError('0 <= priority mask <= 7')
        if self.event_class not in range(0, 2**10):
            raise ValueError('0 <= class <= 1023')
        if self.mask_class not in range(0, 2**10):
            raise ValueError('0 <= mask_class <= 1023')
        if self.type not in range(0, 2**8):
            raise ValueError('0 <= type <= 255')
        if self.mask_type not in range(0, 2**8):
            raise ValueError('0 <= mask_type <= 255')
        guid.valid(self.guid)
        guid.valid(self.mask_guid)

    @classmethod
    def clear(cls):
        return cls(0, 0x7, 0, 0xffff, 0, 0x1FF, guid.clear(), guid.set())

    def filter_str(self):
        return f'{self.priority},{self.event_class},{self.type},{self.guid}'

    def filter_mask_str(self):
        return f'{self.mask_priority},{self.mask_class},{self.mask_type},{self.mask_guid}'
