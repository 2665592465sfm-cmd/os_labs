#!/usr/bin/env python3
"""Inject DTB return-state faults through guest GDB, in fresh disposable QEMU boots."""
from pathlib import Path
import argparse
import json
import os
import re
import subprocess
import time
from debug_mmu import GDB


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--out', type=Path, required=True)
    ap.add_argument('--port', type=int, default=1236)
    opt = ap.parse_args()
    root = Path(__file__).resolve().parents[1]
    os.chdir(root)
    opt.out = opt.out.resolve()
    opt.out.mkdir(parents=True, exist_ok=True)
    nm = subprocess.check_output(['riscv64-unknown-elf-nm','bin/kernel'],text=True)
    kernel_end = int(re.search(r'([0-9a-f]+) [A-Za-z] end\n',nm).group(1),16)
    desc_start = ((kernel_end + 4095) & ~4095) - 0xffffffff40000000
    # sizeof(Page) is checked separately in the actual GDB run.
    nofree_size = next(t * 4096 for t in range(512,1024)
                       if ((desc_start + t * 40 + 4095) & ~4095) == 0x80000000 + t * 4096
                       and desc_start + t * 40 <= 0x80000000 + t * 4096)
    pmm_lines = (root/'kern/mm/pmm.c').read_text().splitlines()
    after_init = next(i+1 for i,s in enumerate(pmm_lines) if s.strip() == 'check_alloc_page();')
    cases = [('zero',0x80000000,0,'invalid DTB memory range'),
             ('overflow',0x80000000,0xffffffffffffffff,'invalid DTB memory range'),
             ('wrong_base',0x90000000,0x8000000,'invalid DTB memory range'),
             ('tiny',0x80000000,0x201000,'not enough RAM for Page descriptors'),
             ('no_free',0x80000000,nofree_size,None)]
    results = []
    for name,base,size,error in cases:
        qlog = (opt.out/(name+'-qemu.txt')).open('w')
        q = subprocess.Popen(['qemu-system-riscv64','-machine','virt','-nographic','-bios','default',
                              '-device','loader,file=bin/ucore.img,addr=0x80200000',
                              '-S','-gdb',f'tcp:127.0.0.1:{opt.port}'],
                             stdin=subprocess.PIPE,stdout=qlog,stderr=subprocess.STDOUT)
        g = None
        try:
            time.sleep(.2)
            g = GDB(['riscv64-unknown-elf-gdb','-q','-nx','bin/kernel'], opt.out/(name+'-gdb.txt'))
            for command in ['set pagination off','set confirm off','set architecture riscv:rv64',
                            f'target remote localhost:{opt.port}','thbreak *pmm_init','continue',
                            f'set variable memory_base = {base:#x}',f'set variable memory_size = {size:#x}',
                            'p sizeof(struct Page)','set $registrations = 0','break best_fit_init_memmap',
                            'commands 2\nsilent\nset $registrations = $registrations + 1\ncontinue\nend']:
                result = g.cmd(command)
                if command == 'p sizeof(struct Page)':
                    assert re.search(r'= 40\b', result), result
            g.cmd('thbreak *__panic' if error else f'thbreak pmm.c:{after_init}')
            g.cmd('continue')
            if error:
                message = g.cmd('x/s $a2')
                assert error in message, message
            else:
                state = g.cmd('p best_area.nr_free')
                assert re.search(r'= 0\b',state), state
            registrations = g.cmd('p $registrations')
            assert re.search(r'= 0\b',registrations), registrations
            g.cmd('printf "PASS: rejected invalid layout or skipped empty free range, registrations=0\\n"')
            results.append({'case':name,'memory_base':base,'memory_size':size,'passed':True,
                            'expected_error':error,'init_memmap_calls':0})
            print('PASS page_init edge:',name)
        finally:
            if g:
                g.close()
            if q.poll() is None:
                q.stdin.write(b'\x01x')
                q.stdin.flush()
                q.wait(timeout=5)
            qlog.close()
    (opt.out/'summary.json').write_text(json.dumps(results,indent=2))


if __name__ == '__main__':
    main()
