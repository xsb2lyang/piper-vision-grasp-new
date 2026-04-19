# YOLO 目标抓取 Demo

这个 demo 和原来的点击抓取窗口是两套独立流程。

适合用在下面这种场景：

- 不想手动点像素
- 只想按“物体类别”来抓取
- 暂停当前画面后，让系统自动取对应检测框中心点作为抓取点

## 启动方式

```bash
./scripts/run_yolo_target_pick_demo.sh --no-dry-run
```

先安全预览：

```bash
./scripts/run_yolo_target_pick_demo.sh --dry-run
```

## 使用流程

1. 先把机械臂移动到保存好的 `observe` 位。
2. 在下拉框里选择目标类别，或者直接输入一个模型可识别的类别名。
3. 点击 `Pause / Freeze`。
4. 如果暂停画面中存在该物体，系统会自动选择该 bbox 的中心点。
5. 点击 `Execute Pick`。

如果暂停画面中没有这个目标物体，程序不会执行抓取，而是会在 `Last Event` 里明确提示没有待抓取目标。

## 说明

- 这个 demo 不需要手动点图像。
- 它和原来的点击抓取 demo 复用同一套手眼、关键位、TCP 和抓取参数配置。
- 原来的点击抓取 demo 没有被替换，仍然通过下面命令启动：

```bash
./scripts/run_click_pick_demo.sh --yolo --no-dry-run
```

