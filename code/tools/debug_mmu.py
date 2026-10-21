#!/usr/bin/env python3
"""Two independent GDBs: native QEMU process + RISC-V guest. No ptrace sysctl changes."""
from pathlib import Path
import argparse
import json
import os
import re
import selectors
import signal
import subprocess
import time


class GDB:
    def __init__(self, args, log):
        self.p = subprocess.Popen(args, stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                                  stderr=subprocess.STDOUT, start_new_session=True)
        self.log = log.open('w', buffering=1)
        self.sel = selectors.DefaultSelector()
        self.sel.register(self.p.stdout, selectors.EVENT_READ)
        self.pending = b''
        self.wait()

    def send(self, command):
        self.log.write('(gdb) ' + command + '\n')
        self.p.stdin.write((command + '\n').encode())
        self.p.stdin.flush()

    def wait(self, timeout=40):
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            if b'(gdb) ' in self.pending:
                before, self.pending = self.pending.split(b'(gdb) ', 1)
                text = before.decode(errors='replace')
                self.log.write(text)
                return text
            if self.sel.select(0.1):
                data = os.read(self.p.stdout.fileno(), 65536)
                if not data:
                    raise RuntimeError('GDB exited: ' + self.pending.decode(errors='replace'))
                self.pending += data
        self.log.write(self.pending.decode(errors='replace'))
        raise TimeoutError('GDB prompt timeout: ' + str(self.log.name))

    def cmd(self, command):
        self.send(command)
        result = self.wait()
        if any(x in result for x in ('No symbol ', 'Cannot access memory', 'Error in sourced command', 'Cannot find bounds', 'not defined')):
            raise RuntimeError(command + ': ' + result)
        return result

    def stop(self):
        if self.p.poll() is None:
            os.kill(self.p.pid, signal.SIGINT)
            return self.wait()

    def close(self):
        if self.p.poll() is None:
            self.p.kill()
            self.p.wait()
        self.log.close()
        self.sel.close()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--qemu', type=Path, required=True)
    parser.add_argument('--source', type=Path, required=True)
    parser.add_argument('--out', type=Path, required=True)
    parser.add_argument('--port', type=int, default=1235)
    opt = parser.parse_args()
    opt.qemu, opt.source, opt.out = opt.qemu.resolve(), opt.source.resolve(), opt.out.resolve()
    root = Path(__file__).resolve().parents[1]
    os.chdir(root)
    opt.out.mkdir(parents=True, exist_ok=True)
    symbols = {}
    for line in subprocess.check_output(['riscv64-unknown-elf-nm','bin/kernel'], text=True).splitlines():
        fields = line.split()
        if len(fields) == 3:
            symbols[fields[2]] = int(fields[0],16)
    addr = symbols['mmu_probe_word']
    cpu_lines = (opt.source / 'target/riscv/cpu_helper.c').read_text().splitlines()
    def lineno(fragment):
        return next(i+1 for i,s in enumerate(cpu_lines) if fragment in s)
    read_pte = lineno('target_ulong ppn = pte >> PTE_PPN_SHIFT;') + 2
    pte_address_line = lineno('target_ulong pte_addr = base + idx * ptesize;')
    calc_pa = lineno('*physical = (ppn | (vpn &') + 2
    fill_done = lineno('prot, mmu_idx, TARGET_PAGE_SIZE);') + 1
    tlb_lines = (opt.source / 'accel/tcg/cputlb.c').read_text().splitlines()
    load_start = next(i for i,s in enumerate(tlb_lines) if s.startswith('load_helper(CPUArchState'))
    tlb_miss_line = next(i+1 for i,s in enumerate(tlb_lines)
                         if i > load_start and 'if (!tlb_hit(tlb_addr, addr))' in s)
    host = guest = None
    qargs = [str(opt.qemu), '-machine','virt','-nographic','-bios','default',
             '-device','loader,file=bin/ucore.img,addr=0x80200000',
             '-S','-gdb',f'tcp:127.0.0.1:{opt.port}']
    (opt.out/'commands.json').write_text(json.dumps({'qemu':qargs,'symbols':symbols}, indent=2))
    try:
        host = GDB(['gdb','-q','-nx','--args'] + qargs, opt.out/'host-gdb.txt')
        for cmd in ('set pagination off','set confirm off','set print pretty on','handle SIGPIPE nostop noprint pass'):
            host.cmd(cmd)
        host.cmd('break riscv_cpu_tlb_fill if address == 0x80200000')
        host.send('run')
        time.sleep(0.7)
        guest = GDB(['riscv64-unknown-elf-gdb','-q','-nx','bin/kernel'], opt.out/'guest-gdb.txt')
        guest.cmd('set pagination off')
        guest.cmd('set confirm off')
        guest.cmd('set architecture riscv:rv64')
        guest.cmd(f'target remote localhost:{opt.port}')
        guest.cmd('p/x $pc')
        guest.cmd('thbreak *mmu_probe_load')
        guest.cmd('thbreak *mmu_probe_after')
        guest.send('continue')
        host.wait()
        host.cmd('printf "BARE translation: address=%#lx mmu_idx=%d access=%d\\n", address, mmu_idx, access_type')
        host.cmd('p/x ((RISCVCPU *)cs)->env.satp')
        host.cmd('tbreak get_physical_address')
        host.cmd('continue')
        host.cmd('set $bare_physical = physical')
        host.cmd('finish')
        host.cmd('p/x *$bare_physical')
        host.cmd('disable 1')
        answer = host.cmd(f'break riscv_cpu_tlb_fill if address == {addr:#x} && access_type == 0')
        number = int(re.search(r'Breakpoint (\d+)',answer).group(1))
        host.cmd('set $fills = 0')
        host.cmd(f'tbreak accel/tcg/cputlb.c:{tlb_miss_line} if addr == {addr:#x} && code_read == 0')
        host.send('continue')
        guest.wait()
        guest.cmd('p/x $pc')
        guest.cmd('x/3i $pc')
        guest.cmd('p/x &mmu_probe_word')
        guest.send('continue')
        host.wait()
        host.cmd('printf "SINGLE-STEP: C software TLB miss path\\n"')
        for command in ('p/x addr','p/x tlb_addr','p mmu_idx','p size','bt 4'):
            host.cmd(command)
        # Step the actual C miss and victim-cache branches. The permanent
        # architecture fill breakpoint then stops inside the call made here.
        host.cmd('next')
        host.cmd('next')
        host.cmd('next')
        frame = host.cmd('frame')
        if 'riscv_cpu_tlb_fill' not in frame:
            raise AssertionError('Expected architecture fill after TLB miss: ' + frame)
        host.cmd('set $fills = $fills + 1')
        host.cmd('bt 7')
        host.cmd('set $cpu = (RISCVCPU *)cs')
        host.cmd(f'set $va = {addr:#x}')
        host.cmd('p/x $cpu->env.satp')
        host.cmd('p sizeof(CPUTLBEntry)')
        host.cmd('set $entry = (CPUTLBEntry *)((char *)$cpu->neg.tlb.f[1].table + (($va >> 7) & $cpu->neg.tlb.f[1].mask))')
        host.cmd('p/x *$entry')
        host.cmd('tbreak get_physical_address')
        host.cmd('continue')
        host.cmd('set $physical_out = physical')
        host.cmd(f'tbreak target/riscv/cpu_helper.c:{pte_address_line}')
        host.cmd('continue')

        def next_to_line(line):
            for _ in range(60):
                frame = host.cmd('frame')
                if 'get_physical_address' not in frame:
                    raise AssertionError('Unexpected frame while single-stepping: ' + frame)
                current = re.search(r'cpu_helper\.c:(\d+)', frame)
                if current and int(current.group(1)) >= line:
                    return
                host.cmd('next')
            raise AssertionError('Single-step bound exceeded')

        host.cmd('printf "SINGLE-STEP: PTE address, PMP check and physical PTE read\\n"')
        next_to_line(read_pte)
        for cmd in ('p i','p levels','p ptshift','p/x base','p/x idx','p/x pte_addr','p/x pte','p/x ppn'):
            host.cmd(cmd)
        host.cmd('printf "SINGLE-STEP: leaf, access permissions, superpage alignment, A/D and PA\\n"')
        next_to_line(calc_pa)
        translated = host.cmd('p/x *physical')
        expected_pa = addr - 0xffffffff40000000
        if not re.search(r'= ' + hex(expected_pa) + r'\b', translated):
            raise AssertionError('Unexpected guest physical address: ' + translated)
        host.cmd('p/x addr')
        host.cmd(f'tbreak target/riscv/cpu_helper.c:{fill_done}')
        host.cmd('continue')
        host.cmd('p/x pa')
        host.cmd('p prot')
        host.cmd('set $entry = (CPUTLBEntry *)((char *)$cpu->neg.tlb.f[1].table + (($va >> 7) & $cpu->neg.tlb.f[1].mask))')
        host.cmd('p/x *$entry')
        host.cmd('x/gx $va + $entry->addend')
        # Auto-count any subsequent actual data miss for this address.
        host.cmd(f'commands {number}\nsilent\nset $fills = $fills + 1\ncontinue\nend')
        host.send('continue')
        guest.wait()
        guest.cmd('p/x $pc')
        for register in ('$t0', '$t1'):
            value = guest.cmd('p/x ' + register)
            if not re.search(r'= 0x241239602411688\b', value):
                raise AssertionError('Guest load mismatch: ' + value)
        host.stop()
        fills = host.cmd('p $fills')
        if not re.search(r'= 1\b', fills):
            raise AssertionError('Expected exactly one translation fill: ' + fills)
        host.cmd('p/x *$entry')
        host.cmd('printf "PASS: two guest loads, one data TLB fill; second load used cached mapping\\n"')
        host.cmd('kill')
        (opt.out/'summary.json').write_text(json.dumps({
            'passed':True,'bare_va':0x80200000,'bare_pa':0x80200000,
            'probe_va':addr,'expected_pa':addr-0xffffffff40000000,
            'guest_load':symbols['mmu_probe_load'],'guest_after':symbols['mmu_probe_after'],
            'data_fills_for_two_loads':1,'root_leaf_index':511,'leaf_level':2,'page_size':1<<30,
            'page_walk_single_step':True,'tlb_c_miss_single_step':True,
            'qemu_version':'4.1.1','source':str(opt.source)}, indent=2))
        print('PASS dual GDB: Bare/Sv39, real load, root leaf, PA, cached second load')
    finally:
        if host:
            host.close()
        if guest:
            guest.close()


if __name__ == '__main__':
    main()
