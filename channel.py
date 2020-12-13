channel_reg = {}


class DuplicateIdentifierError(Exception):
    pass


class Channel:
    """Base class for all channel classes to derive from"""
    def __init_subclass__(cls, **kwargs):
        super().__init_subclass__(**kwargs)
        # todo: check if cls.identifier exist, handle exception accordingly
        if cls.identifier() in channel_reg:
            raise DuplicateIdentifierError()
        channel_reg[cls.identifier()] = cls
