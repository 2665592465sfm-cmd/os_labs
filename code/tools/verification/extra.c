#include <assert.h>
#include <clock.h>
#include <defs.h>
#include <intr.h>
#include <pmm.h>
#include <riscv.h>
#include <stdio.h>
#include <string.h>
#include <trap.h>
#include <../sync/sync.h>

extern void interrupt_handler(struct trapframe *tf);
extern void exception_handler(struct trapframe *tf);
extern void lab3_context_probe(void);
uintptr_t lab3_observed[32];
uintptr_t lab3_expected[32];

static void check_fallbacks(void) {
    static const unsigned irqs[] = {0, 1, 2, 3, 4, 6, 7, 8, 9, 10, 11, 12, 13, 15};
    struct trapframe tf, before;
    for (unsigned i = 0; i < sizeof(irqs) / sizeof(irqs[0]); ++i) {
        memset(&tf, 0, sizeof(tf));
        tf.cause = ((uintptr_t)1 << 63) | irqs[i];
        tf.epc = 0x1234;
        before = tf;
        interrupt_handler(&tf);
        assert(memcmp(&tf, &before, sizeof(tf)) == 0);
    }
    memset(&tf, 0, sizeof(tf));
    tf.cause = 20;
    before = tf;
    exception_handler(&tf);
    assert(memcmp(&tf, &before, sizeof(tf)) == 0);
    // A longer encoding is diagnosed, never guessed to be a 32-bit instruction.
    const uint16_t long_encoding[] = {0x001f, 0, 0};
    tf.cause = CAUSE_ILLEGAL_INSTRUCTION;
    tf.epc = (uintptr_t)long_encoding;
    before = tf;
    exception_handler(&tf);
    assert(memcmp(&tf, &before, sizeof(tf)) == 0);
    cprintf("Lab3 extra: IRQ classification and unsupported fallbacks preserve frame PASS\n");
}

static void check_interrupt_guards(void) {
    bool original = (read_csr(sstatus) & SSTATUS_SIE) != 0;
    intr_disable();
    bool outer, inner;
    local_intr_save(outer);
    assert(!outer && !(read_csr(sstatus) & SSTATUS_SIE));
    local_intr_restore(outer);
    assert(!(read_csr(sstatus) & SSTATUS_SIE));
    intr_enable();
    local_intr_save(outer);
    local_intr_save(inner);
    assert(outer && !inner && !(read_csr(sstatus) & SSTATUS_SIE));
    local_intr_restore(inner);
    assert(!(read_csr(sstatus) & SSTATUS_SIE));
    local_intr_restore(outer);
    assert(read_csr(sstatus) & SSTATUS_SIE);
    size_t before = nr_free_pages();
    struct Page *page = alloc_page();
    assert(page && (read_csr(sstatus) & SSTATUS_SIE));
    free_page(page);
    assert(nr_free_pages() == before && (read_csr(sstatus) & SSTATUS_SIE));
    intr_disable();
    if (original) intr_enable();
    cprintf("Lab3 extra: nested interrupt guards and PMM SIE preservation PASS\n");
}

void lab3_extra_check(void) {
    assert(sizeof(struct trapframe) == 36 * sizeof(uintptr_t));
    assert(offsetof(struct trapframe, status) == 32 * sizeof(uintptr_t));
    assert(offsetof(struct trapframe, epc) == 33 * sizeof(uintptr_t));
    for (unsigned i = 0; i < 32; ++i) lab3_expected[i] = 0x100 + i;
    lab3_expected[0] = 0;
    lab3_context_probe(); // Assembly supplies the actual pre-trap sp/gp/tp values.
    for (unsigned i = 0; i < 32; ++i) assert(lab3_observed[i] == lab3_expected[i]);
    cprintf("Lab3 extra: 32 integer-register slots including sp/gp/tp and c.ebreak return PASS\n");

    asm volatile(".global lab3_break32\nlab3_break32:\n.word 0x00100073" ::: "memory");
    cprintf("Lab3 extra: 32-bit ebreak resumed PASS\n");
    asm volatile(".global lab3_illegal16\nlab3_illegal16:\n.2byte 0x0000" ::: "memory");
    cprintf("Lab3 extra: 16-bit illegal instruction resumed PASS\n");
    asm volatile(".global lab3_illegal32\nlab3_illegal32:\n.word 0x0000007b" ::: "memory");
    cprintf("Lab3 extra: 32-bit illegal instruction resumed PASS\n");
    check_fallbacks();
    check_interrupt_guards();
    cprintf("Lab3 extra: ALL PASS\n");
}
