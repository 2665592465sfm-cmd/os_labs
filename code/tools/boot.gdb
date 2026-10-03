# Run in code/ after `make debug`: $(GCCPREFIX)gdb -x tools/boot.gdb
set pagination off
set confirm off
set architecture riscv:rv64
file bin/kernel
target remote localhost:1234

# QEMU has loaded the firmware and raw kernel before executing the first opcode.
info registers pc
x/10i 0x1000
x/4wx 0x80200000
thbreak *0x80000000
continue
info registers pc a0 a1 a2
thbreak *0x80200000
continue
info registers pc sp ra a0 a1
disassemble kern_entry
si
si
p/x &bootstacktop
info registers sp
si
info registers pc ra
# Continue interactively with `break cprintf`, `continue`, etc.
