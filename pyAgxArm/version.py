#!/usr/bin/env python3
# -*-coding:utf8-*-

from enum import Enum, auto

class AgxArmVersion(Enum):
    AGX_ARM_VERSION_1_0_1 = '1.0.1'
    CURRENT_VERSION = AGX_ARM_VERSION_1_0_1

    VERSION_UNKNOWN = 'unknown'
    def __str__(self):
        return f"{self.name} ({self.value})"
    def __repr__(self):
        return f"{self.name}: {self.value}"


__version__ = AgxArmVersion.CURRENT_VERSION.value