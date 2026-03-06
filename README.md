# pyAgxArm User Guide

> `pyAgxArm` is a Python SDK for AgileX robotic arms and end effectors. It supports CAN communication, status reading, motion control, and end-effector control for Piper, Nero, AgxGripper, and Revo2.

## Table of Contents

- [Switch to 中文](#pyagxarm-使用说明)
- [Introduction](#pyagxarm-user-guide)
- [Environment](#environment)
- [Documentation](#documentation)
- [Install](#install)
- [Communication Setup](#communication-setup)
- [Quick Start](#quick-start)
- [Notes](#notes)
- [Contact](#contact)


### Environment

- Ubuntu: `18.04 / 20.04 / 22.04 / 24.04`
- Python: `3.6` and above (compatible up to `3.14`)

### Documentation

| Topic | Link |
| --- | --- |
| ROS | [agx_arm_ros](https://github.com/agilexrobotics/agx_arm_ros) |
| CAN module manual | [docs/can_user.md](./docs/can_user.md#can-module-manual) |
| Piper API | [docs/piper/piper_api.md](./docs/piper/piper_api.md#piper-api-documentation) |
| Nero API | [docs/nero/nero_api.md](./docs/nero/nero_api.md#nero-api-documentation) |
| AgxGripper API | [docs/effector/agx_gripper/agx_gripper_api.md](./docs/effector/agx_gripper/agx_gripper_api.md#agxgripper-api-documentation) |
| Revo2 API | [docs/effector/revo2/revo2_api.md](./docs/effector/revo2/revo2_api.md#revo2-api-documentation) |
| Nero first-time CAN guide | [docs/nero/first_time_user_guide_can.md](./docs/nero/first_time_user_guide_can.md#nero-first-time-user-guide-can) |
| Ubuntu 24.04 pip guide | [docs/ubuntu_24_04_pip_install.md](./docs/ubuntu_24_04_pip_install.md#ubuntu-2404-pip-installation-guide) |
| Q&A | [docs/Q&A.md](./docs/Q&A.md#qa) |
| Changelog | [CHANGELOG.md](./CHANGELOG.md#changelog) |
| Demos | [pyAgxArm/demos](./pyAgxArm/demos) |

### Install

```shell
pip3 install python-can
```

`python-can` should be newer than `3.3.4`.

```shell
git clone https://github.com/agilexrobotics/pyAgxArm.git
cd pyAgxArm
pip3 install .
```

Ubuntu 24.04 users can also refer to:
[docs/ubuntu_24_04_pip_install.md](./docs/ubuntu_24_04_pip_install.md#ubuntu-2404-pip-installation-guide)

### Communication Setup

See:
[docs/can_user.md](./docs/can_user.md#can-module-manual)

### Quick Start

```python
import time
from pyAgxArm import create_agx_arm_config, AgxArmFactory

cfg = create_agx_arm_config(robot="nero", comm="can", channel="can0")
robot = AgxArmFactory.create_arm(cfg)
robot.connect()

while True:
    ja = robot.get_joint_angles()
    if ja is not None:
        print(ja.msg)
        print(ja.hz, ja.timestamp)
    time.sleep(0.005)
```

### Notes

- Activate CAN first and configure the correct bitrate before reading or controlling the arm.
- Use `channel` in `create_agx_arm_config()` to pass your activated CAN interface name.
- MIT single-joint control is an advanced feature; improper use may damage the robot.

### Contact

- GitHub Issues
- Discord: <https://discord.gg/wrKYTxwDBd>

---

# pyAgxArm 使用说明

> `pyAgxArm` 是 AgileX 机械臂与末端执行器的 Python SDK，支持 CAN 通信、状态读取、运动控制，以及 Piper、Nero、AgxGripper、Revo2 等设备的接口调用。

## 目录

- [切换到 English](#pyagxarm-user-guide)
- [简介](#pyagxarm-使用说明)
- [环境支持](#环境支持)
- [文档入口](#文档入口)
- [安装方法](#安装方法)
- [通信激活](#通信激活)
- [快速开始](#快速开始)
- [注意事项](#注意事项)
- [联系我们](#联系我们)

## 环境支持

- Ubuntu：`18.04 / 20.04 / 22.04 / 24.04`
- Python：`3.6` 及以上（目前适配至 `3.14`）

## 文档入口

| 说明 | 文档 |
| --- | --- |
| ROS | [agx_arm_ros](https://github.com/agilexrobotics/agx_arm_ros) |
| CAN 模块手册 | [docs/can_user.md](./docs/can_user.md#can-模块使用手册) |
| Piper API | [docs/piper/piper_api.md](./docs/piper/piper_api.md#piper-机械臂-api-使用文档) |
| Nero API | [docs/nero/nero_api.md](./docs/nero/nero_api.md#nero-机械臂-api-使用文档) |
| AgxGripper API | [docs/effector/agx_gripper/agx_gripper_api.md](./docs/effector/agx_gripper/agx_gripper_api.md#agxgripper-夹爪-api-使用文档) |
| Revo2 API | [docs/effector/revo2/revo2_api.md](./docs/effector/revo2/revo2_api.md#revo2-灵巧手-api-使用文档) |
| Nero 首次使用 CAN 指南 | [docs/nero/first_time_user_guide_can.md](./docs/nero/first_time_user_guide_can.md#nero-首次使用指南can) |
| Ubuntu 24.04 pip 安装说明 | [docs/ubuntu_24_04_pip_install.md](./docs/ubuntu_24_04_pip_install.md#ubuntu-2404-安装第三方-pip-包的方法) |
| Q&A | [docs/Q&A.md](./docs/Q&A.md#常见问题) |
| 更新日志 | [CHANGELOG.md](./CHANGELOG.md#更新日志) |
| 示例代码 | [pyAgxArm/demos](./pyAgxArm/demos) |

## 安装方法

```shell
pip3 install python-can
```

`python-can` 版本应高于 `3.3.4`。

```shell
git clone https://github.com/agilexrobotics/pyAgxArm.git
cd pyAgxArm
pip3 install .
```

Ubuntu 24.04 可参考：
[docs/ubuntu_24_04_pip_install.md](./docs/ubuntu_24_04_pip_install.md#ubuntu-2404-安装第三方-pip-包的方法)

## 通信激活

详见：
[docs/can_user.md](./docs/can_user.md#can-模块使用手册)

## 快速开始

```python
import time
from pyAgxArm import create_agx_arm_config, AgxArmFactory

cfg = create_agx_arm_config(robot="nero", comm="can", channel="can0")
robot = AgxArmFactory.create_arm(cfg)
robot.connect()

while True:
    ja = robot.get_joint_angles()
    if ja is not None:
        print(ja.msg)
        print(ja.hz, ja.timestamp)
    time.sleep(0.005)
```

## 注意事项

- 使用 CAN 协议时，需要先激活 CAN 设备并设置正确波特率。
- `create_agx_arm_config()` 可通过 `channel` 参数传入激活后的 CAN 名称。
- MIT 单关节控制属于高级功能，使用不当可能损坏机械臂。

## 联系我们

- GitHub：提 issue
- Discord：<https://discord.gg/wrKYTxwDBd>
