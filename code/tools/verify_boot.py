#!/usr/bin/env python3
"""Exercise the real QEMU/GDB reset-to-kernel flow. Not an official grader."""
import argparse
import hashlib
import json
from pathlib import Path
import re
import socket
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[1]


def run(command, **kwargs):
    return subprocess.run(command, check=True, text=True, encoding='utf-8',
                          errors='replace', stdout=subprocess.PIPE,
                          stderr=subprocess.STDOUT, **kwargs).stdout


def check_gdb(expression, label):
    return (f'if !({expression})\n'
            f'  echo FAIL {label}\\n\n  quit 1\nend\n'
            f'echo PASS {label}\\n\n')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--qemu', default='qemu-system-riscv64')
    parser.add_argument('--gdb', default='riscv64-unknown-elf-gdb')
    parser.add_argument('--objdump')
    parser.add_argument('--loader-mode', choices=['device', 'kernel'], default='device')
    parser.add_argument('--output', default='test-output')
    args = parser.parse_args()
    out = (ROOT / args.output).resolve()
    out.mkdir(parents=True, exist_ok=True)
    objdump = args.objdump or args.gdb.replace('gdb', 'objdump')
    disassembly = run([objdump, '-d', '--disassemble=sbi_console_putchar', 'bin/kernel'], cwd=ROOT)
    match = re.search(r'^\s*([0-9a-f]+):[^\n]*\becall\b', disassembly, re.M)
    if not match:
        raise RuntimeError('No ecall found in sbi_console_putchar')
    ecall = int(match[1], 16)
    (out / 'disassembly.txt').write_text(disassembly, encoding='utf-8')
    versions = {name: run([path, '--version']).splitlines()[0]
                for name, path in [('qemu', args.qemu), ('gdb', args.gdb)]}
    image = (ROOT / 'bin/ucore.img').read_bytes()
    first_word = int.from_bytes(image[:4], 'little')
    with socket.socket() as sock:
        sock.bind(('127.0.0.1', 0))
        port = sock.getsockname()[1]

    commands = 'set pagination off\nset confirm off\nset architecture riscv:rv64\n'
    commands += f'target remote 127.0.0.1:{port}\n'
    commands += 'echo === RESET / PRELOADED IMAGE ===\\n\n'
    commands += 'info registers pc\nx/10i 0x1000\nx/4gx 0x1018\nx/4wx 0x80200000\n'
    commands += check_gdb('$pc == 0x1000', 'reset-pc')
    commands += check_gdb(f'*(unsigned int*)0x80200000 == {first_word}', 'image-already-loaded-at-reset')
    # QEMU 4.1.1 has five reset instructions; later versions have six.
    # Step the observed reset stub until it actually transfers to firmware.
    commands += 'echo === RESET INSTRUCTIONS UNTIL FIRMWARE ===\\n\n'
    commands += ('set $reset_steps = 0\n'
                 'while $pc >= 0x1000 && $pc < 0x1100 && $reset_steps < 16\n'
                 '  si\n  info registers pc\n'
                 '  set $reset_steps = $reset_steps + 1\nend\n')
    commands += check_gdb('$pc == 0x80000000', 'reset-to-opensbi')
    commands += 'info registers pc a0 a1 a2\nx/6i $pc\n'
    commands += 'echo === OPENSBI TO KERNEL ===\\n\n'
    commands += 'watch -l *(unsigned int*)0x80200000\nthbreak *0x80200000\ncontinue\n'
    commands += 'info registers pc sp ra a0 a1\ndisassemble kern_entry\n'
    commands += check_gdb('$pc == 0x80200000', 'kernel-entry')
    commands += 'delete breakpoints\nset $saved_ra = $ra\nsi\nsi\n'
    commands += 'echo === STACK AND TAIL TRANSFER ===\\n\n'
    commands += 'info registers pc sp ra\np/x &bootstack\np/x &bootstacktop\n'
    commands += check_gdb('$sp == (unsigned long)&bootstacktop', 'stack-pointer')
    commands += check_gdb('(unsigned long)&bootstacktop - (unsigned long)&bootstack == 8192', 'stack-size')
    commands += 'thbreak *kern_init\ncontinue\ninfo registers pc sp ra\n'
    commands += check_gdb('$pc == (unsigned long)&kern_init && $ra == $saved_ra', 'tail-does-not-write-ra')
    commands += 'printf "BSS range: edata=0x%lx end=0x%lx bytes=%ld\\n", &edata, &end, (long)&end - (long)&edata\n'
    commands += 'echo === C PRINTF ===\\n\nthbreak *cprintf\ncontinue\n'
    commands += 'info registers pc sp a0 a1\nx/s $a0\nx/s $a1\nbt\n'
    commands += check_gdb('$pc == (unsigned long)&cprintf', 'cprintf-reached')
    commands += f'echo === SBI ECALL ===\\n\nthbreak *0x{ecall:x}\ncontinue\n'
    commands += 'info registers pc a0 a7\n'
    commands += check_gdb('$a7 == 1 && $a0 == 40', 'legacy-sbi-putchar-arguments')
    # QEMU/GDB combinations differ in whether stepi stops inside an ecall
    # handler. If CSR registers are available, break at the actual mtvec entry.
    # Older Windows GDB builds without target XML retain the measured fallback.
    if 'version 4.1.1' in versions['qemu']:
        # Its stub exposes CSR names but returns E14 for M-mode CSR reads
        # while halted in S-mode. Observe the ecall directly instead.
        commands += 'si\ninfo registers pc\n'
    else:
        commands += ('if $_isvoid($mtvec)\n  si\nelse\n'
                     '  set $trap_entry = (unsigned long)$mtvec & ~3\n'
                     '  printf "Firmware trap entry: 0x%lx\\n", $trap_entry\n'
                     '  thbreak *$trap_entry\n  continue\nend\ninfo registers pc\n')
    commands += check_gdb('$pc >= 0x80000000 && $pc < 0x80200000', 'ecall-traps-to-firmware')
    commands += f'thbreak *0x{ecall + 4:x}\ncontinue\ninfo registers pc\n'
    commands += check_gdb(f'$pc == 0x{ecall + 4:x}', 'sbi-returns-to-kernel')
    commands += 'detach\nquit\n'
    (out / 'boot-session.gdb').write_text(commands, encoding='utf-8')
    qemu_command = [args.qemu, '-machine', 'virt', '-m', '128M', '-smp', '1',
                    '-nographic', '-bios', 'default', '-monitor', 'none',
                    '-d', 'int', '-D', str(out / 'traps.log'),
                    '-S', '-gdb', f'tcp:127.0.0.1:{port}']
    if args.loader_mode == 'device':
        qemu_command += ['-device', 'loader,file=bin/ucore.img,addr=0x80200000']
    else:
        qemu_command += ['-kernel', 'bin/ucore.img']
    with (out / 'qemu.log').open('wb') as serial:
        process = subprocess.Popen(qemu_command, cwd=ROOT, stdout=serial,
                                   stderr=subprocess.STDOUT, stdin=subprocess.DEVNULL)
        try:
            # TCP connect only checks readiness; QEMU accepts the later GDB session.
            deadline = time.monotonic() + 15
            while True:
                if process.poll() is not None:
                    raise RuntimeError('QEMU exited before GDB connection')
                try:
                    with socket.create_connection(('127.0.0.1', port), timeout=0.2):
                        break
                except OSError:
                    if time.monotonic() > deadline:
                        raise TimeoutError('QEMU GDB server did not become ready')
                    time.sleep(0.1)
            with (out / 'gdb.log').open('wb') as transcript:
                result = subprocess.run([args.gdb, '-q', '-batch', 'bin/kernel', '-x',
                                         str(out / 'boot-session.gdb')], cwd=ROOT,
                                        stdout=transcript, stderr=subprocess.STDOUT, timeout=60)
            result.stdout = (out / 'gdb.log').read_text(encoding='utf-8', errors='replace')
            if result.returncode:
                print(result.stdout)
                raise RuntimeError(f'GDB verification failed ({result.returncode})')
            deadline = time.monotonic() + 5
            while time.monotonic() < deadline:
                if b'(THU.CST) os is loading ...' in (out / 'qemu.log').read_bytes():
                    break
                time.sleep(0.1)
        finally:
            process.terminate()
            try:
                process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait(timeout=5)
    serial_output = (out / 'qemu.log').read_text(encoding='utf-8', errors='replace')
    if '(THU.CST) os is loading ...' not in serial_output:
        raise RuntimeError('Kernel startup message not present')
    checks = re.findall(r'^PASS (.+)$', result.stdout, re.M)
    if len(checks) != 11:
        raise RuntimeError(f'Expected 11 GDB checks, received {len(checks)}')
    traps = (out / 'traps.log').read_text(encoding='utf-8', errors='replace')
    if not re.search(rf'cause:0*9, epc:0x0*{ecall:x}\b', traps):
        raise RuntimeError('QEMU trace did not confirm an ecall from S-mode (cause=9)')
    summary = {'versions': versions, 'checks': checks + ['kernel-startup-message', 'supervisor-ecall-cause-9'],
               'passed': True, 'kernel_sha256': hashlib.sha256(image).hexdigest(),
               'qemu_command': qemu_command,
               'note': 'Local checks only; no course tools/grade.sh was provided.'}
    (out / 'summary.json').write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding='utf-8')
    print('\n'.join('PASS ' + item for item in summary['checks']))
    print(f'{len(summary["checks"])} local checks passed; logs: {out}')


if __name__ == '__main__':
    main()
