set pagination off
set confirm off
set architecture riscv:rv64
target remote 127.0.0.1:55427
echo === RESET / PRELOADED IMAGE ===\n
info registers pc
x/10i 0x1000
x/4gx 0x1018
x/4wx 0x80200000
if !($pc == 0x1000)
  echo FAIL reset-pc\n
  quit 1
end
echo PASS reset-pc\n
if !(*(unsigned int*)0x80200000 == 12567)
  echo FAIL image-already-loaded-at-reset\n
  quit 1
end
echo PASS image-already-loaded-at-reset\n
echo === SIX RESET INSTRUCTIONS ===\n
si
info registers pc
si
info registers pc
si
info registers pc
si
info registers pc
si
info registers pc
si
info registers pc
if !($pc == 0x80000000)
  echo FAIL reset-to-opensbi\n
  quit 1
end
echo PASS reset-to-opensbi\n
info registers pc a0 a1 a2
x/6i $pc
echo === OPENSBI TO KERNEL ===\n
watch -l *(unsigned int*)0x80200000
thbreak *0x80200000
continue
info registers pc sp ra a0 a1
disassemble kern_entry
if !($pc == 0x80200000)
  echo FAIL kernel-entry\n
  quit 1
end
echo PASS kernel-entry\n
delete breakpoints
set $saved_ra = $ra
si
si
echo === STACK AND TAIL TRANSFER ===\n
info registers pc sp ra
p/x &bootstack
p/x &bootstacktop
if !($sp == (unsigned long)&bootstacktop)
  echo FAIL stack-pointer\n
  quit 1
end
echo PASS stack-pointer\n
if !((unsigned long)&bootstacktop - (unsigned long)&bootstack == 8192)
  echo FAIL stack-size\n
  quit 1
end
echo PASS stack-size\n
thbreak *kern_init
continue
info registers pc sp ra
if !($pc == (unsigned long)&kern_init && $ra == $saved_ra)
  echo FAIL tail-does-not-write-ra\n
  quit 1
end
echo PASS tail-does-not-write-ra\n
printf "BSS range: edata=0x%lx end=0x%lx bytes=%ld\n", &edata, &end, (long)&end - (long)&edata
echo === C PRINTF ===\n
thbreak *cprintf
continue
info registers pc sp a0 a1
x/s $a0
x/s $a1
bt
if !($pc == (unsigned long)&cprintf)
  echo FAIL cprintf-reached\n
  quit 1
end
echo PASS cprintf-reached\n
echo === SBI ECALL ===\n
thbreak *0x80200492
continue
info registers pc a0 a7
if !($a7 == 1 && $a0 == 40)
  echo FAIL legacy-sbi-putchar-arguments\n
  quit 1
end
echo PASS legacy-sbi-putchar-arguments\n
if $_isvoid($mtvec)
  si
else
  set $trap_entry = (unsigned long)$mtvec & ~3
  printf "Firmware trap entry: 0x%lx\n", $trap_entry
  thbreak *$trap_entry
  continue
end
info registers pc
if !($pc >= 0x80000000 && $pc < 0x80200000)
  echo FAIL ecall-traps-to-firmware\n
  quit 1
end
echo PASS ecall-traps-to-firmware\n
thbreak *0x80200496
continue
info registers pc
if !($pc == 0x80200496)
  echo FAIL sbi-returns-to-kernel\n
  quit 1
end
echo PASS sbi-returns-to-kernel\n
detach
quit
