# WSL2 Ubuntu 22.04 Complete USB-CAN Setup Guide

> This guide explains how to use a USB-CAN adapter inside WSL2 Ubuntu 22.04, including `usbipd-win` attachment, CAN driver loading, optional custom kernel build for `gs_usb`, and communication testing.

## Table of Contents

- [Switch to 中文](#wsl2-ubuntu-2204-连接-usb-can-模块完整指南)
- [1. Create a Custom-Named Ubuntu 22.04 Instance](#1-create-a-custom-named-ubuntu-2204-instance)
- [2. Windows Side: Install usbipd-win](#2-windows-side-install-usbipd-win)
- [3. WSL Side: Install Required Tools](#3-wsl-side-install-required-tools)
- [4. Attach USB Device to WSL](#4-attach-usb-device-to-wsl)
- [5. Load Kernel Driver and Configure CAN Interface](#5-load-kernel-driver-and-configure-can-interface)
- [6. Build Kernel to Add `gs_usb` Driver (If Needed)](#6-build-kernel-to-add-gs_usb-driver-if-needed)
- [7. Optional Optimization (Passwordless sudo + Auto Module Loading)](#7-optional-optimization-passwordless-sudo--auto-module-loading)
- [8. USB Auto Attach (Windows Side)](#8-usb-auto-attach-windows-side)
- [9. Test Communication](#9-test-communication)
- [10. Common Issues and Fixes](#10-common-issues-and-fixes)
- [11. Quick Command Reference](#11-quick-command-reference)

## 1. Create a Custom-Named Ubuntu 22.04 Instance

If you need multiple isolated environments (for example, an instance named `agx_arm`), use the steps below.

### 1.1 Create and name a new instance

Run this in **PowerShell** or **Command Prompt**:

```powershell
wsl --install -d Ubuntu-22.04 --name agx_arm
```

- `--name agx_arm` sets the new instance name to `agx_arm`.
- After installation, you will be prompted to create a username and password.

### 1.2 Start the target instance

```powershell
wsl -d agx_arm
```

### 1.3 Check whether the instance is WSL 2

In PowerShell:

```powershell
wsl -l -v
```

Example output:
```
  NAME         STATE           VERSION
* agx_arm      Stopped         1          <-- convert if VERSION is 1
  Ubuntu-22.04 Stopped         2
```

### 1.4 Convert to WSL 2 (if needed)

If the target instance is version 1:

```powershell
wsl --set-version agx_arm 2
```

The conversion may take a few minutes. Run `wsl -l -v` again to confirm VERSION is `2`.

### 1.5 Why WSL 2 is required

`usbipd-win` requires a **WSL 2** distribution because:
- WSL 2 uses a real Linux kernel and supports USB/IP and kernel modules like `gs_usb`.
- WSL 1 is a translation layer and cannot directly access physical USB devices or load Linux kernel drivers.

So all later steps must be done in a WSL 2 distribution.

---

## 2. Windows Side: Install usbipd-win

Open PowerShell **as Administrator** and run:

```powershell
winget install --interactive --exact dorssel.usbipd-win
```

If `winget` is unavailable, download the `.msi` from the [usbipd-win releases page](https://github.com/dorssel/usbipd-win/releases).

---

## 3. WSL Side: Install Required Tools

In your WSL Ubuntu terminal (for example, `agx_arm`), run:

```bash
sudo apt update
sudo apt install -y linux-tools-generic hwdata can-utils
```

---

## 4. Attach USB Device to WSL

> **Important**
> It is recommended to unplug the USB-CAN device before starting WSL. Start WSL first and keep it running, then plug in the device and run `usbipd attach`. This helps avoid driver binding issues that may lead to `candump` receiving no data. If this issue already happened, unplug and replug the device once.

### 4.1 Start WSL and keep it running

Open a normal PowerShell window (or open a WSL terminal directly):

```powershell
wsl -d agx_arm
```

Keep that terminal open. Closing it may stop the WSL instance.

### 4.2 Bind and attach the device

In another PowerShell window opened **as Administrator**:

```powershell
# List USB devices and note the CAN adapter BUSID (for example, 1-9)
usbipd list

# Bind device
usbipd bind --busid <BUSID>

# Attach to WSL
usbipd attach --wsl --busid <BUSID>
```

### 4.3 Verify device connection

Back in WSL:

```bash
lsusb
```

You should see something similar to:
`ID 1d50:606f OpenMoko, Inc. Geschwister Schneider CAN adapter`

---

## 5. Load Kernel Driver and Configure CAN Interface

### 5.1 Try loading drivers

```bash
sudo modprobe can
sudo modprobe can_raw
sudo modprobe gs_usb
```

If `gs_usb` fails with `Module not found`, your current WSL kernel does not include that module. Build a custom kernel (Section 6). Otherwise continue to 5.2.

### 5.2 Check CAN interface

```bash
ip link show
```

Normally `can0` should appear. If not, check kernel logs:

```bash
dmesg | grep -i can
```

### 5.3 Configure and bring interface up

```bash
sudo ip link set can0 up type can bitrate 1000000   # 1 Mbps
```

Confirm:

```bash
ip link show can0
```

---

## 6. Build Kernel to Add `gs_usb` Driver (If Needed)

If Step 5.1 reports `Module not found` for `gs_usb`, compile a kernel that includes this driver.

### 6.1 Get current kernel version

```bash
uname -r
```

Example: `6.6.87.2-microsoft-standard-WSL2`  
Save this version and clone the matching branch.

### 6.2 Install build dependencies

```bash
sudo apt install -y build-essential flex bison libssl-dev libelf-dev dwarves libncurses-dev
```

### 6.3 Clone matching kernel source

```bash
# Replace branch name with your uname -r version
git clone https://github.com/microsoft/WSL2-Linux-Kernel.git --depth=1 -b linux-msft-wsl-6.6.87.2
cd WSL2-Linux-Kernel
```

### 6.4 Reuse current kernel config

```bash
cat /proc/config.gz | gunzip > .config
```

### 6.5 Prepare build

```bash
make prepare modules_prepare
```

Some tail-end warnings can usually be ignored.

### 6.6 Configure kernel options (critical)

Open configuration UI:

```bash
make menuconfig
```

Key operations:
- `Up/Down`: move cursor
- `Enter`: enter submenu
- `Space`: toggle option (`[ ]` -> `<M>` -> `[*]`)
- `Exit`: back/exit
- `Save`: save config

Required settings:

1. **Enable CAN subsystem**
   - `Networking support` -> Enter
   - `CAN bus subsystem support` -> set to `<M>`
   - Enter CAN submenu and set items such as `Raw CAN Protocol`, `Broadcast Manager CAN Protocol`, `CAN Gateway/Router`, `SAE J1939`, `ISO 15765-2` to `<M>`
   - Exit back to main menu

2. **Enable CAN USB driver**
   - `Device Drivers` -> `Network device support` -> `CAN Device Drivers` (set `<M>`) -> Enter
   - `CAN USB interfaces` -> Enter
   - `Geschwister Schneider UG and candleLight compatible interfaces` (`GS_USB`) -> set to `<M>`

3. **Save and exit**
   - Exit until prompted, choose **Yes** to save `.config`

### 6.7 Build and install modules

```bash
# Build modules (-j can be adjusted, e.g. -j4)
make modules -j$(nproc)

# Install modules
sudo make modules_install

# Build full kernel image
make -j$(nproc)
```

### 6.8 Replace WSL kernel image

```bash
# Copy new kernel image to Windows user directory
cp arch/x86/boot/bzImage /mnt/c/Users/<YourUserName>/wsl_kernel
```

### 6.9 Configure Windows to use custom kernel

Create or edit `C:\Users\<YourUserName>\.wslconfig`:

```ini
[wsl2]
kernel = C:\\Users\\<YourUserName>\\wsl_kernel
```

### 6.10 Restart WSL and verify

In Windows PowerShell:

```powershell
wsl --shutdown
```

Restart WSL and run:

```bash
uname -r
```

Output should include a `+` suffix (for example `6.6.87.2-microsoft-standard-WSL2+`), indicating the custom kernel is active.

Then load drivers again:

```bash
sudo modprobe can
sudo modprobe can_raw
sudo modprobe gs_usb   # should now succeed
```

### 6.11 Copy kernel modules to another WSL instance (optional)

If modules are already built and installed in one WSL instance, you can copy them into another new instance without rebuilding.

> **Prerequisite:** Both instances must run the same kernel version (`uname -r`), including the same `+`-suffixed custom kernel from `.wslconfig`.

Recommended approach: transfer via Windows filesystem.

1. **In source instance**, copy modules to a Windows path:
   ```bash
   sudo cp -r /lib/modules/6.6.87.2-microsoft-standard-WSL2+ /mnt/c/Users/<YourUserName>/
   ```
   (Adjust the directory name to your actual `uname -r` result)

2. **In target instance**, copy modules into `/lib/modules/`:
   ```bash
   sudo cp -r /mnt/c/Users/<YourUserName>/6.6.87.2-microsoft-standard-WSL2+ /lib/modules/6.6.87.2-microsoft-standard-WSL2+/
   ```

3. **Verify in target instance**:
   ```bash
   sudo modprobe can
   sudo modprobe can_raw
   sudo modprobe gs_usb
   ```
   If no error appears, copy succeeded.

---

## 7. Optional Optimization (Passwordless sudo + Auto Module Loading)

To make usage more convenient, you can auto-load CAN modules and avoid password prompts for `modprobe`.

### 7.1 Configure passwordless `modprobe`

```bash
sudo visudo
```

Add this line at the end (replace `<UserName>`):

```
<UserName> ALL=(ALL) NOPASSWD: /sbin/modprobe
```

> `visudo` validates syntax before saving. If you want passwordless sudo for all commands (not recommended), use `<UserName> ALL=(ALL) NOPASSWD: ALL`.

### 7.2 Auto-load CAN modules in `.bashrc`

Append to `~/.bashrc`:

```bash
# Auto-load CAN modules only when missing
if ! lsmod | grep -q "can"; then
    sudo modprobe can 2>/dev/null
    sudo modprobe can_raw 2>/dev/null
    sudo modprobe gs_usb 2>/dev/null
fi
```

---

## 8. USB Auto Attach (Windows Side)

If you usually plug the adapter into the same USB port:

```powershell
usbipd attach --wsl --auto-attach --busid <BUSID>
```

- This continuously watches the specified BUSID and auto-attaches when plugged in.
- Keep the PowerShell window running (minimize or add to startup if needed).

---

## 9. Test Communication

- **Listen** (Terminal A):
  ```bash
  candump can0
  ```

- **Send test frame** (Terminal B):
  ```bash
  cansend can0 123#1122334455667788
  ```

If the listener receives frames, setup is successful.

---

## 10. Common Issues and Fixes

| Problem | Cause | Fix |
|------|------|----------|
| `usbipd attach` reports "No WSL 2 distribution running" | No running WSL2 instance | Start target distribution first and keep terminal open |
| `lsusb` shows device but `ip link show` has no CAN interface | Driver not bound or attach failed | Check `dmesg`, run `usbipd attach` again, reload `gs_usb` |
| `modprobe gs_usb` reports "Module not found" | Kernel lacks module | Rebuild kernel in Section 6 or copy modules using 6.11 |
| `No such device` when configuring `can0` | Interface name is not `can0` | Confirm actual name with `ip link show` |
| `candump` receives no data | Bitrate mismatch or no bus peer | Verify bitrate (for example 1 Mbps) and hardware wiring |
| `candump can0` gets no data while `can0` is UP | Device was inserted before WSL startup; driver bind issue | Replug USB-CAN, or follow Section 4 order (start WSL first, then attach) |

---

## 11. Quick Command Reference

| Operation | Command |
|------|------|
| List WSL distributions and versions | `wsl -l -v` |
| Start named distribution | `wsl -d agx_arm` |
| Remove a distribution | `wsl --unregister agx_arm` |
| Convert distribution to WSL2 | `wsl --set-version agx_arm 2` |
| List USB devices (WSL) | `lsusb` |
| List USB devices (Windows) | `usbipd list` |
| Attach device | `usbipd attach --wsl --busid <BUSID>` |
| Detach device | `usbipd detach --busid <BUSID>` |
| Show network interfaces | `ip link show` |
| Bring up CAN interface | `sudo ip link set can0 up type can bitrate 1000000` |
| Listen on CAN bus | `candump can0` |
| Send CAN frame | `cansend can0 123#1122334455667788` |

---

**After completing these steps, you can use a USB-CAN adapter normally in WSL2 Ubuntu 22.04 for development and debugging.**

---

# WSL2 Ubuntu 22.04 连接 USB-CAN 模块完整指南

## 目录

- [切换到 English](#wsl2-ubuntu-2204-complete-usb-can-setup-guide)
- [1. 创建自定义命名的 Ubuntu 22.04 实例](#1-创建自定义命名的-Ubuntu-2204-实例)
- [2. Windows 端：安装 usbipd-win](#2-Windows-端安装-usbipd-win)
- [3. WSL 端：安装必要工具](#3-WSL-端安装必要工具)
- [4. 将 USB 设备附加到 WSL](#4-将-USB-设备附加到-WSL)
- [5. 加载内核驱动并配置 CAN 接口](#5-加载内核驱动并配置-CAN-接口)
- [6. 编译内核以添加 `gs_usb` 驱动（如需要）](#6-编译内核以添加-gs_usb-驱动如需要)
- [7. 优化配置（免密 sudo + 自动加载模块）](#7-优化配置免密-sudo--自动加载模块)
- [8. USB 设备自动 attach（Windows 端）](#8-USB-设备自动-attachWindows-端)
- [9. 测试通信](#9-测试通信)
- [10. 常见问题及解决](#10-常见问题及解决)
- [11. 常用命令速查](#11-常用命令速查)

## 1. 创建自定义命名的 Ubuntu 22.04 实例

如果您需要创建多个独立环境（例如命名为 `agx_arm`），可以使用以下方法。

### 1.1 创建并命名新实例

在 **PowerShell** 或 **命令提示符** 中执行：

```powershell
wsl --install -d Ubuntu-22.04 --name agx_arm
```

- `--name agx_arm` 指定新实例的名称为 `agx_arm`。
- 安装成功后，需要输入用户名和密码。

### 1.2 启动指定名称的系统

```powershell
wsl -d agx_arm
```

### 1.3 检查目标系统是否为 WSL 2

在 PowerShell 中运行：

```powershell
wsl -l -v
```

输出示例：
```
  NAME         STATE           VERSION
* agx_arm      Stopped         1          <-- 若 VERSION 为 1，则需转换
  Ubuntu-22.04 Stopped         2
```

### 1.4 转换为 WSL 2（如果需要）

若目标实例版本为 1，执行以下命令将其转换为 WSL 2：

```powershell
wsl --set-version agx_arm 2
```

转换需要几分钟，完成后再次运行 `wsl -l -v` 确认版本已变为 `2`。

### 1.5 为什么必须使用 WSL 2？

`usbipd-win` 工具要求目标发行版必须是 **WSL 2**，因为：
- WSL 2 使用真正的 Linux 内核，支持 USB/IP 协议和内核模块（如 `gs_usb`）。
- WSL 1 是翻译层，无法直接访问物理 USB 设备，也不支持加载内核驱动。

因此，后续所有操作都必须在 WSL 2 发行版中进行。

---

## 2. Windows 端：安装 usbipd-win

以**管理员身份**打开 PowerShell，执行：

```powershell
winget install --interactive --exact dorssel.usbipd-win
```

若 `winget` 不可用，请到 [usbipd-win 发布页](https://github.com/dorssel/usbipd-win/releases) 下载 `.msi` 安装包。

---

## 3. WSL 端：安装必要工具

在 WSL Ubuntu 终端中运行（使用您创建的实例，如 `agx_arm`）：

```bash
sudo apt update
sudo apt install -y linux-tools-generic hwdata can-utils
```

---

## 4. 将 USB 设备附加到 WSL

> **⚠️ 重要提示**
> **建议在启动 WSL 实例之前先断开设备连接**，等 WSL 启动完成并保持运行后，**再插入设备**并执行 `usbipd attach`。这样可以避免因设备在 WSL 启动前已插入而导致驱动加载异常，进而出现 `candump` 无数据的问题。如果已经遇到该问题，只需将设备重新插拔一次即可恢复。

### 4.1 启动 WSL 并保持运行

打开一个**普通权限**的 PowerShell（或直接打开 WSL 终端），启动目标实例：

```powershell
wsl -d agx_arm
```

**保持此终端窗口打开**，不要关闭，否则 WSL 实例会停止运行。

### 4.2 绑定并附加设备

在**另一个以管理员身份打开的 PowerShell** 中：

```powershell
# 列出所有 USB 设备，记下 CAN 适配器的 BUSID（例如 1-9）
usbipd list

# 绑定设备
usbipd bind --busid <BUSID>

# 附加到 WSL
usbipd attach --wsl --busid <BUSID>
```

### 4.3 验证设备已连接

回到 WSL 终端，执行：

```bash
lsusb
```

应能看到类似输出：
`ID 1d50:606f OpenMoko, Inc. Geschwister Schneider CAN adapter`

---

## 5. 加载内核驱动并配置 CAN 接口

### 5.1 尝试加载驱动

```bash
sudo modprobe can
sudo modprobe can_raw
sudo modprobe gs_usb
```

如果 `gs_usb` 加载失败并提示 `Module not found`，说明当前 WSL 内核未包含该驱动，需要**重新编译内核**（见第 6 节）。否则直接跳至 5.2。

### 5.2 检查 CAN 接口

```bash
ip link show
```

正常情况下会出现 `can0` 接口。若未出现，可查看内核日志：

```bash
dmesg | grep -i can
```

### 5.3 配置并启用接口

```bash
sudo ip link set can0 up type can bitrate 1000000   # 波特率 1Mbps
```

确认接口已启用：

```bash
ip link show can0
```

---

## 6. 编译内核以添加 `gs_usb` 驱动（如需要）

如果第 5.1 步加载 `gs_usb` 时遇到 `Module not found` 错误，则需要编译支持该驱动的内核。

### 6.1 获取当前内核版本

在 WSL 终端中执行：

```bash
uname -r
```

输出示例：`6.6.87.2-microsoft-standard-WSL2`
记下这个版本号，后续克隆对应分支。

### 6.2 安装编译依赖

```bash
sudo apt install -y build-essential flex bison libssl-dev libelf-dev dwarves libncurses-dev
```

### 6.3 克隆内核源码（版本与当前一致）

```bash
# 使用 uname -r 得到的版本号替换下面的分支名
git clone https://github.com/microsoft/WSL2-Linux-Kernel.git --depth=1 -b linux-msft-wsl-6.6.87.2
cd WSL2-Linux-Kernel
```

### 6.4 使用当前内核配置

```bash
cat /proc/config.gz | gunzip > .config
```

### 6.5 准备编译环境

```bash
make prepare modules_prepare
```
（末尾若有错误提示，可暂时忽略）

### 6.6 配置内核选项（关键步骤）

执行以下命令打开图形化配置界面：

```bash
make menuconfig
```

**操作说明**：
- `↑` `↓` 方向键：移动光标
- `Enter`：进入子菜单
- `空格`：切换选项状态（`[ ]` → `<M>` → `[*]`）
- `Exit`：返回上一级菜单或退出
- `Save`：保存配置

**具体路径与操作**：

1. **开启 CAN 子系统**
   - 光标移动到 `Networking support` → 按 `Enter` 进入。
   - 找到 `CAN bus subsystem support` → 按 **空格** 将其改为 `<M>`（模块）。
   - 再次按 `Enter` 进入该子菜单。
   - 将内部所有选项（`Raw CAN Protocol`、`Broadcast Manager CAN Protocol`、`CAN Gateway/Router`、`SAE J1939`、`ISO 15765-2` 等）都按 **空格** 设为 `<M>`。
   - 选择两次 `Exit` 退回到主菜单。

2. **进入设备驱动菜单**
   - 光标移动到 `Device Drivers` → 按 `Enter` 进入。
   - 找到 `Network device support` → 按 `Enter` 进入。
   - 找到 `CAN Device Drivers` → 按 **空格** 改为 `<M>` → 按 `Enter` 进入。
   - 找到 `CAN USB interfaces` → 按 `Enter` 进入。
   - 找到 `Geschwister Schneider UG and candleLight compatible interfaces`（即 `GS_USB` 驱动）→ 按 **空格** 改为 `<M>`。

3. **保存并退出**
   - 连续选择 `Exit` 直到出现保存提示框，选择 **Yes** 即可（文件名默认为 `.config`）。

### 6.7 编译并安装内核模块

```bash
# 编译模块（-j 后面的数字可设为 CPU 核心数，如 -j4）
make modules -j$(nproc)

# 安装模块
sudo make modules_install

# 编译完整内核镜像
make -j$(nproc)
```

### 6.8 替换 WSL 内核

```bash
# 将新内核镜像复制到 Windows 用户目录
cp arch/x86/boot/bzImage /mnt/c/Users/<你的用户名>/wsl_kernel
```

### 6.9 配置 Windows 使用新内核

在 Windows 中创建或编辑 `C:\Users\<你的用户名>\.wslconfig`，添加以下内容：

```ini
[wsl2]
kernel = C:\\Users\\<你的用户名>\\wsl_kernel
```

### 6.10 重启 WSL 并验证

在 **Windows PowerShell** 中执行：

```powershell
wsl --shutdown
```

然后重新启动 WSL 终端，执行：

```bash
uname -r
```

输出应带有 `+` 号（如 `6.6.87.2-microsoft-standard-WSL2+`），说明正在使用自定义内核。

最后重新加载驱动：

```bash
sudo modprobe can
sudo modprobe can_raw
sudo modprobe gs_usb   # 现在应成功加载
```

### 6.11 将内核模块复制到其他 WSL 实例（可选）

如果您已经在一台 WSL 实例中编译并安装了内核模块，而想要在**另一个新建的 WSL 实例**中也使用相同的驱动，**无需重新编译**。只需将模块文件复制到新实例即可。

> **前提**：新实例的内核版本必须与已编译模块的版本一致（即 `uname -r` 均显示带 `+` 的相同版本），因为所有实例共享同一个通过 `.wslconfig` 指定的内核镜像。

推荐使用 **Windows 文件系统中转** 的方法：

1. **在原实例中**（已编译并安装模块的实例），将模块目录复制到 Windows 可访问的路径（例如 C 盘用户目录）：
   ```bash
   sudo cp -r /lib/modules/6.6.87.2-microsoft-standard-WSL2+ /mnt/c/Users/<你的用户名>/
   ```
   （请根据实际 `uname -r` 输出的版本号调整目录名）

2. **在新实例中**，将模块目录从 Windows 路径复制到 `/lib/modules/`：
   ```bash
   sudo cp -r /mnt/c/Users/<你的用户名>/6.6.87.2-microsoft-standard-WSL2+ /lib/modules/6.6.87.2-microsoft-standard-WSL2+/
   ```

3. **在新实例中加载模块验证**：
   ```bash
   sudo modprobe can
   sudo modprobe can_raw
   sudo modprobe gs_usb
   ```
   若无报错，说明复制成功。

完成模块复制后，新实例即可正常使用 USB-CAN 设备，无需重复编译内核。

---

## 7. 优化配置（免密 sudo + 自动加载模块）

为了方便使用，可以配置 WSL 使 CAN 模块在每次启动时自动加载，并免去输入密码的麻烦。

### 🔧 7.1 配置 sudo 免密执行 modprobe

编辑 sudoers 文件，允许当前用户无密码执行 `modprobe` 命令：

```bash
sudo visudo
```

在文件末尾添加以下行（将 `<用户名>` 替换为你的实际用户名）：

```
<用户名> ALL=(ALL) NOPASSWD: /sbin/modprobe
```

> **注意**：`visudo` 会检查语法错误，保存前请确认无误。如果希望允许所有命令（不推荐），可改为 `<用户名> ALL=(ALL) NOPASSWD: ALL`。

保存后，执行 `sudo modprobe can` 将不再提示输入密码。

### 🔧 7.2 通过 .bashrc 自动加载 CAN 模块

编辑 `~/.bashrc`，在末尾添加以下脚本：

```bash
# 自动加载 CAN 模块（仅当未加载时）
if ! lsmod | grep -q "can"; then
    sudo modprobe can 2>/dev/null
    sudo modprobe can_raw 2>/dev/null
    sudo modprobe gs_usb 2>/dev/null
fi
```

之后，每次打开终端时，系统会自动检查 CAN 模块是否已加载，若未加载则自动加载。

---

## 8. USB 设备自动 attach（Windows 端）

如果你习惯将 CAN 适配器插在同一个 USB 口，可以使用 `--auto-attach` 实现自动挂载：

```powershell
usbipd attach --wsl --auto-attach --busid <BUSID>
```

- 该命令会持续监控指定的 BusID，设备插入时自动附加到 WSL。
- **需要保持 PowerShell 窗口运行**，可最小化或放入启动项。

---

## 9. 测试通信

- **监听总线**（终端 A）：
  ```bash
  candump can0
  ```

- **发送测试帧**（终端 B）：
  ```bash
  cansend can0 123#1122334455667788
  ```

若监听端能收到报文，则配置成功。

---

## 10. 常见问题及解决

| 问题 | 原因 | 解决方法 |
|------|------|----------|
| `usbipd attach` 报“No WSL 2 distribution running” | 没有正在运行的 WSL 2 实例 | 先启动目标发行版并保持窗口打开 |
| `lsusb` 有设备但 `ip link show` 无 CAN 接口 | 驱动未绑定或设备附加失败 | 检查 `dmesg`，重新执行 `usbipd attach`，卸载并重新加载 `gs_usb` |
| `modprobe gs_usb` 报“Module not found” | 内核未包含驱动 | 按第 6 节重新编译内核，或从其他实例复制模块（6.11） |
| 配置 `can0` 时报“No such device” | 接口名不是 `can0` | 用 `ip link show` 确认实际接口名 |
| `candump` 收不到数据 | 波特率不匹配或总线无其他节点 | 确认实际波特率（如 1Mbps），检查硬件连接 |
| **`candump can0` 无任何数据，但 `ip link show` 显示 `can0` 已 UP** | **设备在 WSL 启动前已插入，导致驱动未正确绑定** | **1. 重新插拔 USB-CAN 设备；<br>2. 或者按照第 4 节提示：先断开设备，启动 WSL，再插入并执行 `usbipd attach`** |

---

### 11. 常用命令速查

| 操作 | 命令 |
|------|------|
| 查看 WSL 发行版及版本 | `wsl -l -v` |
| 启动指定发行版 | `wsl -d agx_arm` |
| 卸载实例 | `wsl --unregister agx_arm` |
| 转换发行版到 WSL 2 | `wsl --set-version agx_arm 2` |
| 查看 USB 设备（WSL） | `lsusb` |
| 查看 USB 设备（Windows） | `usbipd list` |
| 附加设备 | `usbipd attach --wsl --busid <BUSID>` |
| 分离设备 | `usbipd detach --busid <BUSID>` |
| 查看网络接口 | `ip link show` |
| 激活 CAN 模块 | `sudo ip link set can0 up type can bitrate 1000000` |
| 监听 CAN 总线 | `candump can0` |
| 发送 CAN 帧 | `cansend can0 123#1122334455667788` |

---

**完成以上步骤后，您即可在 WSL2 Ubuntu 22.04 中正常使用 USB-CAN 模块进行开发与调试。**
