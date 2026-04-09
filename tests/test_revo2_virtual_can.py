from tests.conftest import hex_payloads, new_virtual_channel, wait_until
from tests.slaves.revo2_can_slave import Revo2CanSlave

from pyAgxArm import AgxArmFactory, ArmModel, PiperFW, create_agx_arm_config


def test_revo2_init_and_position_ctrl_l2():
    channel = new_virtual_channel("ci_revo2")
    slave = Revo2CanSlave(channel=channel)
    slave.start()
    try:
        cfg = create_agx_arm_config(
            robot=ArmModel.PIPER,
            firmeware_version=PiperFW.DEFAULT,
            interface="virtual",
            channel=channel,
        )
        arm = AgxArmFactory.create_arm(cfg)
        arm.connect()
        hand = arm.init_effector(arm.OPTIONS.EFFECTOR.REVO2)
        n0 = len(slave.host_frames)

        hand.position_ctrl(thumb_tip=10)

        assert wait_until(lambda: len(slave.host_frames) > n0)
        host = slave.host_frames[n0:]
        assert host
        assert all(len(x) <= 16 for x in hex_payloads(host))
        arm.disconnect()
    finally:
        slave.stop()


def test_revo2_read_and_control_apis_l2():
    channel = new_virtual_channel("ci_revo2_more")
    slave = Revo2CanSlave(channel=channel)
    slave.start()
    try:
        cfg = create_agx_arm_config(
            robot=ArmModel.PIPER,
            firmeware_version=PiperFW.DEFAULT,
            interface="virtual",
            channel=channel,
        )
        arm = AgxArmFactory.create_arm(cfg)
        arm.connect()
        hand = arm.init_effector(arm.OPTIONS.EFFECTOR.REVO2)
        n0 = len(slave.host_frames)

        hand.speed_ctrl(thumb_tip=10)
        hand.current_ctrl(thumb_tip=10)
        hand.position_time_ctrl(mode="pos", thumb_tip=10)
        hand.position_time_ctrl(mode="time", thumb_tip=20)

        assert wait_until(lambda: len(slave.host_frames) > n0)
        assert wait_until(lambda: hand.get_hand_status() is not None)
        assert wait_until(lambda: hand.get_finger_pos() is not None)
        assert wait_until(lambda: hand.get_finger_spd() is not None)
        assert wait_until(lambda: hand.get_finger_current() is not None)

        ids = {f.arbitration_id for f in slave.host_frames[n0:]}
        assert {0x1B2, 0x1B3, 0x1B5}.issubset(ids)
        arm.disconnect()
    finally:
        slave.stop()
