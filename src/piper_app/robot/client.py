from __future__ import annotations

import time
from typing import Optional

from pyAgxArm import AgxArmFactory, PiperFW

from .factory import PiperConnectionConfig, build_robot_config, infer_piper_fw


class PiperRobotClient:
    def __init__(self, config: PiperConnectionConfig):
        self.config = config
        self._robot = None
        self._gripper = None
        self._firmware_info: dict = {}

    @property
    def robot(self):
        if self._robot is None:
            raise RuntimeError("Robot is not connected.")
        return self._robot

    @property
    def gripper(self):
        return self._gripper

    @property
    def firmware_info(self) -> dict:
        return self._firmware_info

    @property
    def software_version(self) -> str:
        return self._firmware_info.get("software_version", "unknown")

    def probe_firmware(self) -> tuple[str, dict]:
        cfg = build_robot_config(self.config, firmware=PiperFW.DEFAULT)
        robot = AgxArmFactory.create_arm(cfg)
        robot.connect()
        try:
            deadline = time.monotonic() + self.config.firmware_timeout
            while time.monotonic() < deadline:
                fw = robot.get_firmware(timeout=0.2, min_interval=0.2)
                if fw is not None:
                    return infer_piper_fw(fw["software_version"]), fw
                time.sleep(0.05)
        finally:
            robot.disconnect()
        raise TimeoutError(
            f"Timed out waiting for firmware on {self.config.channel}. Check CAN and robot power."
        )

    def connect(self, configure_robot: bool = True, init_gripper: bool = True) -> None:
        firmware_kind, firmware_info = self.probe_firmware()
        cfg = build_robot_config(self.config, firmware=firmware_kind)
        robot = AgxArmFactory.create_arm(cfg)
        gripper = None
        if init_gripper:
            gripper = robot.init_effector(robot.OPTIONS.EFFECTOR.AGX_GRIPPER)
        robot.connect()
        if configure_robot:
            robot.set_speed_percent(int(self.config.speed_percent))
            robot.set_tcp_offset(self.config.tcp_offset)
        time.sleep(0.2)

        self._robot = robot
        self._gripper = gripper
        self._firmware_info = firmware_info

    def disconnect(self) -> None:
        robot = self._robot
        self._robot = None
        self._gripper = None
        self._firmware_info = {}
        if robot is not None:
            robot.disconnect()

    def reconnect(self) -> None:
        self.disconnect()
        time.sleep(0.1)
        self.connect()

    def set_speed_percent(self, speed_percent: int) -> int:
        speed = max(1, min(100, int(speed_percent)))
        self.config.speed_percent = speed
        if self._robot is not None:
            self._robot.set_speed_percent(speed)
        return speed

    def set_tcp_offset(self, tcp_offset: list[float]) -> None:
        self.config.tcp_offset = [float(value) for value in tcp_offset]
        if self._robot is not None:
            self._robot.set_tcp_offset(self.config.tcp_offset)

    def get_tcp_pose(self) -> Optional[list[float]]:
        if self._robot is None:
            return None
        measured = self._robot.get_tcp_pose()
        return None if measured is None else measured.msg

    def get_joint_angles(self) -> Optional[list[float]]:
        if self._robot is None:
            return None
        measured = self._robot.get_joint_angles()
        return None if measured is None else measured.msg

    def get_arm_status(self):
        if self._robot is None:
            return None
        return self._robot.get_arm_status()

    def get_enabled_list(self) -> list[bool]:
        if self._robot is None:
            return [False] * 6
        return self._robot.get_joints_enable_status_list()

    def get_gripper_status(self):
        if self._gripper is None:
            return None
        return self._gripper.get_gripper_status()

    def get_gripper_teaching_pendant_param(self, timeout: float = 0.5, min_interval: float = 0.0):
        if self._gripper is None:
            return None
        return self._gripper.get_gripper_teaching_pendant_param(
            timeout=timeout,
            min_interval=min_interval,
        )

    def enable(self) -> None:
        self.robot.enable()

    def disable(self) -> None:
        self.robot.disable()

    def electronic_emergency_stop(self) -> None:
        self.robot.electronic_emergency_stop()
