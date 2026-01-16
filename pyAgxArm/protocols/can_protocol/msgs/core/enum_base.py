from enum import IntEnum

class EnumBase(IntEnum):
    def __str__(self):
        # return f"{self.__class__.__name__}.{self.name}(0x{self.value:X})"
        return f"{self.name}(0x{self.value:X})"
    def __repr__(self):
        # return f"{self.__class__.__name__}.{self.name}(0x{self.value:X})"
        return f"{self.name}(0x{self.value:X})"
    @classmethod
    def match_value(cls, val):
        if not isinstance(val, int):
            raise ValueError(f"{cls.__name__}: input value must be an integer, got {type(val).__name__}")
        try:
            return cls(val)
        except ValueError:
            if hasattr(cls, "UNKNOWN"):
                return cls.UNKNOWN
            else:
                raise ValueError(f"{cls.__name__}: invalid enum value 0x{val:X}, and no UNKNOWN defined")