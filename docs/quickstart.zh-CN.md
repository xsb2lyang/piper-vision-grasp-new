# 快速上手流程

这份文档给出一条从全新 clone 到跑通当前抓取 demo 的最短路径。

如果你是第一次接触这个仓库，建议先读：

- [onboarding.zh-CN.md](onboarding.zh-CN.md)

## 目标

按本文档操作后，你应该可以完成：

1. 克隆仓库
2. 初始化 Python 环境
3. 检查 D405 和 CAN
4. 打印 ChArUco 标定板
5. 完成相机内参标定
6. 完成手眼标定
7. 验证手眼结果
8. 估计夹爪抓取中心 TCP offset
9. 采集 `home / observe / drop_pose`
10. 运行监控和点击抓取 demo

## 1. 克隆仓库

```bash
git clone https://github.com/xsb2lyang/piper-vision-grasp-new.git
cd piper-vision-grasp-new
```

## 2. 安装系统依赖

完整说明见 [installation.md](installation.md)，最小步骤如下：

```bash
sudo apt update
sudo apt install -y v4l-utils
sudo apt install -y librealsense2 librealsense2-dev librealsense2-utils librealsense2-udev-rules
curl -LsSf https://astral.sh/uv/install.sh | sh
```

## 3. 创建 Python 环境

```bash
./scripts/setup_env.sh
```

如果需要重建：

```bash
./scripts/setup_env.sh --recreate
```

## 4. 检查硬件

### D405

```bash
rs-enumerate-devices
```

### 机械臂 CAN

确保机械臂上电，并且默认 CAN 通道 `can0` 已正常拉起。

## 5. 打印标定板

仓库里已经直接带了可打印的默认标定板：

- [assets/calibration/charuco_default/charuco_board.pdf](../assets/calibration/charuco_default/charuco_board.pdf)
- [assets/calibration/charuco_default/charuco_board.yaml](../assets/calibration/charuco_default/charuco_board.yaml)

打印时务必：

- 使用 **100% 原始比例**
- 禁用打印机的缩放、适配纸张、自动收缩
- 打印后量一下一个方格，确认边长是 `30 mm`

更多说明见：

- [assets/calibration/charuco_default/README.md](../assets/calibration/charuco_default/README.md)

## 6. 做相机内参标定

```bash
./scripts/run_calibrate_intrinsics.sh
```

输出文件：

```text
configs/calibration/camera_intrinsics.yaml
```

## 7. 做手眼标定

```bash
./scripts/run_calibrate_handeye.sh
```

输出文件：

```text
configs/calibration/handeye_active.yaml
```

## 8. 验证手眼结果

```bash
./scripts/run_validate_handeye.sh
```

目标是：

- 切换多个不同视角
- 检查固定标定板在 base 坐标系下的位置是否稳定

## 9. 估计 TCP Offset

如果默认 TCP 不是夹爪真实抓取中心，可以先估计一版更合理的 TCP：

```bash
./scripts/run_estimate_tcp_offset.sh
```

会生成：

```text
configs/calibration/tcp_offset_estimate.yaml
```

如果你认可这版结果，就把它写回：

```text
configs/robot/piper_default.yaml
```

一旦改了 TCP offset，后面这几步都要重做：

- 手眼标定
- 手眼验证
- 关键位采集

## 10. 采集关键位

```bash
./scripts/run_capture_keypoints.sh
```

至少保存：

- `home`
- `observe`
- `drop_pose`

输出文件：

```text
configs/task/pick_demo_points.yaml
```

## 11. 运行监控界面

基础监控：

```bash
./scripts/run_monitor.sh
```

带 YOLO11 检测框：

```bash
./scripts/run_monitor.sh --yolo
```

## 12. 运行点击抓取 Demo

先只做预览：

```bash
./scripts/run_click_pick_demo.sh --yolo --dry-run
```

确认没问题后再真机执行：

```bash
./scripts/run_click_pick_demo.sh --yolo --no-dry-run
```

## 推荐阅读顺序

1. [installation.md](installation.md)
2. [handeye.md](handeye.md)
3. [tcp_offset.md](tcp_offset.md)
4. [keypoints.md](keypoints.md)
5. [pick_demo.md](pick_demo.md)

## 预期会产出的关键文件

完成完整流程后，至少应有：

- `configs/calibration/camera_intrinsics.yaml`
- `configs/calibration/handeye_active.yaml`
- `configs/task/pick_demo_points.yaml`

可选生成物：

- `configs/calibration/handeye_tsai.yaml`
- `configs/calibration/handeye_park.yaml`
- `configs/calibration/tcp_offset_estimate.yaml`

## 额外提醒

- 如果你修改了 TCP offset，就必须重做手眼和关键位
- 如果你修改了 observe 位姿，就很可能需要重新微调点击抓取补偿参数
