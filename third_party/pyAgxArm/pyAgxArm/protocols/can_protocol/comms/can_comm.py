#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import can
from can.message import Message
from enum import IntEnum, auto
from platform import system

from .core.can_comm_base import CanCommBase
from .can_sys_utils import CanSystemInfoBase, LinuxSocketCanSystemInfo

_SUPPORTED_PLATFORMS = {"Linux", "Windows", "Darwin"}


def create_can_comm_config(
    *,
    channel: str = "can0",
    interface: str = "socketcan",
    bitrate: int = 1_000_000,
    enable_check_can: bool = True,
    auto_connect: bool = True,
    timeout: float = 0.001,
    receive_own_messages: bool = False,
    local_loopback: bool = False,
):
    return {
        "channel": channel,
        "interface": interface,
        "bitrate": bitrate,
        "enable_check_can": enable_check_can,
        "auto_connect": auto_connect,
        "timeout": timeout,
        "receive_own_messages": receive_own_messages,
        "local_loopback": local_loopback,
    }


class CanComm:
    """
    Platform selector for python-can based communication.
    """

    def __init__(self, config: dict, comm_type: str = "can"):
        pass

    def __new__(cls, config: dict, comm_type: str = "can"):
        platform_system = system()
        if platform_system not in _SUPPORTED_PLATFORMS:
            supported_text = ", ".join(sorted(_SUPPORTED_PLATFORMS))
            raise RuntimeError(
                f"Unsupported platform: {platform_system}. "
                f"Supported platforms: {supported_text}."
            )
        return CanCommImpl(config, comm_type)


class CanCommImpl(CanCommBase):
    class CAN_STATUS(IntEnum):
        UNKNOWN = 100001
        INIT_CAN_BUS_IS_EXIST = auto()
        INIT_CAN_BUS_OPENED_SUCCESS = auto()
        INIT_CAN_BUS_OPENED_FAILED = auto()
        CLOSE_CAN_BUS_CONNECT_SHUT_DOWN = auto()
        CLOSE_CAN_BUS_WAS_NOT_PROPERLY_INIT = auto()
        CLOSE_SHUTTING_DOWN_CAN_BUS_ERR = auto()
        CLOSED_CAN_BUS_NOT_OPEN = auto()
        READ_CAN_MSG_OK = auto()
        READ_CAN_MSG_OK_NO_CB = auto()
        READ_CAN_MSG_TIMEOUT = auto()
        READ_CAN_MSG_FAILED = auto()
        SEND_MESSAGE_SUCCESS = auto()
        SEND_MESSAGE_FAILED = auto()
        SEND_CAN_BUS_NOT_OK = auto()
        BUS_STATE_ACTIVE = auto()
        BUS_STATE_PASSIVE = auto()
        BUS_STATE_ERROR = auto()
        BUS_STATE_UNKNOWN = auto()

        def __str__(self):
            return f"{self.name} ({self.value})"

        def __repr__(self):
            return f"{self.name}: {self.value}"

    def __init__(self, config: dict, comm_type: str = "can") -> None:
        super().__init__()
        self.recv_bus = None
        self.send_bus = None
        self.sysinfo: CanSystemInfoBase = None
        self._last_recv_error = None
        self._config = config.copy()
        self._comm_type = comm_type
        self._platform_system = system()
        self._type = self._comm_type
        self._channel = self._config["channel"]
        self._interface = (
            self._config["interface"]
            if "interface" in self._config
            else self._config.get("bustype", "socketcan")
        )
        self._bitrate = self._config.get("bitrate", 1000000)
        self._enable_check_can = self._config.get("enable_check_can", False)
        self._auto_connect = self._config.get("auto_connect", False)
        self._timeout = self._config.get("timeout", 0.001)
        self._receive_own_messages = self._config.get("receive_own_messages", False)
        self._local_loopback = self._config.get("local_loopback", False)
        self._is_connected = False
        self._is_stopped = False
        if self._interface == "socketcan":
            self.sysinfo = LinuxSocketCanSystemInfo
        if self._enable_check_can and self.sysinfo is not None:
            self.check_can()
        if self._auto_connect:
            self.connect()

    def __del__(self):
        try:
            self.close()
        except Exception:
            pass

    @staticmethod
    def _shutdown_bus(bus) -> None:
        if bus is None:
            return
        try:
            bus.shutdown()
        except Exception:
            pass

    def _reset_connection_state(self) -> None:
        self.recv_bus = None
        self.send_bus = None
        self._last_recv_error = None
        self._is_connected = False
        self._is_stopped = False

    def connect(self, **kwargs):
        if self.recv_bus is not None and self.send_bus is not None:
            return True

        common_kwargs = dict(
            channel=self._channel,
            interface=self._interface,
            bitrate=self._bitrate,
            receive_own_messages=self._receive_own_messages,
            local_loopback=self._local_loopback,
        )

        recv_bus = None
        send_bus = None
        try:
            recv_bus = can.ThreadSafeBus(**common_kwargs)
            if self._interface == "socketcan":
                send_bus = can.ThreadSafeBus(**common_kwargs)
            else:
                send_bus = recv_bus
        except Exception as exc:
            self._shutdown_bus(recv_bus)
            if send_bus is not recv_bus:
                self._shutdown_bus(send_bus)
            self._reset_connection_state()
            raise can.CanInitializationError(
                f"Failed to open CAN bus on {self._platform_system} "
                f"(interface='{self._interface}', channel='{self._channel}', bitrate={self._bitrate}): {exc}"
            ) from exc

        self.recv_bus = recv_bus
        self.send_bus = send_bus
        self._last_recv_error = None
        self._is_connected = True
        self._is_stopped = False
        return True

    def close(self):
        recv_bus = getattr(self, "recv_bus", None)
        send_bus = getattr(self, "send_bus", None)
        if recv_bus is None or send_bus is None:
            return self.CAN_STATUS.CLOSED_CAN_BUS_NOT_OPEN

        self.recv_bus = None
        self.send_bus = None
        try:
            recv_bus.shutdown()
            if send_bus is not recv_bus:
                send_bus.shutdown()
            self._last_recv_error = None
            self._is_connected = False
            self._is_stopped = True
            return self.CAN_STATUS.CLOSE_CAN_BUS_CONNECT_SHUT_DOWN
        except AttributeError:
            return self.CAN_STATUS.CLOSE_CAN_BUS_WAS_NOT_PROPERLY_INIT
        except Exception:
            return self.CAN_STATUS.CLOSE_SHUTTING_DOWN_CAN_BUS_ERR

    def send(self, msg: Message, timeout=None):
        if self.send_bus is None:
            raise RuntimeError("CAN bus is not connected. Call `connect()` first.")

        bus_status = self._get_states(self.send_bus)
        if bus_status != self.CAN_STATUS.BUS_STATE_ACTIVE:
            raise can.CanOperationError(
                f"CAN bus is not active for send "
                f"(interface='{self._interface}', channel='{self._channel}', status={bus_status})."
            )

        try:
            self.send_bus.send(msg, timeout)
            return True
        except Exception as exc:
            raise can.CanOperationError(
                f"Failed to send CAN message on interface='{self._interface}', "
                f"channel='{self._channel}': {exc}"
            ) from exc

    def recv(self):
        if self.recv_bus is None:
            raise RuntimeError("CAN bus is not connected. Call `connect()` first.")

        can_bus_status = self._get_states(self.recv_bus)
        if can_bus_status not in {
            self.CAN_STATUS.BUS_STATE_ACTIVE,
            self.CAN_STATUS.BUS_STATE_PASSIVE,
            self.CAN_STATUS.BUS_STATE_UNKNOWN,
        }:
            raise can.CanOperationError(
                f"CAN bus is not readable on interface='{self._interface}', "
                f"channel='{self._channel}', status={can_bus_status}."
            )

        try:
            rx_message = self._read_message()
        except Exception as exc:
            self._last_recv_error = exc
            raise can.CanOperationError(
                f"Failed to receive CAN message on interface='{self._interface}', "
                f"channel='{self._channel}': {exc}"
            ) from exc

        if rx_message is None:
            return None
        if self.has_callback():
            self._trigger_callback(rx_message)
        return rx_message

    def _read_message(self):
        return self.recv_bus.recv(self._timeout)

    def _get_states(self, bus=None):
        if isinstance(bus, can.BusABC):
            bus_state = bus.state
        else:
            bus_state = None
        if bus_state == can.BusState.ACTIVE:
            return self.CAN_STATUS.BUS_STATE_ACTIVE
        if bus_state == can.BusState.PASSIVE:
            return self.CAN_STATUS.BUS_STATE_PASSIVE
        if bus_state == can.BusState.ERROR:
            return self.CAN_STATUS.BUS_STATE_ERROR
        return self.CAN_STATUS.BUS_STATE_UNKNOWN

    def check_can(self):
        if not self.sysinfo.is_exists(self._channel):
            raise ValueError(f"CAN socket {self._channel} does not exist.")
        if not self.sysinfo.is_up(self._channel):
            raise RuntimeError(f"CAN port {self._channel} is not UP.")
        actual_bitrate = self.sysinfo.get_bitrate(self._channel)
        if (
            self._bitrate is not None
            and actual_bitrate is not None
            and actual_bitrate != self._bitrate
        ):
            raise ValueError(
                f"CAN port {self._channel} bitrate is {actual_bitrate} bps, expected {self._bitrate} bps."
            )
