# 新设备复现检查清单

这份清单适用于下面这种情况：

- 一台新电脑
- 一台新的 Piper 机械臂
- 一台 D405 相机

目标是让别人按照仓库文档，把当前这套流程复现出来。

## 新硬件上必须重做的部分

下面这些步骤和具体硬件安装强相关，到了新设备上应默认重新做：

- 相机内参标定
- 手眼标定
- 手眼验证
- TCP offset 估计
  - 除非你的夹爪安装方式完全一致，而且已经被验证过
- 本地关键位采集
  - 除非你只是想先从仓库模板起步
- 点击抓取补偿微调
  - 只要观察位或相机视角变了，这一步通常都要重新调

## 可以直接复用的部分

这些是仓库 clone 下来后就应该能直接使用的：

- 环境脚本：`./scripts/setup_env.sh`
- 自检脚本：`./scripts/run_doctor.sh`
- CAN bringup 脚本：`sudo ./scripts/bringup_can.sh`
- 可打印 ChArUco 标定板：`assets/calibration/charuco_default/`
- 受版本管理的关键位模板：`configs/task/pick_demo_template.yaml`
- 默认 YOLO11 权重路径：`third_party/yolo/新松-检测/yolo11m.pt`

## 第一次 bring-up 检查清单

1. clone 仓库并进入目录。
2. 按 [installation.md](installation.md) 安装系统依赖。
3. 运行 `./scripts/setup_env.sh`。
4. 运行 `./scripts/run_doctor.sh`。
5. 如果 CAN 接口存在但没拉起，运行 `sudo ./scripts/bringup_can.sh can0 1000000`。
6. 用 `rs-enumerate-devices` 确认 D405 可见。
7. 以 100% 比例打印 ChArUco 标定板。
8. 做内参标定。
9. 做手眼标定。
10. 做手眼验证。
11. 如果夹爪抓取中心还没验证过，就估计 TCP offset。
12. 二选一：
   - 先直接使用仓库自带的 `configs/task/pick_demo_template.yaml`
   - 或者采集你自己的 `configs/task/pick_demo_points.yaml`
13. 跑监控界面。
14. 先用 `--dry-run` 跑点击抓取。
15. 只有 dry-run 计划看起来合理后，才做真机抓取。

## 最容易出问题的地方

- `pyrealsense2` 导入失败：
  - 用 `./scripts/setup_env.sh --recreate` 重建 `.venv`
- D405 检测不到：
  - 检查数据线、USB 3 口和 `librealsense2` 安装
- `can0` 不存在或没拉起：
  - 检查 USB-CAN 适配器，并运行 `sudo ./scripts/bringup_can.sh`
- 机械臂到达姿态很奇怪：
  - 重新采 `observe`、`staging`、`drop_staging`、`drop_pose`
- 抓取点总有系统性偏差：
  - 重新检查 TCP offset、手眼结果和 `pick_point_offset_m`

## 推荐的验收标准

对于一套新硬件，我建议至少满足下面这些，才算“复现成功”：

- `./scripts/run_doctor.sh`
- `./scripts/run_monitor.sh --yolo`
- `./scripts/run_calibrate_intrinsics.sh`
- `./scripts/run_calibrate_handeye.sh`
- `./scripts/run_validate_handeye.sh`
- `./scripts/run_click_pick_demo.sh --yolo --dry-run`
- 至少完成一次真实抓取
