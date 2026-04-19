from __future__ import annotations

import time
from typing import Optional

import numpy as np

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

    def get_motion_status_code(self) -> Optional[int]:
        status = self.get_arm_status()
        if status is None:
            return None
        motion_status = getattr(status.msg, "motion_status", None)
        if motion_status is None:
            return None
        try:
            return int(motion_status)
        except Exception:
            return None

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

    def wait_enabled_state(self, expected: bool, timeout: float = 3.0, poll_interval: float = 0.05) -> bool:
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            enabled_list = self.get_enabled_list()
            if expected and all(enabled_list):
                return True
            if not expected and not any(enabled_list):
                return True
            time.sleep(max(0.02, float(poll_interval)))
        return False

    def enable_and_wait(self, timeout: float = 3.0) -> bool:
        self.enable()
        return self.wait_enabled_state(True, timeout=timeout)

    def disable_and_wait(self, timeout: float = 3.0) -> bool:
        self.disable()
        return self.wait_enabled_state(False, timeout=timeout)

    def wait_motion_done(self, timeout: float = 8.0, poll_interval: float = 0.1) -> bool:
        time.sleep(0.5)
        start_time = time.monotonic()
        while True:
            motion_status = self.get_motion_status_code()
            if motion_status == 0:
                return True
            if time.monotonic() - start_time > timeout:
                return False
            time.sleep(max(0.02, float(poll_interval)))

    @staticmethod
    def _pose_error(current_pose: list[float], target_pose: list[float]) -> tuple[float, float]:
        current_xyz = np.asarray(current_pose[:3], dtype=np.float64)
        target_xyz = np.asarray(target_pose[:3], dtype=np.float64)
        translation_error = float(np.linalg.norm(current_xyz - target_xyz))

        current_rpy = np.asarray(current_pose[3:6], dtype=np.float64)
        target_rpy = np.asarray(target_pose[3:6], dtype=np.float64)
        rotation_error = float(np.degrees(np.linalg.norm(current_rpy - target_rpy)))
        return translation_error, rotation_error

    def wait_tcp_pose_reached(
        self,
        target_pose: list[float],
        timeout: float = 8.0,
        poll_interval: float = 0.1,
        translation_tol_m: float = 0.015,
        rotation_tol_deg: float = 8.0,
    ) -> bool:
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            current_pose = self.get_tcp_pose()
            if current_pose is not None:
                translation_error, rotation_error = self._pose_error(current_pose, target_pose)
                if translation_error <= translation_tol_m and rotation_error <= rotation_tol_deg:
                    return True
            time.sleep(max(0.02, float(poll_interval)))
        return False

    def wait_joint_pose_reached(
        self,
        target_joint_angles: list[float],
        timeout: float = 8.0,
        poll_interval: float = 0.1,
        joint_tol_rad: float = 0.05,
    ) -> bool:
        deadline = time.monotonic() + timeout
        target = np.asarray(target_joint_angles, dtype=np.float64)
        saw_motion = False
        while time.monotonic() < deadline:
            current = self.get_joint_angles()
            if current is not None:
                current_arr = np.asarray(current, dtype=np.float64)
                if current_arr.shape == target.shape:
                    max_error = float(np.max(np.abs(current_arr - target)))
                    if max_error <= joint_tol_rad:
                        return True
                    motion_status = self.get_motion_status_code()
                    if motion_status is not None and motion_status != 0:
                        saw_motion = True
                    if saw_motion and motion_status == 0 and max_error <= joint_tol_rad * 2.0:
                        return True
            time.sleep(max(0.02, float(poll_interval)))
        return False

    def get_tcp2flange_pose(self, tcp_pose: list[float]) -> list[float]:
        return self.robot.get_tcp2flange_pose(list(tcp_pose))

    def move_tcp_pose(self, tcp_pose: list[float], timeout: float = 8.0) -> bool:
        flange_pose = self.get_tcp2flange_pose(tcp_pose)
        self.robot.move_p(flange_pose)
        return self.wait_tcp_pose_reached(tcp_pose, timeout=timeout)

    def move_linear_tcp_pose(self, tcp_pose: list[float], timeout: float = 8.0) -> bool:
        flange_pose = self.get_tcp2flange_pose(tcp_pose)
        self.robot.move_l(flange_pose)
        return self.wait_tcp_pose_reached(tcp_pose, timeout=timeout)

    def move_joint_pose(self, joint_angles: list[float], timeout: float = 8.0) -> bool:
        self.robot.move_j(list(joint_angles))
        return self.wait_joint_pose_reached(joint_angles, timeout=timeout)

    def command_joint_pose(self, joint_angles: list[float]) -> None:
        self.robot.move_j(list(joint_angles))

    def move_gripper_width(self, width_m: float, force_n: float = 1.0, settle_s: float = 0.8) -> None:
        if self._gripper is None:
            raise RuntimeError("Gripper is not initialized.")
        self._gripper.move_gripper_m(value=float(width_m), force=float(force_n))
        time.sleep(max(0.0, float(settle_s)))
