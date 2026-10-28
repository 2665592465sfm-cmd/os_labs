# Lab3 测试方案与结果

测试运行日期：2026-10-28。平台：Ubuntu 22.04、QEMU 4.1.1 / OpenSBI 0.4、RV64GC/LP64D。以下区分教师官方测试、补充动态检查与源码审计。

## 1. 教师官方评分

保持 `grade.sh`、`inject.py`、`test_lab3.c/.h`、`test_lab3_context.S` 原样，运行 `make grade`。

| 检查 | 实际结果 |
|---|---|
| Trap 入口、寄存器恢复、断点 EPC | 35/35 |
| 非法指令 EPC、回退诊断 | 25/25 |
| 持续 S 模式 timer 与反复返回 | 40/40 |
| 总分 | **100/100** |

原记录：[grade.txt](evidence/grade.txt)。官方定时用例在 200 ticks 打印通过标记；它本身不足以证明十次统计后的关机，因此另做默认运行检查。

## 2. 正常启动和关机

原始命令为 `make -j4`、`make qemu`。检查默认 Best-Fit、原物理页自检、十行严格匹配的 `100 ticks`、无 panic，并验证进程自行正常退出。未把 timeout 杀进程视为关机成功。

记录：[default-run.txt](evidence/default-run.txt)。

## 3. 补充动态测试

命令：`python3 tools/run_validation.py --out /tmp/lab3-extra`。

该工具在独立临时树添加测试，原提交内核和教师测试不变。

| 覆盖 | 输入/观测 | 断言目的 |
|---|---|---|
| 整数寄存器恢复 | 写入区别值，执行真实 c.ebreak，再记录 32 个槽 | 所有可写整数寄存器保持；x0 恒零，sp/gp/tp 与原值一致 |
| 压缩断点 | 0x9002 | cause=断点，正确越过 2 字节并继续 |
| 标准断点 | 0x00100073 | 正确越过 4 字节，避免把所有断点加 2 |
| 压缩非法指令 | 0x0000 | 正确越过 2 字节，避免把所有非法指令加 4 |
| 标准非法指令 | 0x0000007b | 正确越过 4 字节 |
| 其他 IRQ 与未知 IRQ | 十四种合成原因，含未知 15 | 分类正确，frame 保持不变 |
| 未支持异常 | cause=20，EPC=0 | 只诊断，不误读空地址或改变 EPC |
| 更长编码 | 半字 0x001f | 诊断并保持 frame，不猜测 32 位长度 |
| 中断临界区 | 原 SIE=0/1、嵌套保存与恢复 | 内层不会提前开启中断，外层恢复原状态 |
| PMM 包装 | SIE 开启时分配、释放 | 操作后中断状态与空闲页数恢复 |
| timer 后续运行 | 补充检查后再初始化 timer | 仍输出十次统计并正常关机 |

原记录：[extra/qemu.txt](evidence/extra/qemu.txt)，摘要：[extra/summary.json](evidence/extra/summary.json)。

## 4. 真实 timer 的 GDB 检查

命令：`python3 tools/debug_trap.py --out /tmp/lab3-gdb`。

在 `__alltraps`、C `trap`、`__trapret`、实际 `sret` 指令和原返回 PC 设置临时硬件断点：

1. 保存 timer 进入时的 31 个可写整数寄存器。
2. 确认 `sizeof(trapframe)=288`，`a0=sp=旧 sp-288`，槽 2 保存旧 sp。
3. 确认真实 cause 为 `0x8000000000000005`，SPP=1。
4. C 返回时 ticks=1，EPC 未推进。
5. `sret` 前全部 31 个整数寄存器恢复，sp 回到原值。
6. 发出 `si`，并用返回 PC 的硬件断点保证旧版 QEMU 能可靠停止；核对 PC、sp、SIE 和 SPP 的返回后状态。

记录：[gdb/gdb.txt](evidence/gdb/gdb.txt)，命令：[gdb/commands.gdb](evidence/gdb/commands.gdb)，摘要：[gdb/summary.json](evidence/gdb/summary.json)。

首次工具尝试仅在 `sret` 处执行 `si`，没有观察到预期停止，最终连接在正常关机后关闭。保留 [首次 GDB 记录](evidence/gdb/first-attempt-gdb.txt) 和 [首次 QEMU 记录](evidence/gdb/first-attempt-qemu.txt)。增加返回地址临时硬件断点后通过；这只能说明该环境的单步停止行为需要补充控制，不据此断言内核恢复错误或唯一的模拟器根因。

## 5. 不在已验证范围内

没有声称实现/测试用户栈切换、多 hart 同步、嵌套 Trap、浮点/向量上下文、任意长指令恢复或用户地址安全取指。对其他异常的诊断输出不等于能从所有异常恢复。人员本机复现与答辩完成情况另行确认。
