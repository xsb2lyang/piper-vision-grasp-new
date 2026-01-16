import threading
from typing import Optional, TYPE_CHECKING, overload, List

from typing_extensions import Literal, Final
from .arm_driver_interface import ArmDriverInterface
from .driver_context import DriverContext
from ...msgs.core import AttributeBase
from .protocol_parser_interface import ProtocolParserInterface
from ..core.arm_driver_context import ArmDriverContext

if TYPE_CHECKING:
    from ..effector.agx_gripper import AgxGripperDriverDefault
    from ..effector.revo2 import Revo2DriverDefault


class ArmDriverAbstract(ArmDriverInterface):
    _instances = {}
    _lock = threading.Lock()

    _JOINT_NUMS = 6
    _JOINT_INDEX_LIST = [i for i in range(1, _JOINT_NUMS + 1)] + [255]

    _Parser = ProtocolParserInterface

    class EFFECTOR:
        """
        End-effector kind constants.

        Use:
            robot.init_effector(robot.EFFECTOR.AGX_GRIPPER)
        """

        AGX_GRIPPER: Final[Literal["agx_gripper"]] = "agx_gripper"
        REVO2: Final[Literal["revo2"]] = "revo2"

    def __init_subclass__(cls, **kwargs):
        super().__init_subclass__(**kwargs)
        cls._JOINT_INDEX_LIST = [i for i in range(1, cls._JOINT_NUMS + 1)] + [255]

    def __init__(self, config: dict):
        self._config = config.copy()
        self._ctx = DriverContext(config)
        self._connected = False
        self._effector_kind: Optional[str] = None
        self._effector = None
        self._parser = self._Parser(self._ctx.fps)
        self._arm_ctx = ArmDriverContext(config, self._ctx, self._parser)

    def _send_msg(self, msg: AttributeBase) -> None:
        """Send one control message.

        Parameters
        ----------
        `msg`: AttributeBase
        - The message to send.
        """
        if isinstance(msg, AttributeBase):
            data = self._parser.pack(msg)
            if data is not None:
                self._ctx.get_comm().send(data)
        else:
            raise TypeError(
                "msg must be AttributeBase"
            )

    def _send_msgs(
        self,
        msgs: List[AttributeBase]
    ) -> None:
        """Send a sequence of control messages (with optional intervals).

        Parameters
        ----------
        `msgs`: list[AttributeBase]
        - The messages to send.
        """
        if isinstance(msgs, list):
            for i, msg in enumerate(msgs):
                self._send_msg(msg)
        else:
            raise TypeError(
                "msgs must be a list of AttributeBase"
            )

    @property
    def joint_nums(self):
        return self._JOINT_NUMS
    
    def get_context(self):
        return self._ctx

    @overload
    def init_effector(
        self, effector: Literal["agx_gripper"]
    ) -> "AgxGripperDriverDefault":
        ...

    @overload
    def init_effector(
        self, effector: Literal["revo2"]
    ) -> "Revo2DriverDefault":
        ...

    def init_effector(self, effector: str):
        """
        Initialize end-effector driver exactly once and return the driver instance.

        Notes
        -----
        - This method is intentionally one-shot to avoid registering multiple
          callbacks into the same DriverContext threads.
        - If called again, it raises RuntimeError.
        """
        if self._effector_kind is not None:
            raise RuntimeError(
                f"effector already initialized: {self._effector_kind}. "
                "Create a new arm instance if you need a different effector."
            )

        effector_kind = str(effector).strip().lower()
        self._effector_kind = effector_kind

        if effector_kind == self.EFFECTOR.AGX_GRIPPER:
            from ..effector.agx_gripper import AgxGripperDriverDefault

            self._effector = AgxGripperDriverDefault(self._config, self.get_context())
            return self._effector

        if effector_kind == self.EFFECTOR.REVO2:
            from ..effector.revo2 import Revo2DriverDefault

            self._effector = Revo2DriverDefault(self._config, self.get_context())
            return self._effector

        raise ValueError(f"Unsupported effector kind: {effector}")

    def get_instance(self):
        raise NotImplementedError

    def get_driver_version(self):
        raise NotImplementedError

    def create_comm(self, config: dict = {}, comm: str = "can"):
        return self._ctx.create_comm(config, comm)

    def connect(self, start_read_thread: bool = True) -> None:
        if not self._ctx.get_comm():
            self._ctx.init_comm()
        if self._ctx.get_comm() is None:
            raise ValueError("comm is None")
        with self._lock:
            if self._connected:
                return
            self._connected = self._ctx.get_comm().is_connected()
        if start_read_thread:
            self._ctx.start_th()

    def is_connected(self) -> bool:
        return self._ctx.get_comm().is_connected()

    def is_ok(self):
        return self._arm_ctx.is_ok()

    def get_fps(self):
        return self._arm_ctx.get_fps()

    def get_config(self) -> dict:
        return self._config

    def get_type(self):
        return self._ctx.get_comm().get_type()

    def get_channel(self):
        return self._ctx.get_comm().get_channel()

    def get_joint_states(self):
        raise NotImplementedError

    def get_ee_pose(self):
        raise NotImplementedError

    def get_arm_status(self):
        raise NotImplementedError

    def get_driver_states(self):
        raise NotImplementedError

    def get_motor_states(self):
        raise NotImplementedError

    def enable(self):
        raise NotImplementedError

    def disable(self):
        raise NotImplementedError

    def reset(self):
        raise NotImplementedError

    def electronic_emergency_stop(self):
        raise NotImplementedError
