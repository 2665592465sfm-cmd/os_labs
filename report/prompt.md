# Lab3 提示词

以下规格在实现前依据本届指导书及教师 `lab3.zip` 整理。后续修订按实际问题补充，禁止把未运行的检查记作通过。

## P1：继承物理页初始化和 Best-Fit

```text
[PROMPT]
将本组 Lab2 已验证的物理页初始化与完整 Best-Fit 模块适配到教师 Lab3 框架的 lab2 标记位置；当前负责人 2412396。保留 Lab3 的中断保存/恢复包装、原有宏和测试。默认接入 Best-Fit。只移植所需实现，不复制 Lab2 的整个 pmm.c，也不引入 Buddy、SLUB 或 MMU 探针。

[RELY]
Lab3 的 pmm.c/pmm.h、memlayout.h/mmu.h、dtb.h、sync.h，教师 Best-Fit 文件已有测试，以及本组 Lab2 对应实现。Lab3 的头文件没有 Lab2 新增的 PHYSICAL_MEMORY_END、KERNEL_BEGIN_PADDR，因此必须由本框架已有宏推导边界，不能直接照抄不存在的符号。Page 布局、原子状态宏和 local_intr_save/restore 必须保留。

[GUARANTEE]
page_init(void)；best_fit_pmm_manager 的 init/init_memmap/alloc_pages/free_pages/nr_free_pages/check；init_pmm_manager 选择正确实例。原 basic_check/best_fit_check 的正文保持不变。

[SPECIFICATION]
page_init 的输入为已解析的单段 DTB RAM，固定 DRAM_BASE；检查空范围、加法溢出、管理上界和描述符容量。先保留所有页，再注册排除固件、内核、描述符与对齐间隙后的完整空闲页。npage 是页号上界，描述符数量是 npage-nbase。
Best-Fit 空闲块按地址排序，选择最小的足够大块，同长度选先遇到者，精确匹配摘除，较大块分割；失败返回 NULL 且不改变状态。回收按地址插入并合并连续前后块，页数仅增加本次释放量。合法输入 n>0，调用者不得重复释放。已有框架测试和中断临界区不得绕过或改写。
验收：源码差异审计、默认编译启动、原分配器检查；由后续 Trap 检查确认新中断包装未破坏运行。
```

## P2：完整 Trap 入口、上下文恢复与返回

```text
[PROMPT]
在 kern/trap/trapentry.S 的两个 lab3 function1 标记处实现 RESTORE_ALL 和 __alltraps 到 C trap 的桥接；将标记中的 YOUR CODE 改为 2412396。禁止修改已有 SAVE_ALL、trapframe 布局、trap 签名与 sret。覆盖模块完整职责，不以伪代码指定逐条指令顺序。输出实际修改及布局核对结果。

[RELY]
仅依赖 trapentry.S 的 SAVE_ALL、trap.h 的 pushregs/trapframe、riscv.h 的 LOAD/STORE/REGBYTES、RV64 ABI 和 S 模式 Trap 返回语义。本框架在当前内核栈保存 36 个寄存器槽位，RV64 下为 288 字节；gpr[0..31] 后依次为 status/epc/badvaddr/cause。

[GUARANTEE]
RESTORE_ALL 输入 sp 指向已保存的 trapframe，恢复 C 处理后应返回的执行状态；__alltraps 把当前 frame 指针作为 a0 调用 void trap(struct trapframe *tf)，返回后进入已有 __trapret 和 sret。

[SPECIFICATION]
SAVE_ALL 已用 sscratch 暂存旧 sp 并存入槽位 2；恢复前保持 frame 基址有效，恢复所有可写整数寄存器，最后从槽位 2 恢复 sp。不能在 frame 读取完成前改变 sp，不能把当前 frame 地址当成旧 sp。x0 恒为零。
从 frame 恢复 sstatus 与 sepc，临时寄存器也必须恢复为原值；badvaddr/cause 是记录信息，不要求写回对应 CSR。尊重 frame 中 SPP/SPIE，不强制切换到 U 模式，也不提前开启 SIE；最终特权返回由 sret 完成。当前实验验证内核 S 模式，不宣称实现用户栈切换、嵌套 Trap 或浮点/向量上下文。
传给 trap 的 a0 必须等于当前 frame 地址，C 调用前栈满足 ABI 对齐；恢复后执行点应采用 C 处理更新后的 epc。
验收：结构体槽位和汇编差异审计；未修改的官方上下文/断点测试；补充 16/32 位异常往返、sp 与寄存器状态、sret 前后 SPP/SIE/SPIE 的真实 GDB 检查。
```

## P3：中断、异常分发后的处理模块

```text
[PROMPT]
在 kern/trap/trap.c 的 lab3 function2 标记处实现 interrupt_handler 和 exception_handler；署名 2412396。保留文件其他已有函数、宏、框架测试和评分代码。允许在标记区域增加必要 include、私有常量与辅助定义。先核对原始框架，再实现可验证行为。

[RELY]
trapframe、trap_dispatch、print_trapframe、print_ticks、clock_set_next_event、ticks、TICK_NUM、IRQ_*、CAUSE_*、sbi_shutdown。教师代码 TICK_NUM=100，但没有定义指导书提到的 SHUTDOWN_AFTER；在本模块补全区域定义 SHUTDOWN_AFTER=10，含义为输出十次统计后关机，保留 TICK_NUM 原值。

[GUARANTEE]
void interrupt_handler(struct trapframe *tf);
void exception_handler(struct trapframe *tf);
不得修改 trap_dispatch、trap、idt_init、print_ticks 等既有函数。

[SPECIFICATION]
中断：剥离 cause 的最高中断标志后分发。IRQ_S_TIMER 每次重新安排下一事件且 ticks 恰加一；每达到 TICK_NUM 的倍数调用已有 print_ticks；达到 SHUTDOWN_AFTER 次统计时调用 sbi_shutdown。定时中断不改变 tf->epc。其余框架 IRQ 类型仅输出对应类型提示；未知类型输出 Unknown interrupt: cause N 并 print_trapframe，保持 frame 不变。
异常：CAUSE_ILLEGAL_INSTRUCTION 输出 Illegal instruction at，CAUSE_BREAKPOINT 输出 Breakpoint at，包含原 epc；读取映射且可读的异常指令半字，按编码区分 16 位与 32 位，分别更新 epc+2/+4，不能把所有断点当 2 字节或全部异常当 4 字节。此 RV64GC 教学路径只承诺这两种长度，遇到更长的指令编码只输出 frame，不猜测长度恢复；不宣称完整安全取指或通用非法指令模拟。其他异常只 print_trapframe，不修改 epc 或伪造恢复。
保持原输出格式检查：Supervisor software interrupt、Unknown interrupt: cause 15、已有 frame 输出。不得靠修改测试、删断言、检测评分宏跳过逻辑来得分。
验收：原官方三项测试；正常启动十次 100 ticks 后真实关机；16/32 位断点及非法指令连续执行后到达后续标记；未知原因不修改 frame；真实 timer 的 EPC 不跳过原指令。
```

## P4：独立验证、GDB 演示与证据记录

```text
[PROMPT]
为本次 Lab3 建立可重复运行的验证和调试工具。测试写在新工具文件或隔离临时构建树中，禁止修改教师 tools/grade.sh、inject.py、test_lab3.c/.h、test_lab3_context.S 和原 basic_check/best_fit_check。运行真实 QEMU 4.1.1，记录命令、版本、输出、退出码和断言，失败应非零退出。不要生成假终端截图。

[RELY]
最终内核源码、教师原始测试、本提示词 P1/P2/P3 的接口契约、QEMU 与交叉 GDB、nm/objdump。新测试不放 kern/test，避免与官方注入目录冲突。对原教师测试分别进行哈希审计。

[GUARANTEE]
独立默认构建/启动验证；原样 make grade；覆盖未包含于官方评分的异常长度和恢复验证；可复用 GDB 流程及原始日志；需求到验收记录的映射。

[SPECIFICATION]
T1 默认构建通过且分配器原检查通过。
T2 原官方评分逐项展示真实结果，不能把补充测试冒称官方评分。
T3 正常 timer 连续 1000 次事件，对应十行 100 ticks，之后 QEMU 通过 SBI 正常退出；单次超时或被强制杀进程不算关机成功。
T4 分别实际触发 16 位 c.ebreak、32 位 ebreak、16 位非法编码和 32 位非法自定义编码，检查 cause、旧 epc、增量、后续执行标记和寄存器；断点测试避免 GDB 软件断点把异常截走。
T5 GDB 对 __alltraps、trap、__trapret、sret 设置硬件断点，确认 frame=a0=保存后的 sp、旧 sp 在槽 2、CSR 槽偏移正确、sret 返回 S 模式且 sp 恢复。解释硬件自动保存与软件保存的边界。
T6 合成未支持异常与未知中断，检查诊断及 frame 不变；不能误把异常 cause 20 当访存指令并读取空 epc。
T7 local_intr_save/restore 前后开关状态保持，嵌套临界区不提前开中断；当前测试只针对单 hart。
输出只报告实际执行过的覆盖项，源码审计与动态验证分开记录，日志中的 PASS 必须来自断言结果。若测试脚本自身有错误，修复工具并如实记录，不修改被测实现迎合错误测试。
```
