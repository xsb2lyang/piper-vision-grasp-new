import pytest

from pyAgxArm import AgxArmFactory, ArmModel, PiperFW, create_agx_arm_config

from tests.conftest import hex_payloads, new_virtual_channel, wait_until
from tests.slaves.piper_can_slave import PiperCanSlave

def _make_piper_arm(fw, channel):
    cfg = create_agx_arm_config(
        robot=ArmModel.PIPER,
        firmeware_version=fw,
        interface="virtual",
        channel=channel,
    )
    return AgxArmFactory.create_arm(cfg)


def _assert_send_only_flow(arm, device):
    arm.connect()
    joints = [0.0] * arm.joint_nums

    arm.set_speed_percent(100)
    arm.set_motion_mode(arm.OPTIONS.MOTION_MODE.J)
    arm.set_installation_pos(arm.OPTIONS.INSTALLATION_POS.HORIZONTAL)
    arm.enable()
    arm.move_j(joints)
    arm.move_js(joints)
    arm.move_mit(1, p_des=0.0, v_des=0.0, kp=10.0, kd=0.8, t_ff=0.0)
    arm.disable()
    arm.disconnect()

    ok = wait_until(lambda: len(device.host_frames) >= 8)
    assert ok, "Timeout waiting for host command frames on virtual CAN"

    host_hex = hex_payloads(device.host_frames)
    assert host_hex
    assert all(len(x) <= 16 for x in host_hex)


@pytest.mark.parametrize("fw", [PiperFW.DEFAULT, PiperFW.V183, PiperFW.V188])
def test_piper_driver_demo_style_api_with_virtual_device(fw):
    channel = new_virtual_channel("ci_piper")
    device = PiperCanSlave(channel=channel)
    device.start()
    try:
        arm = _make_piper_arm(fw, channel)
        _assert_send_only_flow(arm, device)
    finally:
        device.stop()


def test_piper_driver_extended_motion_and_safety_l2():
    channel = new_virtual_channel("ci_piper_ext")
    device = PiperCanSlave(channel=channel)
    device.start()
    try:
        arm = _make_piper_arm(PiperFW.DEFAULT, channel)
        arm.connect()
        pose = [0.1, 0.0, 0.3, 0.0, 0.7853981633974483, 0.0]
        sp = [0.1, 0.0, 0.35, 0.0, 0.7853981633974483, 0.0]
        ep = [0.1, 0.0, 0.4, 0.0, 0.7853981633974483, 0.0]

        arm.set_motion_mode(arm.OPTIONS.MOTION_MODE.P)
        arm.move_p(pose)

        arm.set_motion_mode(arm.OPTIONS.MOTION_MODE.L)
        arm.move_l(pose)

        arm.set_motion_mode(arm.OPTIONS.MOTION_MODE.C)
        arm.move_c(sp, pose, ep)

        arm.electronic_emergency_stop()
        arm.reset()
        arm.disconnect()

        assert wait_until(lambda: len(device.host_frames) >= 10)
    finally:
        device.stop()


def test_piper_only_set_payload_smoke():
    channel = new_virtual_channel("ci_piper_payload")
    device = PiperCanSlave(channel=channel)
    device.start()
    try:
        arm = _make_piper_arm(PiperFW.DEFAULT, channel)
        arm.connect()
        n0 = len(device.host_frames)
        assert arm.set_payload(arm.OPTIONS.PAYLOAD.EMPTY)
        assert wait_until(lambda: len(device.host_frames) > n0)
        acks = [f for f in device.device_frames if f.arbitration_id == 0x476]
        assert acks and acks[-1].data[0] == 0x77
        arm.disconnect()
    finally:
        device.stop()


def test_piper_read_apis_with_virtual_feedback():
    channel = new_virtual_channel("ci_piper_read")
    device = PiperCanSlave(channel=channel)
    device.start()
    try:
        arm = _make_piper_arm(PiperFW.DEFAULT, channel)
        arm.connect()
        # 发送一帧即可触发从机主动反馈，随后校验读取类 API。
        arm.set_speed_percent(100)
        assert wait_until(lambda: len(device.device_frames) > 0)

        ja = arm.get_joint_angles()
        fp = arm.get_flange_pose()
        st = arm.get_arm_status()
        ms = arm.get_motor_states(1)
        ds = arm.get_driver_states(1)
        es = arm.get_joint_enable_status(1)
        es_all = arm.get_joints_enable_status_list()

        assert ja is not None and len(ja.msg) == 6
        assert fp is not None and len(fp.msg) == 6
        assert st is not None
        assert ms is not None
        assert ds is not None
        assert isinstance(es, bool)
        assert isinstance(es_all, list) and len(es_all) == 6
        arm.disconnect()
    finally:
        device.stop()


def test_piper_leader_follower_apis_send_expected_frames():
    channel = new_virtual_channel("ci_piper_lf")
    device = PiperCanSlave(channel=channel)
    device.start()
    try:
        arm = _make_piper_arm(PiperFW.DEFAULT, channel)
        arm.connect()
        n0 = len(device.host_frames)

        arm.set_leader_mode()
        arm.set_follower_mode()
        arm.move_leader_to_home()
        arm.move_leader_follower_to_home()
        arm.restore_leader_drag_mode()

        assert wait_until(lambda: len(device.host_frames) > n0)
        ids = {f.arbitration_id for f in device.host_frames[n0:]}
        assert 0x470 in ids
        assert 0x191 in ids
        arm.disconnect()
    finally:
        device.stop()


def test_piper_get_firmware_with_realistic_multiframe_hex():
    channel = new_virtual_channel("ci_piper_fw")
    device = PiperCanSlave(channel=channel)
    device.start()
    try:
        arm = _make_piper_arm(PiperFW.DEFAULT, channel)
        arm.connect()
        # Piper 固件读取逻辑会参考当前通信 FPS，先触发一轮正常通信。
        arm.set_speed_percent(100)
        assert wait_until(lambda: arm.get_fps() > 0, timeout=1.0)
        fw = arm.get_firmware(timeout=1.0, min_interval=0.0)
        assert fw is not None
        assert fw["hardware_version"] == "H-V1.2-1"
        assert fw["motor_ratio_and_batch"] == "10"
        assert fw["node_type"] == "ARM_MC"
        assert fw["software_version"] == "S-V1.8-8"
        assert fw["production_date"] == "250925"
        assert fw["node_number"] == "15"
        arm.disconnect()
    finally:
        device.stop()


def test_piper_proprietary_apis_l2():
    channel = new_virtual_channel("ci_piper_private")
    device = PiperCanSlave(channel=channel)
    device.start()
    try:
        arm = _make_piper_arm(PiperFW.DEFAULT, channel)
        arm.connect()
        arm.set_speed_percent(100)
        assert wait_until(lambda: arm.get_fps() > 0, timeout=1.0)

        # get_* 系列
        assert arm.get_joint_angle_vel_limits(1, timeout=1.0, min_interval=0.0) is not None
        assert arm.get_joint_acc_limits(1, timeout=1.0, min_interval=0.0) is not None
        assert arm.get_flange_vel_acc_limits(timeout=1.0, min_interval=0.0) is not None
        assert arm.get_crash_protection_rating(timeout=1.0, min_interval=0.0) is not None

        # set_* 系列
        assert arm.calibrate_joint(1, timeout=1.0)
        assert arm.set_joint_angle_vel_limits(1, timeout=1.0)
        assert arm.set_joint_acc_limits(1, timeout=1.0)
        assert arm.set_flange_vel_acc_limits(timeout=1.0)
        assert arm.set_crash_protection_rating(1, 0, timeout=1.0)
        assert arm.set_flange_vel_acc_limits_to_default(timeout=1.0)
        assert arm.set_joint_angle_vel_acc_limits_to_default(timeout=1.0)
        assert arm.set_links_vel_acc_period_feedback(enable=True, timeout=1.0)

        ids = {f.arbitration_id for f in device.device_frames}
        assert {0x473, 0x47C, 0x478, 0x47B, 0x476}.issubset(ids)
        arm.disconnect()
    finally:
        device.stop()
