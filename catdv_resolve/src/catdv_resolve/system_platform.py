from __future__ import annotations
from enum import Enum, auto
import platform


class Platform(Enum):
    Unknown = auto()
    OSX = auto()
    Linux = auto()
    Windows = auto()

    @classmethod
    def determine(cls) -> Platform:
        system_name = platform.system()
        if system_name == "Darwin":
            return cls.OSX
        elif system_name == "Linux":
            return cls.Linux
        elif system_name == "Windows":
            return cls.Windows
        else:
            return cls.Unknown
