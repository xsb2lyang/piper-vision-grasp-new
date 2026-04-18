from __future__ import annotations

import math
import time
from typing import Callable, List


def wrap_to_pi(angle: float) -> float:
    return (angle + math.pi) % (2.0 * math.pi) - math.pi


def clamp_tcp_pose(pose: List[float]) -> List[float]:
    pose = pose[:]
    pose[3] = wrap_to_pi(pose[3])
    pose[4] = max(-math.pi / 2.0, min(math.pi / 2.0, pose[4]))
    pose[5] = wrap_to_pi(pose[5])
    return pose


def wait_bool(fn: Callable[[], bool], timeout: float = 3.0, interval: float = 0.05) -> bool:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if fn():
            return True
        time.sleep(interval)
    return False
