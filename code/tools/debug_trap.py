#!/usr/bin/env python3
"""Observe a real S-timer trap from entry through sret using hardware breakpoints."""
from pathlib import Path
import argparse
import json
import re
import subprocess
import tempfile


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--out', type=Path, required=True)
    parser.add_argument('--qemu', default='qemu-system-riscv64')
    parser.add_argument('--port', type=int, default=1237)
    opt = parser.parse_args()
    root = Path(__file__).resolve().parents[1]
    opt.out = opt.out.resolve()
    opt.out.mkdir(parents=True, exist_ok=True)
    asm = subprocess.check_output(['riscv64-unknown-elf-objdump', '-d', 'bin/kernel'], cwd=root, text=True)
    body = asm.split('<__trapret>:', 1)[1].split('\n\n', 1)[0]
    match = re.search(r'^\s*([0-9a-f]+):.*\bsret\b', body, re.M)
    assert match, 'Cannot locate actual sret instruction'
    sret = int(match.group(1), 16)
    registers = ['zero', 'ra', 'sp', 'gp', 'tp', 't0', 't1', 't2', 's0', 's1',
                 'a0', 'a1', 'a2', 'a3', 'a4', 'a5', 'a6', 'a7',
                 's2', 's3', 's4', 's5', 's6', 's7', 's8', 's9', 's10', 's11', 't3', 't4', 't5', 't6']

    def check(expression, message):
        return [f'if !({expression})', f'  printf "FAIL: {message}\\n"', '  quit 1', 'end']

    commands = ['set pagination off', 'set confirm off', 'set print pretty on', 'set trace-commands on',
                'set architecture riscv:rv64', f'target remote localhost:{opt.port}',
                'thbreak *__alltraps', 'continue']
    commands += [f'set $before_{name} = ${name}' for name in registers[1:]]
    commands += ['set $old_epc = $sepc', 'set $old_status = $sstatus',
                 'printf "TRAP ENTRY\\n"', 'p/x $pc', 'p/x $sp', 'p/x $sepc', 'p/x $sstatus', 'p/x $scause',
                 'thbreak *trap', 'continue', 'set $tf = (struct trapframe *)$a0',
                 'printf "C ENTRY AND FRAME\\n"', 'p sizeof(struct trapframe)', 'p/x $a0', 'p/x $sp', 'p/x *$tf']
    commands += check('sizeof(struct trapframe) == 288 && $a0 == $sp && $sp == $before_sp - 288', 'frame layout or ABI argument')
    commands += check('$tf->gpr.sp == $before_sp && $tf->epc == $old_epc', 'saved sp or epc')
    commands += check('$tf->cause == 0x8000000000000005 && ($tf->status & 0x100) != 0', 'expected S-mode timer')
    commands += ['thbreak *__trapret', 'continue', 'printf "C RETURN\\n"', 'p ticks', 'p/x $tf->epc']
    commands += check('ticks == 1 && $tf->epc == $old_epc', 'timer count or wrongly advanced timer epc')
    commands += [f'thbreak *{sret:#x}', 'continue', 'printf "BEFORE SRET\\n"', 'p/x $sp', 'p/x $sepc', 'p/x $sstatus']
    for name in registers[1:]:
        commands += check(f'${name} == $before_{name}', 'restored ' + name)
    commands += check('$sepc == $old_epc && ($sstatus & 0x100) != 0 && ($sstatus & 2) == 0', 'pre-sret CSR state')
    # QEMU 4.1.1 may run through a privilege-return single step without a
    # debugger stop. A temporary hardware breakpoint at the saved return PC
    # provides an independent stop without changing guest instructions.
    commands += ['thbreak *$old_epc', 'si', 'printf "AFTER SRET\\n"', 'p/x $pc', 'p/x $sp', 'p/x $sstatus']
    commands += check('$pc == $old_epc && $sp == $before_sp', 'sret execution position or stack')
    commands += check('($sstatus & 2) != 0 && ($sstatus & 0x100) == 0', 'sret SIE/SPP state')
    commands += ['printf "PASS: real timer frame, 31 writable GPRs, unchanged EPC and sret return\\n"', 'detach', 'quit']
    qargs = [opt.qemu, '-machine', 'virt', '-nographic', '-bios', 'default',
             '-device', 'loader,file=bin/ucore.img,addr=0x80200000', '-S', '-gdb', f'tcp:127.0.0.1:{opt.port}']
    process = None
    with tempfile.TemporaryDirectory(prefix='lab3-gdb-') as directory, (opt.out / 'qemu.txt').open('w') as serial:
        command_file = Path(directory) / 'trap.gdb'
        command_file.write_text('\n'.join(commands) + '\n')
        (opt.out / 'commands.gdb').write_text(command_file.read_text())
        try:
            process = subprocess.Popen(qargs, cwd=root, stdin=subprocess.DEVNULL, stdout=serial, stderr=subprocess.STDOUT)
            # GDB's remote timeout handles target startup; no ptrace attachment is used.
            result = subprocess.run(['riscv64-unknown-elf-gdb', '-q', '-nx', '-batch', 'bin/kernel',
                                     '-ex', 'set remotetimeout 10', '-x', str(command_file)],
                                    cwd=root, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, timeout=35)
            (opt.out / 'gdb.txt').write_text(result.stdout)
            result.check_returncode()
            assert 'PASS: real timer frame' in result.stdout
            assert process.wait(timeout=20) == 0
        finally:
            if process and process.poll() is None:
                process.kill()
                process.wait()
    (opt.out / 'summary.json').write_text(json.dumps({'passed': True, 'port': opt.port, 'trapframe_bytes': 288,
        'writable_integer_registers_checked': 31, 'actual_timer': True, 'ticks_at_first_return': 1,
        'timer_epc_unchanged': True, 'sret_address': hex(sret), 'sret_single_step': True,
        'stack_restored': True, 'sie_restored': True, 'spp_cleared_by_sret': True}, indent=2))
    print('PASS GDB: real S-timer, frame/ABI, 31 GPRs, CSR and sret single-step')


if __name__ == '__main__':
    main()
