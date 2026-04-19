# YOLO 本地部署说明

本说明只覆盖“本机实时检测”场景，不涉及云端调度或机械臂 TCP 联动。

## 当前目录的实际组成

- `ultralytics/`：Ultralytics 源码快照
- `yolo11n.pt`：仓库自带的最小可运行权重
- `realtime_detect_local.py`：本地实时检测入口
- `detect_for_program.py`：原始联动脚本，包含 cloud / arm 通信逻辑
- `cloud_sender.py` / `cloud_recevier.py` / `arm_receiver.py`：联动测试脚本

## 推荐环境

建议直接使用仓库主流程已经在用的 `eih-ur5`：

```bash
conda activate eih-ur5
```

安装 YOLO 运行依赖：

```bash
cd third_party/yolo/新松-检测
python -m pip install -e .
```

如果后续需要补额外依赖，可优先观察报错后按需安装。

## 最小运行

### 1. 使用 RealSense D435

```bash
conda activate eih-ur5
python third_party/yolo/新松-检测/realtime_detect_local.py --source realsense
```

### 2. 使用普通 USB 摄像头

```bash
conda activate eih-ur5
python third_party/yolo/新松-检测/realtime_detect_local.py --source 0
```

### 3. 无界面 smoke test

```bash
conda activate eih-ur5
python third_party/yolo/新松-检测/realtime_detect_local.py \
  --source realsense \
  --headless \
  --max-frames 10 \
  --save-dir third_party/yolo/新松-检测/runs/local_smoke
```

## 常用参数

- `--weights <path>`：指定模型权重
- `--device cpu`：CPU 推理
- `--device 0`：若 CUDA 正常，可切到第一张 GPU
- `--imgsz 640`：推理尺寸
- `--conf 0.25`：置信度阈值
- `--classes 0 2 5`：仅保留指定类别

## 重要说明

当前仓库里可直接发现的权重只有 `yolo11n.pt`，这是通用预训练模型。

这意味着：

1. 现在可以先验证“实时检测链路能跑通”。
2. 如果你要识别你们自己的工业零件类别，还需要你自己的训练后权重文件。
