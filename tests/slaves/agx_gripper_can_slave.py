import threading
from typing import List

import can

from tests.slaves import _can_payloads as pl


class AgxGripperCanSlave:
    """夹爪模拟从机：主机 0x159 -> 0x2A8 状态反馈 + 0x159 控制回显（与 agx_gripper Parser RX 表一致）。"""

    def __init__(self, channel: str):
        self._bus = can.Bus(interface="virtual", channel=channel, receive_own_messages=False)
        self._host_frames: List[can.Message] = []
        self._device_frames: List[can.Message] = []
        self._lock = threading.Lock()
        self._stop = threading.Event()
        self._th = threading.Thread(target=self._loop, daemon=True)
        self._tp_range = 100
        self._tp_max_range_mm = 70
        self._tp_friction = 1

    def start(self):
        self._th.start()

    def stop(self):
        self._stop.set()
        self._th.join(timeout=1.0)
        self._bus.shutdown()

    @property
    def host_frames(self):
        with self._lock:
            return list(self._host_frames)

    @property
    def device_frames(self):
        with self._lock:
            return list(self._device_frames)

    def _send_and_record(self, msg: can.Message) -> None:
        self._bus.send(msg, timeout=0.2)
        with self._lock:
            self._device_frames.append(msg)

    def _reply_to_159(self, data: bytes) -> None:
        fb_2a8 = can.Message(
            is_extended_id=False,
            arbitration_id=0x2A8,
            data=pl.pack_gripper_feedback_2a8(0, 0, 0, 0),
        )
        self._send_and_record(fb_2a8)

        echo_159 = can.Message(
            is_extended_id=False,
            arbitration_id=0x159,
            data=bytes(data.ljust(8, b"\x00")[:8]),
        )
        self._send_and_record(echo_159)

    def _reply_to_477(self, data: bytes) -> None:
        d = data.ljust(8, b"\x00")
        if d[3] == 0xAE:
            m = can.Message(
                is_extended_id=False,
                arbitration_id=0x476,
                data=pl.pack_set_instruction_response(0x77, 0),
            )
            self._send_and_record(m)
        if d[0] == 0x04:
            m = can.Message(
                is_extended_id=False,
                arbitration_id=0x47E,
                data=pl.pack_gripper_teaching_pendant_param_47e(
                    self._tp_range, self._tp_max_range_mm, self._tp_friction
                ),
            )
            self._send_and_record(m)

    def _reply_to_47d(self, data: bytes) -> None:
        d = data.ljust(8, b"\x00")
        self._tp_range = int(d[0])
        self._tp_max_range_mm = int(d[1])
        self._tp_friction = int(d[2])
        self._send_and_record(
            can.Message(
                is_extended_id=False,
                arbitration_id=0x476,
                data=pl.pack_set_instruction_response(0x7D, 0),
            )
        )
        self._send_and_record(
            can.Message(
                is_extended_id=False,
                arbitration_id=0x47E,
                data=pl.pack_gripper_teaching_pendant_param_47e(
                    self._tp_range, self._tp_max_range_mm, self._tp_friction
                ),
            )
        )

    def _loop(self):
        while not self._stop.is_set():
            frame = self._bus.recv(timeout=0.05)
            if frame is None:
                continue
            with self._lock:
                self._host_frames.append(frame)
            aid = frame.arbitration_id
            payload = bytes(frame.data)
            if aid == 0x159:
                self._reply_to_159(payload)
            elif aid == 0x477:
                self._reply_to_477(payload)
            elif aid == 0x47D:
                self._reply_to_47d(payload)
