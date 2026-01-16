#!/usr/bin/env python3
# -*-coding:utf8-*-
from typing_extensions import Literal

from ....core.attritube_base import AttributeBase


class ArmMsgMasterArmMoveToHome(AttributeBase):
    """
    transmit

    请求主臂回零指令（基于 V1.7-4 版本后）

    CAN ID:
        0x191

    Args:
        mode: 请求回零模式
            0: 恢复主从臂模式
            1: 主臂回零
            2: 主从臂一起回零
    """
    """
    transmit

    Request Master Arm Move to Home Command (Based on version V1.7-4 and later)

    CAN ID:
        0x191

    Args:
        mode (int): Request return-to-zero mode.
            0: Restore master-slave arm mode.
            1: Master arm return-to-zero.
            2: Master and slave arms return-to-zero together.
    """

    def __init__(self, mode: Literal[0, 1, 2] = 1):
        if mode not in [0, 1, 2]:
            raise ValueError(f"'mode' Value {mode} out of range [0, 1, 2]")
        self.mode = mode


