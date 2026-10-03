# Lab1 补齐任务的实际执行规格

日期：2026-10-03。来源：用户要求“进行初步补齐和确认，要完美按照作业要求来，先不着急上传”，AI 据此拟定并实际执行。此文本不是原实验开始前的用户输入。

[PROMPT]
任务：核对 Lab1 两道练习、环境、报告模板、提示词和 Git 交付结构；补齐本地复核与终端截图准备。
操作要求：读取课程原文及实际项目；仅修改本地 lab1 的 code/report；保留原始内核实现、已有提示词历史和原始证据；在对应路径直接创建或修改文件。
输出要求：完整报告、真实提示词记录、可复现的终端截图操作脚本、复核日志及交付检查表。不得上传。

[RELY]
entry.S：la sp, bootstacktop；tail kern_init。
init.c：kern_init 调用 memset 和 cprintf，随后无限循环。
kernel.ld：BASE_ADDRESS=0x80200000；ENTRY(kern_entry)。
KSTACKSIZE=8192；PGSIZE=4096；SBI_CONSOLE_PUTCHAR=1。
现有 verify_boot.py 能启动真实 QEMU、连接 GDB，检查 11 项调试断言和 2 项串口/异常条件。
课程使用 Ubuntu/Linux 为主要环境；本机实际可用 Windows RV64 裸机工具链、QEMU 7.2.0、GDB 12.1 和 Python。
模板要求实际编译运行及评分结果；收到的 tools 只有 function.mk 和 kernel.ld，不包含 grade.sh。

[GUARANTEE]
保留已有内核接口：int kern_init(void) __attribute__((noreturn)); int cprintf(const char *fmt, ...); void cons_putc(int c); void sbi_console_putchar(unsigned char ch); uint64_t sbi_call(uint64_t sbi_type,uint64_t arg0,uint64_t arg1,uint64_t arg2)。本次不要求新增内核函数。
复核 Python 接口：main()；check_gdb(expression, label)。不得修改断言以掩盖失败。
增加 PowerShell Show-Checkpoint([string]$Message) 和终端截图引导脚本；可新增局部辅助函数，不能改动内核公开接口。

[SPECIFICATION]
## verify_boot.py main()
Pre-Condition：真实 RV64 内核已构建，QEMU/GDB 可执行，本机临时端口可用。
Post-Condition：复核 reset=0x1000、OpenSBI=0x80000000、kernel=0x80200000；验证栈、RA、输出和 S-mode ecall；保存真实原始日志。
Case 1：任何调试断言失败，返回失败并保留日志。
Case 2：评分脚本缺失，保留真实 make grade 错误，将官方评分状态标为待补。
Requirements：新增复核日志与原记录分开；不编造特权级读数，不声称本地检查是官方评分。
## check_gdb(expression, label)
Pre-Condition：expression 来自真实寄存器/符号，label 是可读的检查名。
Post-Condition：输出用于 GDB 的条件检查；失败退出非零，成功记录 PASS。
## Show-Checkpoint([string]$Message)
Pre-Condition：用户正在自己打开的终端中执行截图引导脚本，上一阶段输出仍可见。
Post-Condition：提示应保存的截图名称，并等待用户继续；不自动按键、截图或上传。
Requirements：截图应来自实际终端运行；不得把重排日志冒充终端截图。
## 报告和提交结构
Pre-Condition：模板、课程练习、组员信息和实际证据已可读取。
Post-Condition：六部分报告齐全；成员及分工正确；所有图片和证据链接存在；code 和 report 符合小组通知。
Requirements：区分已完成、需要教师材料、需要组长手动确认的事项；不把“准备好”写成“提交完成”。
