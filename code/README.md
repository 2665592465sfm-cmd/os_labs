# Lab1：最小可执行内核与启动流程

本目录保留课程提供的 ucore RISC-V 内核框架。Lab1 的练习是分析入口汇编并使用 QEMU/GDB 验证启动流程，无须实现中断、进程或内存分配功能。

Makefile 已明确 RV64 架构和 ABI，允许覆盖工具链前缀，GDB 目标使用同一前缀；启动目标使用 `-kernel`，向 QEMU 内置的 OpenSBI 动态固件传递正确的内核入口。

## Linux / WSL / Ubuntu

2026-10-04 已在本机 WSL2 + Ubuntu 22.04.5 LTS 完成配置和实际验证；13 项本地启动检查通过。项目在 Ubuntu 的 `~/os-course/os-labs`，AI 工具使用现有 Codex。实际日志位于 `../report/evidence/ubuntu`。

在这台电脑进入 Ubuntu 后运行：

```sh
source ~/os-course/env.sh
cd ~/os-course/os-labs/code
make
make qemu
```

准备 RISC-V 裸机 GCC（包含 binutils 和 GDB）、GNU make、QEMU 和 Python 3。

```sh
make
make qemu
```

QEMU 打印 `(THU.CST) os is loading ...` 后进入内核的无限循环，这是本实验的预期行为；按 Ctrl+A，然后松开并按 X 退出 QEMU。

在两个终端中分别运行：

```sh
# 终端 1
make debug

# 终端 2
make gdb
# 或使用课程练习的交互式调试脚本：
riscv64-unknown-elf-gdb -x tools/boot.gdb
```

自动验证复位地址、固件跳转、内核入口、栈初始化和 SBI 调用：

```sh
make check
```

若工具链名称是 `riscv-none-elf-*`，为所有 make 命令添加 `GCCPREFIX=riscv-none-elf-`。QEMU 和 Python 命令也可分别通过 `QEMU=...`、`PYTHON=...` 覆盖。

## 本次 Windows 测试

本次使用可解压运行的工具，无须配置系统级 PATH 或安装 WSL：

- [xPack RISC-V GCC 11.3.0-1](https://github.com/xpack-dev-tools/riscv-none-elf-gcc-xpack/releases/tag/v11.3.0-1)：包含 GCC 11.3.0、GDB 12.1 和 binutils。
- [xPack Windows Build Tools 4.4.1-3](https://github.com/xpack-dev-tools/windows-build-tools-xpack/releases/tag/v4.4.1-3)：GNU make 和 shell 工具。
- [QEMU Windows 2022-12-30](https://qemu.weilnetz.de/w64/2022/)：QEMU 7.2.0，使用与课程旧版 SBI 控制台接口兼容的固件。
- Python 3 和 Git for Windows 的 Unix 辅助工具。

当前电脑的工具存放在本任务的 `work/toolchains`，不上传 Git 仓库。在 `code` 中运行：

```powershell
powershell -ExecutionPolicy Bypass -File .\run-lab.ps1 -Action build
powershell -ExecutionPolicy Bypass -File .\run-lab.ps1 -Action run
powershell -ExecutionPolicy Bypass -File .\run-lab.ps1 -Action check
```

`Bypass` 仅作用于这次 PowerShell 进程。若工具位于其他位置，传入 `-ToolsRoot "工具目录"`，目录结构应为：

```text
工具目录/
  gcc/xpack-riscv-none-elf-gcc-11.3.0-1/bin/
  make/xpack-windows-build-tools-4.4.1-3/bin/
  qemu/qemu-system-riscv64.exe
```

## 测试证据与边界

### 实际终端截图

2026-10-05 已收到组长提供的六张真实 Ubuntu 终端截图，覆盖 `make -B`、`make check`、`make qemu` 上下两部分及 GDB 上下两部分。图片位于 `../report/images/ubuntu-*.png`，原始附件对应关系和校验值见 `../report/evidence/ubuntu/user-terminal-screenshots.json`。报告正文采用这组截图和 Ubuntu 实测值。

在自己打开的 PowerShell 中运行下面的命令。脚本实际执行构建、QEMU 和验证命令，在每个阶段暂停，提示截图文件名。QEMU 输出内核启动信息后，按 Ctrl+A、松开、再按 X 退出，继续截图。

```powershell
powershell -ExecutionPolicy Bypass -File .\review-lab.ps1 -Python "D:/python/python.exe"
```

其他电脑应把 `-Python` 改为自己的 Python 路径；工具不在默认位置时，另传 `-ToolsRoot`。将 `terminal-build.png`、`terminal-qemu.png`、`terminal-check.png`、`terminal-grade.png` 保存到仓库的 `report/images`。截取完整的命令与结果；窗口较小时可分别截取，不应改写错误信息。

上述脚本用于重跑 Windows 验证；当前交付已使用六张 Ubuntu 终端截图。原有 JPG 是真实 Windows 日志的浏览器展示图，作为报告附录保留。`grade` 如仍提示缺少脚本，应保存实际报错，不能把它记成评分通过。截图脚本不会上传仓库。

`make check` 是本实验新增的本地验证，不是教师提供的评分器。它真实启动 QEMU 并连接 GDB，保存调试日志、串口日志、校验结果和镜像 SHA256 到 `test-output`。

课程提供的 Makefile 含 `make grade`，但本次收到的文件没有 `tools/grade.sh`。不能据此声称官方评分通过。完整报告与已保存的测试证据位于仓库的 `report` 目录。
