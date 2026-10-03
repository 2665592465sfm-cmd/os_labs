# 操作系统实验报告

## 实验基本信息

| 项目 | 内容 |
|------|------|
| **实验名称** | Lab1：最小可执行内核与启动流程 |
| **小组成员** | 2412396-申丰铭（组长）、2411688-马翔宇、2413992-任诗清 |
| **完成日期** | 2026-10-03 |

### 小组分工

| 成员 | 负责的练习/模块 |
|------|----------------|
| 2412396-申丰铭（组长） | 统筹实验；配置交叉编译与仿真环境；完成练习2；修正启动参数；整合代码与验证脚本；管理实验分支和提交 |
| 2411688-马翔宇 | 负责练习1；分析入口汇编、链接脚本、内核栈与调用约定；整理 OS 原理对应关系 |
| 2413992-任诗清 | 整理测试日志、截图和提示词；协助复核练习2；检查报告格式与图片引用 |

报告分工：申丰铭负责整体逻辑、环境、调试过程及主稿整合；马翔宇负责入口汇编解释和知识点总结；任诗清负责证据整理和全文校对。

---

## 一、实验目的

1. 理解 RISC-V 从复位、执行固件到进入最小内核的过程，区分 QEMU、MROM、OpenSBI 与内核的职责。
2. 理解链接脚本如何确定内存布局与入口地址，掌握 C/汇编源文件经交叉编译生成 ELF 和裸镜像的流程。
3. 解释入口代码建立栈并移交 C 初始化函数的原因，理解 SBI 控制台输出调用链。
4. 用 QEMU/GDB 观察真实的 PC、SP、RA 变化，以调试证据验证源码分析和 AI 解释。

Lab1 两项练习分别要求源码分析与启动调试，没有要求实现新的内存管理、调度或中断功能。本次保留内核框架，补充运行兼容性、调试脚本、测试证据和报告。

---

## 二、实验环境

本次在 Windows 上运行 RISC-V 交叉编译器，生成 RV64 裸机内核 ELF 与镜像，并在 QEMU 的 RISC-V `virt` 机器中运行。ELF 头的 `Machine: RISC-V` 与入口 `0x80200000` 见 [elf-layout.log](evidence/elf-layout.log)。

课程的 Linux 准备章节以 Ubuntu/Linux 为主要实验环境，工具链章节也介绍 WSL 与 macOS 的使用。本次 Windows 是实际采用并验证过的工具组合；报告不把它写成 Ubuntu 测试记录。若课程要求统一在 Linux 复现，应在对应环境另行验证。

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

完整版本输出见 [environment.log](evidence/environment.log)。工具来自 xPack 官方 GitHub Releases 与 QEMU 官网列出的 Windows 构建站点，下载后核对发布方 SHA256/SHA512。工具保存在本地工作目录，仓库只保存实验源代码和交付文件。

| 成员 | AI 编程工具 | 底层模型 | 备注 |
|------|------------|---------|------|
| 2412396-申丰铭 | Codex 桌面应用 | GPT-6（本次会话） | 组长提供资料，工具直接读取项目、构建和调试 |
| 2411688-马翔宇 | 未提供个人使用记录 | 未提供 | 本报告的 AI 会话由组长发起 |
| 2413992-任诗清 | 未提供个人使用记录 | 未提供 | 本报告的 AI 会话由组长发起 |

真实输入记录见 [prompt.md](prompt.md)。最初请求没有使用四段式；在组长要求补齐后，AI 拟定四段式任务规格并据此实际重新构建、调试与复核，全文保存在 [task-spec.md](evidence/followup/task-spec.md)。记录区分用户原文、事后复现需求和这次真实执行规格。

---

## 三、实验整体逻辑分析

### 3.1 本章节的逻辑主线

本章解决的问题是：没有已有操作系统替我们分配栈、创建进程并调用 `main`，如何让最小内核开始执行并输出信息。

```text
QEMU 预先装入固件与内核镜像
 → CPU 复位，PC=0x1000，执行 MROM 复位桩
 → PC=0x80000000，进入 OpenSBI
 → OpenSBI 完成环境设置，以 S-mode 进入 0x80200000
 → kern_entry 设置内核栈，tail 跳入 kern_init
 → kern_init 初始化 BSS 范围并调用 cprintf
 → 格式化输出通过 SBI ecall 请求固件输出字符
 → 内核进入 while(1) 无限循环
```

需要区分镜像装入与控制权移交：本次 `-kernel bin/ucore.img` 模式下，CPU 尚停在 `0x1000` 时，GDB 已读到 `0x80200000` 上的内核指令。因此镜像由 QEMU 在执行前装入，OpenSBI 主要进行固件初始化、确定下一阶段地址与特权级，并移交控制权。

### 3.2 功能的逐步实现

1. **确定布局和入口。** `kernel.ld` 设置基址并组织 `.text`、`.rodata`、`.data` 等段；先确定布局，代码的地址引用才能与装载位置相符。
2. **编译与生成镜像。** `.c`、`.S` 编译为 RV64 目标文件，链接生成含调试信息的 `bin/kernel`，再由 `objcopy -O binary` 生成 `bin/ucore.img`。
3. **建立 C 运行环境。** `entry.S` 设置 SP 后跳到 `kern_init`；先有栈，C 函数才能安全保存寄存器和调用其他函数。
4. **实现可见输出。** 调用链为 `kern_init → cprintf → vcprintf → vprintfmt → cputch → cons_putc → sbi_console_putchar → ecall`。内核负责格式化，OpenSBI 负责控制台服务。
5. **逐段验证。** 用单步观察复位桩，在固件和内核入口设断点，检查栈、尾跳转和 SBI 调用，使结论能对应源码、机器指令和运行日志。

---

## 四、实验内容与实现

### 功能模块：构建、启动与本地验证

**负责人：** 2412396-申丰铭。

#### 模块功能描述

原框架已提供以下接口，本实验分析并验证它们，保留其原有实现：

```c
int kern_init(void) __attribute__((noreturn));
int cprintf(const char *fmt, ...);
int vcprintf(const char *fmt, va_list ap);
void cons_putc(int c);
void sbi_console_putchar(unsigned char ch);
uint64_t sbi_call(uint64_t sbi_type, uint64_t arg0,
                  uint64_t arg1, uint64_t arg2);
void *memset(void *s, char c, size_t n);
```

| 文件 | 实际改动 |
|------|----------|
| `code/Makefile` | 明确 RV64 架构和 ABI；允许覆盖工具前缀；GDB 使用同一前缀；用 `-kernel` 向动态固件传入入口；增加本地 `check` |
| `code/tools/boot.gdb` | 提供复位、固件、内核入口和栈初始化的交互式调试步骤 |
| `code/tools/verify_boot.py` | 真正启动 QEMU 并连接 GDB，检查启动路径，保存日志与镜像哈希 |
| `code/run-lab.ps1` | 临时配置 Windows 工具路径，支持构建、运行、调试与验证 |
| `code/review-lab.ps1` | 实际执行终端复核，在构建、运行、检查和评分结果处提示用户手动保存截图 |
| `code/README.md` | 提供 Linux/WSL 和本次 Windows 环境复现方法 |

#### 最终提示词

最初任务是依据本地 Lab1 和课程链接完成实验。组长随后要求按作业要求补齐；本次 AI 拟定并实际采用四段式规格，重新构建、运行和检查。下面摘录这次执行规格，全文及来源见 [task-spec.md](evidence/followup/task-spec.md) 和 [prompt.md](prompt.md)，不把它写成原实验开始前的用户输入。

````markdown
[PROMPT]
核对 Lab1 两道练习、环境、报告模板、提示词和 Git 交付结构；补齐本地复核与终端截图准备。直接修改实际文件，保留原始内核与证据，不上传。
[RELY]
以提供的 entry.S、init.c、kernel.ld、Makefile 与 libs 为准。
BASE_ADDRESS=0x80200000，PGSIZE=4096，KSTACKSIZE=8192。
[GUARANTEE]
保留 int kern_init(void)、int cprintf(const char *fmt, ...)、void cons_putc(int c)、void sbi_console_putchar(unsigned char ch) 等已有接口。
复核 verify_boot.py 的 main()、check_gdb(expression, label)。
增加 PowerShell Show-Checkpoint([string]$Message) 及截图引导脚本。
[SPECIFICATION]
Pre-Condition：RV64 裸机工具链、RISC-V virt QEMU 与 GDB 可用。
Post-Condition：观察 0x1000、0x80000000、0x80200000；验证栈、尾跳转及启动输出。
Case 1：调试断言失败，保留日志并退出失败。
Case 2：缺少官方评分脚本，记录实际报错，保留待确认状态。
Requirements：以实际代码和运行结果为准；缺失评分器不能写成通过；不得捏造提示词历史或截图。
````

#### 实现迭代过程

**第一阶段：源码与工具链。** 原环境未配置可用的 WSL/RISC-V GCC/QEMU，使用官方可解压工具包建立本机实验环境。Makefile 增加 RV64 参数，避免工具链默认 RV32 设置产生架构错误。GCC 编译、链接和镜像转换成功。

**第二阶段：启动兼容。** 原目标使用 `-device loader,file=bin/ucore.img,addr=0x80200000`。本次 QEMU 7.2.0 的 OpenSBI 动态固件没有收到下一阶段地址，显示 `Domain0 Next Address : 0x0000000000000000`，GDB 等待内核断点超时。改用 `-kernel bin/ucore.img` 后，下一跳变为 `0x80200000`，断点成功触发。改动针对启动参数，没有增写内核启动逻辑。

**第三阶段：验证工具。** xPack GDB 提示 `XML support was disabled at compile time`，基本寄存器和断点可用，但不能读动态目标描述中的 `priv`。因此用 GDB 的 PC/SP/RA 观察执行位置，用 QEMU 异常日志验证 `supervisor_ecall` 和原因 9。之后修正验证器漏匹配地址 `0x` 前缀的问题，全部检查通过；此处是日志解析问题，并非内核错误。

**第四阶段：按统一提示词框架复核。** 原始用户提示词未使用课程四段式，因此最初保存的规格只是事后整理。组长授权补齐后，先形成包含真实接口和前后置条件的四段式执行规格，再据此重新构建、执行 `make qemu` 和 QEMU/GDB 验证；13 项检查全部通过，内核镜像哈希与第一轮相同。新增终端截图引导脚本，尚待组长实际保存终端截图。原始用户输入与这次 AI 拟定规格分开记录。

**最终结果：** 重新构建后，`make qemu` 输出启动信息；本地 `make check` 的 13 项检查通过。原始 `tools/grade.sh` 缺失，官方评分无法运行，没有报告为通过。

### 练习1：理解内核启动中的程序入口操作

**负责人：** 2411688-马翔宇。

```asm
kern_entry:
    la sp, bootstacktop
    tail kern_init
```

**`la sp, bootstacktop` 的操作与目的。** `la` 是取得地址的伪指令，将符号 `bootstacktop` 的地址写入 SP，不是读取该地址上存放的值。`bootstack` 通过 `.space KSTACKSIZE` 预留 8192 字节，栈从高地址向低地址增长，因此 SP 初始化为区域上界。

实测 `bootstack=0x80201000`、`bootstacktop=0x80203000`，相差 `0x2000` 即 8192 字节。内核刚开始执行时 SP 仍为固件栈地址 `0x80046ef0`；执行 `la` 后为 `0x80203000`。这建立内核自己的栈，使 C 函数能够保存寄存器、使用局部变量和调用函数，地址也满足栈对齐要求。

本次反汇编为：

```asm
0x80200000: auipc sp,0x3
0x80200004: mv    sp,sp
0x80200008: j     0x8020000a <kern_init>
```

`la` 展开为 PC 相对地址构造。这里低位偏移恰为 0，`addi sp,sp,0` 被显示为 `mv sp,sp`。机器指令受工具链和链接松弛影响，应检查当前镜像，而不能只凭伪指令名称推断。

**`tail kern_init` 的操作与目的。** `tail` 把控制权交给 `kern_init`，不为本次跳转写入新返回地址。入口汇编已经完成建栈，而 `kern_init` 为 `noreturn` 并最终无限循环，因此无需返回入口代码。

本次它被链接松弛为两字节的 `j`。执行前后 RA 都为 `0x800097dc`，PC 从 `0x80200008` 变为 `0x8020000a`，验证其没有改写 RA。`tail` 不负责初始化栈，其行为与普通 `call` 不同。

### 练习2：使用 GDB 验证启动流程

**负责人：** 2412396-申丰铭；任诗清协助整理证据。

#### 调试过程

在两个终端分别运行 `make debug` 和 `make gdb`。`-S` 让 CPU 执行前暂停，`-s` 开放本机 1234 端口；GDB 读取 ELF 符号后连接 QEMU。交互步骤为：

```gdb
file bin/kernel
set architecture riscv:rv64
target remote localhost:1234
info registers pc
x/10i 0x1000
x/4wx 0x80200000
thbreak *0x80000000
continue
thbreak *0x80200000
continue
disassemble kern_entry
si
si
info registers sp
si
info registers pc ra
```

交互脚本是 `code/tools/boot.gdb`。自动验证使用空闲本机端口避免冲突，[gdb.log](evidence/gdb.log) 和 [boot-session.gdb](evidence/boot-session.gdb) 保存本次会话。后者含本次临时端口，重新测试应运行验证器生成新会话。

#### 最初执行的指令位于什么地址，完成什么功能？

GDB 连接后 PC 为 `0x1000`。前六条指令属于 QEMU `virt` 的 MROM 复位桩，尚未执行位于 `0x80000000` 的 OpenSBI：

| 地址 | 指令 | 功能 |
|------|------|------|
| `0x1000` | `auipc t0,0x0` | 取得复位桩地址，作为读取后续常量的基准 |
| `0x1004` | `addi a2,t0,40` | 设置动态固件信息指针，本次 `a2=0x1028` |
| `0x1008` | `csrr a0,mhartid` | 读取 hart 编号作为参数，本次为 0 |
| `0x100c` | `ld a1,32(t0)` | 读取设备树地址，本次为 `0x87e00000` |
| `0x1010` | `ld t0,24(t0)` | 读取下一阶段固件地址，本次为 `0x80000000` |
| `0x1014` | `jr t0` | 跳入 OpenSBI，移交控制权 |

单步后 PC 顺序是 `0x1004 → 0x1008 → 0x100c → 0x1010 → 0x1014 → 0x80000000`。这段代码准备参数并进入固件，没有完成所有设备初始化。复位地址由硬件实现决定，不能把 QEMU 的 `0x1000` 推广为所有 RISC-V 处理器固定地址。

#### 固件到内核第一条指令

观察固件入口后，设置 `thbreak *0x80200000` 并继续。断点停在 `entry.S` 的第一条指令，测得：

```text
pc=0x80200000 <kern_entry>
sp=0x80046ef0，ra=0x800097dc
a0=0，a1=0x87e00000
```

OpenSBI 日志显示 `Domain0 Next Address=0x80200000`、`Domain0 Next Mode=S-mode`，与入口断点和后续 S-mode ecall 证据一致。

也按练习提示设置了 `watch -l *(unsigned int*)0x80200000`。监视点没有触发，直接到达内核断点；在初始 `PC=0x1000` 时内存首字已为 `0x00003117`，与当前镜像一致。因此本次内核由 QEMU 执行前装入，不能据此报告“OpenSBI 加载瞬间”。

#### C 初始化和 SBI 输出

`kern_init` 调用 `memset(edata,0,end-edata)` 清理 BSS 范围，再调用 `cprintf`。本次 `--gc-sections` 去掉未引用内容，最终 `edata=end=0x80203008`，BSS 范围长度为 0。因此本次没有验证非空 BSS 的逐字节清零；代码仍保留一般内核启动所需的初始化语义。

在 `cprintf` 入口，`a0` 指向 `"%s\n\n"`，`a1` 指向 `"(THU.CST) os is loading ...\n"`。在首字符 `ecall` 前，`a7=1` 为旧版 SBI 控制台调用号，`a0=0x28` 为字符 `(`。单步后 PC 进入固件异常入口 `0x80000408`，处理后返回 `0x8020047e`。

QEMU 异常日志记录：

```text
cause:0000000000000009, epc:0x000000008020047a,
tval:0x0000000000000000, desc=supervisor_ecall
```

它证明内核通过 S-mode 环境调用请求固件服务。最后串口输出 `(THU.CST) os is loading ...`，内核进入无限循环。停止输出符合框架预期，此时尚无 shell 或调度器。

#### 拓展：现代笔记本启动流程

普通 x86 笔记本通常由 CPU 复位进入主板固件，UEFI 初始化必要硬件并选择启动项，再执行引导程序，最后装入系统内核并移交控制权。它与实验共同体现分阶段引导思想，但复位地址、固件接口、介质和内核格式不同。实验由 QEMU 直接装入镜像，未实现从真实磁盘查找、读取和校验内核的完整流程。

课程 Lab1 页面没有单独的 Challenge 编程任务，因此本次没有额外添加 Challenge 实现。

---

## 五、测试与验证

以下图片是**浏览器中展示真实命令日志的截图**。内容读取自已保存的实际运行日志；它们不是 Linux 桌面或终端窗口截图。原始文本同时保存在 `evidence`，便于核对上下文。

为补齐模板中的直接测试运行截图，已准备 `code/review-lab.ps1`。当前终端窗口截图尚未保存，不能将本节的日志展示图标成终端截图。

### 5.1 编译与运行

实际执行 `make GCCPREFIX=riscv-none-elf-`，8 个源文件编译成功，链接和镜像转换成功。`make qemu` 输出固件信息和内核字符串，经 Ctrl+A、X 退出后命令返回 0。

![编译与 QEMU 实际运行日志](images/build-and-qemu.jpg)

原始证据：[build.log](evidence/build.log)、[make-qemu.log](evidence/make-qemu.log)、[elf-layout.log](evidence/elf-layout.log)。

### 5.2 复位、内核入口和栈

![GDB 复位与固件入口日志](images/gdb-reset.jpg)

![GDB 内核入口、栈和尾跳转日志](images/gdb-kernel.jpg)

原始证据：[gdb.log](evidence/gdb.log)、[kernel-symbols.log](evidence/kernel-symbols.log)、[entry-disassembly.log](evidence/entry-disassembly.log)。

### 5.3 本地自动检查和 SBI 证据

13 项检查包括：复位 PC；复位时镜像已存在；进入 OpenSBI；进入内核；栈顶地址；栈大小；尾跳转不写 RA；到达 `cprintf`；SBI 参数；进入固件异常入口；返回内核；启动字符串；S-mode ecall 原因 9。全部通过。

![13 项本地检查和 SBI 调用证据](images/local-checks.jpg)

原始证据：[local-check.log](evidence/local-check.log)、[traps.log](evidence/traps.log)、[summary.json](evidence/summary.json)。本次镜像 SHA256：

```text
997228412f63ece956133e3582821b2c5af2014b758ef19fd8ad26c080d38664
```

### 5.4 官方评分器缺失

实际执行 `make grade` 报错：

```text
sh: can't open 'tools/grade.sh': No such file or directory
make: *** [Makefile:203: grade] Error 2
```

![官方评分器缺失的实际输出](images/grade-unavailable.jpg)

原始证据：[official-grade-unavailable.log](evidence/official-grade-unavailable.log)。收到的代码未提供评分脚本，所以不能宣称官方评分通过；上述 `make check` 是补充的本地验证。若教师随后提供原版评分器，需另行检查。

### 5.5 按四段式执行的补齐复核

在补齐规格制定后，实际再次执行 `make grade`、构建、`make qemu` 和 `make check`。构建及运行成功，13 项本地检查通过，`make grade` 仍因脚本缺失返回 2。组长确认没有其他代码包或单独评分脚本。课程当前的 Lab1 文件树在 `tools` 下也只列出 `function.mk` 和 `kernel.ld`；这说明需要向教师确认 Lab1 是否适用统一模板中的评分项，而不能借用其他实验或架构的评分脚本。

复核证据：[build.log](evidence/followup/build.log)、[qemu-run.log](evidence/followup/qemu-run.log)、[local-check.log](evidence/followup/local-check.log)、[gdb.log](evidence/followup/gdb.log)、[official-grade.log](evidence/followup/official-grade.log)、[execution.json](evidence/followup/execution.json)。`execution.json` 保存执行规格 SHA256，可与本次 [task-spec.md](evidence/followup/task-spec.md) 对照。

---

## 六、实验总结与收获

### 对操作系统的理解

| 实验知识点 | 对应 OS 原理 | 含义、关系与差异 |
|------------|-------------|----------------|
| 分阶段引导 | 系统启动 | 先准备环境再移交控制权；本实验直接装入镜像，未完整覆盖磁盘引导 |
| 链接地址、装载地址 | 程序装载和地址空间 | 布局应与实际物理位置匹配；这里尚无进程虚拟地址空间 |
| 内核栈与 SP | 函数调用和执行上下文 | 栈存放调用信息与局部数据；未涉及各进程独立栈与切换 |
| OpenSBI 与 ecall | 特权级和异常 | S-mode 内核请求 M-mode 固件服务；不同于 U-mode 用户请求 S-mode 内核的系统调用 |
| BSS 初始化 | C 运行环境 | 零初始化数据一般需运行前清零；本次实际范围为空，验证有相应边界 |
| 格式化与串口输出 | I/O 抽象 | 上层格式化、下层输出字符；本实验依赖固件服务，未建立完整驱动系统 |
| 断点、单步、反汇编 | 系统调试 | 源码体现意图，指令与寄存器体现执行；伪指令展开受工具链影响 |

`ENTRY(kern_entry)` 声明 ELF 入口，不能单独保证裸镜像首字节属于哪个段，因此还要核对段布局和反汇编。本次两者均对应 `0x80200000`。`ALIGN(0x1000)` 是向上对齐到 4096 字节边界，不是对齐到 `2^0x1000`。

裸二进制没有 ELF 那样的入口头，其入口依赖启动参数和布局约定。`.bss` 的 NOBITS 数据通常不直接占据输出文件字节；镜像是否包含零填充取决于实际可加载段。本次 8 KiB 栈位于 `.data`，体现在镜像中，实际 BSS 范围为空。

本实验未覆盖的重要 OS 原理包括：物理页分配与回收、多级页表、虚拟内存、进程/线程管理、抢占调度、中断框架、同步互斥、用户态系统调用、文件系统与持久存储。能启动并打印信息的最小内核，还没有这些完整系统功能。

### AI 协作开发的经验

先读取真实框架和要求，再用实际工具验证解释。仅凭模板假设存在 `make grade`，或把镜像装载一概归给 OpenSBI，都可能与当前代码和运行方式不符。

错误输出可以定位问题层次：固件下一跳为 0 指向启动参数；GDB XML 提示说明寄存器接口受限；异常地址匹配失败属于验证器解析。修改后运行对应检查，比只改写自然语言描述更可靠。

提示词记录应保留真实输入，复现需求可另外整理；报告需逐项核对地址、函数名、截图和测试边界。不能把整理的文字冒充实际历史，也不能把本地检查写成官方评分结果。

本次补齐把四段式规格放在重新验证之前，并按规格实际执行。今后的实验应在首次实现前就准备好四段式提示词，使任务、依赖、接口与行为规格能直接指导开发。

### 参考资料

1. [课程 Lab1 练习](http://8.135.34.58/lab2026/_book/lab1/lab1_2_1_exercise.html)。
2. [课程报告要求](http://8.135.34.58/lab2026/_book/lab1/lab1_5_requirement.html)。
3. 组长提供的报告模板、环境说明和原始 Lab1 源码。
4. [QEMU 官方下载说明](https://www.qemu.org/download/)及 [Windows 构建档案](https://qemu.weilnetz.de/w64/2022/)。
5. [xPack 官方工具链发行版](https://github.com/xpack-dev-tools/riscv-none-elf-gcc-xpack/releases/tag/v11.3.0-1)。
6. [课程 Linux 环境说明](http://8.135.34.58/lab2026/_book/lab0/0_Linux.html)、[提示词结构](http://8.135.34.58/lab2026/_book/lab0.5/3_prompt_structure.html)、[Lab1 文件组成](http://8.135.34.58/lab2026/_book/lab1/lab1_2_2_file.html)。

