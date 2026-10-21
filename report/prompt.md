# Lab2 最终提示词汇总

这些内容是按本次功能需求整理、经代码与测试证据复核的最终提示词和行为规格，不是初次生成代码前的逐轮原始对话记录。P3/P4、P5/P6 分别区分实现与测试任务；P7 记录源码调试任务。每份提示词覆盖一个可独立验收的任务，规格描述可观察的行为和不变量。

## P1：物理内存探测和 Page 初始化

```text
[PROMPT]
任务：在 kern/mm/pmm.c 的 lab2 function1 标记处实现 static void page_init(void)。必须修改实际文件，保留 lab2 注释，将 YOUR CODE 替换为 2412396。按本项目的地址转换约定实现，不硬编码空闲页数量，不改变设备树解析器或测试程序。

[RELY]
工程实际接口：get_memory_base()/get_memory_size() 返回 uint64_t；pmm_manager 已完成 init；init_memmap(struct Page *, size_t) 注册连续空闲页；pa2page(uintptr_t) 将物理地址转换为描述符。
struct Page 包含 ref、flags、property、page_link；通过 SetPageReserved、set_page_ref 和 list_init 初始化。PGSIZE=4096，nbase=DRAM_BASE/PGSIZE，DRAM_BASE=0x80000000。
PHYSICAL_MEMORY_END=0x88000000，PHYSICAL_MEMORY_OFFSET=0xffffffff40000000；end 是链接器提供的内核结束虚拟地址；PADDR 依赖 va_pa_offset。pages 指向描述符数组的虚拟地址，npage 是物理页号上界而非页面数量。

[GUARANTEE]
实现 static void page_init(void)。不得改动 pmm.h、memlayout.h、mmu.h 中原有结构布局、宏及公开接口，不得改动 DTB 解析器、原始测试和评分脚本。本任务不改变 pmm_init/init_memmap 的既有接口；允许新增本模块内的 static 辅助函数。

[SPECIFICATION]
## page_init
Pre-Condition：在 Sv39 启用、BSS 清零及 dtb_init 完成后执行；当前物理页管理器为空。当前平台以固定 DRAM_BASE 为起点并使用单段 RAM。
Post-Condition：va_pa_offset 正确；npage 取设备树内存末端和框架可管理末端的较小者的完整页上界；pages 在 end 后按页对齐；描述符覆盖 [nbase,npage)，并正确预留固件、内核、对齐空间和描述符数组；仅剩余完整空闲页交给管理器。
Case 1：有效范围且管理元数据放得下时，每个可管理物理页均有唯一描述符；固件、内核、元数据和不完整页保持不可分配；只登记其余完整页，空闲计数与该区间长度一致。
Case 2：零大小、地址加法溢出、不符合固定起点或描述符空间不足时 panic，不能先写越界内存。
Case 3：无完整空闲页时不调用 init_memmap，不传入长度 0。
Requirements：打印探测范围、描述符大小、空闲起点及页数；不混用物理地址、虚拟地址和描述符下标；保持原评分脚本不变。
```

## P2：Best-Fit 模块及注册

```text
[PROMPT]
任务：在 kern/mm/best_fit_pmm.c 的 lab2 function2-2 标记位置实现完整 Best-Fit 物理页管理模块，并在 pmm.c 的 init_pmm_manager 中将默认实例切换为 best_fit_pmm_manager。模块必须协同完成状态初始化、空闲页登记、连续分配、释放合并、空闲统计和检查注册；核心目标是选择满足请求的最小空闲连续块。
操作约束：修改工程中的真实文件，保留 lab2 注释，把 YOUR CODE 替换为实际负责人的学号；本次已有实现归属 2412396。禁止修改已有 basic_check/best_fit_check 的任何函数正文、测试断言和评分脚本；禁止修改 pmm.h、memlayout.h、mmu.h、list.h 中已有接口、宏定义和数据结构。只允许补全标记位置、切换默认实例，以及在独立文件中新增测试；本模块可自行新增 static 辅助函数和私有状态。
验证要求：保留原有两项检查并运行 make qemu、make grade；额外用断言验证最小适配、分割、前后合并、分配失败状态不变和页数恢复。不能删除断言或改写测试输出使其通过。

[RELY]
struct pmm_manager 的成员：const char *name；void (*init)(void)；void (*init_memmap)(struct Page *, size_t)；struct Page *(*alloc_pages)(size_t)；void (*free_pages)(struct Page *, size_t)；size_t (*nr_free_pages)(void)；void (*check)(void)。
struct Page 的现有字段：int ref；uint64_t flags；unsigned int property；list_entry_t page_link。PageProperty 表示空闲块头；块头 property 为连续空闲页数。可用宏和函数：PageReserved、PageProperty、SetPageProperty、ClearPageProperty、set_page_ref、le2page 及 list.h 双向链表接口；现有 pages/npage/nbase 表示描述符及页号边界。
free_area_t 已含 list_entry_t free_list 和 unsigned int nr_free。框架测试会临时保存、重置和恢复 free_list/nr_free，因此这两个名字必须对应本模块的真实权威状态。不要依赖测试不可见的第二套状态。现有 basic_check/best_fit_check 只读作验收条件，不可修改。

[GUARANTEE]
必须实现或注册以下接口，签名与现有工程一致：
static void best_fit_init(void);
static void best_fit_init_memmap(struct Page *base, size_t n);
static struct Page *best_fit_alloc_pages(size_t n);
static void best_fit_free_pages(struct Page *base, size_t n);
static size_t best_fit_nr_free_pages(void);
const struct pmm_manager best_fit_pmm_manager;
修改 static void init_pmm_manager(void) 的默认选择；其原有职责保持不变。
既有 static void best_fit_check(void) 绑定到 check 回调，正文不变。允许自行增加 static 内部辅助函数，其命名和实现方式不作规定。

[SPECIFICATION]
## best_fit_init
Pre-Condition：初始化一个尚未登记物理页、没有活动分配的管理器实例。
Post-Condition：空闲集合为空、空闲页计数为 0，状态能够被后续接口及原框架测试一致观察。

## best_fit_init_memmap
Pre-Condition：管理器已初始化；base 起的 n>0 个描述符对应合法、连续、处于保留状态且尚未登记的可用物理页。
Post-Condition：恰有这 n 页转为可分配、引用计数为 0；空闲总数增加 n，先前状态不丢失；登记后的空闲区间无重叠，元数据与页面范围一致；物理相邻的空闲区间可以合为同一连续块。
Requirements：n==0 违反接口契约，保留相应断言；不能因登记管理器而改变 Page 布局或将其他保留页变为空闲。

## best_fit_alloc_pages
Pre-Condition：n>0；空闲块、块头属性和总数一致。
Post-Condition：成功时返回长度至少为 n 的最小候选空闲块的起点，向调用方交付恰好 n 个连续页；活动分配之间及与剩余空闲页之间不重叠，引用计数为 0，空闲计数减少 n。
Case 1：有长度恰为 n 的候选，整块交付；交付区不再带有空闲块头属性。
Case 2：最小候选长度大于 n，交付其前 n 页，剩余页仍可分配，元数据与剩余长度一致。
Case 3：总空闲数不足，或虽有足够总量却没有长度至少 n 的连续块，返回 C 空指针 NULL；链表连接、空闲属性和计数均保持原状。
Requirements：n==0 违反契约，应由既有断言拒绝；不要求特定的查找数据结构。相同最小长度候选均满足 Best-Fit，不能以返回第一个可用大块替代最小块选择。

## best_fit_free_pages
Pre-Condition：base 起 n>0 页是合法的、未重复归还的已分配连续物理页，位于描述符范围内；调用者不传入保留页或已空闲的页面。
Post-Condition：输入 n 页可重新分配、引用计数为 0；原有活动分配不受影响；空闲数只增加一次 n。与前驱、后继或两侧相邻空闲区间均能合并，空闲块之间无重叠且长度准确。
Case 1：两侧均不相邻，产生独立空闲块。Case 2：仅一侧相邻，形成联合区间。Case 3：两侧相邻，形成覆盖三者的连续区间。
Requirements：保留 n>0、描述符范围和不可释放保留/空闲块头的断言；不把这些局部断言宣称为任意野指针或所有错误部分释放的完整检测。

## best_fit_nr_free_pages
Pre-Condition：管理器已初始化，空闲状态有效。
Post-Condition：返回当前空闲页总量，与所有空闲块长度之和相等；查询不改变任何管理状态。

## best_fit_pmm_manager / init_pmm_manager
Pre-Condition：上述回调与原 best_fit_check 已可用。
Post-Condition：注册结构的六项回调均对应本模块；默认启动输出 best_fit_pmm_manager，并通过该实例执行分配和检查；选择其他分配器的独立演示不改变默认验收目标。
```

## P3：Buddy System 实现和接入

```text
[PROMPT]
任务：在 kern/mm/buddy_pmm.c/.h 从零实现 Buddy System 页分配器，注册 buddy_pmm_manager，以 PMM=buddy 接入构建；默认仍为 Best-Fit。必须修改项目文件；不要把已有 First-Fit 换名冒充 Buddy。

[RELY]
复用 pmm_manager、struct Page、链表、page2ppn、nbase/npage 和保留/空闲标志。可管理 RAM 最多 128 MiB、32768 个 4 KiB 页；初始空闲区起点可能不是大块对齐地址，长度也可能不是 2 的幂。接口允许 alloc_pages 返回至少 n 页。

[GUARANTEE]
static void buddy_init(void);
static void buddy_init_memmap(struct Page *base, size_t n);
static struct Page *buddy_alloc_pages(size_t n);
static void buddy_free_pages(struct Page *base, size_t n);
static size_t buddy_nr_free_pages(void);
const struct pmm_manager buddy_pmm_manager;
在 Makefile/pmm.c 提供独立选择。不得改变已有 Page/pmm_manager 的字段、原有宏和公开接口，不得修改 First-Fit/Best-Fit 的原始检查或评分脚本。新增阶数常量、私有结构/标记和 static 辅助函数仅限本模块内部。实现与测试保持独立函数和职责。

[SPECIFICATION]
## buddy_init
Pre-Condition：没有活动 Buddy 分配，准备初始化实例。
Post-Condition：各阶空闲状态为空，空闲总数为 0。
## buddy_init_memmap
Pre-Condition：输入保留页的合法连续范围，n>0。
Post-Condition：将整个可用范围分解为尽量大的、按物理页号对齐的 2^order 块；不丢失起止零碎页，不触及保留区。
## buddy_alloc_pages
Pre-Condition：n>0。
Post-Condition：成功时返回覆盖请求、长度为最小适配 2 的幂且按物理页号对齐的连续块，与其他活动分配互斥；计数按实际块长扣减，未交付的页仍可管理。无合适块或超出最大阶时返回 NULL，原状态保持不变。
## buddy_free_pages
Pre-Condition：base 为本分配器返回的块头，n 为原请求或对应实际块大小；不支持部分释放。
Post-Condition：校验实际块边界和已分配状态；与相同阶且空闲的真正伙伴递归合并；只增加实际释放页数；绝不把只是相邻的非伙伴误合并。
## buddy_nr_free_pages
Pre-Condition：实例已初始化。
Post-Condition：返回所有空闲阶链表所表示的实际页数之和；不改变状态。
## buddy_pmm_manager
Pre-Condition：回调和独立 buddy_check 可用。
Post-Condition：注册所有回调；仅选择 PMM=buddy 时使用该实例，默认仍为 Best-Fit。
Requirements：伙伴关系以物理页号为准，不以 Page 数组偏移误代物理对齐；保留参数、块头和分配状态断言；单 hart 启动期使用，不宣称支持并发。
```

## P4：Buddy System 独立测试

```text
[PROMPT]
任务：针对 P3 的 Buddy 分配器，在 buddy_pmm.c 内编写 buddy_check 和独立状态审计，接入 manager.check。用真实 QEMU 运行，不能只打印 PASS。

[RELY]
Buddy 以 2^order 页为单位实际分配，初始范围不一定按最大阶对齐；PageProperty 仅标识空闲块头；page_link 在已分配页中可临时作为测试持有队列；通过 pmm_manager 接口获取计数。

[GUARANTEE]
提供 static void buddy_check(void) 和 static void audit_buddy(void)；前者执行场景检查并归还测试资源，后者只验证不变量而不修改状态。不得改动原始 Best-Fit 检查或评分文件，不得为迎合测试修改分配接口。每个 PASS 之前必须有相应断言。

[SPECIFICATION]
## buddy_check
Pre-Condition：Buddy 已完成真实物理页初始化，当前无其他用户分配。
Post-Condition：测试释放所有临时块、恢复初始空闲页数和最大可合并状态。
Case 1：3 页/9 页请求分别扣减 4/16 页，并验证物理页号对齐、拆分和递归合并。
Case 2：固定随机种子的 1200 次混合分配/释放，维护至少 32 个活动槽；检查区间不重叠及实际内存首尾数据未损坏。
Case 3：逐页耗尽全部空闲页，验证 NULL、计数为 0，再全部归还并审计。
Case 4：超过最大阶请求返回 NULL，状态不变。
## audit_buddy
Pre-Condition：分配或释放操作已经返回，管理器不处于修改中间状态。
Post-Condition：检查空闲块长度、对齐、界限、区间互斥、计数之和，以及不存在仍可合并的同阶伙伴；不变量违反时断言失败，否则不改变任何管理状态。
```

## P5：简化 SLUB 对象分配器

```text
[PROMPT]
任务：从零新增 kern/mm/slub.c/.h，提供简化的 SLUB 风格两层分配，接入现有内核的测试过程。必须实现真实 kmalloc/kfree，而非只描述设计。

[RELY]
底层 alloc_pages/free_pages/nr_free_pages 支持 Best-Fit、First-Fit 或 Buddy；虚实转换用 page2pa+va_pa_offset、PADDR 和 pa2page。物理页 PGSIZE=4096；struct Page 是页描述符，本工程大小为 40 字节，不能混淆两者。可以在已分配页内存放 slab 头、位图和链表，但不能破坏 Page 描述符和底层计数。

[GUARANTEE]
实现 void *kmalloc(size_t size)、void kfree(void *ptr)，在 slub.h 声明；缓存初始化可自行设计为 static 辅助函数。不得更改现有 Page/pmm_manager 布局、物理页分配接口及框架宏、断言和评分脚本；仅允许新增本模块私有 slab 元数据和大小类定义。测试 void slub_check(void) 作为 P6 的独立验收任务编写。

[SPECIFICATION]
## kmalloc
Pre-Condition：物理页管理器已初始化；仅单 hart 启动期调用。
Post-Condition：16~2048 字节采用 2 的幂大小类；小对象来自单页 slab，元数据和对象区分离，对象至少 16 字节对齐；较大对象直接分配连续页并记录释放所需原页数。
Case 1：size=0、大小计算可能溢出或资源不足时返回 NULL，不能泄漏已申请页。
Case 2：缓存现有 slab 有空槽则复用；无空槽时按需申请新页。
## kfree
Pre-Condition：ptr 为 NULL 或本分配器返回的未释放指针；不支持任意外部/野指针。
Post-Condition：NULL 无操作；小对象释放位图槽并维护使用量，整页空闲时归还底层；大对象按所记录页数归还；合法释放后无内存泄漏。
Requirements：检查 magic、大小类、槽边界/对齐和位图状态；说明这是保留缓存/对象两层思想的简化实现，不包含 Linux SLUB 的 per-CPU 机制或锁。
```

## P6：SLUB 独立测试

```text
[PROMPT]
任务：为 P5 的 kmalloc/kfree 实现 slub_check，自动在启动时验证，不能修改分配器以硬编码测试返回值。

[RELY]
接口是 kmalloc、kfree、nr_free_pages；小对象最小 16 字节对齐；大小类上限 2048 字节，大对象使用页分配。测试可以使用固定数组保存临时指针。

[GUARANTEE]
提供 void slub_check(void)，可在三种底层 PMM 下运行；不得修改生产接口、已有测试或评分脚本以规避失败。每个检查有明确断言，结束时释放所有对象。

[SPECIFICATION]
Pre-Condition：PMM 可用、无未释放 SLUB 对象。
Post-Condition：所有对象已归还，空闲页数等于测试开始值。
Case 1：覆盖 1/15/16/17 及各大小类临界点，直到 2048/2049、4096、8193，共 27 个大小；检验对齐、区间无重叠、逐字节内容完整。
Case 2：同类申请 270 个对象，保证跨多个 slab；在当前 slab 内释放一个槽并重新申请，验证精确复用和其他对象不受影响。
Case 3：释放所有对象验证整页回收；验证 kmalloc(0)、极大溢出请求、资源不足返回 NULL，kfree(NULL) 安全。
Requirements：区分 SLUB 自测与官方 make grade 的覆盖范围，不把额外测试称为官方评分。
```

## P7：QEMU 双 GDB 地址翻译调试

```text
[PROMPT]
任务：依据课程 lab2_4_qemu_mmu_debug.html，用真实 QEMU 4.1.1 源码和两个 GDB 跟踪一次内核访存的地址转换，保存可复现脚本及原始日志。普通 GDB 调试宿主 x86_64 QEMU，RISC-V GDB 调试客体内核。使用现有官方源码单独 --enable-debug 构建，不替换日常 QEMU。

[RELY]
target/riscv/cpu_helper.c 的 get_physical_address、riscv_cpu_tlb_fill；accel/tcg/cputlb.c 的 load_helper、tlb_fill、tlb_set_page；tcg/i386/tcg-target.inc.c 生成软件 TLB 查找快路径。用源码搜索确认名字和实际行号。
内核启动根页表仅第 511 项有效，值为 0x200000cf，是 1 GiB 叶子；不要假设一定执行三级遍历。可新增无分配副作用的 mmu_probe：sfence.vma 后连续两次 ld 读取同一个已知内核数据地址。

[GUARANTEE]
提供 tools/debug_mmu.py 或等价可复现流程、宿主/客体 GDB 日志、地址和结果摘要；不修改 QEMU 源码，不关闭系统 ptrace 防护。可以用原生 GDB 启动自己的 QEMU 子进程，避免 attach 权限问题。

[SPECIFICATION]
Pre-Condition：内核和 QEMU 都有调试信息，默认内核为 Best-Fit；调试端口独立于常用的 1234。
Post-Condition：记录 Bare 模式 satp=0 时的地址直通；在 Sv39 中记录真实 ld 指令、VA、satp、根页表 PA、索引、PTE、叶子层级、PA、权限及填入后的软件 TLB 项；用 next 逐行观察 C 的 TLB 未命中、victim 检查和页表关键分支，不仅在前后断点取值；证明第二次 ld 得到相同值且该地址仅发生一次 data fill。
Requirements：说明代码生成快路径和 C 慢路径的区别；区分客体 PA 与宿主 HVA/addend；如依赖缺失则优先使用 Python 标准库；完整记录真实问题，不编造失败或测试结果。
```

