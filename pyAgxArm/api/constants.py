# ---------- robot 可选字段 ----------

ROBOT_OPTION_FIELDS = {
    "nero": {
        "joint_limits",
        "auto_set_motion_mode",
    },
    "piper": {
        "joint_limits",
        "auto_set_motion_mode",
    },
    "piper_h": {
        "joint_limits",
        "auto_set_motion_mode",
    },
    "piper_l": {
        "joint_limits",
        "auto_set_motion_mode",
    },
    "piper_x": {
        "joint_limits",
        "auto_set_motion_mode",
    },
}

# ---------- 预定义机械臂关节名字 ----------

ROBOT_JOINT_NAME = {
    "nero": ["joint1", "joint2", "joint3", "joint4", "joint5", "joint6", "joint7"],
    "piper": ["joint1", "joint2", "joint3", "joint4", "joint5", "joint6"],
    "piper_h": ["joint1", "joint2", "joint3", "joint4", "joint5", "joint6"],
    "piper_l": ["joint1", "joint2", "joint3", "joint4", "joint5", "joint6"],
    "piper_x": ["joint1", "joint2", "joint3", "joint4", "joint5", "joint6"],
}

# ---------- 预定义机械臂关节限位 ----------

ROBOT_JOINT_LIMIT_PRESET_RAD = {
    "nero": {
        "joint1": [-2.705261, 2.705261],
        "joint2": [-1.745330, 1.745330],
        "joint3": [-2.757621, 2.757621],
        "joint4": [-1.012291, 2.146755],
        "joint5": [-2.757621, 2.757621],
        "joint6": [-0.733039, 0.959932],
        "joint7": [-1.570797, 1.570797],
    },
    "piper": {
        "joint1": [-2.617994, 2.617994],
        "joint2": [0.0, 3.141593],
        "joint3": [-2.967060, 0.0],
        "joint4": [-1.745330, 1.745330],
        "joint5": [-1.221730, 1.221730],
        "joint6": [-2.094396, 2.094396],
    },
    "piper_h": {
        "joint1": [-2.617994, 2.617994],
        "joint2": [0.0, 3.141593],
        "joint3": [-2.967060, 0.0],
        "joint4": [-1.745330, 1.745330],
        "joint5": [-1.221730, 1.221730],
        "joint6": [-2.094396, 2.094396],
    },
    "piper_l": {
        "joint1": [-2.617994, 2.617994],
        "joint2": [0.0, 3.141593],
        "joint3": [-2.967060, 0.0],
        "joint4": [-1.745330, 1.745330],
        "joint5": [-1.221730, 1.221730],
        "joint6": [-2.094396, 2.094396],
    },
    "piper_x": {
        "joint1": [-2.617994, 2.617994],
        "joint2": [0.0, 3.141593],
        "joint3": [-2.967060, 0.0],
        "joint4": [-1.570797, 1.570797],
        "joint5": [-1.570797, 1.570797],
        "joint6": [-2.094396, 2.094396],
    },
}

ROBOT_JOINT_LIMIT_PRESET_DEG = {
    "nero": {
        "joint1": [-155.0, 155.0],
        "joint2": [-100.0, 100.0],
        "joint3": [-158.0, 158.0],
        "joint4": [-58.0, 123.0],
        "joint5": [-158.0, 158.0],
        "joint6": [-42.0, 55.0],
        "joint7": [-90.0, 90.0],
    },
    "piper": {
        "joint1": [-150.0, 150.0],
        "joint2": [0.0, 180.0],
        "joint3": [-170.0, 0.0],
        "joint4": [-100.0, 100.0],
        "joint5": [-70.0, 70.0],
        "joint6": [-120.0, 120.0],
    },
    "piper_h": {
        "joint1": [-150.0, 150.0],
        "joint2": [0.0, 180.0],
        "joint3": [-170.0, 0.0],
        "joint4": [-100.0, 100.0],
        "joint5": [-70.0, 70.0],
        "joint6": [-120.0, 120.0],
    },
    "piper_l": {
        "joint1": [-150.0, 150.0],
        "joint2": [0.0, 180.0],
        "joint3": [-170.0, 0.0],
        "joint4": [-100.0, 100.0],
        "joint5": [-70.0, 70.0],
        "joint6": [-120.0, 120.0],
    },
    "piper_x": {
        "joint1": [-150.0, 150.0],
        "joint2": [0.0, 180.0],
        "joint3": [-170.0, 0.0],
        "joint4": [-90.0, 90.0],
        "joint5": [-90.0, 90.0],
        "joint6": [-120.0, 120.0],
    },
}

ROBOT_JOINT_LIMIT_PRESET = ROBOT_JOINT_LIMIT_PRESET_RAD
