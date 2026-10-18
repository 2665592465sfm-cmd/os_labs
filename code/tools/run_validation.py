#!/usr/bin/env python3
"""Run real QEMU boots; record output and exit via the QEMU escape command."""
import argparse
import os
from pathlib import Path
import selectors
import subprocess
import time


def boot(qemu, ram, output, use_make=False):
    args = [qemu, '-machine', 'virt', '-m', str(ram), '-nographic', '-bios', 'default',
            '-device', 'loader,file=bin/ucore.img,addr=0x80200000']
    if use_make:
        assert ram == 128, 'make qemu uses the default 128 MiB configuration'
        args = ['make', 'qemu', 'QEMU=' + qemu]
    p = subprocess.Popen(args, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    data = bytearray()
    selector = selectors.DefaultSelector()
    selector.register(p.stdout, selectors.EVENT_READ)
    deadline = time.monotonic() + 35
    passed = False
    try:
        while time.monotonic() < deadline:
            if selector.select(0.2):
                part = os.read(p.stdout.fileno(), 65536)
                if not part:
                    break
                data.extend(part)
                if b'kernel panic' in data or b'assertion failed' in data:
                    break
                if b'satp physical address:' in data and data.endswith(b'\n'):
                    passed = True
                    break
            if p.poll() is not None:
                break
        p.stdin.write(b'\x01x')
        p.stdin.flush()
        tail, _ = p.communicate(timeout=5)
        data.extend(tail)
    finally:
        if p.poll() is None:
            p.kill()
            tail, _ = p.communicate()
            data.extend(tail)
        selector.close()
        output.write_text('$ ' + ' '.join(args) + '\n' + data.decode(errors='replace'))
    if not passed or b'PASS' not in data or p.returncode != 0:
        raise SystemExit('boot validation failed: ' + str(output))


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--out', type=Path, required=True)
    parser.add_argument('--manager', default='best_fit', choices=['best_fit', 'first_fit', 'buddy'])
    parser.add_argument('--ram', type=int, default=128)
    parser.add_argument('--qemu', default='qemu-system-riscv64')
    parser.add_argument('--make-qemu', action='store_true')
    opt = parser.parse_args()
    root = Path(__file__).resolve().parents[1]
    os.chdir(root)
    opt.out = opt.out.resolve()
    opt.out.mkdir(parents=True, exist_ok=True)
    for command in (['make', 'clean'], ['make', '-j4', 'PMM=' + opt.manager]):
        result = subprocess.run(command, capture_output=True, text=True)
        with (opt.out / 'build.txt').open('a') as f:
            f.write('$ ' + ' '.join(command) + '\n' + result.stdout + result.stderr)
        result.check_returncode()
    boot(opt.qemu, opt.ram, opt.out / 'qemu.txt', opt.make_qemu)
    print(f'PASS {opt.manager} RAM={opt.ram} MiB; logs: {opt.out}')
