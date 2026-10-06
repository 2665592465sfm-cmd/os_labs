# Lab1早期环境记录

保存日期：2026-10-06。这些是此前Windows与Ubuntu/QEMU6.2的真实运行记录。当前报告采用指定QEMU4.1.1的新证据；历史文字按当时状态阅读。

## 附录 A：早期 Windows 验证环境

初始阶段在 Windows 完成的真实验证保留作历史补充。正文练习使用 Ubuntu 实测值；本附录不把 Windows 日志标为 Linux 会话。

| 项目 | 实际配置 |
|------|----------|
| 宿主环境 | Windows x86-64、PowerShell |
| 交叉编译器 | xPack GNU RISC-V Embedded GCC 11.3.0-1；GCC 11.3.0 |
| 编译目标 | `-march=rv64gc -mabi=lp64d -mcmodel=medany` |
| 调试器 | xPack GDB 12.1，目标 `riscv:rv64` |
| 构建工具 | GNU Make 4.4.1，Git for Windows 的 Unix 辅助工具 |
| 模拟器 | QEMU 7.2.0，`virt`；自动验证使用 1 个 hart、128 MiB RAM |
| 固件 | QEMU 内置 OpenSBI v1.1，基址 `0x80000000` |
| 内核入口 | `0x80200000` |
| 自动验证 | Python 3.13.2 |

完整版本输出见 [environment.log](../environment.log)。工具来自 xPack 官方 GitHub Releases 与 QEMU 官网列出的 Windows 构建站点，下载后核对发布方 SHA256/SHA512。工具保存在本地工作目录，仓库只保存实验源代码和交付文件。


## 附录 B：早期 Windows 验证与补齐记录

以下五张JPG是此前Windows日志展示截图；旧Ubuntu6.2的六张终端截图保留在附录C。当前正文采用指定QEMU4.1.1的真实日志，指定环境正式终端截图已收到5/5张，其余待补；来源与校验值见[截图清单](../qemu-4.1.1/user-terminal-screenshots.json)。

### B.1 编译与运行

实际执行 `make GCCPREFIX=riscv-none-elf-`，8 个源文件编译成功，链接和镜像转换成功。`make qemu` 输出固件信息和内核字符串，经 Ctrl+A、X 退出后命令返回 0。

![编译与 QEMU 实际运行日志](../../images/build-and-qemu.jpg)

原始证据：[build.log](../build.log)、[make-qemu.log](../make-qemu.log)、[elf-layout.log](../elf-layout.log)。

### B.2 复位、内核入口和栈

![GDB 复位与固件入口日志](../../images/gdb-reset.jpg)

![GDB 内核入口、栈和尾跳转日志](../../images/gdb-kernel.jpg)

原始证据：[gdb.log](../gdb.log)、[kernel-symbols.log](../kernel-symbols.log)、[entry-disassembly.log](../entry-disassembly.log)。

### B.3 本地自动检查和 SBI 证据

13 项检查包括：复位 PC；复位时镜像已存在；进入 OpenSBI；进入内核；栈顶地址；栈大小；尾跳转不写 RA；到达 `cprintf`；SBI 参数；进入固件异常入口；返回内核；启动字符串；S-mode ecall 原因 9。全部通过。

![13 项本地检查和 SBI 调用证据](../../images/local-checks.jpg)

原始证据：[local-check.log](../local-check.log)、[traps.log](../traps.log)、[summary.json](../summary.json)。本次镜像 SHA256：

```text
997228412f63ece956133e3582821b2c5af2014b758ef19fd8ad26c080d38664
```

### B.4 官方评分器缺失

实际执行 `make grade` 报错：

```text
sh: can't open 'tools/grade.sh': No such file or directory
make: *** [Makefile:203: grade] Error 2
```

![官方评分器缺失的实际输出](../../images/grade-unavailable.jpg)

原始证据：[official-grade-unavailable.log](../official-grade-unavailable.log)。收到的代码未提供评分脚本，所以不能宣称官方评分通过；上述 `make check` 是补充的本地验证。若教师随后提供原版评分器，需另行检查。

### B.5 按四段式执行的补齐复核

在补齐规格制定后，实际再次执行 `make grade`、构建、`make qemu` 和 `make check`。构建及运行成功，13 项本地检查通过，`make grade` 仍因脚本缺失返回 2。组长确认没有其他代码包或单独评分脚本。课程当前的 Lab1 文件树在 `tools` 下也只列出 `function.mk` 和 `kernel.ld`；这是收到新答疑之前的核对记录；根据答疑第3条，目前不再把该评分项作为 Lab1 待办，不借用其他实验或架构的评分脚本。

复核证据：[build.log](../followup/build.log)、[qemu-run.log](../followup/qemu-run.log)、[local-check.log](../followup/local-check.log)、[gdb.log](../followup/gdb.log)、[official-grade.log](../followup/official-grade.log)、[execution.json](../followup/execution.json)。`execution.json` 保存执行规格 SHA256，可与本次 [task-spec.md](../followup/task-spec.md) 对照。



---

## 附录 C：此前QEMU6.2的真实截图（历史记录）

以下六张图均来自此前Ubuntu的QEMU6.2/OpenSBI0.9环境，原始字节和来源保持不变。它们不能替代指定QEMU4.1.1环境的新截图；相关寄存器值仅解释这次历史运行。

### 5.1 重新编译

![Ubuntu make -B 编译输出](../../images/ubuntu-build.png)

截图显示八个源文件的编译、`bin/kernel` 的链接及 `objcopy` 生成 `bin/ucore.img`。目标是 RV64 裸机内核，ELF 机器类型和入口见 [elf-layout.log](../ubuntu/elf-layout.log)。独立保存的完整构建日志见 [build.log](../ubuntu/run-20261004-191910/build.log)。

### 5.2 本地自动检查

![Ubuntu make check 的 13 项通过结果](../../images/ubuntu-check.png)

截图明确显示 `13 local checks passed`。检查覆盖复位 PC、复位时已装入的镜像、进入 OpenSBI、进入内核、栈顶、栈大小、尾跳转保持 RA、到达 `cprintf`、SBI 参数、进入固件陷阱入口、返回内核、启动字符串及 S-mode ecall 原因 9。

原始证据：[check.log](../ubuntu/run-20261004-191910/check.log)、[summary.json](../ubuntu/run-20261004-191910/boot/summary.json)、[traps.log](../ubuntu/run-20261004-191910/boot/traps.log)。`make check` 是本次补充的本地验证，不是教师官方评分器。

### 5.3 QEMU 启动与内核输出

![Ubuntu make qemu 固件输出上部](../../images/ubuntu-qemu-opensbi.png)

![Ubuntu make qemu 内核输出下部](../../images/ubuntu-qemu-kernel.png)

两图共同展示同一类启动过程：OpenSBI v0.9 的固件基址为 `0x80000000`，下一阶段地址为 `0x80200000`，下一阶段特权级为 S-mode；内核输出 `(THU.CST) os is loading ...`。之后框架停在无限循环，符合预期。独立完整日志见 [make-qemu.log](../ubuntu/run-20261004-191910/make-qemu.log)。两张新截图本身未显示退出步骤；此前真实自动运行日志显示正常退出，退出码为 0，见 [execution.json](../ubuntu/run-20261004-191910/execution.json)。

### 5.4 GDB 复位、内核入口与栈

![Ubuntu GDB 从复位进入固件和内核](../../images/ubuntu-gdb-reset.png)

![Ubuntu GDB 建栈和尾跳转](../../images/ubuntu-gdb-stack.png)

第五张图观察到初始 PC 为 `0x1000`，复位桩后进入固件 `0x80000000`，随后断点停在内核入口 `0x80200000`。进入内核时 SP 为 `0x80017ee0`，RA 为 `0x800078cc`。

第六张图显示入口反汇编为 `auipc sp,0x3`、`mv sp,sp` 和 `j kern_init`；执行建栈后 SP 为 `0x80203000`，随后 PC 为 `0x8020000a <kern_init>`，RA 仍为 `0x800078cc`。这与练习 1 对建栈和尾跳转的分析一致。独立完整 GDB 会话见 [gdb.log](../ubuntu/boot/gdb.log)。

