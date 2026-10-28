# Lab3：中断、异常与 Trap 上下文

环境沿用 Ubuntu 22.04、QEMU **4.1.1**、RISC-V GCC/GDB。默认 Best-Fit，保留教师 Lab3 的中断临界区包装。

## 默认运行与评分

```bash
source ~/os-course/env.sh
cd ~/os-course/os-labs-lab3/code
make -j4
make qemu
# 正常行为：输出十次 100 ticks，然后由 SBI 自动关机。
make grade
# 官方三项评分为 100 分；评分会清理构建。
make -j4
```

切勿把 Lab2 的整个 pmm.c 覆盖到这里：Lab3 的 alloc/free/nr_free 已包含 local_intr_save/restore。

## 补充测试和 GDB 演示

```bash
python3 tools/run_validation.py --out /tmp/lab3-extra
python3 tools/debug_trap.py --out /tmp/lab3-gdb
cat /tmp/lab3-extra/summary.json
cat /tmp/lab3-gdb/summary.json
```

补充测试在临时树注入，不修改教师测试或当前默认构建。GDB 工具使用端口 1237，以硬件断点观察一个真实 S-timer 从 SAVE_ALL、C 处理到 RESTORE_ALL/sret 的全过程，并检查 31 个可写整数寄存器、frame、栈和 CSR。运行前退出其他占用同一端口的调试会话。

## 手动观察

终端 A：

```bash
source ~/os-course/env.sh
cd ~/os-course/os-labs-lab3/code
make debug
```

终端 B：

```bash
source ~/os-course/env.sh
cd ~/os-course/os-labs-lab3/code
riscv64-unknown-elf-gdb -q -nx bin/kernel
```

```gdb
set pagination off
set architecture riscv:rv64
target remote localhost:1234
thbreak *__alltraps
continue
p/x $scause
p/x $sepc
set $old_sp = $sp
set $old_epc = $sepc
thbreak *trap
continue
set $tf = (struct trapframe *)$a0
p sizeof(struct trapframe)
p/x *$tf
thbreak *__trapret
continue
p ticks
p/x $tf->epc
disassemble __trapret
```

如需观察 `sret`，按本次反汇编的实际地址设置临时硬件断点；到达后再对 `$old_epc` 设置临时硬件断点，执行 `si`，确认返回 PC 和 sp。旧 QEMU 在 `sret` 处可能没有按预期单步停止，因此不能只靠没有返回提示符判断内核卡死。完整自动生成命令见 `/tmp/lab3-gdb/commands.gdb`。

## 范围

Trap frame 为 36 个 RV64 槽，即 288 字节；sp 最后恢复，sstatus/sepc 从 frame 恢复。异常长度按 16/32 位编码区分。SHUTDOWN_AFTER 在教师框架中缺失，当前在补全区域定义为 10 次统计。当前为单 hart 内核 S→S 返回，不提供用户栈切换或浮点/向量上下文保存。
