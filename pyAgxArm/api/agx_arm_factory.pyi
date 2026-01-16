# agx_arm_factory.pyi
from typing_extensions import TypedDict, Literal
from typing import Any, Dict, Type, TypeVar, overload
from ..protocols.can_protocol.drivers.core.arm_driver_interface import ArmDriverInterface
from ..protocols.can_protocol.drivers.piper import PiperDriverDefault
from ..protocols.can_protocol.drivers.nero import NeroDriverDefault
from ..protocols.can_protocol.drivers.piper_h import PiperHDriverDefault
from ..protocols.can_protocol.drivers.piper_l import PiperLDriverDefault
from ..protocols.can_protocol.drivers.piper_x import PiperXDriverDefault

class NeroCanDefaultConfig():
    pass
class PiperCanDefaultConfig():
    pass
class PiperHCanDefaultConfig():
    pass
class PiperLCanDefaultConfig():
    pass
class PiperXCanDefaultConfig():
    pass

@overload
def create_agx_arm_config(
    robot: Literal["nero"],
    comm: Literal["can"],
    firmeware_version: Literal["default"] = ...,
    **kwargs: Any
) -> NeroCanDefaultConfig: ...

@overload
def create_agx_arm_config(
    robot: Literal["piper"],
    comm: Literal["can"],
    firmeware_version: Literal["default"] = ...,
    **kwargs: Any
) -> PiperCanDefaultConfig: ...

@overload
def create_agx_arm_config(
    robot: Literal["piper_h"],
    comm: Literal["can"],
    firmeware_version: Literal["default"] = ...,
    **kwargs: Any
) -> PiperHCanDefaultConfig: ...

@overload
def create_agx_arm_config(
    robot: Literal["piper_l"],
    comm: Literal["can"],
    firmeware_version: Literal["default"] = ...,
    **kwargs: Any
) -> PiperLCanDefaultConfig: ...

@overload
def create_agx_arm_config(
    robot: Literal["piper_x"],
    comm: Literal["can"],
    firmeware_version: Literal["default"] = ...,
    **kwargs: Any
) -> PiperXCanDefaultConfig: ...

T = TypeVar("T", bound=Any)

class AgxArmFactory:

    @classmethod
    @overload
    def create_arm(cls, config: NeroCanDefaultConfig, **kwargs) -> NeroDriverDefault: ...
    @classmethod
    @overload
    def create_arm(cls, config: PiperCanDefaultConfig, **kwargs) -> PiperDriverDefault: ...
    @classmethod
    @overload
    def create_arm(cls, config: PiperHCanDefaultConfig, **kwargs) -> PiperHDriverDefault: ...
    @classmethod
    @overload
    def create_arm(cls, config: PiperLCanDefaultConfig, **kwargs) -> PiperLDriverDefault: ...
    @classmethod
    @overload
    def create_arm(cls, config: PiperXCanDefaultConfig, **kwargs) -> PiperXDriverDefault: ...
