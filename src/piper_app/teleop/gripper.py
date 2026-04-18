from __future__ import annotations

from dataclasses import dataclass
from typing import Optional


DEFAULT_GRIPPER_MAX_RANGE_M = 0.07
DEFAULT_GRIPPER_STEP_M = 0.005
DEFAULT_GRIPPER_FORCE_N = 1.0


@dataclass
class GripperSnapshot:
    mode: str = "width"
    value: Optional[float] = None
    force_feedback: Optional[float] = None
    driver_enabled: Optional[bool] = None
    homed: Optional[bool] = None
    sensor_ok: Optional[bool] = None
    driver_error: Optional[bool] = None
    status_text: str = "Not connected"


def build_gripper_snapshot(status_message) -> GripperSnapshot:
    if status_message is None:
        return GripperSnapshot()
    foc_status = status_message.msg.foc_status
    return GripperSnapshot(
        mode=status_message.msg.mode,
        value=status_message.msg.value,
        force_feedback=status_message.msg.force,
        driver_enabled=foc_status.driver_enable_status,
        homed=foc_status.homing_status,
        sensor_ok=not foc_status.sensor_status,
        driver_error=foc_status.driver_error_status,
        status_text=(
            f"enabled={foc_status.driver_enable_status} "
            f"homed={foc_status.homing_status} "
            f"sensor_ok={not foc_status.sensor_status} "
            f"driver_error={foc_status.driver_error_status}"
        ),
    )
