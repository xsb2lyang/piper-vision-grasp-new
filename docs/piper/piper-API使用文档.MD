# API使用文档

## 导入模块

```python
from pyAgxArm import create_agx_arm_config, AgxArmFactory
```

## 创建实例并连接

### 创建配置参数 create_agx_arm_config()

- 定义

```python
create_agx_arm_config(
        robot:Literal["nero","piper","piper_h","piper_l","piper_x"],
        comm:Literal["can"],
        firmeware_version: str = "default",
        **kwargs) -> dict
```

- 参数说明:

|名称|类型|说明|
|---|---|---|
|robot|str|["nero","piper","piper_h","piper_l","piper_x"]参数可选，选择预期创建的机械臂实例|
|comm|str|["can"]可选，选择连接机械臂的通讯方式|
|firmeware_version|str|默认为"default"，选择机械臂当前底层对应的主控固件版本|
|---可选参数---|||
|joint_limit|dict|默认可以不输入，程序内自动根据机械臂赋值指定的关节限位，如果要指定，需要手动输入dict类型的关节限位，单位：弧度，示例下文可见，暂时不会对手动输入的关节限位生效到实际控制中|
|当通讯方式为can时|||
|channel|str|默认为"can0"，选择预期连接的can channel|
|interface|str|默认为"socketcan"，选择连接can模块的接口种类，官方can模块连接到linux系统中必须为"socketcan"，如果想要连接macos，需要更换串口can模块然后将该参数设置为"slcan"|
|bitrate|int|默认为1000000，预期can端口的波特率，机械臂官方can模块默认为1Mbps|
|enable_check_can|bool|默认为True，功能为是否打开创建内部Comm实例时检查can模块，默认打开|
|auto_connect|bool|默认为True，功能为是否打开创建内部Comm实例时自动创建can bus实例，默认打开|
|timeout|float|默认为1.0，设置can bus读取和发送的超时时间|

- 返回值:

类型: dict

结构如下：

```json
{
    "robot": "nero",
    "comm":{
        "type":"can",
        "can":{
            "channel": "can0",
            "interface": "socketcan",
            "bitrate": 1000000,
            "enable_check_can": true,
            "auto_connect": true,
            "timeout": 1.0
        }
    },
    "joint_limit":{
        "j1":[-2.617994, 2.617994],
        "j2":[0.0, 3.141593],
        "j3":[-2.967060, 0.0],
        "j4":[-1.745330, 1.745330],
        "j5":[-1.221730, 1.221730],
        "j6":[-2.094396, 2.094396]
    },
}
```

关节运动限位单位为弧度

夹爪运动限位单位为米

- 使用示例:

```python
cfg = create_agx_arm_config(robot="piper", channel="can0")
print(cfg)
```

### 创建机械臂Driver实例 AgxArmFactory.create_arm()

- 功能说明:

根据传入的配置文件，使用工厂创建不同的机械臂实例

- 定义:

```python
create_arm(cls, config: dict, **kwargs) -> T
```

- 参数说明:

|名称|类型|说明|
|---|---|---|
|config|dict|读取配置参数字典|

- 返回值:

类型:Driver

不同臂、通讯类型、固件版本有不同的实例创建

- 使用示例:

```python
import time
from pyAgxArm import create_agx_arm_config, AgxArmFactory
cfg = create_agx_arm_config(robot="piper", channel="can0")
robot = AgxArmFactory.create_arm(cfg)
```

### 创建连接 connect()

- 功能说明:

该指令用来创建连接，启动读取线程

- 定义:

```python
connect(self, start_read_thread: bool = True) -> None
```

- 参数说明:

|名称|类型|说明|
|---|---|---|
|start_read_thread|bool|是否打开读取数据线程，默认为打开|

- 使用示例:

```python
import time
from pyAgxArm import create_agx_arm_config, AgxArmFactory
cfg = create_agx_arm_config(robot="piper", channel="can0")
robot = AgxArmFactory.create_arm(cfg)
robot.connect()
```

## 通用状态相关

### 通信是否正常 is_ok()

- 功能说明:

用于判断机械臂数据接收是否正常。该值由 SDK 内部的数据监控逻辑根据“最近一段时间是否持续收不到数据”计算得出。

- 定义:

```python
is_ok(self) -> bool
```

- 返回值:

类型：`bool`

- 使用示例:

```python
import time
from pyAgxArm import create_agx_arm_config, AgxArmFactory

cfg = create_agx_arm_config(robot="piper", channel="can0")
robot = AgxArmFactory.create_arm(cfg)
robot.connect()

time.sleep(0.5)
print("arm is_ok =", robot.is_ok())
```

### 获取机械臂数据接收频率 get_fps()

- 功能说明:

获取机械臂数据监控的接收频率（Hz）。该频率是 SDK 对机械臂解析器收到数据的统计值。

- 定义:

```python
get_fps(self) -> float
```

- 返回值:

类型：`float`（单位：Hz）

- 使用示例:

```python
import time
from pyAgxArm import create_agx_arm_config, AgxArmFactory

cfg = create_agx_arm_config(robot="piper", channel="can0")
robot = AgxArmFactory.create_arm(cfg)
robot.connect()

time.sleep(0.5)
print("arm fps =", robot.get_fps(), "Hz")
```

## 机械臂数据读取相关

### 读取机械臂状态 get_arm_status()

- 功能说明:

读取机械臂整体状态反馈（控制模式、运动模式、急停/异常状态、轨迹点编号等）。

- 定义:

```python
get_arm_status(self) -> MessageAbstract[ArmMsgFeedbackStatus] | None
```

- 返回值:

类型：`MessageAbstract[ArmMsgFeedbackStatus] | None`

- 消息字段说明（`arm_status.msg`）:

|字段|类型|说明|
|---|---|---|
|ctrl_mode|int|控制模式（待机/CAN/示教/以太网/WiFi/离线轨迹等）|
|arm_status|int|机械臂状态（正常/急停/奇异/超限/碰撞等）|
|mode_feedback|int|模式反馈（MOVE P/J/L/C/MIT 等）|
|teach_status|int|示教状态（开始记录/结束记录/执行/暂停/继续/终止等）|
|motion_status|int|运动状态：0 已到达；1 未到达|
|trajectory_num|int|轨迹点编号（离线轨迹模式下反馈）|
|err_status|object|错误状态位（关节角度超限/关节通信异常等）|

- 使用示例:

```python
import time
from pyAgxArm import create_agx_arm_config, AgxArmFactory

cfg = create_agx_arm_config(robot="piper", channel="can0")
robot = AgxArmFactory.create_arm(cfg)
robot.connect()

while True:
    arm_status = robot.get_arm_status()
    if arm_status is not None:
        print(arm_status.msg)
        print(arm_status.hz, arm_status.timestamp)
    time.sleep(0.02)
```

### 读取机械臂关节消息 get_joint_states()

- 功能说明:

获取关节角消息

- 定义:

```python
get_joint_states(self) -> MessageAbstract[list[float]] | None
```

- 返回值:

类型：`MessageAbstract[list[float]] | None`

[j1, j2, j3, j4, j5, j6]

`js.msg` 为长度 6 的 `list[float]`，单位：rad，并带有 `hz/timestamp` 元数据。

- 使用示例:

```python
import time
from pyAgxArm import create_agx_arm_config, AgxArmFactory
cfg = create_agx_arm_config(robot="piper", channel="can0")
robot = AgxArmFactory.create_arm(cfg)
robot.connect()
while True:
    js = robot.get_joint_states()
    if js is not None:
        print(js.msg) # list
        print(js.hz, js.timestamp)
    time.sleep(0.005)
```

### 读取机械臂末端位姿 get_ee_pose()

- 功能说明:

获取末端位姿消息

- 定义:

```python
get_ee_pose(self) -> MessageAbstract[list[float]] | None
```

- 返回值:

类型：`MessageAbstract[list[float]] | None`

[x, y, z, rx, ry, rz]

`ee.msg` 为长度 6 的 `list[float]`：`[x, y, z, roll, pitch, yaw]`，xyz 单位 m，姿态单位 rad，并带有 `hz/timestamp` 元数据。

- 使用示例:

```python
import time
from pyAgxArm import create_agx_arm_config, AgxArmFactory
cfg = create_agx_arm_config(robot="piper", channel="can0")
robot = AgxArmFactory.create_arm(cfg)
robot.connect()
while True:
    ee = robot.get_ee_pose()
    if ee is not None:
        print(ee.msg) # list
        print(ee.hz, ee.timestamp)
    time.sleep(0.005)
```

### 读取机械臂电机状态 get_motor_states()

- 功能说明:

读取指定关节的电机高速反馈（位置/速度/电流/扭矩）。

- 定义:

```python
get_motor_states(self, joint_index: Literal[1, 2, 3, 4, 5, 6]) -> MessageAbstract[ArmMsgFeedbackHighSpd] | None
```

- 参数说明:

|名称|类型|说明|
|---|---|---|
|joint_index|int|关节序号，范围：1~6|

- 返回值:

类型：`MessageAbstract[ArmMsgFeedbackHighSpd] | None`

- 消息字段说明（`ms.msg`）:

|字段|类型|说明|
|---|---|---|
|pos|float|电机位置，单位：rad|
|motor_speed|float|电机速度，单位：rad/s|
|current|float|电机电流，单位：A|
|torque|float|电机扭矩，单位：N·m|

- 使用示例:

```python
import time
from pyAgxArm import create_agx_arm_config, AgxArmFactory

cfg = create_agx_arm_config(robot="piper", channel="can0")
robot = AgxArmFactory.create_arm(cfg)
robot.connect()

ms = robot.get_motor_states(1)
if ms is not None:
    print(ms.msg.pos, ms.msg.motor_speed, ms.msg.current, ms.msg.torque)
    print(ms.hz, ms.timestamp)
```

### 读取机械臂关节控制消息 get_joint_ctrl_states()

- 功能说明:

获取机械臂控制帧消息，用于获取主臂给从臂发送的控制帧

- 定义:

```python
get_joint_ctrl_states(self) -> MessageAbstract[list[float]] | None
```

- 返回值:

类型：`MessageAbstract[list[float]] | None`

[j1, j2, j3, j4, j5, j6]

反馈长度为6的float类型列表，单位为弧度。

- 使用示例:

```python
import time
from pyAgxArm import create_agx_arm_config, AgxArmFactory
cfg = create_agx_arm_config(robot="piper", channel="can0")
robot = AgxArmFactory.create_arm(cfg)
robot.connect()
while True:
    jc = robot.get_joint_ctrl_states()
    if jc is not None:
        print(jc.msg) # list
        print(jc.hz, jc.timestamp)
    time.sleep(0.005)
```

### 读取机械臂驱动器状态 get_driver_states()

- 功能说明:

读取指定关节的驱动器低速反馈（电压/温度/母线电流/驱动状态位等）。

- 定义:

```python
get_driver_states(self, joint_index: Literal[1, 2, 3, 4, 5, 6]) -> MessageAbstract[ArmMsgFeedbackLowSpd] | None
```

- 参数说明:

|名称|类型|说明|
|---|---|---|
|joint_index|int|关节序号，范围：1~6|

- 返回值:

类型：`MessageAbstract[ArmMsgFeedbackLowSpd] | None`

- 消息字段说明（`ds.msg`）:

|字段|类型|说明|
|---|---|---|
|vol|float|驱动电压|
|foc_temp|float|驱动温度，单位：°C|
|motor_temp|float|电机温度，单位：°C|
|bus_current|float|母线电流，单位：A|
|foc_status|object|驱动状态位（电压过低/过温/过流/碰撞/失能/堵转等）|

- 使用示例:

```python
import time
from pyAgxArm import create_agx_arm_config, AgxArmFactory

cfg = create_agx_arm_config(robot="piper", channel="can0")
robot = AgxArmFactory.create_arm(cfg)
robot.connect()

ds = robot.get_driver_states(1)
if ds is not None:
    print(ds.msg.vol, ds.msg.foc_temp, ds.msg.motor_temp, ds.msg.bus_current)
    print(ds.msg.foc_status.driver_enable_status)
    print(ds.hz, ds.timestamp)
```

### 读取关节电机使能状态 get_joint_enable_status()

- 功能说明:

获取机械臂关节电机的使能状态

- 定义:

```python
get_joint_enable_status(self, joint_index: Literal[1, 2, 3, 4, 5, 6]) -> bool
```

- 参数说明:

|名称|类型|说明|
|---|---|---|
|joint_index|int|关节序号|

- 返回值:

类型：`bool`（`True` 为使能，`False` 为未使能或当前无反馈）

True为关节电机使能，False为关节电机未使能

- 使用示例:

```python
import time
from pyAgxArm import create_agx_arm_config, AgxArmFactory
cfg = create_agx_arm_config(robot="piper", channel="can0")
robot = AgxArmFactory.create_arm(cfg)
robot.connect()
success = robot.get_joint_enable_status(1)
if success:
    print("关节1电机已使能")
```

### 读取全部关节使能状态 get_joints_enable_status_list()

- 功能说明:

读取全部关节电机的使能状态列表（按关节 1~6 顺序）。

- 定义:

```python
get_joints_enable_status_list(self) -> list[bool]
```

- 返回值:

类型：`list[bool]`

- 使用示例:

```python
from pyAgxArm import create_agx_arm_config, AgxArmFactory

cfg = create_agx_arm_config(robot="piper", channel="can0")
robot = AgxArmFactory.create_arm(cfg)
robot.connect()

print(robot.get_joints_enable_status_list())
```

### 读取固件信息 get_firmware()

- 功能说明:

读取机械臂固件信息（软件版本/硬件版本/生产日期等）。该接口会下发查询帧并等待对应反馈。

- 定义:

```python
get_firmware(self, timeout: float = 1.0, min_interval: float = 1.0) -> dict | None
```

- 参数说明:

|名称|类型|说明|
|---|---|---|
|timeout|float|等待反馈超时时间（秒），默认 1.0；`timeout=0.0` 表示非阻塞|
|min_interval|float|最小请求间隔（秒），默认 1.0|

- 返回值:

类型：`dict | None`

常见字段：

|key|类型|说明|
|---|---|---|
|software_version|str|软件版本（例如 `S-V1.8-2`）|
|hardware_version|str|硬件版本（例如 `H-V1.2-1`）|
|production_date|str|生产日期（例如 `250925`）|
|node_type|str|节点类型|
|node_number|int|节点编号|

- 使用示例:

```python
from pyAgxArm import create_agx_arm_config, AgxArmFactory

cfg = create_agx_arm_config(robot="piper", channel="can0")
robot = AgxArmFactory.create_arm(cfg)
robot.connect()

fw = robot.get_firmware()
if fw is not None:
    print(fw)
```

## 机械臂参数设定相关

### 设定机械臂运行速度 set_speed_percent()

- 功能说明:

该指令用来设定机械臂在位置速度模式(move_j)、末端控制模式(move_p)和直线控制模式(move_l)下的运行速度百分比

- 定义:

```python
set_speed_percent(self, percent: int = 100) -> None
```

- 参数说明:

|名称|类型|说明|
|---|---|---|
|percent|int|设定机械臂运行速度，默认为100,范围[0,100]|

- 使用示例:

```python
import time
from pyAgxArm import create_agx_arm_config, AgxArmFactory
cfg = create_agx_arm_config(robot="piper", channel="can0")
robot = AgxArmFactory.create_arm(cfg)
robot.connect()
# 设定机械臂运行速度为百分之百
robot.set_speed_percent(100)
```

### 设定机械臂安装位置 set_installation_pos()

- 功能说明:

该指令用来设定机械臂安装位置，有水平、朝左和朝右三个方向

- 定义:

```python
set_installation_pos(self, pos: Literal["horizontal", "left", "right"] = "horizontal") -> None
```

- 参数说明:

|名称|类型|说明|
|---|---|---|
|pos|str|`["horizontal", "left", "right"]`|

- 使用示例:

```python
import time
from pyAgxArm import create_agx_arm_config, AgxArmFactory
cfg = create_agx_arm_config(robot="piper", channel="can0")
robot = AgxArmFactory.create_arm(cfg)
robot.connect()
# 设定水平安装
robot.set_installation_pos(robot.INSTALLATION_POS.HORIZONTAL)
```

### 设定运动模式 set_motion_mode()

- 功能说明:

设置运动模式（`move_p/move_j/move_l/move_c/move_mit/move_js`）。该接口会下发模式设置到控制器。

- 定义:

```python
set_motion_mode(self, motion_mode: Literal["p", "j", "l", "c", "mit", "js"] = "p") -> None
```

- 参数说明:

|名称|类型|说明|
|---|---|---|
|motion_mode|str|运动模式：`p/j/l/c/mit/js`（建议使用 `robot.MOTION_MODE.xxx` 常量）|

- 使用示例:

```python
from pyAgxArm import create_agx_arm_config, AgxArmFactory

cfg = create_agx_arm_config(robot="piper", channel="can0")
robot = AgxArmFactory.create_arm(cfg)
robot.connect()

robot.set_motion_mode(robot.MOTION_MODE.J)
```

### 设定机械臂末端负载 set_ee_load()

- 功能说明:

该指令用来设定机械臂末端负载

- 定义:

```python
set_ee_load(self, load: Literal['empty', 'half', 'full'] = 'empty', timeout: float = 1.0) -> bool
```

- 参数说明:

|名称|类型|说明|
|---|---|---|
|load|int|范围为['empty', 'half', 'full']；'empty'为空载，'half'为半载，'full'为满载|
|timeout|float|设定指令发送后，等待反馈的循环时间|

- 返回值:

类型:bool

True为指令应答返回，并不表明设定成功

- 使用示例:

```python
import time
from pyAgxArm import create_agx_arm_config, AgxArmFactory
cfg = create_agx_arm_config(robot="piper", channel="can0")
robot = AgxArmFactory.create_arm(cfg)
robot.connect()
# 设定满载
robot.set_ee_load(robot.EE_LOAD.FULL)
```

### 设定机械臂为主臂 set_master_mode()

- 功能说明:

该指令会将机械臂设置为从臂模式，该模式会令关节驱动切换到mit模式，在该模式下，响应速度相较位置速度控制模式快，并且没有精度补偿

- 定义:

```python
set_master_mode(self) -> None
```

- 使用示例:

```python
import time
from pyAgxArm import create_agx_arm_config, AgxArmFactory
cfg = create_agx_arm_config(robot="piper", channel="can0")
robot = AgxArmFactory.create_arm(cfg)
robot.connect()
robot.set_master_mode()
```

### 设定机械臂为从臂 set_slave_mode()

- 功能说明:

该指令会将机械臂设置为从臂模式，该模式会令关节驱动切换到mit模式，在该模式下，响应速度相较位置速度控制模式快，并且没有精度补偿

- 定义:

```python
set_slave_mode(self) -> None
```

- 使用示例:

```python
import time
from pyAgxArm import create_agx_arm_config, AgxArmFactory
cfg = create_agx_arm_config(robot="piper", channel="can0")
robot = AgxArmFactory.create_arm(cfg)
robot.connect()
robot.set_slave_mode()
```

### 主臂回 Home move_master_to_home()

- 功能说明:

让主臂回到 Home 位姿（主臂相关）。该操作完成后，建议调用 `restore_master_drag_mode()` 恢复主臂“零力拖动”状态。

- 定义:

```python
move_master_to_home(self) -> None
```

- 使用示例:

```python
from pyAgxArm import create_agx_arm_config, AgxArmFactory

cfg = create_agx_arm_config(robot="piper", channel="can0")
robot = AgxArmFactory.create_arm(cfg)
robot.connect()

robot.set_master_mode()
robot.move_master_to_home()
robot.restore_master_drag_mode()
```

### 恢复主臂零力拖动 restore_master_drag_mode()

- 功能说明:

将主臂恢复为“零力拖动”状态（主臂相关），通常用于 `move_master_to_home()` 之后。

- 定义:

```python
restore_master_drag_mode(self) -> None
```

## 机械臂控制相关

### 使能机械臂 enable()

- 功能说明:

该指令会将机械臂使能上电

- 定义:

```python
enable(self, joint_index: Literal[1, 2, 3, 4, 5, 6, 7, 255] = 255) -> bool
```

- 参数说明:

|名称|类型|说明|
|---|---|---|
|joint_index|int|数值为1～7时可以单独使能选中的关节，若为0xFF则为使能全部电机|

- 返回值:

类型:bool

使能成功状态，True为使能成功

- 使用示例:

```python
import time
from pyAgxArm import create_agx_arm_config, AgxArmFactory
cfg = create_agx_arm_config(robot="piper", channel="can0")
robot = AgxArmFactory.create_arm(cfg)
robot.connect()
# 使能全部
while not robot.enable():
    time.sleep(0.01)
```

### 失能机械臂 disable()

- 功能说明:

该指令会将机械臂失电，如果执行指令时机械臂关节为抬起状态，会立刻掉下，需确保机械臂安全再使用

- 定义:

```python
disable(self, joint_index: Literal[1, 2, 3, 4, 5, 6, 7, 255] = 255) -> bool
```

- 参数说明:

|名称|类型|说明|
|---|---|---|
|joint_index|int|数值为1～7时可以单独使能选中的关节，若为0xFF则为失能全部电机|

- 返回值:

类型:bool

失能成功状态，True为失能成功

- 使用示例:

```python
import time
from pyAgxArm import create_agx_arm_config, AgxArmFactory
cfg = create_agx_arm_config(robot="piper", channel="can0")
robot = AgxArmFactory.create_arm(cfg)
robot.connect()
# 失能全部
while not robot.disable():
    time.sleep(0.01)
```

### 重置机械臂 reset()

- 功能说明:

该指令会将机械臂模式重置并令机械臂立刻失电，如果执行指令时机械臂关节为抬起状态，会立刻掉下，需确保机械臂安全再使用

- 定义:

```python
reset(self) -> None
```

- 使用示例:

```python
import time
from pyAgxArm import create_agx_arm_config, AgxArmFactory
cfg = create_agx_arm_config(robot="piper", channel="can0")
robot = AgxArmFactory.create_arm(cfg)
robot.connect()
robot.reset()
```

### 电子急停机械臂 electronic_emergency_stop()

- 功能说明:

该指令会将机械臂设置为急停，如果执行指令时机械臂关节为抬起状态，机械臂会缓慢以一个恒定阻尼落下

- 定义:

```python
electronic_emergency_stop(self) -> None
```

- 使用示例:

```python
import time
from pyAgxArm import create_agx_arm_config, AgxArmFactory
cfg = create_agx_arm_config(robot="piper", channel="can0")
robot = AgxArmFactory.create_arm(cfg)
robot.connect()
robot.electronic_emergency_stop()
```

### 关节运动(位置速度控制模式) move_j()

- 功能说明:

该指令会将机械臂设置为关节位置速度控制模式

- 定义:

```python
move_j(self, joints: list[float]) -> None
```

- 参数说明:

|名称|类型|说明|
|---|---|---|
|joints|list[float]|各关节目标角度数组，单位：rad，数值精度：1.74532925199e-5|

- 使用示例:

```python
import time
from pyAgxArm import create_agx_arm_config, AgxArmFactory
cfg = create_agx_arm_config(robot="piper", channel="can0")
robot = AgxArmFactory.create_arm(cfg)
robot.connect()
while not robot.enable():
    time.sleep(0.01)
robot.set_speed_percent(100)
robot.move_j([0, 0.4, -0.4, 0, -0.4, 0])
while robot.get_arm_status().msg.motion_status != 0:
    time.sleep(0.1)
print("已到达目标位置")
```

注意:

如果连续该指令会覆盖上一次的目标值

### 关节运动(从臂控制模式) move_js()

- 功能说明:

该指令会将机械臂设置为从臂模式，该模式会令关节驱动切换到mit模式，在该模式下，响应速度相较位置速度控制模式快

- 定义:

```python
move_js(self, joints: list[float]) -> None
```

- 参数说明:

|名称|类型|说明|
|---|---|---|
|joints|list[float]|各关节目标角度数组，单位：弧度，数值精度：1.74532925199e-5|

- 使用示例:

```python
import time
from pyAgxArm import create_agx_arm_config, AgxArmFactory
cfg = create_agx_arm_config(robot="piper", channel="can0")
robot = AgxArmFactory.create_arm(cfg)
robot.connect()
while not robot.enable():
    time.sleep(0.01)
# robot.set_speed_percent(100) # 该模式下设定的速度失效
robot.move_js([0, 0.4, -0.4, 0, -0.4, 0])
```

注意:

1. 如果连续该指令会覆盖上一次的目标值

2. 由于响应变快，关节的控制力度相较于位置速度模式小，刚度也会变小

3. 在旧版本机械臂固件下，如果机械臂当前模式为从臂模式，如果想要切换到位置速度控制模式，需要先执行`robot.reset()`，机械臂此时会重置掉电，然后再执行move_j才能够正常控制

### 末端控制 move_p()

- 功能说明:

该指令为发送一个末端点位，机械臂会根据当前点位和目标点位进行关节角度解算

- 定义:

```python
move_p(self, pose: list[float]) -> None
```

- 参数说明:

|名称|类型|说明|
|---|---|---|
|pose|list[float]|目标位姿,位置单位：米，数值精度：1e-6；姿态单位：弧度，数值精度：1.74532925199e-5|

- 使用示例:

```python
import time
from pyAgxArm import create_agx_arm_config, AgxArmFactory
cfg = create_agx_arm_config(robot="piper", channel="can0")
robot = AgxArmFactory.create_arm(cfg)
robot.connect()
while not robot.enable():
    time.sleep(0.01)
robot.set_speed_percent(100)
robot.move_p([0.1, 0.0, 0.3, 0.0, 1.570796326794896619, 0.0])
while robot.get_arm_status().msg.motion_status != 0:
    time.sleep(0.1)
print("已到达目标位置")
```

注意:

如果连续执行该指令会覆盖上一次的目标值

## 高级参数读取/配置相关

### 读取关节角度/速度限制 get_joint_angle_vel_limits()

- 功能说明:

查询指定关节的角度限制与速度限制（由控制器反馈）。

- 定义:

```python
get_joint_angle_vel_limits(
    self,
    joint_index: Literal[1, 2, 3, 4, 5, 6],
    timeout: float = 1.0,
    min_interval: float = 1.0,
) -> MessageAbstract[ArmMsgFeedbackCurrentMotorAngleLimitMaxSpd] | None
```

- 参数说明:

|名称|类型|说明|
|---|---|---|
|joint_index|int|关节序号，范围：1~6|
|timeout|float|等待反馈超时时间（秒），默认 1.0；`timeout=0.0` 表示非阻塞|
|min_interval|float|最小请求间隔（秒），默认 1.0|

- 返回值:

类型：`MessageAbstract[ArmMsgFeedbackCurrentMotorAngleLimitMaxSpd] | None`

- 使用示例:

```python
from pyAgxArm import create_agx_arm_config, AgxArmFactory

cfg = create_agx_arm_config(robot="piper", channel="can0")
robot = AgxArmFactory.create_arm(cfg)
robot.connect()

limit = robot.get_joint_angle_vel_limits(1)
if limit is not None:
    print(limit.msg.min_angle_limit, limit.msg.max_angle_limit)
    print(limit.msg.min_joint_spd, limit.msg.max_joint_spd)
```

### 读取关节加速度限制 get_joint_acc_limits()

- 功能说明:

查询指定关节的最大加速度限制。

- 定义:

```python
get_joint_acc_limits(
    self,
    joint_index: Literal[1, 2, 3, 4, 5, 6],
    timeout: float = 1.0,
    min_interval: float = 1.0,
) -> MessageAbstract[ArmMsgFeedbackCurrentMotorMaxAccLimit] | None
```

- 参数说明:

|名称|类型|说明|
|---|---|---|
|joint_index|int|关节序号，范围：1~6|
|timeout|float|等待反馈超时时间（秒），默认 1.0；`timeout=0.0` 表示非阻塞|
|min_interval|float|最小请求间隔（秒），默认 1.0|

- 返回值:

类型：`MessageAbstract[ArmMsgFeedbackCurrentMotorMaxAccLimit] | None`

### 读取末端速度/加速度限制 get_ee_vel_acc_limits()

- 功能说明:

查询末端最大线速度/角速度与线加速度/角加速度限制。

- 定义:

```python
get_ee_vel_acc_limits(self, timeout: float = 1.0, min_interval: float = 1.0) -> MessageAbstract[ArmMsgFeedbackCurrentEndVelAccParam] | None
```

- 参数说明:

|名称|类型|说明|
|---|---|---|
|timeout|float|等待反馈超时时间（秒），默认 1.0；`timeout=0.0` 表示非阻塞|
|min_interval|float|最小请求间隔（秒），默认 1.0|

- 返回值:

类型：`MessageAbstract[ArmMsgFeedbackCurrentEndVelAccParam] | None`

### 读取碰撞防护等级 get_crash_protection_rating()

- 功能说明:

查询各关节碰撞防护等级（控制器返回列表）。

- 定义:

```python
get_crash_protection_rating(
    self,
    joint_index: Literal[1, 2, 3, 4, 5, 6, 255] = 255,
    timeout: float = 1.0,
    min_interval: float = 1.0,
) -> MessageAbstract[list[int]] | None
```

- 参数说明:

|名称|类型|说明|
|---|---|---|
|joint_index|int|1~6 查询单关节；255 查询全部|
|timeout|float|等待反馈超时时间（秒），默认 1.0；`timeout=0.0` 表示非阻塞|
|min_interval|float|最小请求间隔（秒），默认 1.0|

- 返回值:

类型：`MessageAbstract[list[int]] | None`

### 关节置零/标定 calibrate_joint()

- 功能说明:

对指定关节执行置零/标定流程（等待控制器 ACK/响应并返回结果）。

- 定义:

```python
calibrate_joint(
    self,
    joint_index: Literal[1, 2, 3, 4, 5, 6, 255] = 255,
    timeout: float = 1.0,
) -> bool
```

- 参数说明:

|名称|类型|说明|
|---|---|---|
|joint_index|int|1~6 标定单关节；255 标定全部|
|timeout|float|等待响应超时时间（秒），默认 1.0|

- 返回值:

类型：`bool`（`True` 表示收到成功响应；`False` 表示超时或失败）

### 配置关节角度/速度限制 set_joint_angle_vel_limits()

- 功能说明:

设置指定关节的角度/速度限制，并可通过读回校验是否生效（具体以固件/协议为准）。

- 定义:

```python
set_joint_angle_vel_limits(
    self,
    joint_index: Literal[1, 2, 3, 4, 5, 6],
    min_angle_limit: float,
    max_angle_limit: float,
    min_joint_spd: float,
    max_joint_spd: float,
    timeout: float = 1.0,
) -> bool
```

- 参数说明:

|名称|类型|说明|
|---|---|---|
|joint_index|int|关节序号，范围：1~6|
|min_angle_limit|float|最小角度限制（rad）|
|max_angle_limit|float|最大角度限制（rad）|
|min_joint_spd|float|最小速度限制（rad/s）|
|max_joint_spd|float|最大速度限制（rad/s）|
|timeout|float|等待 ACK/校验超时时间（秒），默认 1.0|

### 配置关节加速度限制 set_joint_acc_limits()

- 功能说明:

设置指定关节的最大加速度限制。

- 定义:

```python
set_joint_acc_limits(
    self,
    joint_index: Literal[1, 2, 3, 4, 5, 6],
    max_joint_acc: float,
    timeout: float = 1.0,
) -> bool
```

- 参数说明:

|名称|类型|说明|
|---|---|---|
|joint_index|int|关节序号，范围：1~6|
|max_joint_acc|float|最大加速度（rad/s^2）|
|timeout|float|等待 ACK/校验超时时间（秒），默认 1.0|

### 配置末端速度/加速度限制 set_ee_vel_acc_limits()

- 功能说明:

设置末端速度/加速度限制。

- 定义:

```python
set_ee_vel_acc_limits(
    self,
    end_max_linear_vel: float,
    end_max_angular_vel: float,
    end_max_linear_acc: float,
    end_max_angular_acc: float,
    timeout: float = 1.0,
) -> bool
```

### 配置碰撞防护等级 set_crash_protection_rating()

- 功能说明:

设置碰撞防护等级（可指定单关节或全部关节）。

- 定义:

```python
set_crash_protection_rating(
    self,
    joint_index: Literal[1, 2, 3, 4, 5, 6, 255] = 255,
    rating: int = 0,
    timeout: float = 1.0,
) -> bool
```

### 恢复末端速度/加速度默认值 set_ee_vel_acc_limits_to_default()

- 功能说明:

将末端速度/加速度限制恢复为默认值。

- 定义:

```python
set_ee_vel_acc_limits_to_default(self, timeout: float = 1.0) -> bool
```

### 恢复关节角度/速度/加速度默认值 set_joint_angle_vel_acc_limits_to_default()

- 功能说明:

将关节角度/速度/加速度限制恢复为默认值。

- 定义:

```python
set_joint_angle_vel_acc_limits_to_default(self, timeout: float = 1.0) -> bool
```

### 设置关节/末端速度加速度周期反馈 set_joint_ee_vel_acc_period_feedback()

- 功能说明:

设置关节/末端速度加速度周期反馈开关或周期参数（用于周期性反馈控制参数）。

- 定义:

```python
set_joint_ee_vel_acc_period_feedback(
    self,
    joint_vel_acc: bool = True,
    ee_vel_acc: bool = True,
    period_ms: int = 10,
    timeout: float = 1.0,
) -> bool
```

### 末端直线运动 move_l()

- 功能说明:

该指令为发送一个末端点位，机械臂会根据当前点位和目标点位进行直线规划

- 定义:

```python
move_l(self, pose: list[float]) -> None
```

- 参数说明:

|名称|类型|说明|
|---|---|---|
|pose|list[float]|目标位姿,位置单位：米，数值精度：1e-6；姿态单位：弧度，数值精度：1.74532925199e-5|

- 使用示例:

```python
import time
from pyAgxArm import create_agx_arm_config, AgxArmFactory
cfg = create_agx_arm_config(robot="piper", channel="can0")
robot = AgxArmFactory.create_arm(cfg)
robot.connect()
while not robot.enable():
    time.sleep(0.01)
robot.set_speed_percent(100)
robot.move_l([0.1, 0.0, 0.3, 0.0, 1.570796326794896619, 0.0])
while robot.get_arm_status().msg.motion_status != 0:
    time.sleep(0.1)
print("已到达目标位置")
```

注意:

连续执行该指令虽然可以覆盖上一次的目标，但是由于底层每接收到新的点位，都需要重新进行直线规划，因此不能够使用该指令连续发目标点

### 末端圆弧运动 move_c()

- 功能说明:

末端圆弧运动控制：通过“起点/中间点/终点”三个末端位姿进行圆弧轨迹规划并执行。

- 定义:

```python
move_c(self, start_pose: list[float], mid_pose: list[float], end_pose: list[float]) -> None
```

- 参数说明:

|名称|类型|说明|
|---|---|---|
|start_pose|list[float]|起点位姿 `[x, y, z, roll, pitch, yaw]`（m / rad）|
|mid_pose|list[float]|中间点位姿 `[x, y, z, roll, pitch, yaw]`（m / rad）|
|end_pose|list[float]|终点位姿 `[x, y, z, roll, pitch, yaw]`（m / rad）|

- 使用示例:

```python
from pyAgxArm import create_agx_arm_config, AgxArmFactory

cfg = create_agx_arm_config(robot="piper", channel="can0")
robot = AgxArmFactory.create_arm(cfg)
robot.connect()

sp = [0.2, 0.0, 0.3, 0.0, 1.5708, 0.0]
mp = [0.2, 0.05, 0.35, 0.0, 1.5708, 0.0]
ep = [0.2, 0.0, 0.4, 0.0, 1.5708, 0.0]
robot.move_c(sp, mp, ep)
```

### 单关节mit控制 move_mit()

- 功能说明:

该指令为使用关节驱动底层的mit控制接口，控制单个关节电机，可以实现电流模拟的力矩控制

- 定义:

```python
move_mit(
    self,
    joint_index: Literal[1, 2, 3, 4, 5, 6],
    p_des: float = 0.0,
    v_des: float = 0.0,
    kp: float = 10.0,
    kd: float = 0.8,
    t_ff: float = 0.0,
    ) -> None
```

- 参数说明:

|名称|类型|说明|
|---|---|---|
|joint_index|int|目标关节，有效值范围[1, 2, 3, 4, 5, 6]|
|p_des|float|目标位置，数值范围[-12.5, 12.5]，单位：弧度，默认值0.0，数值精度：3.8147554741741054e-4|
|v_des|float|目标速度，数值范围[-45.0, 45.0]，单位：弧度/秒，默认值0.0，数值精度：2.197802197802198e-2|
|kp|float|位置增益，数值范围[0.0, 500.0]，默认值10.0，数值精度：1.221001221001221e-1|
|kd|float|速度增益，数值范围[-5.0, 5.0]，默认值0.8。数值精度：2.442002442002442e-3|
|t_ff|float|前馈扭矩，数值范围[-18.0, 18.0]，单位N·m，默认值0.0，数值精度：6.274509803921569e-2|

- 使用示例:

```python
import time
from pyAgxArm import create_agx_arm_config, AgxArmFactory
cfg = create_agx_arm_config(robot="piper", channel="can0")
robot = AgxArmFactory.create_arm(cfg)
robot.connect()
while not robot.enable():
    time.sleep(0.01)
# robot.set_speed_percent(100) # 该模式下速度设置无效
robot.move_mit(1, 0.0)
robot.move_mit(2, 0.4)
robot.move_mit(3, -0.4)
robot.move_mit(4, 0.0)
robot.move_mit(5, -0.4)
robot.move_mit(6, 0.4)
```

注意:

如果连续执行该指令会覆盖上一次的目标值
