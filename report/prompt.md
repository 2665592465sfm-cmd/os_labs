# Lab2 最终提示词汇总

这些提示词按本次实现的功能整理，均使用课程规定的四段式框架。P3/P4、P5/P6 分别区分实现与测试任务；P7 记录源码调试任务。

## P1：物理内存探测和 Page 初始化

```text
[PROMPT]
任务：在 kern/mm/pmm.c 的 lab2 function1 标记处实现 static void page_init(void)。必须修改实际文件，保留 lab2 注释，将 YOUR CODE 替换为 2412396。按本项目的地址转换约定实现，不硬编码空闲页数量，不改变设备树解析器或测试程序。

[RELY]
工程实际接口：get_memory_base()/get_memory_size() 返回 uint64_t；pmm_manager 已完成 init；init_memmap(struct Page *, size_t) 注册连续空闲页；pa2page(uintptr_t) 将物理地址转换为描述符。
struct Page 包含 ref、flags、property、page_link；通过 SetPageReserved、set_page_ref 和 list_init 初始化。PGSIZE=4096，nbase=DRAM_BASE/PGSIZE，DRAM_BASE=0x80000000。
PHYSICAL_MEMORY_END=0x88000000，PHYSICAL_MEMORY_OFFSET=0xffffffff40000000；end 是链接器提供的内核结束虚拟地址；PADDR 依赖 va_pa_offset。pages 指向描述符数组的虚拟地址，npage 是物理页号上界而非页面数量。

[GUARANTEE]
实现 static void page_init(void)。不修改 pmm_init、init_memmap、地址转换宏和测试的接口。允许新增本模块内的 static 辅助函数。

[SPECIFICATION]
## page_init
Pre-Condition：在 Sv39 启用、BSS 清零及 dtb_init 完成后执行；当前物理页管理器为空。当前平台以固定 DRAM_BASE 为起点并使用单段 RAM。
Post-Condition：va_pa_offset 正确；npage 取设备树内存末端和框架可管理末端的较小者的完整页上界；pages 在 end 后按页对齐；描述符覆盖 [nbase,npage)，并正确预留固件、内核、对齐空间和描述符数组；仅剩余完整空闲页交给管理器。
Case 1：正常范围，验证描述符数组完全放得下后再写入；先将所有描述符置为保留状态，再注册空闲区。
Case 2：零大小、地址加法溢出、不符合固定起点或描述符空间不足时 panic，不能先写越界内存。
Case 3：无完整空闲页时不调用 init_memmap，不传入长度 0。
Requirements：打印探测范围、描述符大小、空闲起点及页数；不混用物理地址、虚拟地址和描述符下标；保持原评分脚本不变。
```

## P2：Best-Fit 模块及注册

```text
[PROMPT]
任务：参考 default_pmm.c，在 kern/mm/best_fit_pmm.c 的 lab2 function2-2 标记处从零实现完整 Best-Fit 管理器，定义 best_fit_pmm_manager，并在 pmm.c 默认选择它。修改真实文件；保留两个框架测试函数 basic_check 和 best_fit_check 的全部正文；把 YOUR CODE 替换为 2412396。

[RELY]
struct pmm_manager 的六个回调为 init(void)、init_memmap(struct Page*,size_t)、alloc_pages(size_t)、free_pages(struct Page*,size_t)、nr_free_pages(void)、check(void)。Page 和链表接口以 pmm.h、memlayout.h、list.h 为准。
测试直接使用 free_list 和 nr_free，并临时保存、重置和恢复链表表头，因此必须提供兼容这两个名字的本模块状态，不能另建测试不可见的权威空闲状态。所有空闲块的头页用 PageProperty 标识，property 记录块长度。

[GUARANTEE]
实现 best_fit_init、best_fit_init_memmap、best_fit_alloc_pages、best_fit_free_pages、best_fit_nr_free_pages，定义 const struct pmm_manager best_fit_pmm_manager，check 指向既有 best_fit_check；修改 init_pmm_manager 的默认选择。可以增加 static 插入/合并辅助函数。

[SPECIFICATION]
## init / init_memmap
Pre-Condition：管理器初次初始化；init_memmap 输入 n>0 的连续保留页。
Post-Condition：init 建立空表并置计数为 0；init_memmap 清除输入区间保留标志、清零引用并按地址有序插入，合并相邻块，空闲计数增加 n。
## alloc_pages
Pre-Condition：n>0，空闲链表与计数一致。
Post-Condition：返回满足需求且长度最小的块的前 n 页；并列时选低地址块。分配后剩余块仍有序且元数据有效，计数减少 n；失败返回 NULL 并保持状态不变。
Case 1：恰好匹配，移除整块并清除头页空闲属性。Case 2：大于请求，正确拆分剩余块。Case 3：总量不足或无足够连续块，返回 NULL。
## free_pages / nr_free_pages
Pre-Condition：输入为合法、未重复释放的已分配连续页，n>0。
Post-Condition：清零引用，按地址插入并合并前后相邻空闲块；计数只增加一次 n；nr_free_pages 返回准确总数。
Requirements：不得修改既有两项检查；将额外测试放到独立模块；Best-Fit 为提交默认，First-Fit 和 Buddy 的演示可通过编译开关选择。
```

## P3：Buddy System 实现和接入

```text
[PROMPT]
任务：在 kern/mm/buddy_pmm.c/.h 从零实现 Buddy System 页分配器，注册 buddy_pmm_manager，以 PMM=buddy 接入构建；默认仍为 Best-Fit。必须修改项目文件；不要把已有 First-Fit 换名冒充 Buddy。

[RELY]
复用 pmm_manager、struct Page、链表、page2ppn、nbase/npage 和保留/空闲标志。可管理 RAM 最多 128 MiB、32768 个 4 KiB 页；初始空闲区起点可能不是大块对齐地址，长度也可能不是 2 的幂。接口允许 alloc_pages 返回至少 n 页。

[GUARANTEE]
实现 buddy_init、buddy_init_memmap、buddy_alloc_pages、buddy_free_pages、buddy_nr_free_pages 和 buddy_pmm_manager；在 Makefile/pmm.c 提供独立选择。实现代码和测试代码分别组织。

[SPECIFICATION]
## init_memmap
Pre-Condition：输入保留页的连续范围，n>0。
Post-Condition：将整个可用范围分解为尽量大的、按物理页号对齐的 2^order 块；不丢失起止零碎页，不触及保留区。
## alloc_pages
Pre-Condition：n>0。
Post-Condition：请求上取整到 2 的幂；查找可用阶并反复二分，返回物理页号对齐的块；计数按实际块大小扣减；无合适块/超出最大阶返回 NULL。
## free_pages
Pre-Condition：base 为本分配器返回的块头，n 为原请求或对应实际块大小；不支持部分释放。
Post-Condition：校验实际块边界和已分配状态；与相同阶且空闲的真正伙伴递归合并；只增加实际释放页数；绝不把只是相邻的非伙伴误合并。
Requirements：伙伴关系用绝对物理页号异或计算；使用额外分配标记和头页长度检查错误释放；单 hart 启动期使用，不宣称支持并发。
```

## P4：Buddy System 独立测试

```text
[PROMPT]
任务：针对 P3 的 Buddy 分配器，在 buddy_pmm.c 内编写 buddy_check 和独立状态审计，接入 manager.check。用真实 QEMU 运行，不能只打印 PASS。

[RELY]
Buddy 以 2^order 页为单位实际分配，初始范围不一定按最大阶对齐；PageProperty 仅标识空闲块头；page_link 在已分配页中可临时作为测试持有队列；通过 pmm_manager 接口获取计数。

[GUARANTEE]
提供 buddy_check(void)、检查阶链表和计数的不变量审计；已有生产分配逻辑保持独立。每个 PASS 之前必须有相应断言。

[SPECIFICATION]
Pre-Condition：Buddy 已完成真实物理页初始化，当前无其他用户分配。
Post-Condition：测试释放所有临时块、恢复初始空闲页数和最大可合并状态。
Case 1：3 页/9 页请求分别扣减 4/16 页，并验证物理页号对齐、拆分和递归合并。
Case 2：固定随机种子的 1200 次混合分配/释放，维护至少 32 个活动槽；检查区间不重叠及实际内存首尾数据未损坏。
Case 3：逐页耗尽全部空闲页，验证 NULL、计数为 0，再全部归还并审计。
Case 4：超过最大阶请求返回 NULL，状态不变。
Requirements：审计检查空闲块长度/对齐/界限、区间互斥、计数之和，以及可合并的同阶伙伴不同时残留。
```

## P5：简化 SLUB 对象分配器

```text
[PROMPT]
任务：从零新增 kern/mm/slub.c/.h，提供简化的 SLUB 风格两层分配，接入现有内核的测试过程。必须实现真实 kmalloc/kfree，而非只描述设计。

[RELY]
底层 alloc_pages/free_pages/nr_free_pages 支持 Best-Fit、First-Fit 或 Buddy；虚实转换用 page2pa+va_pa_offset、PADDR 和 pa2page。Page 大小 4096。可以在已分配页内存放 slab 头、位图和链表，但不能破坏 Page 描述符和底层计数。

[GUARANTEE]
实现 void *kmalloc(size_t)、void kfree(void*)；提供 slub.h。缓存初始化可为 static 辅助函数。测试 slub_check 独立编写。

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
提供 slub_check(void)，可在三种底层 PMM 下运行；每个检查有明确断言，结束时释放所有对象。

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
Post-Condition：记录 Bare 模式 satp=0 时的地址直通；在 Sv39 中记录真实 ld 指令、VA、satp、根页表 PA、索引、PTE、叶子层级、PA、权限及填入后的软件 TLB 项；证明第二次 ld 得到相同值且该地址仅发生一次 data fill。
Requirements：说明代码生成快路径和 C 慢路径的区别；区分客体 PA 与宿主 HVA/addend；如依赖缺失则优先使用 Python 标准库；完整记录真实问题，不编造失败或测试结果。
```

