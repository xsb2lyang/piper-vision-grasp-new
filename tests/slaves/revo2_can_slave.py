import threading
from collections import deque
from typing import Deque

import can

from tests.slaves import _can_payloads as pl

DEVICE_FRAMES_MAX = 8192

_REVO2_CMD_IDS = frozenset({0x1B1, 0x1B2, 0x1B3, 0x1B5})


class Revo2CanSlave:
    """Revo2：主机 0x1Bx 指令后 **单次** 回 0x1C0/0x1C1（不测周期上送）。"""

    def __init__(self, channel: str):
        self._bus = can.Bus(interface="virtual", channel=channel, receive_own_messages=False)
        self._host_frames: Deque[can.Message] = deque(maxlen=DEVICE_FRAMES_MAX)
        self._device_frames: Deque[can.Message] = deque(maxlen=DEVICE_FRAMES_MAX)
        self._lock = threading.Lock()
        self._stop = threading.Event()
        self._th = threading.Thread(target=self._loop, daemon=True)

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

    def _reply_fingers_from_cmd(self, data: bytes) -> None:
        pos = can.Message(
            is_extended_id=False,
            arbitration_id=0x1C1,
            data=pl.pack_revo2_finger_pos_1c1(),
        )
        self._send_and_record(pos)
        hand = can.Message(
            is_extended_id=False,
            arbitration_id=0x1C0,
            data=pl.pack_revo2_hand_status_1c0(),
        )
        self._send_and_record(hand)
        spd = can.Message(
            is_extended_id=False,
            arbitration_id=0x1C2,
            data=pl.pack_revo2_finger_spd_1c2(),
        )
        self._send_and_record(spd)
        current = can.Message(
            is_extended_id=False,
            arbitration_id=0x1C3,
            data=pl.pack_revo2_finger_current_1c3(),
        )
        self._send_and_record(current)

    def _loop(self):
        while not self._stop.is_set():
            frame = self._bus.recv(timeout=0.05)
            if frame is None:
                continue
            with self._lock:
                self._host_frames.append(frame)
            if frame.arbitration_id in _REVO2_CMD_IDS:
                self._reply_fingers_from_cmd(bytes(frame.data))
