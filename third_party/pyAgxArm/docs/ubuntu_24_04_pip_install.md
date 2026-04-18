# Ubuntu 24.04 pip Installation Guide

> On Ubuntu 24.04, direct `pip3 install pyAgxArm` in system Python may fail due to package management restrictions.

## Table of Contents

- [Switch to 中文](#ubuntu-2404-安装第三方-pip-包的方法)
- [Environment](#environment)
- [Method 1: Virtual Environment (recommended)](#method-1-virtual-environment-recommended)
- [Method 2: Force install to system environment](#method-2-force-install-to-system-environment)

## Environment

On Ubuntu 24.04, direct `pip3 install pyAgxArm` in system Python may fail due to package management restrictions.

## Method 1: Virtual Environment (recommended)

Use official `python3.12-venv`, then install in the virtual environment:

```bash
sudo apt install python3-pip
sudo apt install python3.12-venv
python3 -m venv ~/venv
source ~/venv/bin/activate
pip install pyAgxArm
```

## Method 2: Force install to system environment

Use `--break-system-packages`:

```bash
pip install --user pyAgxArm --break-system-packages
```

To avoid typing this flag every time, write pip config:

```bash
mkdir -p ~/.config/pip
echo -e "[global]\nbreak-system-packages=true" > ~/.config/pip/pip.conf
```

Config content:

```ini
[global]
break-system-packages=true
```

After that, `pip install` works similarly to Ubuntu 22.04 and earlier.

---

# Ubuntu 24.04 安装第三方 pip 包的方法

> 在 Ubuntu 24.04 系统环境下直接执行 `pip3 install pyAgxArm` 可能会报错，本文提供两种解决方案。

## 目录

- [切换到 English](#ubuntu-2404-pip-installation-guide)
- [环境说明](#环境说明)
- [方法一：使用虚拟环境（推荐）](#方法一使用虚拟环境推荐)
- [方法二：强制安装到系统环境](#方法二强制安装到系统环境)

## 环境说明

在 Ubuntu 24.04 系统环境下直接执行 `pip3 install pyAgxArm` 可能会报错，本文提供两种解决方案。

## 方法一：使用虚拟环境（推荐）

使用官方 `python3.12-venv` 创建虚拟环境，然后在虚拟环境中安装：

```bash
sudo apt install python3-pip
sudo apt install python3.12-venv
python3 -m venv ~/venv
source ~/venv/bin/activate
pip install pyAgxArm
```

## 方法二：强制安装到系统环境

通过添加 `--break-system-packages` 标志来绕过限制：

```bash
pip install --user pyAgxArm --break-system-packages
```

**避免每次都输入该标志：** 可以将规则写入配置文件：

```bash
mkdir -p ~/.config/pip
echo -e "[global]\nbreak-system-packages=true" > ~/.config/pip/pip.conf
```

上述命令会创建 `~/.config/pip` 文件夹（如果不存在），然后创建 `pip.conf` 配置文件，内容如下：

```ini
[global]
break-system-packages=true
```

之后即可像 Ubuntu 22.04 及更早版本一样正常使用 `pip install` 命令安装包。
