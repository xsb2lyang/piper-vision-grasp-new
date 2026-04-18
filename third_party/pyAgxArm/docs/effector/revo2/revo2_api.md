# Revo2 API Documentation

> This document describes the `pyAgxArm` API for the Revo2 dexterous hand end effector, covering instance creation, status reading, and finger control.

## Table of Contents

- [Switch to 中文](#revo2-灵巧手-api-使用文档)
- [Create Instance and Connect](#create-instance-and-connect)
  - [Create Arm Driver Instance — AgxArmFactory.create\_arm()](#create-arm-driver-instance--agxarmfactorycreate_arm)
  - [Initialize End Effector — init\_effector()](#initialize-end-effector--init_effector)
  - [Create Connection — connect()](#create-connection--connect)
- [General Status](#general-status)
  - [Check Communication Status — is\_ok()](#check-communication-status--is_ok)
  - [Get Effector Data Receive Frequency — get\_fps()](#get-effector-data-receive-frequency--get_fps)
- [Data Reading](#data-reading)
  - [MessageAbstract Return Value General Description](#messageabstract-return-value-general-description)
  - [Get Hand Status — get\_hand\_status()](#get-hand-status--get_hand_status)
  - [Get Finger Position — get\_finger\_pos()](#get-finger-position--get_finger_pos)
  - [Get Finger Speed — get\_finger\_spd()](#get-finger-speed--get_finger_spd)
  - [Get Finger Current — get\_finger\_current()](#get-finger-current--get_finger_current)
- [Effector Control](#effector-control)
  - [Position Control — position\_ctrl()](#position-control--position_ctrl)
  - [Speed Control — speed\_ctrl()](#speed-control--speed_ctrl)
  - [Current Control — current\_ctrl()](#current-control--current_ctrl)
  - [Position/Time Hybrid Control — position\_time\_ctrl()](#positiontime-hybrid-control--position_time_ctrl)

---

## Create Instance and Connect

### Create Arm Driver Instance — `AgxArmFactory.create_arm()`

**Usage Example:**

```python
from pyAgxArm import create_agx_arm_config, AgxArmFactory, ArmModel, NeroFW

cfg = create_agx_arm_config(robot=ArmModel.NERO, firmeware_version=NeroFW.DEFAULT, channel="can0")
robot = AgxArmFactory.create_arm(cfg)
```

> **Tip:** Accepted values for the `robot` parameter: `"nero"` / `"piper"` / `"piper_h"` / `"piper_l"` / `"piper_x"`.

---

### Initialize End Effector — `init_effector()`

**Description:** Creates the corresponding effector instance based on the specified end-effector type.

**Function Definition:**

```python
init_effector(self, effector: str) -> EffectorDriver
```

**Parameters:**

| Name | Type | Description |
| --- | --- | --- |
| `effector` | `str` | The end effector to initialize |

You can use the predefined variables in the `EFFECTOR` class inside the arm Driver as input arguments, defined as follows:

```python
class EFFECTOR:
    """
    End-effector kind constants.

    Use:
        robot.init_effector(robot.OPTIONS.EFFECTOR.AGX_GRIPPER)
    """

    AGX_GRIPPER: Final[Literal["agx_gripper"]] = "agx_gripper"
    REVO2: Final[Literal["revo2"]] = "revo2"
```

**Return Value:** `EffectorDriver` — Different `effector` input parameters return the corresponding Driver.

**Usage Example:**

```python
from pyAgxArm import create_agx_arm_config, AgxArmFactory, ArmModel, NeroFW

cfg = create_agx_arm_config(robot=ArmModel.NERO, firmeware_version=NeroFW.DEFAULT, channel="can0")
robot = AgxArmFactory.create_arm(cfg)
end_effector = robot.init_effector(robot.OPTIONS.EFFECTOR.REVO2)
```

> **Note:**
> 1. The `init_effector` function can only be called once; it is not possible to initialize two effectors
> 2. It is recommended to create the effector before connecting

---

### Create Connection — `connect()`

**Description:** Creates the connection and starts the data reading thread.

**Function Definition:**

```python
connect(self, start_read_thread: bool = True) -> None
```

**Parameters:**

| Name | Type | Description |
| --- | --- | --- |
| `start_read_thread` | `bool` | Whether to start the data reading thread; defaults to enabled |

**Usage Example:**

```python
from pyAgxArm import create_agx_arm_config, AgxArmFactory, ArmModel, NeroFW

cfg = create_agx_arm_config(robot=ArmModel.NERO, firmeware_version=NeroFW.DEFAULT, channel="can0")
robot = AgxArmFactory.create_arm(cfg)
end_effector = robot.init_effector(robot.OPTIONS.EFFECTOR.REVO2)
robot.connect()
```

---

## General Status

### Check Communication Status — `is_ok()`

**Description:** Checks whether end-effector data reception is normal. This value is computed by the SDK's internal data monitoring logic based on whether data has not been received for a recent period of time.

**Function Definition:**

```python
is_ok(self) -> bool
```

**Return Value:** `bool`

**Usage Example:**

```python
import time
from pyAgxArm import create_agx_arm_config, AgxArmFactory, ArmModel, NeroFW

cfg = create_agx_arm_config(robot=ArmModel.NERO, firmeware_version=NeroFW.DEFAULT, channel="can0")
robot = AgxArmFactory.create_arm(cfg)
end_effector = robot.init_effector(robot.OPTIONS.EFFECTOR.REVO2)
robot.connect()

time.sleep(0.5)
print("effector is_ok =", end_effector.is_ok())
```

---

### Get Effector Data Receive Frequency — `get_fps()`

**Description:** Gets the receive frequency (Hz) of the end-effector data monitor. This frequency is a statistic computed by the SDK on data received by the effector parser.

**Function Definition:**

```python
get_fps(self) -> float
```

**Return Value:** `float` (unit: Hz)

**Usage Example:**

```python
import time
from pyAgxArm import create_agx_arm_config, AgxArmFactory, ArmModel, NeroFW

cfg = create_agx_arm_config(robot=ArmModel.NERO, firmeware_version=NeroFW.DEFAULT, channel="can0")
robot = AgxArmFactory.create_arm(cfg)
end_effector = robot.init_effector(robot.OPTIONS.EFFECTOR.REVO2)
robot.connect()

time.sleep(0.5)
print("effector fps =", end_effector.get_fps(), "Hz")
```

---

## Data Reading

### MessageAbstract Return Value General Description

Most reading interfaces in this SDK return `MessageAbstract[T] | None`, where:

| Field | Type | Description |
| --- | --- | --- |
| `ret.msg` | `T` | The message data body (e.g. hand status / finger position / speed structs) |
| `ret.hz` | `float` | The receive frequency for this message type (computed by SDK), unit: Hz |
| `ret.timestamp` | `float` | The message timestamp (recorded by SDK), unit: s |

---

### Get Hand Status — `get_hand_status()`

**Description:** Reads the dexterous hand's per-finger running status feedback (left/right hand flag, per-finger motor status: idle/running/stalled).

**Function Definition:**

```python
get_hand_status(self) -> Optional[MessageAbstract[FeedbackHandStatus]]
```

**Return Value:** `MessageAbstract[FeedbackHandStatus] | None`

**Message Fields (`.msg`):**

| Field | Type | Description |
| --- | --- | --- |
| `left_or_right` | `int` | Left/right hand flag: 1=left, 2=right, range: [1, 2] |
| `thumb_tip` | `int` | Thumb tip motor status: 0=idle, 1=running, 2=stalled, range: [0, 2] |
| `thumb_base` | `int` | Thumb base motor status: 0=idle, 1=running, 2=stalled, range: [0, 2] |
| `index_finger` | `int` | Index finger motor status: 0=idle, 1=running, 2=stalled, range: [0, 2] |
| `middle_finger` | `int` | Middle finger motor status: 0=idle, 1=running, 2=stalled, range: [0, 2] |
| `ring_finger` | `int` | Ring finger motor status: 0=idle, 1=running, 2=stalled, range: [0, 2] |
| `pinky_finger` | `int` | Pinky finger motor status: 0=idle, 1=running, 2=stalled, range: [0, 2] |

**Usage Example:**

```python
import time
from pyAgxArm import create_agx_arm_config, AgxArmFactory, ArmModel, NeroFW

cfg = create_agx_arm_config(robot=ArmModel.NERO, firmeware_version=NeroFW.DEFAULT, channel="can0")
robot = AgxArmFactory.create_arm(cfg)
end_effector = robot.init_effector(robot.OPTIONS.EFFECTOR.REVO2)
robot.connect()

time.sleep(0.2)
hs = end_effector.get_hand_status()
if hs is not None:
    print(hs.msg)
    print(hs.hz, hs.timestamp)
```

---

### Get Finger Position — `get_finger_pos()`

**Description:** Reads the dexterous hand's per-finger position feedback (0~100).

**Function Definition:**

```python
get_finger_pos(self) -> Optional[MessageAbstract[FeedbackFingerPos]]
```

**Return Value:** `MessageAbstract[FeedbackFingerPos] | None`

**Message Fields (`.msg`):**

| Field | Type | Description |
| --- | --- | --- |
| `thumb_tip` | `int` | Thumb tip position, range: [0, 100] |
| `thumb_base` | `int` | Thumb base position, range: [0, 100] |
| `index_finger` | `int` | Index finger position, range: [0, 100] |
| `middle_finger` | `int` | Middle finger position, range: [0, 100] |
| `ring_finger` | `int` | Ring finger position, range: [0, 100] |
| `pinky_finger` | `int` | Pinky finger position, range: [0, 100] |

**Usage Example:**

```python
import time
from pyAgxArm import create_agx_arm_config, AgxArmFactory, ArmModel, NeroFW

cfg = create_agx_arm_config(robot=ArmModel.NERO, firmeware_version=NeroFW.DEFAULT, channel="can0")
robot = AgxArmFactory.create_arm(cfg)
end_effector = robot.init_effector(robot.OPTIONS.EFFECTOR.REVO2)
robot.connect()

time.sleep(0.2)
fp = end_effector.get_finger_pos()
if fp is not None:
    print(fp.msg)
    print(fp.hz, fp.timestamp)
```

---

### Get Finger Speed — `get_finger_spd()`

**Description:** Reads the dexterous hand's per-finger speed feedback.

**Function Definition:**

```python
get_finger_spd(self) -> Optional[MessageAbstract[FeedbackFingerSpd]]
```

**Return Value:** `MessageAbstract[FeedbackFingerSpd] | None`

**Message Fields (`.msg`):**

| Field | Type | Description |
| --- | --- | --- |
| `thumb_tip` | `int` | Thumb tip speed, range: [-100, 100] |
| `thumb_base` | `int` | Thumb base speed, range: [-100, 100] |
| `index_finger` | `int` | Index finger speed, range: [-100, 100] |
| `middle_finger` | `int` | Middle finger speed, range: [-100, 100] |
| `ring_finger` | `int` | Ring finger speed, range: [-100, 100] |
| `pinky_finger` | `int` | Pinky finger speed, range: [-100, 100] |

**Usage Example:**

```python
import time
from pyAgxArm import create_agx_arm_config, AgxArmFactory, ArmModel, NeroFW

cfg = create_agx_arm_config(robot=ArmModel.NERO, firmeware_version=NeroFW.DEFAULT, channel="can0")
robot = AgxArmFactory.create_arm(cfg)
end_effector = robot.init_effector(robot.OPTIONS.EFFECTOR.REVO2)
robot.connect()

time.sleep(0.2)
fs = end_effector.get_finger_spd()
if fs is not None:
    print(fs.msg)
    print(fs.hz, fs.timestamp)
```

---

### Get Finger Current — `get_finger_current()`

**Description:** Reads the dexterous hand's per-finger current feedback.

**Function Definition:**

```python
get_finger_current(self) -> Optional[MessageAbstract[FeedbackFingerCurrent]]
```

**Return Value:** `MessageAbstract[FeedbackFingerCurrent] | None`

**Message Fields (`.msg`):**

| Field | Type | Description |
| --- | --- | --- |
| `thumb_tip` | `int` | Thumb tip current, range: [-100, 100] |
| `thumb_base` | `int` | Thumb base current, range: [-100, 100] |
| `index_finger` | `int` | Index finger current, range: [-100, 100] |
| `middle_finger` | `int` | Middle finger current, range: [-100, 100] |
| `ring_finger` | `int` | Ring finger current, range: [-100, 100] |
| `pinky_finger` | `int` | Pinky finger current, range: [-100, 100] |

**Usage Example:**

```python
import time
from pyAgxArm import create_agx_arm_config, AgxArmFactory, ArmModel, NeroFW

cfg = create_agx_arm_config(robot=ArmModel.NERO, firmeware_version=NeroFW.DEFAULT, channel="can0")
robot = AgxArmFactory.create_arm(cfg)
end_effector = robot.init_effector(robot.OPTIONS.EFFECTOR.REVO2)
robot.connect()

time.sleep(0.2)
fc = end_effector.get_finger_current()
if fc is not None:
    print(fc.msg)
    print(fc.hz, fc.timestamp)
```

---

## Effector Control

### Position Control — `position_ctrl()`

**Description:** Controls each finger's target position in "position mode".

**Function Definition:**

```python
position_ctrl(
    self,
    thumb_tip: int = 0,
    thumb_base: int = 0,
    index_finger: int = 0,
    middle_finger: int = 0,
    ring_finger: int = 0,
    pinky_finger: int = 0,
) -> None
```

**Parameters:**

| Name | Type | Description |
| --- | --- | --- |
| `thumb_tip` | `int` | Thumb tip position, range: [0, 100], default: 0 |
| `thumb_base` | `int` | Thumb base position, range: [0, 100], default: 0 |
| `index_finger` | `int` | Index finger position, range: [0, 100], default: 0 |
| `middle_finger` | `int` | Middle finger position, range: [0, 100], default: 0 |
| `ring_finger` | `int` | Ring finger position, range: [0, 100], default: 0 |
| `pinky_finger` | `int` | Pinky finger position, range: [0, 100], default: 0 |

**Usage Example:**

```python
from pyAgxArm import create_agx_arm_config, AgxArmFactory, ArmModel, NeroFW

cfg = create_agx_arm_config(robot=ArmModel.NERO, firmeware_version=NeroFW.DEFAULT, channel="can0")
robot = AgxArmFactory.create_arm(cfg)
end_effector = robot.init_effector(robot.OPTIONS.EFFECTOR.REVO2)
robot.connect()

# 全部张开/归零
end_effector.position_ctrl()

# 拇指尖到 100，其余不变（示例）
end_effector.position_ctrl(thumb_tip=100)
```

---

### Speed Control — `speed_ctrl()`

**Description:** Controls each finger's target speed in "speed mode".

**Function Definition:**

```python
speed_ctrl(
    self,
    thumb_tip: int = 0,
    thumb_base: int = 0,
    index_finger: int = 0,
    middle_finger: int = 0,
    ring_finger: int = 0,
    pinky_finger: int = 0,
) -> None
```

**Parameters:**

| Name | Type | Description |
| --- | --- | --- |
| `thumb_tip` | `int` | Thumb tip speed, range: [-100, 100], default: 0 |
| `thumb_base` | `int` | Thumb base speed, range: [-100, 100], default: 0 |
| `index_finger` | `int` | Index finger speed, range: [-100, 100], default: 0 |
| `middle_finger` | `int` | Middle finger speed, range: [-100, 100], default: 0 |
| `ring_finger` | `int` | Ring finger speed, range: [-100, 100], default: 0 |
| `pinky_finger` | `int` | Pinky finger speed, range: [-100, 100], default: 0 |

**Usage Example:**

```python
from pyAgxArm import create_agx_arm_config, AgxArmFactory, ArmModel, NeroFW

cfg = create_agx_arm_config(robot=ArmModel.NERO, firmeware_version=NeroFW.DEFAULT, channel="can0")
robot = AgxArmFactory.create_arm(cfg)
end_effector = robot.init_effector(robot.OPTIONS.EFFECTOR.REVO2)
robot.connect()

end_effector.speed_ctrl(thumb_tip=50)
```

---

### Current Control — `current_ctrl()`

**Description:** Controls each finger's target current in "current mode".

**Function Definition:**

```python
current_ctrl(
    self,
    thumb_tip: int = 0,
    thumb_base: int = 0,
    index_finger: int = 0,
    middle_finger: int = 0,
    ring_finger: int = 0,
    pinky_finger: int = 0,
) -> None
```

**Parameters:**

| Name | Type | Description |
| --- | --- | --- |
| `thumb_tip` | `int` | Thumb tip current, range: [-100, 100], default: 0 |
| `thumb_base` | `int` | Thumb base current, range: [-100, 100], default: 0 |
| `index_finger` | `int` | Index finger current, range: [-100, 100], default: 0 |
| `middle_finger` | `int` | Middle finger current, range: [-100, 100], default: 0 |
| `ring_finger` | `int` | Ring finger current, range: [-100, 100], default: 0 |
| `pinky_finger` | `int` | Pinky finger current, range: [-100, 100], default: 0 |

**Usage Example:**

```python
from pyAgxArm import create_agx_arm_config, AgxArmFactory, ArmModel, NeroFW

cfg = create_agx_arm_config(robot=ArmModel.NERO, firmeware_version=NeroFW.DEFAULT, channel="can0")
robot = AgxArmFactory.create_arm(cfg)
end_effector = robot.init_effector(robot.OPTIONS.EFFECTOR.REVO2)
robot.connect()

end_effector.current_ctrl(thumb_tip=10)
```

---

### Position/Time Hybrid Control — `position_time_ctrl()`

**Description:** Position/time hybrid control: first send the target position with `mode="pos"`, then send the arrival time (unit: 10ms) with `mode="time"`.

> **Note:** The interval between the two messages should not exceed 50ms.

**Function Definition:**

```python
position_time_ctrl(
    self,
    mode: Literal['pos', 'time'] = 'pos',
    thumb_tip: int = 0,
    thumb_base: int = 0,
    index_finger: int = 0,
    middle_finger: int = 0,
    ring_finger: int = 0,
    pinky_finger: int = 0,
) -> None
```

**Parameters:**

| Name | Type | Description |
| --- | --- | --- |
| `mode` | `Literal['pos', 'time']` | Control mode, default: `'pos'` |
| `thumb_tip` | `int` | Thumb tip: pos mode range [0, 100], time mode range [0, 255] (unit: 10 ms), default: 0 |
| `thumb_base` | `int` | Thumb base: pos mode range [0, 100], time mode range [0, 255] (unit: 10 ms), default: 0 |
| `index_finger` | `int` | Index finger: pos mode range [0, 100], time mode range [0, 255] (unit: 10 ms), default: 0 |
| `middle_finger` | `int` | Middle finger: pos mode range [0, 100], time mode range [0, 255] (unit: 10 ms), default: 0 |
| `ring_finger` | `int` | Ring finger: pos mode range [0, 100], time mode range [0, 255] (unit: 10 ms), default: 0 |
| `pinky_finger` | `int` | Pinky finger: pos mode range [0, 100], time mode range [0, 255] (unit: 10 ms), default: 0 |

**Usage Example:**

```python
import time
from pyAgxArm import create_agx_arm_config, AgxArmFactory, ArmModel, NeroFW

cfg = create_agx_arm_config(robot=ArmModel.NERO, firmeware_version=NeroFW.DEFAULT, channel="can0")
robot = AgxArmFactory.create_arm(cfg)
end_effector = robot.init_effector(robot.OPTIONS.EFFECTOR.REVO2)
robot.connect()

# 拇指尖移动到位置 100，然后设置 2 秒到位（200 * 10ms）
end_effector.position_time_ctrl(mode="pos", thumb_tip=100)
end_effector.position_time_ctrl(mode="time", thumb_tip=200)
```

---

# Revo2 灵巧手 API 使用文档

> 本文档描述 `pyAgxArm` SDK 为 Revo2 灵巧手末端执行器提供的 Python API。涵盖实例创建、状态读取、手指控制等全部接口。

## 目录

- [切换到 English](#revo2-api-documentation)
- [创建实例并连接](#创建实例并连接)
  - [创建机械臂 Driver 实例 — AgxArmFactory.create\_arm()](#创建机械臂-driver-实例--agxarmfactorycreate_arm)
  - [初始化末端执行器 — init\_effector()](#初始化末端执行器--init_effector)
  - [创建连接 — connect()](#创建连接--connect)
- [通用状态](#通用状态)
  - [通信是否正常 — is\_ok()](#通信是否正常--is_ok)
  - [获取执行器数据接收频率 — get\_fps()](#获取执行器数据接收频率--get_fps)
- [数据读取](#数据读取)
  - [MessageAbstract 返回值通用说明](#messageabstract-返回值通用说明)
  - [读取末端执行器状态 — get\_hand\_status()](#读取末端执行器状态--get_hand_status)
  - [读取各指位置 — get\_finger\_pos()](#读取各指位置--get_finger_pos)
  - [读取各指速度 — get\_finger\_spd()](#读取各指速度--get_finger_spd)
  - [读取各指电流 — get\_finger\_current()](#读取各指电流--get_finger_current)
- [执行器控制](#执行器控制)
  - [位置控制 — position\_ctrl()](#位置控制--position_ctrl)
  - [速度控制 — speed\_ctrl()](#速度控制--speed_ctrl)
  - [电流控制 — current\_ctrl()](#电流控制--current_ctrl)
  - [位置/时间混合控制 — position\_time\_ctrl()](#位置时间混合控制--position_time_ctrl)

---

## 创建实例并连接

### 创建机械臂 Driver 实例 — `AgxArmFactory.create_arm()`

**使用示例：**

```python
from pyAgxArm import create_agx_arm_config, AgxArmFactory, ArmModel, NeroFW

cfg = create_agx_arm_config(robot=ArmModel.NERO, firmeware_version=NeroFW.DEFAULT, channel="can0")
robot = AgxArmFactory.create_arm(cfg)
```

> **提示：** `robot` 形参范围：`"nero"` / `"piper"` / `"piper_h"` / `"piper_l"` / `"piper_x"`。

---

### 初始化末端执行器 — `init_effector()`

**功能说明：** 根据传入的末端执行器种类，创建对应的执行器实例。

**函数定义：**

```python
init_effector(self, effector: str) -> EffectorDriver
```

**参数说明：**

| 名称 | 类型 | 说明 |
| --- | --- | --- |
| `effector` | `str` | 初始化指定的执行器 |

可以通过机械臂 Driver 内部的 `EFFECTOR` 类中的预定义变量来作为输入的实参，定义如下：

```python
class EFFECTOR:
    """
    End-effector kind constants.

    Use:
        robot.init_effector(robot.OPTIONS.EFFECTOR.AGX_GRIPPER)
    """

    AGX_GRIPPER: Final[Literal["agx_gripper"]] = "agx_gripper"
    REVO2: Final[Literal["revo2"]] = "revo2"
```

**返回值：** `EffectorDriver` — 不同的输入参数 `effector`，返回对应的 Driver。

**使用示例：**

```python
from pyAgxArm import create_agx_arm_config, AgxArmFactory, ArmModel, NeroFW

cfg = create_agx_arm_config(robot=ArmModel.NERO, firmeware_version=NeroFW.DEFAULT, channel="can0")
robot = AgxArmFactory.create_arm(cfg)
end_effector = robot.init_effector(robot.OPTIONS.EFFECTOR.REVO2)
```

> **注意：**
> 1. `init_effector` 函数只能执行一次，无法初始化两个执行器
> 2. 最好在连接前进行执行器的创建

---

### 创建连接 — `connect()`

**功能说明：** 创建连接并启动数据读取线程。

**函数定义：**

```python
connect(self, start_read_thread: bool = True) -> None
```

**参数说明：**

| 名称 | 类型 | 说明 |
| --- | --- | --- |
| `start_read_thread` | `bool` | 是否打开读取数据线程，默认为打开 |

**使用示例：**

```python
from pyAgxArm import create_agx_arm_config, AgxArmFactory, ArmModel, NeroFW

cfg = create_agx_arm_config(robot=ArmModel.NERO, firmeware_version=NeroFW.DEFAULT, channel="can0")
robot = AgxArmFactory.create_arm(cfg)
end_effector = robot.init_effector(robot.OPTIONS.EFFECTOR.REVO2)
robot.connect()
```

---

## 通用状态

### 通信是否正常 — `is_ok()`

**功能说明：** 用于判断末端执行器数据接收是否正常。该值由 SDK 内部的数据监控逻辑根据"最近一段时间是否持续收不到数据"计算得出。

**函数定义：**

```python
is_ok(self) -> bool
```

**返回值：** `bool`

**使用示例：**

```python
import time
from pyAgxArm import create_agx_arm_config, AgxArmFactory, ArmModel, NeroFW

cfg = create_agx_arm_config(robot=ArmModel.NERO, firmeware_version=NeroFW.DEFAULT, channel="can0")
robot = AgxArmFactory.create_arm(cfg)
end_effector = robot.init_effector(robot.OPTIONS.EFFECTOR.REVO2)
robot.connect()

time.sleep(0.5)
print("effector is_ok =", end_effector.is_ok())
```

---

### 获取执行器数据接收频率 — `get_fps()`

**功能说明：** 获取末端执行器数据监控的接收频率（Hz）。该频率是 SDK 对执行器解析器收到数据的统计值。

**函数定义：**

```python
get_fps(self) -> float
```

**返回值：** `float`（单位：Hz）

**使用示例：**

```python
import time
from pyAgxArm import create_agx_arm_config, AgxArmFactory, ArmModel, NeroFW

cfg = create_agx_arm_config(robot=ArmModel.NERO, firmeware_version=NeroFW.DEFAULT, channel="can0")
robot = AgxArmFactory.create_arm(cfg)
end_effector = robot.init_effector(robot.OPTIONS.EFFECTOR.REVO2)
robot.connect()

time.sleep(0.5)
print("effector fps =", end_effector.get_fps(), "Hz")
```

---

## 数据读取

### MessageAbstract 返回值通用说明

本 SDK 多数读取接口返回 `MessageAbstract[T] | None`。其中：

| 字段 | 类型 | 说明 |
| --- | --- | --- |
| `ret.msg` | `T` | 消息数据本体（例如灵巧手状态/各指位置/速度等结构体） |
| `ret.hz` | `float` | 该消息类型的接收频率（由 SDK 统计），单位：Hz |
| `ret.timestamp` | `float` | 消息时间戳（由 SDK 记录），单位：s |

---

### 读取末端执行器状态 — `get_hand_status()`

**功能说明：** 读取灵巧手各指运行状态反馈（左右手标志、各指电机状态：空闲/运行/堵转）。

**函数定义：**

```python
get_hand_status(self) -> Optional[MessageAbstract[FeedbackHandStatus]]
```

**返回值：** `MessageAbstract[FeedbackHandStatus] | None`

**消息字段（`.msg`）：**

| 字段 | 类型 | 说明 |
| --- | --- | --- |
| `left_or_right` | `int` | 左右手标志：1=左手，2=右手，范围：[1, 2] |
| `thumb_tip` | `int` | 拇指尖电机状态：0=空闲，1=运行，2=堵转，范围：[0, 2] |
| `thumb_base` | `int` | 拇指根电机状态：0=空闲，1=运行，2=堵转，范围：[0, 2] |
| `index_finger` | `int` | 食指电机状态：0=空闲，1=运行，2=堵转，范围：[0, 2] |
| `middle_finger` | `int` | 中指电机状态：0=空闲，1=运行，2=堵转，范围：[0, 2] |
| `ring_finger` | `int` | 无名指电机状态：0=空闲，1=运行，2=堵转，范围：[0, 2] |
| `pinky_finger` | `int` | 小指电机状态：0=空闲，1=运行，2=堵转，范围：[0, 2] |

**使用示例：**

```python
import time
from pyAgxArm import create_agx_arm_config, AgxArmFactory, ArmModel, NeroFW

cfg = create_agx_arm_config(robot=ArmModel.NERO, firmeware_version=NeroFW.DEFAULT, channel="can0")
robot = AgxArmFactory.create_arm(cfg)
end_effector = robot.init_effector(robot.OPTIONS.EFFECTOR.REVO2)
robot.connect()

time.sleep(0.2)
hs = end_effector.get_hand_status()
if hs is not None:
    print(hs.msg)
    print(hs.hz, hs.timestamp)
```

---

### 读取各指位置 — `get_finger_pos()`

**功能说明：** 读取灵巧手各指位置反馈（0~100）。

**函数定义：**

```python
get_finger_pos(self) -> Optional[MessageAbstract[FeedbackFingerPos]]
```

**返回值：** `MessageAbstract[FeedbackFingerPos] | None`

**消息字段（`.msg`）：**

| 字段 | 类型 | 说明 |
| --- | --- | --- |
| `thumb_tip` | `int` | 拇指尖位置，范围：[0, 100] |
| `thumb_base` | `int` | 拇指根位置，范围：[0, 100] |
| `index_finger` | `int` | 食指位置，范围：[0, 100] |
| `middle_finger` | `int` | 中指位置，范围：[0, 100] |
| `ring_finger` | `int` | 无名指位置，范围：[0, 100] |
| `pinky_finger` | `int` | 小指位置，范围：[0, 100] |

**使用示例：**

```python
import time
from pyAgxArm import create_agx_arm_config, AgxArmFactory, ArmModel, NeroFW

cfg = create_agx_arm_config(robot=ArmModel.NERO, firmeware_version=NeroFW.DEFAULT, channel="can0")
robot = AgxArmFactory.create_arm(cfg)
end_effector = robot.init_effector(robot.OPTIONS.EFFECTOR.REVO2)
robot.connect()

time.sleep(0.2)
fp = end_effector.get_finger_pos()
if fp is not None:
    print(fp.msg)
    print(fp.hz, fp.timestamp)
```

---

### 读取各指速度 — `get_finger_spd()`

**功能说明：** 读取灵巧手各指速度反馈。

**函数定义：**

```python
get_finger_spd(self) -> Optional[MessageAbstract[FeedbackFingerSpd]]
```

**返回值：** `MessageAbstract[FeedbackFingerSpd] | None`

**消息字段（`.msg`）：**

| 字段 | 类型 | 说明 |
| --- | --- | --- |
| `thumb_tip` | `int` | 拇指尖速度，范围：[-100, 100] |
| `thumb_base` | `int` | 拇指根速度，范围：[-100, 100] |
| `index_finger` | `int` | 食指速度，范围：[-100, 100] |
| `middle_finger` | `int` | 中指速度，范围：[-100, 100] |
| `ring_finger` | `int` | 无名指速度，范围：[-100, 100] |
| `pinky_finger` | `int` | 小指速度，范围：[-100, 100] |

**使用示例：**

```python
import time
from pyAgxArm import create_agx_arm_config, AgxArmFactory, ArmModel, NeroFW

cfg = create_agx_arm_config(robot=ArmModel.NERO, firmeware_version=NeroFW.DEFAULT, channel="can0")
robot = AgxArmFactory.create_arm(cfg)
end_effector = robot.init_effector(robot.OPTIONS.EFFECTOR.REVO2)
robot.connect()

time.sleep(0.2)
fs = end_effector.get_finger_spd()
if fs is not None:
    print(fs.msg)
    print(fs.hz, fs.timestamp)
```

---

### 读取各指电流 — `get_finger_current()`

**功能说明：** 读取灵巧手各指电流反馈。

**函数定义：**

```python
get_finger_current(self) -> Optional[MessageAbstract[FeedbackFingerCurrent]]
```

**返回值：** `MessageAbstract[FeedbackFingerCurrent] | None`

**消息字段（`.msg`）：**

| 字段 | 类型 | 说明 |
| --- | --- | --- |
| `thumb_tip` | `int` | 拇指尖电流，范围：[-100, 100] |
| `thumb_base` | `int` | 拇指根电流，范围：[-100, 100] |
| `index_finger` | `int` | 食指电流，范围：[-100, 100] |
| `middle_finger` | `int` | 中指电流，范围：[-100, 100] |
| `ring_finger` | `int` | 无名指电流，范围：[-100, 100] |
| `pinky_finger` | `int` | 小指电流，范围：[-100, 100] |

**使用示例：**

```python
import time
from pyAgxArm import create_agx_arm_config, AgxArmFactory, ArmModel, NeroFW

cfg = create_agx_arm_config(robot=ArmModel.NERO, firmeware_version=NeroFW.DEFAULT, channel="can0")
robot = AgxArmFactory.create_arm(cfg)
end_effector = robot.init_effector(robot.OPTIONS.EFFECTOR.REVO2)
robot.connect()

time.sleep(0.2)
fc = end_effector.get_finger_current()
if fc is not None:
    print(fc.msg)
    print(fc.hz, fc.timestamp)
```

---

## 执行器控制

### 位置控制 — `position_ctrl()`

**功能说明：** 按"位置模式"控制各手指目标位置。

**函数定义：**

```python
position_ctrl(
    self,
    thumb_tip: int = 0,
    thumb_base: int = 0,
    index_finger: int = 0,
    middle_finger: int = 0,
    ring_finger: int = 0,
    pinky_finger: int = 0,
) -> None
```

**参数说明：**

| 名称 | 类型 | 说明 |
| --- | --- | --- |
| `thumb_tip` | `int` | 拇指尖位置，范围：[0, 100]，默认：0 |
| `thumb_base` | `int` | 拇指根位置，范围：[0, 100]，默认：0 |
| `index_finger` | `int` | 食指位置，范围：[0, 100]，默认：0 |
| `middle_finger` | `int` | 中指位置，范围：[0, 100]，默认：0 |
| `ring_finger` | `int` | 无名指位置，范围：[0, 100]，默认：0 |
| `pinky_finger` | `int` | 小指位置，范围：[0, 100]，默认：0 |

**使用示例：**

```python
from pyAgxArm import create_agx_arm_config, AgxArmFactory, ArmModel, NeroFW

cfg = create_agx_arm_config(robot=ArmModel.NERO, firmeware_version=NeroFW.DEFAULT, channel="can0")
robot = AgxArmFactory.create_arm(cfg)
end_effector = robot.init_effector(robot.OPTIONS.EFFECTOR.REVO2)
robot.connect()

# 全部张开/归零
end_effector.position_ctrl()

# 拇指尖到 100，其余不变（示例）
end_effector.position_ctrl(thumb_tip=100)
```

---

### 速度控制 — `speed_ctrl()`

**功能说明：** 按"速度模式"控制各手指目标速度。

**函数定义：**

```python
speed_ctrl(
    self,
    thumb_tip: int = 0,
    thumb_base: int = 0,
    index_finger: int = 0,
    middle_finger: int = 0,
    ring_finger: int = 0,
    pinky_finger: int = 0,
) -> None
```

**参数说明：**

| 名称 | 类型 | 说明 |
| --- | --- | --- |
| `thumb_tip` | `int` | 拇指尖速度，范围：[-100, 100]，默认：0 |
| `thumb_base` | `int` | 拇指根速度，范围：[-100, 100]，默认：0 |
| `index_finger` | `int` | 食指速度，范围：[-100, 100]，默认：0 |
| `middle_finger` | `int` | 中指速度，范围：[-100, 100]，默认：0 |
| `ring_finger` | `int` | 无名指速度，范围：[-100, 100]，默认：0 |
| `pinky_finger` | `int` | 小指速度，范围：[-100, 100]，默认：0 |

**使用示例：**

```python
from pyAgxArm import create_agx_arm_config, AgxArmFactory, ArmModel, NeroFW

cfg = create_agx_arm_config(robot=ArmModel.NERO, firmeware_version=NeroFW.DEFAULT, channel="can0")
robot = AgxArmFactory.create_arm(cfg)
end_effector = robot.init_effector(robot.OPTIONS.EFFECTOR.REVO2)
robot.connect()

end_effector.speed_ctrl(thumb_tip=50)
```

---

### 电流控制 — `current_ctrl()`

**功能说明：** 按"电流模式"控制各手指目标电流。

**函数定义：**

```python
current_ctrl(
    self,
    thumb_tip: int = 0,
    thumb_base: int = 0,
    index_finger: int = 0,
    middle_finger: int = 0,
    ring_finger: int = 0,
    pinky_finger: int = 0,
) -> None
```

**参数说明：**

| 名称 | 类型 | 说明 |
| --- | --- | --- |
| `thumb_tip` | `int` | 拇指尖电流，范围：[-100, 100]，默认：0 |
| `thumb_base` | `int` | 拇指根电流，范围：[-100, 100]，默认：0 |
| `index_finger` | `int` | 食指电流，范围：[-100, 100]，默认：0 |
| `middle_finger` | `int` | 中指电流，范围：[-100, 100]，默认：0 |
| `ring_finger` | `int` | 无名指电流，范围：[-100, 100]，默认：0 |
| `pinky_finger` | `int` | 小指电流，范围：[-100, 100]，默认：0 |

**使用示例：**

```python
from pyAgxArm import create_agx_arm_config, AgxArmFactory, ArmModel, NeroFW

cfg = create_agx_arm_config(robot=ArmModel.NERO, firmeware_version=NeroFW.DEFAULT, channel="can0")
robot = AgxArmFactory.create_arm(cfg)
end_effector = robot.init_effector(robot.OPTIONS.EFFECTOR.REVO2)
robot.connect()

end_effector.current_ctrl(thumb_tip=10)
```

---

### 位置/时间混合控制 — `position_time_ctrl()`

**功能说明：** 位置/时间混合控制：先用 `mode="pos"` 下发目标位置，再用 `mode="time"` 下发到位时间（单位 10ms）。

> **注意：** 两条消息的间隔不应超过 50ms。

**函数定义：**

```python
position_time_ctrl(
    self,
    mode: Literal['pos', 'time'] = 'pos',
    thumb_tip: int = 0,
    thumb_base: int = 0,
    index_finger: int = 0,
    middle_finger: int = 0,
    ring_finger: int = 0,
    pinky_finger: int = 0,
) -> None
```

**参数说明：**

| 名称 | 类型 | 说明 |
| --- | --- | --- |
| `mode` | `Literal['pos', 'time']` | 控制模式，默认：`'pos'` |
| `thumb_tip` | `int` | 拇指尖：pos 模式范围 [0, 100]，time 模式范围 [0, 255]（单位：10 ms），默认：0 |
| `thumb_base` | `int` | 拇指根：pos 模式范围 [0, 100]，time 模式范围 [0, 255]（单位：10 ms），默认：0 |
| `index_finger` | `int` | 食指：pos 模式范围 [0, 100]，time 模式范围 [0, 255]（单位：10 ms），默认：0 |
| `middle_finger` | `int` | 中指：pos 模式范围 [0, 100]，time 模式范围 [0, 255]（单位：10 ms），默认：0 |
| `ring_finger` | `int` | 无名指：pos 模式范围 [0, 100]，time 模式范围 [0, 255]（单位：10 ms），默认：0 |
| `pinky_finger` | `int` | 小指：pos 模式范围 [0, 100]，time 模式范围 [0, 255]（单位：10 ms），默认：0 |

**使用示例：**

```python
import time
from pyAgxArm import create_agx_arm_config, AgxArmFactory, ArmModel, NeroFW

cfg = create_agx_arm_config(robot=ArmModel.NERO, firmeware_version=NeroFW.DEFAULT, channel="can0")
robot = AgxArmFactory.create_arm(cfg)
end_effector = robot.init_effector(robot.OPTIONS.EFFECTOR.REVO2)
robot.connect()

# 拇指尖移动到位置 100，然后设置 2 秒到位（200 * 10ms）
end_effector.position_time_ctrl(mode="pos", thumb_tip=100)
end_effector.position_time_ctrl(mode="time", thumb_tip=200)
```
