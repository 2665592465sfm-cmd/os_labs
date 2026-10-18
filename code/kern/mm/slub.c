#include <slub.h>
#include <pmm.h>
#include <stdio.h>
#include <string.h>

// lab2 Challenge 2412396: educational SLUB-style two-level allocator.
// Single hart/boot-time only; no per-CPU caches or concurrency support.
#define CACHE_COUNT 8
#define SLAB_MAGIC 0x534c55424c414232UL
#define LARGE_CLASS CACHE_COUNT
struct slab {
    uint64_t magic;
    list_entry_t link;
    size_t class_id, inuse, capacity, npages;
    uint64_t used[4];
};
static list_entry_t caches[CACHE_COUNT];
static int initialized;
static const size_t header_size = (sizeof(struct slab) + 15) & ~15UL;

static void init_caches(void) {
    if (initialized) return;
    for (unsigned i = 0; i < CACHE_COUNT; ++i) list_init(&caches[i]);
    initialized = 1;
}

void *kmalloc(size_t size) {
    if (size == 0 || size > ~(size_t)0 - header_size - PGSIZE) return NULL;
    init_caches();
    unsigned id = 0;
    while (id < CACHE_COUNT && ((size_t)16 << id) < size) ++id;
    if (id == LARGE_CLASS) {
        size_t npages = (size + header_size + PGSIZE - 1) / PGSIZE;
        struct Page *p = alloc_pages(npages);
        if (!p) return NULL;
        struct slab *s = (void *)(page2pa(p) + va_pa_offset);
        memset(s, 0, header_size);
        s->magic = SLAB_MAGIC;
        s->class_id = LARGE_CLASS;
        s->npages = npages;
        s->inuse = 1;
        return (char *)s + header_size;
    }
    struct slab *s = NULL;
    for (list_entry_t *le = list_next(&caches[id]); le != &caches[id]; le = list_next(le)) {
        struct slab *candidate = to_struct(le, struct slab, link);
        if (candidate->inuse < candidate->capacity) { s = candidate; break; }
    }
    if (!s) {
        struct Page *p = alloc_page();
        if (!p) return NULL;
        s = (void *)(page2pa(p) + va_pa_offset);
        memset(s, 0, header_size);
        s->magic = SLAB_MAGIC;
        s->class_id = id;
        s->npages = 1;
        s->capacity = (PGSIZE - header_size) / ((size_t)16 << id);
        assert(s->capacity <= 256 && s->capacity > 0);
        list_add(&caches[id], &s->link);
    }
    for (size_t i = 0; i < s->capacity; ++i) {
        uint64_t mask = 1UL << (i % 64);
        if (!(s->used[i / 64] & mask)) {
            s->used[i / 64] |= mask;
            ++s->inuse;
            return (char *)s + header_size + i * ((size_t)16 << id);
        }
    }
    panic("SLUB bitmap/count invariant broken");
}

void kfree(void *ptr) {
    if (!ptr) return;
    struct slab *s = (void *)ROUNDDOWN((uintptr_t)ptr, PGSIZE);
    assert(s->magic == SLAB_MAGIC && s->inuse > 0);
    if (s->class_id == LARGE_CLASS) {
        assert(ptr == (char *)s + header_size);
        size_t npages = s->npages;
        s->magic = 0;
        free_pages(pa2page(PADDR(s)), npages);
        return;
    }
    assert(s->class_id < CACHE_COUNT);
    size_t offset = (uintptr_t)ptr - (uintptr_t)s - header_size;
    size_t slot_size = (size_t)16 << s->class_id;
    assert((uintptr_t)ptr >= (uintptr_t)s + header_size && offset % slot_size == 0);
    size_t i = offset / slot_size;
    assert(i < s->capacity && (s->used[i / 64] & (1UL << (i % 64))));
    s->used[i / 64] &= ~(1UL << (i % 64));
    if (--s->inuse == 0) {
        list_del(&s->link);
        s->magic = 0;
        free_page(pa2page(PADDR(s)));
    }
}

void slub_check(void) {
    static const size_t sizes[] = {1,15,16,17,31,32,33,63,64,65,127,128,129,255,256,257,511,512,513,1023,1024,1025,2047,2048,2049,4096,8193};
    size_t before = nr_free_pages();
    void *objects[27];
    assert(kmalloc(0) == NULL && kmalloc(~(size_t)0) == NULL);
    kfree(NULL);
    for (unsigned i = 0; i < 27; ++i) {
        objects[i] = kmalloc(sizes[i]);
        assert(objects[i] && !((uintptr_t)objects[i] & 15));
        for (unsigned j = 0; j < i; ++j) {
            assert((char *)objects[i] + sizes[i] <= (char *)objects[j] || (char *)objects[j] + sizes[j] <= (char *)objects[i]);
        }
        memset(objects[i], i + 1, sizes[i]);
    }
    for (unsigned i = 0; i < 27; ++i) {
        unsigned char *p = objects[i];
        for (size_t j = 0; j < sizes[i]; ++j) assert(p[j] == i + 1);
        kfree(p);
    }
    assert(nr_free_pages() == before);
    cprintf("SLUB: 27 size boundaries, 16-byte alignment, data isolation, large objects PASS\n");

    void *many[270];
    for (unsigned i = 0; i < 270; ++i) {
        many[i] = kmalloc(16);
        assert(many[i]);
        memset(many[i], i & 255, 16);
    }
    // More than one slab, freeing/reusing a slot in a still-live slab.
    void *hole = many[269];
    kfree(hole);
    many[269] = kmalloc(16);
    assert(many[269] == hole);
    memset(many[269], 269 & 255, 16);
    for (unsigned i = 0; i < 270; ++i) {
        assert(((unsigned char *)many[i])[15] == (i & 255));
        kfree(many[i]);
    }
    assert(nr_free_pages() == before);
    assert(kmalloc((npage - nbase + 1) * PGSIZE) == NULL);
    cprintf("SLUB: multi-slab, slot reuse, NULL/OOM, full page recovery PASS\n");
}
