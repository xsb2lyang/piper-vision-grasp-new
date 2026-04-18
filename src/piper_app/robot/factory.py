from __future__ import annotations

from dataclasses import dataclass, field
from platform import system
from typing import Iterable, Tuple

from pyAgxArm import ArmModel, PiperFW, create_agx_arm_config


@dataclass
class PiperConnectionConfig:
    robot: str = ArmModel.PIPER
    interface: str = "socketcan"
    channel: str = "can0"
    bitrate: int = 1_000_000
    firmware_timeout: float = 5.0
    speed_percent: int = 10
    tcp_offset: list[float] = field(default_factory=lambda: [0.0] * 6)


def resolve_can_backend() -> Tuple[str, str]:
    platform_system = system()
    if platform_system == "Windows":
        return "agx_cando", "0"
    if platform_system == "Linux":
        return "socketcan", "can0"
    if platform_system == "Darwin":
        return "slcan", "/dev/ttyACM0"
    raise RuntimeError(
        "This workspace currently supports Linux `socketcan`, Windows `agx_cando`, and macOS `slcan`."
    )


def resolve_can_backend_defaults(
    interface: str | None,
    channel: str | None,
) -> Tuple[str, str]:
    auto_interface, auto_channel = resolve_can_backend()
    resolved_interface = auto_interface if interface in (None, "", "auto") else interface
    resolved_channel = auto_channel if channel in (None, "", "auto") else channel
    return resolved_interface, resolved_channel


def infer_piper_fw(software_version: str) -> str:
    if software_version >= "S-V1.8-8":
        return PiperFW.V188
    if software_version >= "S-V1.8-3":
        return PiperFW.V183
    return PiperFW.DEFAULT


def normalize_tcp_offset(values: Iterable[float]) -> list[float]:
    items = [float(value) for value in values]
    if len(items) != 6:
        raise ValueError("tcp_offset must contain exactly 6 values.")
    return items


def build_robot_config(config: PiperConnectionConfig, firmware: str) -> dict:
    return create_agx_arm_config(
        robot=config.robot,
        firmeware_version=firmware,
        interface=config.interface,
        channel=config.channel,
        bitrate=config.bitrate,
        enable_check_can=True,
    )
