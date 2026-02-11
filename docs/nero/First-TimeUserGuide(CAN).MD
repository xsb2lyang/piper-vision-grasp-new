# First-Time User Guide(CAN)

有关首次使用nero配合`pyAgxArm`实现数据读取和控制

## 一 环境要求

- Ubuntu 20.04 / 22.04（推荐）/ 24.04
- Python ≥ 3.8
- pip安装 pyAgxArm
- ubuntu安装 can-utils

## 二 硬件连接以及软件执行流程

准备：nero机械臂、nero机械臂适配器、can转usb模块(带type-c转usb-A线材)、ubuntu系统PC一台(需要有usb-A接口)

### 方法一

1. 将usb转can模块连接nero机械臂的can线(在航插线上，注意要剥开线皮露出铜线)，黄色出线对应模块的H，蓝色出线对应模块的L，使用一字螺丝刀拧紧接线端子；
2. 将can转usb模块连接PC，在PC上激活can模块(详见：[can_user](../can_user.MD))，这里假设激活的can名称为`can0`；
3. 使用nero机械臂适配器，一端连接交流电（100-240v~50/60Hz），另一端对插适配器与航插线的xt30接口，然后将航插插入机械臂，将nero机械臂上电；
4. 观察机械臂指示灯，待机械臂指示灯绿色后，连接nero网页上位机，在上位机端打开can推送；
5. 在PC上执行`candump can0`，看是否有数据，有的话`pyAgxArm`即可正常读取数据

### 方法二

1. 将usb转can模块连接nero机械臂的can线(在航插线上，注意要剥开线皮露出铜线)，黄色出线对应模块的H，蓝色出线对应模块的L，使用一字螺丝刀拧紧接线端子；
2. 将can转usb模块连接PC，在PC上激活can模块(详见：[can_user](../can_user.MD))，这里假设激活的can名称为`can0`；
3. 使用nero机械臂适配器，一端连接交流电（100-240v~50/60Hz），另一端对插适配器与航插线的xt30接口，然后将航插插入机械臂，将nero机械臂上电；
4. 观察机械臂指示灯，待机械臂指示灯绿色后，在PC上编写代码，调用`pyAgxArm`的`set_normal_mode()`函数

    ```python
    from pyAgxArm import create_agx_arm_config, AgxArmFactory
    robot_cfg = create_agx_arm_config(robot="nero", comm="can", channel="can0", interface="socketcan")
    robot = AgxArmFactory.create_arm(robot_cfg)
    robot.connect()
    robot.set_normal_mode()
    ```

    该函数作用是将机械臂切换到普通模式并开启can推送，执行该指令后，机械臂会自动使能

5. 在PC上开启终端执行`candump can0`，看是否有数据，有的话`pyAgxArm`即可正常读取数据

### 总结

- 两种方法区别：
  - 方法一：通过网页上位机开启CAN推送
  - 方法二：通过pyAgxArm进入机械臂的normal mode，并开启can主动上报

- 执行`candump can0`，正常的数据流如下

    ![alt text](../../asserts/pictures/candump_can0.png)

- 附上一段开启can模式后，读取关节数据的代码，注意这里将`robot.set_normal_mode()`注释掉了，可以按需开启

    ```python
    from pyAgxArm import create_agx_arm_config, AgxArmFactory
    import time
    robot_cfg = create_agx_arm_config(robot="nero", comm="can", channel="can0", interface="socketcan")
    robot = AgxArmFactory.create_arm(robot_cfg)
    robot.connect()
    #robot.set_normal_mode()
    time.sleep(1)
    while True:
        print(robot.get_joint_angles())
        time.sleep(0.01)
    ```

## 三 常见错误排查

1. candump没有数据

    - 未开启网页can推送
    - 未开启normal mode
    - 激活can模块时bitrate错误
    - H/L接反
    - can线连接时线头没有露出铜线就连接了can模块

2. connect失败

    - can0不存在

3. 机械臂灯非绿色

    - 机械臂未初始化完成

    - 检查电源是否正常，适配器12v输出是否有电压

## ⚠️ 安全提示

- 首次上电请确保机械臂周围无障碍物

- 不要在未知状态下发送运动指令
