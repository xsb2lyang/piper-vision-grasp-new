#!/usr/bin/env python3
# -*-coding:utf8-*-
from .....core.attritube_base import AttributeBase
from typing import Union


class GripperFocStatus(AttributeBase):
    def __init__(self):
        self.voltage_too_low = False
        self.motor_overheating = False
        self.driver_overcurrent = False
        self.driver_overheating = False
        self.sensor_status = False
        self.driver_error_status = False
        self.driver_enable_status = False
        self.homing_status = False


class ArmMsgFeedbackGripper(AttributeBase):
    """
    feedback

    夹爪反馈消息

    Gripper Feedback Message

    CAN ID:
        0x2A8

    Args:
        width: 夹爪张开宽度（原始整数值，单位：µm）
        force: 夹持力（原始整数值，单位：mN）
        status_code: 夹爪状态码（uint8）

    位描述 / Byte Definitions:

        Byte 0-3: width_um (int32), unit: µm
            - Physical: width_m = width_um * 1e-6
        Byte 4-5: force_mN (int16), unit: mN
            - Physical: force_N = force_mN * 1e-3
        Byte 6: status_code (uint8)
            bit[0] Power voltage low (0: Normal, 1: Low)
            bit[1] Motor over-temperature (0: Normal, 1: Over-temperature)
            bit[2] Driver over-current (0: Normal, 1: Over-current)
            bit[3] Driver over-temperature (0: Normal, 1: Over-temperature)
            bit[4] Sensor status (0: Normal, 1: Abnormal)
            bit[5] Driver error status (0: Normal, 1: Error)
            bit[6] Driver enable status (1: Enabled, 0: Disabled)
            bit[7] Zeroing status (0: Not zeroed, 1: Zeroed or previously zeroed)
        Byte 7: Reserved
    """

    def __init__(
        self, width: Union[int, float] = 0, force: Union[int, float] = 0, status_code: int = 0
    ):
        self.width = width
        self.force = force
        self._status_code = status_code
        self.foc_status = GripperFocStatus()

    @property
    def status_code(self):
        return self._status_code

    @status_code.setter
    def status_code(self, value: int):
        if not (0 <= value < 2**8):
            raise ValueError("status_code must be an 8-bit integer between 0 and 255.")
        self._status_code = value
        # Update foc_status based on the status_code bits
        self.foc_status.voltage_too_low = bool(value & (1 << 0))
        self.foc_status.motor_overheating = bool(value & (1 << 1))
        self.foc_status.driver_overcurrent = bool(value & (1 << 2))
        self.foc_status.driver_overheating = bool(value & (1 << 3))
        self.foc_status.sensor_status = bool(value & (1 << 4))
        self.foc_status.driver_error_status = bool(value & (1 << 5))
        self.foc_status.driver_enable_status = bool(value & (1 << 6))
        self.foc_status.homing_status = bool(value & (1 << 7))


__all__ = ["ArmMsgFeedbackGripper", "GripperFocStatus"]
