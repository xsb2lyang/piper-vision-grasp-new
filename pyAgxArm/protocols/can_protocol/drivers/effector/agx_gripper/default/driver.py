import copy
from typing import Optional, Callable, TypeVar

from .parser import Parser
from .....msgs.piper.default import ArmMsgFeedbackRespSetInstruction
from .....msgs.core.attritube_base import AttributeBase
from ....core.driver_context import DriverContext
from ....core.effector_driver_context import EffectorDriverContext
from .....msgs.effector.agx_gripper.default import (
    ArmMsgFeedbackGripper,
    ArmMsgFeedbackGripperTeachingPendantParam,
    ArmMsgGripperCtrl,
    ArmMsgGripperTeachingPendantParamConfig,
)
from .....msgs.core.msg_abstract import MessageAbstract
from .....msgs.piper.default import (
    ArmMsgParamEnquiryAndConfig,
)


T = TypeVar('T')


class Driver:
    """
    agx_gripper end-effector driver.
    """

    def __init__(self, config: dict, ctx: DriverContext):
        self._config = config.copy()
        self._ctx = ctx
        self._parser = Parser(self._ctx.fps)
        self._effector_ctx = EffectorDriverContext(config, self._ctx, self._parser)

    # -------------------------
    # Internal send helpers
    # -------------------------
    def _send_msg(self, msg: AttributeBase) -> None:
        if isinstance(msg, AttributeBase):
            data = self._parser.pack(msg)
            if data is not None:
                self._ctx.get_comm().send(data)
        else:
            raise TypeError(
                "msg must be AttributeBase"
            )

    # -------------------------
    # Common "set_*" templates (ACK-only / ACK+verify)
    # -------------------------
    def _clear_resp_set_instruction(self) -> None:
        """Clear cached `resp_set_instruction` message if present."""
        if getattr(self._parser, "resp_set_instruction", None) is not None:
            self._parser.resp_set_instruction.msg.clear()

    def _is_resp_set_instruction(self, instruction_index: int) -> bool:
        """Return True if cached `resp_set_instruction` matches instruction_index."""
        return (
            getattr(self._parser, "resp_set_instruction", None) is not None
            and self._parser.resp_set_instruction.msg.instruction_index
            == instruction_index
        )

    def _ack_only_set(
        self,
        *,
        request: Callable[[], None],
        instruction_index: int,
        timeout: float = 1.0,
        stamp_key: str,
        clear_before: bool = True,
    ) -> bool:
        """
        Template for set_* APIs where success is defined as "ACK received".

        Returns False on timeout. True means the controller acknowledged the request.
        """
        if clear_before:
            self._clear_resp_set_instruction()

        def is_ready() -> bool:
            return self._is_resp_set_instruction(instruction_index)

        def get_value() -> bool:
            return True

        return bool(
            self._ctx._request_and_get(
                request=request,
                is_ready=is_ready,
                get_value=get_value,
                timeout=timeout,
                min_interval=0.0,
                stamp_attr=stamp_key,
            )
        )

    def _ack_and_check_set(
        self,
        *,
        request: Callable[[], None],
        instruction_index: int,
        check: Callable[[], bool],
        timeout: float = 1.0,
        stamp_key: str,
        clear_before: bool = True,
    ) -> bool:
        """
        Template for set_* APIs where success is "ACK received and state verified".

        Returns False on timeout, or if `check()` fails.
        """
        if clear_before:
            self._clear_resp_set_instruction()

        def is_ready() -> bool:
            return (
                self._is_resp_set_instruction(instruction_index)
                and check()
            )

        def get_value() -> bool:
            return True

        return bool(
            self._ctx._request_and_get(
                request=request,
                is_ready=is_ready,
                get_value=get_value,
                timeout=timeout,
                min_interval=0.0,
                stamp_attr=stamp_key,
            )
        )

    def _resp_set_instruction_get(
        self,
        *,
        request: Callable[[], None],
        instruction_index: int,
        get_value: Callable[[], T],
        timeout: float = 1.0,
        stamp_key: str,
        clear_before: bool = True,
    ) -> Optional[T]:
        """
        Wait for `resp_set_instruction` with a specific instruction index, then
        compute and return a typed value via `get_value()`.
        """
        if clear_before:
            self._clear_resp_set_instruction()

        def is_ready() -> bool:
            return self._is_resp_set_instruction(instruction_index)

        return self._ctx._request_and_get(
            request=request,
            is_ready=is_ready,
            get_value=get_value,
            timeout=timeout,
            min_interval=0.0,
            stamp_attr=stamp_key,
        )

    # -------------------------
    # Public APIs (gripper)
    # -------------------------
    def is_ok(self):
        return self._effector_ctx.is_ok()
    
    def get_fps(self):
        return self._effector_ctx.get_fps()

    def get_gripper_status(self) -> Optional[MessageAbstract[ArmMsgFeedbackGripper]]:
        """
        Get the gripper status.

        Returns
        -------
        MessageAbstract[ArmMsgFeedbackGripper] | None
            The gripper status. If the gripper status is not available, return None.

        Message
        -------
        `width`: Current gripper width, unit: m

        `force`: Current gripper force, unit: N

        `foc_status`: Driver status.
        - `voltage_too_low`: Power voltage too low, type: bool
        - `motor_overheating`: Motor over-temperature, type: bool
        - `driver_overcurrent`: Driver over-current, type: bool
        - `driver_overheating`: Driver over-temperature, type: bool
        - `sensor_status`: Sensor status, type: bool
        - `driver_error_status`: Driver error status, type: bool
        - `driver_enable_status`: Driver enable status, type: bool
        - `homing_status`: Zeroing status, type: bool

        Examples
        --------
        >>> gs = end_effector.get_gripper_status()
        >>> if gs is not None:
        >>>     print(gs.msg.width, gs.msg.force)
        >>>     print(gs.hz, gs.timestamp)
        """
        gs: Optional[MessageAbstract[ArmMsgFeedbackGripper]] = getattr(
            self._parser, "gripper", None
        )
        if gs is not None:
            gs.hz = self._ctx.fps.get_fps(gs.msg_type)
            return gs
        return None

    def get_gripper_ctrl_states(self) -> Optional[MessageAbstract[ArmMsgGripperCtrl]]:
        """
        Get the gripper control states.

        Returns
        -------
        MessageAbstract[ArmMsgGripperCtrl] | None
            The gripper control status. If the gripper control status is not
            available, return None.

        Message
        -------
        `width`: Current gripper width, unit: m
        `force`: Current gripper force, unit: N
        `status_code`: Status code
        `set_zero`: Set zero

        Examples
        --------
        >>> gcs = end_effector.get_gripper_ctrl_states()
        >>> if gcs is not None:
        >>>     print(gcs.msg.width, gcs.msg.force)
        >>>     print(gcs.hz, gcs.timestamp)
        """
        gcs: Optional[MessageAbstract[ArmMsgGripperCtrl]] = getattr(
            self._parser, "gripper_ctrl_feedback", None
        )
        if gcs is not None:
            gcs.hz = self._ctx.fps.get_fps(gcs.msg_type)
            return gcs
        return None

    def disable_gripper(self) -> bool:
        """
        Disable the gripper.

        Returns
        -------
        bool
            True if the gripper is disabled, False otherwise.

        Notes
        -----
        This API infers the result from feedback.

        Examples
        --------
        >>> if end_effector.disable_gripper():
        >>>     print("Gripper disabled")
        """
        self._send_msg(ArmMsgGripperCtrl(status_code=0))
        gs = self.get_gripper_status()
        if gs is not None:
            return not gs.msg.foc_status.driver_enable_status
        return False

    def calibrate_gripper(self, timeout: float = 1.0) -> bool:
        """
        Calibrate gripper zero point.

        This function will set the current position as the gripper zero point.

        Returns
        -------
        bool
            True if an ACK/response is received within `timeout` and the controller
            reports success, False otherwise.

            Notes
            -----
            This API relies on `0x476 resp_set_instruction`:
            - byte0: instruction_index == 0x75
            - byte1: is_set_zero_successfully == 1

        Examples
        --------
        >>> end_effector.disable_gripper()
        >>> input("Please move the gripper to the zero position...")
        >>> if end_effector.calibrate_gripper():
        >>>     end_effector.move_gripper(width=0.0)
        """
        self._ctx._validate_timeout(timeout)

        def request() -> None:
            self._send_msg(ArmMsgGripperCtrl(set_zero=0xAE))

        def get_value() -> bool:
            # 0x476 byte1: is_set_zero_successfully
            resp: Optional[MessageAbstract[ArmMsgFeedbackRespSetInstruction]] = \
                getattr(self._parser, "resp_set_instruction", None)
            return resp is not None and resp.msg.is_set_zero_successfully == 1

        res = self._resp_set_instruction_get(
            request=request,
            instruction_index=0x75,
            get_value=get_value,
            timeout=timeout,
            stamp_key="agx_gripper_calibrate",
            clear_before=True,
        )
        return bool(res)

    def move_gripper(self, width: float = 0.0, force: float = 1.0) -> None:
        """
        Move the gripper to the target width and force.

        Parameters
        ----------
        `width`: float, optional
        - Width of the gripper in meters. Range: [0.0, 0.1]. Default is 0.0.
            (Numerical precision: 1e-6 m)

        `force`: float, optional
        - Force of the gripper in N. Range: [0.0, 3.0]. Default is 1.0.
            (Numerical precision: 1e-3 N)

        Examples
        --------
        >>> end_effector.move_gripper(width=0.05, force=1.0)
        """
        if width < 0.0 or width > 0.1:
            raise ValueError("Width should be between 0.0 and 0.1 in m")
        if force < 0.0 or force > 3.0:
            raise ValueError("Force should be between 0.0 and 3.0 in N")

        width_i = round(width * 1e6)
        force_i = round(force * 1e3)
        self._send_msg(ArmMsgGripperCtrl(
            width=width_i, force=force_i, status_code=1))

    def get_gripper_teaching_pendant_param(
        self, timeout: float = 1.0, min_interval: float = 1.0
    ) -> Optional[MessageAbstract[ArmMsgFeedbackGripperTeachingPendantParam]]:
        """
        Query gripper teaching pendant parameters.

        This uses the shared arm ParamEnquiry frame and waits for gripper-specific
        feedback (0x47E) parsed by this end-effector parser.

        Examples
        --------
        >>> param = end_effector.get_gripper_teaching_pendant_param()
        >>> if param is not None:
        >>>     print(
        ...         param.msg.teaching_range_per,
        ...         param.msg.max_range_config,
        ...         param.msg.teaching_friction,
        ...     )
        >>>     print(param.hz, param.timestamp)
        """
        def request() -> None:
            self._send_msg(ArmMsgParamEnquiryAndConfig(param_enquiry=4))

        def is_ready() -> bool:
            return (
                getattr(self._parser, "gripper_teaching_pendant_param", None) is not None
                and self._parser.gripper_teaching_pendant_param.msg.teaching_range_per
                is not None
            )

        def get_value() -> MessageAbstract[ArmMsgFeedbackGripperTeachingPendantParam]:
            self._parser.gripper_teaching_pendant_param.hz = self._ctx.fps.get_fps(
                self._parser.gripper_teaching_pendant_param.msg_type
            )
            return copy.deepcopy(self._parser.gripper_teaching_pendant_param)

        def clear() -> None:
            self._parser.gripper_teaching_pendant_param.msg.clear()

        return self._ctx._request_and_get(
            request=request,
            is_ready=is_ready,
            get_value=get_value,
            clear=clear,
            timeout=timeout,
            min_interval=min_interval,
            stamp_attr="agx_gripper_teaching_pendant_param",
        )

    def set_gripper_teaching_pendant_param(
        self,
        teaching_range_per: int = 100,
        max_range_config: float = 0.0,
        teaching_friction: int = 1,
        timeout: float = 1.0,
    ) -> bool:
        """
        Set gripper teaching pendant parameters.

        Notes
        -----
        True indicates the controller acknowledged the request. For semantics and
        common conventions, see parent arm driver's `Driver` docstring.

        Examples
        --------
        >>> ok = end_effector.set_gripper_teaching_pendant_param(
        ...     teaching_range_per=100,
        ...     max_range_config=0.07,
        ...     teaching_friction=1,
        ... )
        >>> if ok:
        >>>     print("Gripper teaching pendant parameter set successfully")
        """
        self._ctx._validate_timeout(timeout)
        if not isinstance(teaching_range_per, int):
            raise TypeError("Teaching range per should be an integer")
        if teaching_range_per < 100 or teaching_range_per > 200:
            raise ValueError("Teaching range per should be between 100 and 200")
        if max_range_config not in [0, 0.07, 0.1]:
            raise ValueError("Max range config should be 0, 0.07, 0.1")
        if teaching_friction not in [1, 2, 3, 4, 5, 6, 7, 8, 9, 10]:
            raise ValueError(
                "Teaching friction should be 1, 2, 3, 4, 5, 6, 7, 8, 9, 10"
            )

        max_range_i = round(max_range_config * 1e3)
        msg = ArmMsgGripperTeachingPendantParamConfig(
            teaching_range_per, max_range_i, teaching_friction
        )

        def request() -> None:
            self._send_msg(msg)

        def check() -> bool:
            res = self.get_gripper_teaching_pendant_param(timeout=0.0)
            return not (
                res is None
                or res.msg.teaching_range_per != teaching_range_per
                or round(res.msg.max_range_config * 1e3) != max_range_i
                or res.msg.teaching_friction != teaching_friction
            )

        return self._ack_and_check_set(
            request=request,
            instruction_index=0x7D,
            check=check,
            timeout=timeout,
            stamp_key="agx_gripper_set_teaching_pendant_param",
        )
