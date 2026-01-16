#!/usr/bin/env python3
# -*-coding:utf8-*-
from typing_extensions import Literal, Union

from .....core.attritube_base import AttributeBase


class ArmMsgGripperCtrl(AttributeBase):
    """
    transmit

    夹爪控制指令

    Gripper Control Command

    CAN ID:
        0x159

    Notes
    -----
    Payload layout (8 bytes):
    - Byte 0-3: width_um (int32), unit: µm
      - Physical: width_m = width_um * 1e-6
    - Byte 4-5: force_mN (int16), unit: mN
      - Physical: force_N = force_mN * 1e-3
    - Byte 6: status_code (uint8)
      - 0x00: disable gripper (driver disable)
      - 0x01: execute width/force control
      - 0x02, 0x03: reserved (protocol-defined)
    - Byte 7: set_zero (uint8)
      - 0xAE: set current position as zero
      - 0x00: no-op

    Args:
        width: raw integer width in µm (NOT meters).
        force: raw integer force in mN (NOT Newton).
        status_code: see above.
        set_zero: 0xAE triggers zeroing.
    """

    def __init__(
        self,
        width: Union[int, float] = 0,
        force: Union[int, float] = 0,
        status_code: Literal[0x00, 0x01, 0x02, 0x03] = 0,
        set_zero: Literal[0x00, 0xAE] = 0,
    ):
        if status_code not in [0x00, 0x01, 0x02, 0x03]:
            raise ValueError(
                f"'status_code' Value {status_code} out of range "
                "[0x00, 0x01, 0x02, 0x03]"
            )
        if not (0 <= force <= 3000):
            raise ValueError(f"'force' Value {force} out of range 0-3000")
        if set_zero not in [0x00, 0xAE]:
            raise ValueError(
                f"'set_zero' Value {set_zero} out of range [0x00,0xAE]"
            )
        self.width = width
        self.force = force
        self.status_code = status_code
        self.set_zero = set_zero


__all__ = ["ArmMsgGripperCtrl"]
