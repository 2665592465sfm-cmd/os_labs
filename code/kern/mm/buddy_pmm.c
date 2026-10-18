#include <buddy_pmm.h>
#include <stdio.h>
#include <string.h>

// lab2 Buddy System 2412396: order k owns 2^k physically aligned pages.
#define MAX_ORDER 15
#define BUDDY_ALLOC (1UL << 2)
static list_entry_t orders[MAX_ORDER + 1];
static size_t buddy_free;

static unsigned order_for(size_t n) {
    unsigned k = 0;
    while (k < MAX_ORDER && ((size_t)1 << k) < n) ++k;
    return k;
}

static void add_block(struct Page *p, unsigned k) {
    p->property = (size_t)1 << k;
    SetPageProperty(p);
    list_add(&orders[k], &p->page_link);
}

static void merge_block(struct Page *p, unsigned k) {
    while (k < MAX_ORDER) {
        size_t buddy_ppn = page2ppn(p) ^ ((size_t)1 << k);
        if (buddy_ppn < nbase || buddy_ppn >= npage) break;
        struct Page *q = pages + buddy_ppn - nbase;
        if (!PageProperty(q) || q->property != ((size_t)1 << k)) break;
        list_del(&q->page_link);
        ClearPageProperty(q);
        q->property = 0;
        if (q < p) p = q;
        ++k;
    }
    add_block(p, k);
}

static void buddy_init(void) {
    for (unsigned k = 0; k <= MAX_ORDER; ++k) list_init(&orders[k]);
    buddy_free = 0;
}

static void buddy_init_memmap(struct Page *base, size_t n) {
    assert(n > 0);
    for (struct Page *p = base; p < base + n; ++p) {
        assert(PageReserved(p));
        p->flags = p->property = 0;
        set_page_ref(p, 0);
    }
    buddy_free += n;
    while (n != 0) {
        unsigned k = MAX_ORDER;
        while (((size_t)1 << k) > n || (page2ppn(base) & (((size_t)1 << k) - 1))) --k;
        size_t length = (size_t)1 << k;
        merge_block(base, k);
        base += length;
        n -= length;
    }
}

static struct Page *buddy_alloc_pages(size_t n) {
    assert(n > 0);
    if (n > ((size_t)1 << MAX_ORDER)) return NULL;
    unsigned wanted = order_for(n), k = wanted;
    while (k <= MAX_ORDER && list_empty(&orders[k])) ++k;
    if (k > MAX_ORDER) return NULL;
    struct Page *p = le2page(list_next(&orders[k]), page_link);
    list_del(&p->page_link);
    ClearPageProperty(p);
    while (k > wanted) {
        --k;
        add_block(p + ((size_t)1 << k), k);
    }
    size_t actual = (size_t)1 << wanted;
    for (size_t i = 0; i < actual; ++i) {
        p[i].flags = BUDDY_ALLOC;
        p[i].property = 0;
    }
    p->property = actual;
    buddy_free -= actual;
    return p;
}

static void buddy_free_pages(struct Page *base, size_t n) {
    assert(n > 0 && n <= ((size_t)1 << MAX_ORDER));
    unsigned k = order_for(n);
    size_t actual = (size_t)1 << k;
    assert(base >= pages && base + actual <= pages + npage - nbase);
    assert(base->property == actual && (page2ppn(base) & (actual - 1)) == 0);
    for (size_t i = 0; i < actual; ++i) {
        assert(base[i].flags == BUDDY_ALLOC);
        base[i].flags = base[i].property = 0;
        set_page_ref(base + i, 0);
    }
    buddy_free += actual;
    merge_block(base, k);
}

static size_t buddy_nr_free_pages(void) { return buddy_free; }

// Audit every free interval and the maximal-coalescing invariant independently.
static void audit_buddy(void) {
    size_t total = 0;
    for (unsigned k = 0; k <= MAX_ORDER; ++k) {
        for (list_entry_t *le = list_next(&orders[k]); le != &orders[k]; le = list_next(le)) {
            struct Page *p = le2page(le, page_link);
            size_t length = (size_t)1 << k, ppn = page2ppn(p);
            assert(PageProperty(p) && p->property == length && !(ppn & (length - 1)));
            assert(ppn + length <= npage);
            total += length;
            if (k < MAX_ORDER) {
                size_t partner = ppn ^ length;
                if (partner >= nbase && partner < npage) {
                    struct Page *q = pages + partner - nbase;
                    assert(!PageProperty(q) || q->property != length);
                }
            }
            for (unsigned j = k; j <= MAX_ORDER; ++j) {
                for (list_entry_t *other = list_next(&orders[j]); other != &orders[j]; other = list_next(other)) {
                    struct Page *q = le2page(other, page_link);
                    if (q != p) assert(p + length <= q || q + ((size_t)1 << j) <= p);
                }
            }
        }
    }
    assert(total == buddy_free);
}

static void buddy_check(void) {
    size_t before = buddy_free;
    struct Page *a = buddy_alloc_pages(3), *b = buddy_alloc_pages(9);
    assert(a && b && a != b);
    assert(buddy_free == before - 4 - 16);
    assert(!(page2ppn(a) & 3) && !(page2ppn(b) & 15));
    buddy_free_pages(a, 3);
    buddy_free_pages(b, 9);
    assert(buddy_free == before);
    audit_buddy();
    cprintf("Buddy: rounding, alignment, split and recursive merge PASS\n");

    // Mixed live allocations: page writes and pairwise interval checks.
    struct Page *live[32] = {0};
    size_t requests[32] = {0};
    unsigned seed = 2412396;
    for (unsigned step = 0; step < 1200; ++step) {
        seed = seed * 1664525U + 1013904223U;
        unsigned slot = (seed >> 16) % 32;
        if (live[slot]) {
            unsigned char *mem = (void *)(page2pa(live[slot]) + va_pa_offset);
            assert(mem[0] == (unsigned char)slot && mem[live[slot]->property * PGSIZE - 1] == (unsigned char)slot);
            buddy_free_pages(live[slot], requests[slot]);
            live[slot] = NULL;
        } else {
            size_t n = (seed % 31) + 1;
            struct Page *p = buddy_alloc_pages(n);
            assert(p);
            for (unsigned i = 0; i < 32; ++i) {
                if (live[i]) assert(p + p->property <= live[i] || live[i] + live[i]->property <= p);
            }
            live[slot] = p;
            requests[slot] = n;
            memset((void *)(page2pa(p) + va_pa_offset), slot, p->property * PGSIZE);
        }
    }
    for (unsigned i = 0; i < 32; ++i) if (live[i]) buddy_free_pages(live[i], requests[i]);
    assert(buddy_free == before);
    audit_buddy();
    cprintf("Buddy: 1200 deterministic mixed allocation/free operations PASS\n");

    list_entry_t held;
    list_init(&held);
    struct Page *p;
    size_t allocated = 0;
    while ((p = buddy_alloc_pages(1)) != NULL) {
        list_add(&held, &p->page_link);
        ++allocated;
    }
    assert(allocated == before && buddy_free == 0 && buddy_alloc_pages(1) == NULL);
    while (!list_empty(&held)) {
        p = le2page(list_next(&held), page_link);
        list_del(&p->page_link);
        buddy_free_pages(p, 1);
    }
    assert(buddy_free == before && buddy_alloc_pages(((size_t)1 << MAX_ORDER) + 1) == NULL);
    audit_buddy();
    cprintf("Buddy: full exhaustion, NULL and complete recovery PASS (%lu pages)\n", before);
}

const struct pmm_manager buddy_pmm_manager = {
    .name = "buddy_pmm_manager", .init = buddy_init, .init_memmap = buddy_init_memmap,
    .alloc_pages = buddy_alloc_pages, .free_pages = buddy_free_pages,
    .nr_free_pages = buddy_nr_free_pages, .check = buddy_check,
};
