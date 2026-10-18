# Lab2：物理内存和页表

默认管理器：Best-Fit。环境：WSL2 Ubuntu 22.04、QEMU **4.1.1**、RISC-V GCC/GDB。

```bash
source ~/os-course/env.sh
make clean
make -j4
make qemu  # Ctrl+A，松开，再 X 退出
make grade # 官方初始化/Best-Fit 检查，20/20
make -j4
```

## 分配器与测试

切换编译宏前必须 `make clean`。`make clean && make PMM=buddy` 使用 Buddy，`PMM=first_fit` 使用原 First-Fit；无参数默认 Best-Fit。Buddy 申请 n 页会实际分配上取整的 2 的幂页；释放时传原请求或实际块大小，不支持部分释放。

```bash
python3 tools/run_validation.py --out /tmp/lab2-best --manager best_fit
python3 tools/run_validation.py --out /tmp/lab2-buddy --manager buddy
python3 tools/run_validation.py --out /tmp/lab2-first --manager first_fit
python3 tools/run_validation.py --out /tmp/lab2-best --manager best_fit
python3 tools/test_page_init_edges.py --out /tmp/lab2-edges
```

SLUB 的 kmalloc/kfree 由启动检查验证，不支持并发调用。额外测试均保留断言，不改动老师的既有测试。

## QEMU 源码调试

源码和独立调试构建目录示例：

```bash
mkdir -p ~/os-course/toolchains/qemu-4.1.1-debug
cd ~/os-course/toolchains/qemu-4.1.1-debug
../qemu-4.1.1-source/configure --target-list=riscv64-softmmu \
  --python=python3 --disable-docs --disable-werror --enable-debug
make -j4
# 无须 make install
```

回到本目录，先确保编译的是默认 Best-Fit，然后执行：

```bash
python3 tools/debug_mmu.py \
  --qemu ~/os-course/toolchains/qemu-4.1.1-debug/riscv64-softmmu/qemu-system-riscv64 \
  --source ~/os-course/toolchains/qemu-4.1.1-source \
  --out /tmp/lab2-mmu
```

脚本启动两个独立 GDB，分别控制宿主 QEMU 子进程和客体内核；使用端口 1235，边界测试使用 1236，不改变系统 ptrace 设置。

报告、最终提示词、截图和原始证据位于上级 report/。使用 `mmu_probe_load`、`mmu_probe_after`、`mmu_probe_word` 符号可手动重做访存演示；地址随链接变化时以 ELF 符号为准。
