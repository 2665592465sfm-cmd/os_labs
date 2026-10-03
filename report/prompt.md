# Lab1 提示词与 AI 协作记录

日期：2026-10-03。工具：Codex 桌面应用；本次会话模型：GPT-6。

记录本次 Lab1 工作中的真实用户输入。AI 自主执行的文件读取、编译、调试与修复属于任务执行过程，没有写成组员逐轮输入的提示词。个人文件路径在提交版中仅保留文件名。

## 一、实际用户输入

### Prompt 1：实验完成请求

附带本地目录：`lab1`，包含 Makefile、kern、libs、tools。

```text
这是我们lab1的实验文档和实验代码：
http://8.135.34.58/lab2026/_book/ 完成
```

用途：依据真实代码和课程页面完成实验。执行结果：读取两个练习，准备构建、QEMU/GDB 调试、报告及证据。

### Prompt 2：提供模板和环境指南

附带：《实验报告模板(1).md》《0_environment_setup(2).md》《3_startdash.md》。

```text
是这个吗
```

随后对资料询问回复：

```text
我已经发了
```

用途：补充报告格式及课程环境说明。执行结果：按模板组织报告，环境说明以实际版本和日志为准。

### Prompt 3：成员与分工

```text
2412396 申丰铭 2411688马翔宇 2413992任诗清 分工你随意填写，但注意申丰铭是组长，也就是我，做的事情最多
```

用途：提供成员信息，指定组长承担主要任务。结果：申丰铭负责统筹、环境、练习2和整合；马翔宇负责练习1及原理分析；任诗清负责证据整理、提示词和报告校对。

## 二、按课程框架整理的复现提示词

以下为根据任务和真实接口整理的复现需求，未作为单独 Prompt 发送。

```text
[PROMPT]
任务：完成 Lab1 最小内核入口分析和 QEMU/GDB 启动验证。
操作要求：读取真实源码、课程练习和报告模板；在 lab1 分支 code/report 保存实际文件；保留内核现有功能，修正影响本次运行的构建与启动兼容问题。
输出要求：源代码、调试脚本、report.md、prompt.md、images 和可核对的真实日志。

[RELY]
entry.S：la sp, bootstacktop；tail kern_init。
init.c：memset(edata,0,end-edata)；cprintf；while(1)。
kernel.ld：BASE_ADDRESS=0x80200000；ENTRY(kern_entry)。
memlayout.h：KSTACKPAGE=2；KSTACKSIZE=KSTACKPAGE*PGSIZE。
mmu.h：PGSIZE=4096。
sbi.c：SBI_CONSOLE_PUTCHAR=1，通过 ecall 请求固件服务。
练习1解释 la 和 tail；练习2实际观察复位到内核首指令。

[GUARANTEE]
保留 kern_init、cprintf、cons_putc、sbi_console_putchar、sbi_call 等已有接口和框架。
允许新增独立主机验证工具，调整 Makefile 工具前缀、目标架构与启动参数。
交付可复现的 GDB 交互步骤和自动验证步骤。

[SPECIFICATION]
Pre-Condition：RV64 裸机工具链、QEMU virt 与 GDB 可用。
Post-Condition：观察 PC=0x1000、固件入口=0x80000000、内核入口=0x80200000；验证栈、尾跳转和输出。
Case 1：原参数无法向动态固件传入内核入口时，结合固件日志修正启动方式。
Case 2：GDB 不支持扩展寄存器时，用基本寄存器和 QEMU 异常日志验证，不能虚构读数。
Case 3：缺少官方 grade.sh 时，保存真实报错；本地检查需标明不是官方评分器。
Requirements：根据模板回答全部练习；区分源码语义、实测与解释；不捏造截图、历史或官方通过结果。
```

## 三、实际执行反馈与修正

1. 本机缺少实验工具：使用官方 Windows 可解压工具包，核对校验值，没有安装新的 WSL。
2. 原 `-device loader` 方式下 OpenSBI 下一跳为 0：改用 `-kernel` 传入入口地址。
3. GDB 未启用 XML 目标描述，不能读 `priv`：用 QEMU 异常日志核对 S-mode ecall。
4. 验证器漏匹配异常地址的 `0x` 前缀：修正规则，重新检查通过。
5. 缺少原始 `grade.sh`：保存实际报错，记录本地 13 项验证通过。

这些反馈由 AI 从真实工具输出中发现，执行过程中没有额外的逐轮用户提示词。

