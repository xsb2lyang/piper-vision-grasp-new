from pyAgxArm.api.agx_arm_factory import create_agx_arm_config, AgxArmFactory
import time
robot_cfg = create_agx_arm_config(robot="nero", comm="can", channel="can0", interface="socketcan")
print(robot_cfg)
robot = AgxArmFactory.create_arm(robot_cfg)
robot.connect()
print(robot.get_channel())
print(robot.__doc__)

end_effector = robot.init_effector(robot.EFFECTOR.REVO2)
print(end_effector.__doc__)


# -------------------------- Basic ---------------------------

# while not robot.enable():
#     time.sleep(0.01)

# while not robot.disable():
#     time.sleep(0.01)

# robot.set_speed_percent(100)
# robot.set_motion_mode(robot.MOTION_MODE.P)
# robot.set_normal_mode()


# -------------------------- Move -----------------------------

# The following poses are for Piper and need to be replaced with Nero poses to run successfully on Nero.

# robot.move_p([0.3, 0.0, 0.45, 0.0, 1.570796326794896619, 0.0])
# time.sleep(0.1)
# while robot.get_arm_status().msg.motion_status != 0:
#     time.sleep(0.1)

# robot.move_j([0] * 7)
# time.sleep(0.1)
# while robot.get_arm_status().msg.motion_status != 0:
#     time.sleep(0.1)


# -------------------------- reset ----------------------------

# robot.move_j([0] * 7)
# time.sleep(2)

# robot.electronic_emergency_stop()
# time.sleep(1)

# robot.reset()


# -------------------------- Get data -------------------------


while True:
    break

    # print(robot.get_fps())
    # print(robot.is_ok())

    t = time.time()

    # print(robot.get_arm_status())

    # print(robot.get_joint_states())
    # print(robot.get_ee_pose())

    # print(robot.get_driver_states(1))
    # print(robot.get_motor_states(1))
    # print(robot.get_joint_enable_status(1))
    # print(robot.get_joints_enable_status_list())

    t = round((time.time() - t) * 1000, 4)

    if t > 1:
        print("\nTime elapsed: ", t, "ms")

    print()

    time.sleep(0.005)
