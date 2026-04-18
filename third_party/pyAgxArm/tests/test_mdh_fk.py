"""MDH forward kinematics (offline, no CAN)."""
import math

import pytest

from pyAgxArm import AgxArmFactory, ArmModel, PiperFW, NeroFW, create_agx_arm_config
from pyAgxArm.utiles.mdh_kinematics import fk_from_mdh, get_mdh

from tests.conftest import new_virtual_channel


def _make_arm(robot: str, fw):
    ch = new_virtual_channel("mdh_fk")
    cfg = create_agx_arm_config(
        robot=robot,
        firmeware_version=fw,
        interface="virtual",
        channel=ch,
    )
    return AgxArmFactory.create_arm(cfg)


@pytest.mark.parametrize(
    "robot,fw,n",
    [
        (ArmModel.PIPER, PiperFW.DEFAULT, 6),
        (ArmModel.PIPER_H, PiperFW.DEFAULT, 6),
        (ArmModel.PIPER_L, PiperFW.DEFAULT, 6),
        (ArmModel.PIPER_X, PiperFW.DEFAULT, 6),
        (ArmModel.NERO, NeroFW.DEFAULT, 7),
    ],
)
def test_fk_returns_pose6_list_and_deterministic(robot, fw, n):
    """Driver ``fk`` returns ``[x,y,z,roll,pitch,yaw]`` (m, rad), not MessageAbstract."""
    arm = _make_arm(robot, fw)
    q = [0.0] * n
    a = arm.fk(q)
    b = arm.fk(q)
    assert isinstance(a, list)
    assert len(a) == 6
    assert a == b
    assert all(math.isfinite(x) for x in a)


def test_fk_wrong_length_raises():
    arm = _make_arm(ArmModel.PIPER, PiperFW.DEFAULT)
    with pytest.raises(ValueError):
        arm.fk([0.0] * 5)


def test_get_mdh_fk_from_mdh_piper_zero_configuration():
    """Low-level API: cached table shape matches joint count."""
    mdh = get_mdh("piper")
    assert len(mdh) == 6
    pose = fk_from_mdh(list(mdh), [0.0] * 6)
    assert len(pose) == 6
    assert all(math.isfinite(x) for x in pose)


def test_get_mdh_unknown_robot_raises():
    with pytest.raises(KeyError):
        get_mdh("not_a_robot")
