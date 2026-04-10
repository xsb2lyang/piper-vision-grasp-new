# 测试 API 覆盖清单（当前版本）

基于 `tests/test_*.py` 中的实际调用统计，分为“已覆盖”和“暂未覆盖”。

## 已覆盖 API

### 工厂与基础连接

`AgxArmFactory.load_class`, `AgxArmFactory.create_arm`, `connect`, `disconnect`, `init_effector`

### 机械臂（Piper / Nero）

`set_speed_percent`, `set_motion_mode`, `enable`, `disable`, `move_j`, `move_js`, `move_mit`, `move_p`, `move_l`, `move_c`, `electronic_emergency_stop`, `reset`

### 机型专有

`set_installation_pos`（Piper）, `set_payload`（Piper）, `set_normal_mode`（Nero）, `get_leader_joint_angles`（Nero）

### 机械臂读取类（Piper / Nero）

`get_joint_angles`, `get_flange_pose`, `fk`, `get_arm_status`, `get_driver_states`, `get_motor_states`, `get_joint_enable_status`, `get_joints_enable_status_list`

### 运动学（MDH，见 `test_mdh_fk.py`）

`get_mdh`, `fk_from_mdh`（`pyAgxArm.utiles.mdh_kinematics`）

### 机械臂读取与信息（Piper / Nero）

`get_firmware`

### 主从相关（Piper / Nero）

`set_leader_mode`, `set_follower_mode`, `move_leader_to_home`（Piper）, `move_leader_follower_to_home`（Piper）, `restore_leader_drag_mode`（Piper）

### Piper 专有

`set_links_vel_acc_period_feedback`, `get_joint_angle_vel_limits`, `get_joint_acc_limits`, `get_flange_vel_acc_limits`, `get_crash_protection_rating`, `calibrate_joint`, `set_joint_angle_vel_limits`, `set_joint_acc_limits`, `set_flange_vel_acc_limits`, `set_crash_protection_rating`, `set_flange_vel_acc_limits_to_default`, `set_joint_angle_vel_acc_limits_to_default`

### 末端

`move_gripper_m`, `move_gripper_deg`, `move_gripper`, `get_gripper_status`, `get_gripper_ctrl_states`, `disable_gripper`, `reset_gripper`, `calibrate_gripper`, `get_gripper_teaching_pendant_param`, `set_gripper_teaching_pendant_param`（AgxGripper）

`position_ctrl`, `speed_ctrl`, `current_ctrl`, `position_time_ctrl`, `get_hand_status`, `get_finger_pos`, `get_finger_spd`, `get_finger_current`（Revo2）

## 暂未覆盖 API

当前清单中无暂未覆盖 API。

## 本地测试指令

`python3 -m pytest -q tests`

`python3 -m pytest -q tests/test_piper_driver_virtual_can.py`

`python3 -m pytest -q tests/test_nero_driver_virtual_can.py`

`python3 -m pytest -q tests/test_agx_gripper_virtual_can.py tests/test_revo2_virtual_can.py`

`python3 -m pytest -q tests/test_factory_config.py`

`python3 -m pytest -q tests/test_mdh_fk.py`

