# piper-vision-grasp-new

[English](README.md)

这是一个面向 **Piper 眼在手上视觉抓取** 的应用层工作区，基于以下三部分构建：

- `third_party/pyAgxArm` 中 vendored 的 `pyAgxArm` SDK
- `third_party/yolo/新松-检测` 中 vendored 的 YOLO 代码
- `src/piper_app` 中我们自己的标定、监控、遥操作和点击抓取工具

## 项目亮点

- 基于 `pyrealsense2` 的 D405 / D435 风格 RealSense 相机支持
- 基于 ChArUco 的内参标定与 eye-in-hand 手眼标定
- 机械臂 + 相机只读监控界面，支持 YOLO11 检测框叠加
- 面向夹爪抓取中心的 TCP offset 估计流程
- `home / observe / drop_pose` 关键位采集工具
- 集成深度、手眼和夹爪控制的点击抓取 demo

## 目录结构

```text
.
├── apps/                  # 本地薄启动脚本
├── assets/                # 标定板和静态资源
├── configs/               # 机器人、相机、标定、任务配置
├── docs/                  # 使用文档
├── scripts/               # 推荐入口脚本
├── src/piper_app/         # 应用层 Python 包
├── tests/                 # 轻量导入与配置检查
└── third_party/           # vendored 上游依赖
```

## 快速开始

推荐环境：

- Ubuntu
- `uv`
- Python `3.10`
- 仓库本地 `.venv`

初始化或重建环境：

```bash
./scripts/setup_env.sh
./scripts/setup_env.sh --recreate
```

启动监控界面：

```bash
./scripts/run_monitor.sh
./scripts/run_monitor.sh --yolo
```

启动点击抓取 demo：

```bash
./scripts/run_click_pick_demo.sh --yolo --dry-run
./scripts/run_click_pick_demo.sh --yolo --no-dry-run
```

## 核心工作流

### 1. 标定

```bash
./scripts/run_calibrate_intrinsics.sh
./scripts/run_calibrate_handeye.sh
./scripts/run_validate_handeye.sh
./scripts/run_estimate_tcp_offset.sh
```

### 2. 关键位采集

```bash
./scripts/run_capture_keypoints.sh
```

建议至少采集并保存：

- `home`
- `observe`
- `drop_pose`

### 3. 遥操作

```bash
./scripts/run_gui.sh
./scripts/run_keyboard.sh
```

### 4. 监控与感知

```bash
./scripts/run_monitor.sh
./scripts/run_monitor.sh --yolo
```

### 5. 视觉抓取 Demo

```bash
./scripts/run_click_pick_demo.sh --yolo --dry-run
./scripts/run_click_pick_demo.sh --yolo --no-dry-run
```

## 文档

- [第一次上手指南](docs/onboarding.zh-CN.md)
- [First-Time Onboarding](docs/onboarding.md)
- [快速上手流程](docs/quickstart.zh-CN.md)
- [Quick Start Workflow](docs/quickstart.md)
- [安装说明](docs/installation.md)
- [遥操作](docs/teleop.md)
- [手眼标定](docs/handeye.md)
- [关键位采集](docs/keypoints.md)
- [TCP Offset 估计](docs/tcp_offset.md)
- [点击抓取 Demo](docs/pick_demo.md)

## 可直接打印复用的标定板

仓库里已经直接包含默认 ChArUco 标定板资产，别人 clone 后可以直接打印：

- [assets/calibration/charuco_default/charuco_board.pdf](assets/calibration/charuco_default/charuco_board.pdf)
- [assets/calibration/charuco_default/charuco_board.png](assets/calibration/charuco_default/charuco_board.png)
- [assets/calibration/charuco_default/charuco_board.yaml](assets/calibration/charuco_default/charuco_board.yaml)
- [assets/calibration/charuco_default/README.md](assets/calibration/charuco_default/README.md)

## 项目说明

- 当前顶层项目名已经统一为 **`piper-vision-grasp-new`**
- `pyAgxArm` 仍然作为上游 SDK 保留在 `third_party/pyAgxArm`
- 内部 Python 包名暂时仍然是 `piper_app`，但仓库名和分发元数据已经切到新的项目名

## 致谢

- AgileX Robotics 的 `pyAgxArm`
- `Ultralytics YOLO11`
- `third_party/yolo/新松-检测` 中 vendored 的本地 YOLO 工作区
