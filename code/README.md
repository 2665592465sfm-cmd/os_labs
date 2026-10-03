# Lab1：最小可执行内核与启动流程

本目录保留课程提供的 ucore RISC-V 内核框架。Lab1 的练习是分析入口汇编并使用 QEMU/GDB 验证启动流程，无须实现中断、进程或内存分配功能。

Makefile 已明确 RV64 架构和 ABI，允许覆盖工具链前缀，GDB 目标使用同一前缀；启动目标使用 `-kernel`，向 QEMU 内置的 OpenSBI 动态固件传递正确的内核入口。

## Linux / WSL / Ubuntu

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

`make check` 是本实验新增的本地验证，不是教师提供的评分器。它真实启动 QEMU 并连接 GDB，保存调试日志、串口日志、校验结果和镜像 SHA256 到 `test-output`。

课程提供的 Makefile 含 `make grade`，但本次收到的文件没有 `tools/grade.sh`。不能据此声称官方评分通过。完整报告与已保存的测试证据位于仓库的 `report` 目录。
