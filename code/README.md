# Lab1：最小可执行内核与启动流程

本目录保留课程提供的 ucore RISC-V 内核框架。Lab1 的练习是分析入口汇编并使用 QEMU/GDB 验证启动流程，无须实现中断、进程或内存分配功能。

Makefile 已明确 RV64 架构和 ABI，允许覆盖工具链前缀，GDB 目标使用同一前缀；启动目标已恢复原框架的 `-device loader` 方式，按课程答疑使用精确QEMU4.1.1/OpenSBI0.4。

## Linux / WSL / Ubuntu

2026-10-05已在本机WSL2 + Ubuntu22.04.5配置指定QEMU4.1.1，并实际编译、启动和验证；13项额外本地检查通过。项目在 Ubuntu 的 `~/os-course/os-labs`，AI 工具使用现有 Codex。当前日志位于 `../report/evidence/qemu-4.1.1`；旧6.2截图为历史记录，新截图待补。

在这台电脑进入 Ubuntu 后运行：

```sh
source ~/os-course/env.sh
cd ~/os-course/os-labs/code
make
make qemu
```

准备RISC-V裸机GCC/binutils、可调试RISC-V的GDB、GNU make、精确QEMU4.1.1和Python3。

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

## 早期Windows测试（历史参考）

以下为此前Windows验证的工具记录，不作为指定QEMU4.1.1课程环境的交付依据。当前应使用上面的Ubuntu环境。

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

2026-10-05 已收到组长提供的六张真实 Ubuntu 终端截图，覆盖 `make -B`、`make check`、`make qemu` 上下两部分及 GDB 上下两部分。图片位于 `../report/images/ubuntu-*.png`，原始附件对应关系和校验值见 `../report/evidence/ubuntu/user-terminal-screenshots.json`。这组图来自QEMU6.2，已保留在报告历史附录；正文改用QEMU4.1.1的新日志，新终端截图待补。

在自己打开的 PowerShell 中运行下面的命令。脚本实际执行构建、QEMU 和验证命令，在每个阶段暂停，提示截图文件名。QEMU 输出内核启动信息后，按 Ctrl+A、松开、再按 X 退出，继续截图。

```powershell
powershell -ExecutionPolicy Bypass -File .\review-lab.ps1 -Python "D:/python/python.exe"
```

其他电脑应把 `-Python` 改为自己的 Python 路径；工具不在默认位置时，另传 `-ToolsRoot`。将 `terminal-build.png`、`terminal-qemu.png`、`terminal-check.png` 保存到仓库的 `report/images`。截取完整的命令与结果；窗口较小时可分别截取，不应改写错误信息。

上述脚本用于重跑 Windows 验证；此前六张Ubuntu终端截图为6.2历史记录，4.1.1新图待补。原有 JPG 是真实 Windows 日志的浏览器展示图，作为报告附录保留。根据答疑第3条，本脚本默认不再尝试make grade；历史报错保留，不记为评分通过。截图脚本不会上传仓库。

`make check` 是本实验新增的本地验证，不是教师提供的评分器。它真实启动 QEMU 并连接 GDB，保存调试日志、串口日志、校验结果和镜像 SHA256 到 `test-output`。

课程提供的 Makefile 含 `make grade`，但本次收到的文件没有 `tools/grade.sh`。不能据此声称官方评分通过。完整报告与已保存的测试证据位于仓库的 `report` 目录。

## 2026-10-05课程答疑修订

Lab1仅需分析两道练习并跑通make qemu。make check是可选辅助；prompt.md可为空，报告可省略模块修改部分。每位组员在自己电脑跑通，共同写一份报告，只需提交一人的截图；全员在截止前参加答辩。

组长已补齐答疑第18条并确认必须QEMU4.1.1；当前版本已修正，原loader方式运行成功，13项额外本地检查通过。旧图不能视为4.1.1证据，请补拍指定环境的新图。
