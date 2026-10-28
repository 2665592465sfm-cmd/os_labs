#!/usr/bin/env python3
"""Supplementary checks in a disposable tree; teacher tests stay untouched."""
from pathlib import Path
import argparse
import json
import re
import shutil
import subprocess
import tempfile


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--out', type=Path, required=True)
    parser.add_argument('--qemu', default='qemu-system-riscv64')
    opt = parser.parse_args()
    root = Path(__file__).resolve().parents[1]
    opt.out = opt.out.resolve()
    opt.out.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix='lab3-verify-') as directory:
        build = Path(directory) / 'code'
        shutil.copytree(root, build, ignore=shutil.ignore_patterns('bin', 'obj', 'test-output', '__pycache__', '.qemu*.out'))
        verify = build / 'kern/verify'
        verify.mkdir()
        for name in ('extra.c', 'context.S'):
            shutil.copyfile(root / 'tools/verification' / name, verify / name)
        init = build / 'kern/init/init.c'
        text = init.read_text()
        anchor = '    clock_init();'
        assert text.count(anchor) == 1
        text = text.replace(anchor, '    extern void lab3_extra_check(void);\n    lab3_extra_check();\n\n' + anchor)
        init.write_text(text)
        make = build / 'Makefile'
        text = make.read_text()
        anchor = 'KCFLAGS\t\t+='
        assert text.count(anchor) == 1
        text = text.replace(anchor, 'KINCLUDE += kern/verify\nKSRCDIR += kern/verify\n\n' + anchor)
        make.write_text(text)
        result = subprocess.run(['make', '-j4'], cwd=build, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
        (opt.out / 'build.txt').write_text('$ make -j4\n' + result.stdout)
        result.check_returncode()
        args = [opt.qemu, '-machine', 'virt', '-nographic', '-bios', 'default',
                '-device', 'loader,file=bin/ucore.img,addr=0x80200000']
        try:
            result = subprocess.run(args, cwd=build, stdin=subprocess.DEVNULL, stdout=subprocess.PIPE,
                                    stderr=subprocess.STDOUT, text=True, timeout=25)
        except subprocess.TimeoutExpired as error:
            output = error.stdout or b''
            if isinstance(output, bytes): output = output.decode(errors='replace')
            (opt.out / 'qemu.txt').write_text(output)
            raise RuntimeError('QEMU timed out; shutdown was not proved') from error
        (opt.out / 'qemu.txt').write_text('$ ' + ' '.join(args) + '\n' + result.stdout)
        result.check_returncode()
        assert 'Lab3 extra: ALL PASS' in result.stdout
        assert 'kernel panic' not in result.stdout and 'assertion failed' not in result.stdout
        assert result.stdout.splitlines().count('100 ticks') == 10
        symbols = {}
        for line in subprocess.check_output(['riscv64-unknown-elf-nm', 'bin/kernel'], cwd=build, text=True).splitlines():
            fields = line.split()
            if len(fields) == 3: symbols[fields[2]] = int(fields[0], 16)
        probes = [('lab3_context_break16', 'Breakpoint', 2), ('lab3_break32', 'Breakpoint', 4),
                  ('lab3_illegal16', 'Illegal instruction', 2), ('lab3_illegal32', 'Illegal instruction', 4)]
        for symbol, label, length in probes:
            assert f'{label} at 0x{symbols[symbol]:016x}' in result.stdout, symbol
        # Reaching the independent post-instruction markers complements these exact EPC checks.
        summary = {'passed': True, 'integer_register_slots_checked': 32, 'instruction_lengths': [2, 4],
                   'probes': {symbol: {'epc': hex(symbols[symbol]), 'length': length} for symbol, _, length in probes},
                   'synthetic_irq_cases': 14, 'unknown_exception_preserves_frame': True,
                   'long_encoding_diagnosed_without_epc_change': True, 'nested_interrupt_guards': True,
                   'periodic_reports': 10, 'qemu_exit': result.returncode,
                   'scope': 'RV64GC, one hart, readable kernel exception instructions; no user-stack or FP/vector context claim'}
        (opt.out / 'summary.json').write_text(json.dumps(summary, indent=2))
        print('PASS supplementary Lab3: 32 slots, 16/32-bit traps, fallbacks, interrupt guards, ten reports and shutdown')


if __name__ == '__main__':
    main()
