import time
import threading
from typing import Callable, TypeVar, Optional, Dict
from ...comms import CommsFactory, create_comm_config
from .....utiles.fps import FPSManager


T = TypeVar('T')


class DriverContext:
    def __init__(self, config: dict):
        self._config = config.copy()
        self.comm = None

        self.fps = FPSManager()
        self.fps.set_cal_fps_time_interval(0.1)

        self._parser_packet_fun_list = []
        self._data_monitor_fun_list = []
        self._read_stop_event = threading.Event()
        self._monitor_stop_event = threading.Event()

        self._read_th = None
        self._monitor_th = None

        self._comm_initialized = False  # 标记是否已初始化

        # Stamp dictionary for request throttling (used by _request_and_get).
        # Key is an arbitrary string (e.g. "firmware", "joint_acc:3").
        self._req_stamp: Dict[str, float] = {}

    def create_comm(self, config: dict={}, comm: str="can"):
        cfg = config or self._config or create_comm_config(comm)
        self.comm = CommsFactory.create_comm(comm, "impl", config=cfg, comm_type=comm)
        return self.comm

    def init_comm(self):
        if self._comm_initialized:
            return self.comm
        comm_cfg = self._config["comm"]
        comm_type = comm_cfg["type"]

        self.comm = CommsFactory.create_comm(
            comm_type,
            "impl",
            config=comm_cfg[comm_type],
            comm_type=comm_type
        )
        self._comm_initialized = True
        self.comm.set_callback(self._run_parser_packet_funs)
    
    def is_comm_init(self):
        return self._comm_initialized

    def get_comm(self):
        return self.comm

    def register_parser_packet_fun(self, cb):
        self._parser_packet_fun_list.append(cb)
    
    def _run_parser_packet_funs(self, rx_data):
        for cb in self._parser_packet_fun_list:
            cb(rx_data)

    def register_data_monitor_fun(self, cb):
        self._data_monitor_fun_list.append(cb)
    
    def _run_data_monitor_funs(self):
        for cb in self._data_monitor_fun_list:
            cb()

    def start_th(self):
        if not self.comm:
            raise NotImplementedError("comm is None!! Please init comm")

        self._read_stop_event.clear()
        self._monitor_stop_event.clear()

        self._read_th = threading.Thread(
            target=self._read_loop, daemon=True
        )
        self._read_th.start()

        self._monitor_th = threading.Thread(
            target=self._monitor_loop, daemon=True
        )
        self._monitor_th.start()

        self.fps.start()

    def _read_loop(self):
        while not self._read_stop_event.is_set():
            self.comm.recv()

    def _monitor_loop(self):
        while not self._monitor_stop_event.is_set():
            self._run_data_monitor_funs()
            time.sleep(0.05)

    # -------------------------
    # Common "request_and_get" helpers
    # -------------------------
    def _validate_timeout(self, timeout: float) -> None:
        """Validate common `timeout` argument."""
        if timeout < 0.0:
            raise ValueError("Timeout should be greater than 0.0")

    def _validate_min_interval(self, min_interval: float) -> None:
        """Validate common `min_interval` argument."""
        if min_interval < 0.0:
            raise ValueError("min_interval should be greater than or equal to 0.0")

    def _wait_for_response(self, func: Callable, timeout: float = 1.0):
        """
        Poll `func()` until it returns truthy or timeout expires.

        Returns
        -------
        bool
            True if `func()` returned True before timeout, False otherwise.
        """
        self._validate_timeout(timeout)

        if timeout == 0.0:
            # Non-blocking mode.
            return func()

        start_time = time.time()
        while time.time() - start_time < timeout:
            if func():
                return True
            time.sleep(0.0005)
        return False

    def _request_and_get(
        self,
        *,
        request: Callable[[], None],
        is_ready: Callable[[], bool],
        get_value: Callable[[], T],
        clear: Optional[Callable[[], None]]= None,
        timeout: float = 1.0,
        min_interval: float = 0.0,
        stamp_attr: str,
    ):
        """
        Compose "request → wait → read cached value → clear cache" into one template.

        This is intended for query/config APIs that follow a request/response pattern:
        - send a request frame (once per `min_interval`)
        - wait for parser-side cache to be updated (`_wait_for_response`)
        - read and optionally clear cached data

        Notes
        -----
        - `timeout == 0.0` runs `is_ready()` once and returns immediately.
        - This function does NOT change the waiting mechanism; it reuses the existing
          polling implementation in `_wait_for_response`.
        """
        self._validate_timeout(timeout)
        self._validate_min_interval(min_interval)

        def throttle_request() -> None:
            last_ts = self._req_stamp.get(stamp_attr, 0.0)
            now = time.time()
            if now - last_ts >= min_interval:
                request()
                self._req_stamp[stamp_attr] = now

        throttle_request()
        if not self._wait_for_response(is_ready, timeout):
            return None

        value = get_value()
        if clear is not None:
            clear()
        self._req_stamp[stamp_attr] = 0.0
        return value
