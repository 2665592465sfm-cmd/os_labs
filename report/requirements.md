# Lab3 需求清单

依据 2026-10-28 正常访问的本届实验指导书与教师 `lab3.zip`。网页地址、抓取日期和哈希见 [course-sources.json](evidence/course-sources.json)，代码来源见 [source-audit.json](evidence/source-audit.json)。

## 1. 主线与范围

```text
Lab2 内存初始化与 Best-Fit
 → stvec / Trap 入口
 → SAVE_ALL 建立 frame
 → __alltraps 调用 C trap
 → interrupt_handler / exception_handler
 → RESTORE_ALL
 → sret 返回
```

本届必做编程任务为上下文恢复/入口桥接、中断/异常处理两个模块，并补齐 Lab2 依赖。指导书背景中的用户态切换介绍不等于已经实现用户栈切换；本实验按当前 S 模式内核验证。

## 2. 需求及验收

| 编号 | 行为要求 | 验收方式 |
|---|---|---|
| R01 | 原 Lab2 初始化和 Best-Fit 适配到本框架 | 编译、原内存自检、源码差异 |
| R02 | Lab3 中断临界区包装保持原样 | 源码审计、嵌套 SIE 动态测试 |
| R03 | frame 为原 SAVE_ALL 的 36 个槽，a0 指向 frame | 布局断言、GDB 观测 |
| R04 | 恢复所有可写整数寄存器，sp 最后恢复 | 补充寄存器测试、真实 timer GDB |
| R05 | 恢复保存的 sstatus/sepc，由 sret 返回 | 官方异常返回、GDB CSR/PC 检查 |
| R06 | timer 每次重置下一事件并 ticks+1 | 官方持续 timer 测试、默认运行 |
| R07 | 每 100 次中断输出统计，输出十次后关机 | 默认运行十行输出、QEMU 退出码 0 |
| R08 | 识别其余已有 IRQ，未知 IRQ 输出 frame | 官方测试、补充分类与 frame 不变断言 |
| R09 | 非法指令/断点输出原 EPC，按 16/32 位编码推进 | 官方测试、四类真实异常及后续执行标记 |
| R10 | 其他异常只诊断，不假定通用恢复 | 官方及补充 frame 不变检查 |
| R11 | 原测试、SAVE_ALL、接口、结构体、宏保持 | 逐文件 SHA256 和函数区域对比 |
| R12 | 保留 lab2/lab3 标记，填负责人学号 | 源码扫描 |
| R13 | 提交源代码、报告、prompt 和引用图片 | 文件清单、链接检查、分支与 ZIP 核对 |

## 3. 指导书与实际框架的适配决策

- Lab3 头文件没有 Lab2 新加的两个物理边界宏，使用 `KERNTOP-PHYSICAL_MEMORY_OFFSET` 和 `KERNBASE-PHYSICAL_MEMORY_OFFSET` 推导，保留本框架原定义。
- 教师 `trap.c` 定义 `TICK_NUM=100`，但未定义指导书引用的 `SHUTDOWN_AFTER`；在允许补全区域增加 `SHUTDOWN_AFTER=10`，按“统计输出次数”计数，不把它解释为十个中断。
- 教师评分实际检查的输出包括 `Breakpoint at`、`Illegal instruction at`、`Supervisor software interrupt`、`Unknown interrupt: cause 15`；保留原 Trap frame 打印格式。
- RV64GC 的本次恢复路径处理 16/32 位异常指令。更长编码只诊断，不宣称已实现扩展 ISA 指令恢复或安全用户取指。
- `sret` 返回特权级由保存的 SPP 决定。本次为 S→S，不强制清除保存的 SPP 来转 U。

## 4. 提交前的人员信息

申丰铭为组长。马翔宇、任诗清本次实际分工、AI 工具/模型及个人心得按组长要求保留“待补充”，不沿用 Lab2 的完成经历。
