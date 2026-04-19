# 第一次上手指南

这份文档是给第一次打开这个仓库的人准备的，目标是让别人可以按正确顺序阅读文档，并一步一步复现我们现在已经实现的流程。

## 适合谁看

如果你希望：

- 第一次 clone 就知道从哪里开始
- 知道文档应该按什么顺序看
- 复现当前这套 Piper + D405 + 手眼标定 + 点击抓取流程

就先看这份文档。

## 推荐阅读顺序

第一次上手建议按这个顺序看：

1. [../README.zh-CN.md](../README.zh-CN.md)
2. [installation.md](installation.md)
3. [quickstart.zh-CN.md](quickstart.zh-CN.md)
4. [handeye.md](handeye.md)
5. [tcp_offset.md](tcp_offset.md)
6. [keypoints.md](keypoints.md)
7. [pick_demo.md](pick_demo.md)

## 第一次上手每一步怎么做

### 第 1 步：克隆仓库

```bash
git clone https://github.com/xsb2lyang/piper-vision-grasp-new.git
cd piper-vision-grasp-new
```

### 第 2 步：先看根 README

先读：

- [../README.zh-CN.md](../README.zh-CN.md)

这一步先搞清楚三件事：

- 这个项目是干什么的
- 主要文档入口在哪里
- 平时该用哪些 `scripts/` 里的脚本

### 第 3 步：搭环境

按 [installation.md](installation.md) 做。

最短命令是：

```bash
./scripts/setup_env.sh
```

做完之后至少确认：

- `.venv` 已经创建成功
- `rs-enumerate-devices` 能看到 D405
- 机械臂 CAN 可以正常使用

### 第 4 步：打印标定板

仓库已经带了可直接打印的默认板：

- [../assets/calibration/charuco_default/charuco_board.pdf](../assets/calibration/charuco_default/charuco_board.pdf)

打印前先看：

- [../assets/calibration/charuco_default/README.md](../assets/calibration/charuco_default/README.md)

### 第 5 步：照快速上手跑一遍

接下来读：

- [quickstart.zh-CN.md](quickstart.zh-CN.md)

这份文档是当前项目最适合“照着一步一步做”的清单。

### 第 6 步：按顺序做标定

参考：

- [handeye.md](handeye.md)

依次运行：

```bash
./scripts/run_calibrate_intrinsics.sh
./scripts/run_calibrate_handeye.sh
./scripts/run_validate_handeye.sh
```

### 第 7 步：如果需要，再估计 TCP Offset

如果夹爪抓取中心和当前业务 TCP 不一致，就看：

- [tcp_offset.md](tcp_offset.md)

并运行：

```bash
./scripts/run_estimate_tcp_offset.sh
```

如果你采用了新的 TCP offset，那么后面必须重做：

- 手眼标定
- 手眼验证
- 关键位采集

### 第 8 步：采集关键位

看：

- [keypoints.md](keypoints.md)

运行：

```bash
./scripts/run_capture_keypoints.sh
```

至少保存：

- `home`
- `observe`
- `drop_pose`

你也可以先直接使用仓库自带的参考模板：

- `configs/task/pick_demo_template.yaml`

抓取 demo 会优先使用你本地的 `configs/task/pick_demo_points.yaml`；如果你还没有自己采集，它会自动回退到这份受版本管理的模板。

### 第 9 步：先确认监控链路正常

运行：

```bash
./scripts/run_monitor.sh
./scripts/run_monitor.sh --yolo
```

这一步要确认：

- 机械臂状态能正常刷新
- D405 画面正常
- 开启 YOLO 后检测框正常显示

### 第 10 步：最后跑点击抓取

读：

- [pick_demo.md](pick_demo.md)

然后先用 dry-run：

```bash
./scripts/run_click_pick_demo.sh --yolo --dry-run
```

确认没问题后再真机执行：

```bash
./scripts/run_click_pick_demo.sh --yolo --no-dry-run
```

## 实用建议

- 手眼标定之后不要跳过验证步骤。
- 只要改了 TCP offset，就把标定和关键位相关步骤重做一遍。
- 只要改了 `observe`，点击抓取补偿大概率也要重新微调。
- 如果中途乱了，回到 [quickstart.zh-CN.md](quickstart.zh-CN.md)，按顺序重新走一遍。 
