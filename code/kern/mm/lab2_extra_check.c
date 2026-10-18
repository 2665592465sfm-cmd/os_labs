#include <pmm.h>
#include <best_fit_pmm.h>
#include <stdio.h>
#include <string.h>
#include <lab2_extra_check.h>

volatile uint64_t mmu_probe_word __attribute__((aligned(4096))) = 0x241239602411688UL;

__noinline void mmu_probe(void) {
    // Stable observable load pair. No page-table changes or allocator effects.
    asm volatile("sfence.vma\n"
                 ".global mmu_probe_load\nmmu_probe_load:\n"
                 "ld t0, 0(%0)\n"
                 "ld t1, 0(%0)\n"
                 ".global mmu_probe_after\nmmu_probe_after:\n"
                 : : "r"(&mmu_probe_word) : "t0", "t1", "memory");
    cprintf("MMU probe: two loads from VA=0x%016lx value=0x%016lx\n",
            (uintptr_t)&mmu_probe_word, mmu_probe_word);
}

// Additional checks; the supplied basic_check/best_fit_check remain unchanged.
void lab2_extra_check(void) {
    if (pmm_manager != &best_fit_pmm_manager) return;
    size_t initial = nr_free_pages();
    struct Page *pool = alloc_pages(24);
    assert(pool);
    free_pages(pool + 1, 6);
    free_pages(pool + 10, 3);
    free_pages(pool + 16, 4);
    struct Page *a = alloc_pages(3), *b = alloc_pages(2), *c = alloc_pages(2);
    assert(a == pool + 10 && b == pool + 16 && c == pool + 18);
    free_pages(a, 3);
    free_pages(b, 2);
    free_pages(c, 2);
    free_pages(pool, 1);
    free_pages(pool + 7, 3);
    free_pages(pool + 13, 3);
    free_pages(pool + 20, 4);
    assert(nr_free_pages() == initial);
    cprintf("Best-Fit extra: smallest-fit, exact-fit, split, two-sided merge PASS\n");

    struct Page *slots[24] = {0};
    size_t lengths[24] = {0};
    unsigned seed = 2412396;
    for (unsigned step = 0; step < 800; ++step) {
        seed = seed * 1103515245U + 12345;
        unsigned slot = (seed >> 16) % 24;
        if (slots[slot]) {
            unsigned char *p = (void *)(page2pa(slots[slot]) + va_pa_offset);
            assert(p[0] == slot && p[lengths[slot] * PGSIZE - 1] == slot);
            free_pages(slots[slot], lengths[slot]);
            slots[slot] = NULL;
        } else {
            size_t n = (seed % 17) + 1;
            struct Page *p = alloc_pages(n);
            assert(p);
            for (unsigned j = 0; j < 24; ++j) {
                if (slots[j]) assert(p + n <= slots[j] || slots[j] + lengths[j] <= p);
            }
            slots[slot] = p;
            lengths[slot] = n;
            memset((void *)(page2pa(p) + va_pa_offset), slot, n * PGSIZE);
        }
    }
    for (unsigned i = 0; i < 24; ++i) if (slots[i]) free_pages(slots[i], lengths[i]);
    assert(nr_free_pages() == initial && alloc_pages(initial + 1) == NULL);
    // A fragmented free list that failed to coalesce would fail this request.
    pool = alloc_pages(initial);
    assert(pool && nr_free_pages() == 0 && alloc_page() == NULL);
    free_pages(pool, initial);
    assert(nr_free_pages() == initial);
    cprintf("Best-Fit extra: 800 mixed operations, isolation, exhaustion and recovery PASS\n");
}
