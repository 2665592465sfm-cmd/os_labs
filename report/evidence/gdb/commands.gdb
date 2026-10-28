set pagination off
set confirm off
set print pretty on
set trace-commands on
set architecture riscv:rv64
target remote localhost:1237
thbreak *__alltraps
continue
set $before_ra = $ra
set $before_sp = $sp
set $before_gp = $gp
set $before_tp = $tp
set $before_t0 = $t0
set $before_t1 = $t1
set $before_t2 = $t2
set $before_s0 = $s0
set $before_s1 = $s1
set $before_a0 = $a0
set $before_a1 = $a1
set $before_a2 = $a2
set $before_a3 = $a3
set $before_a4 = $a4
set $before_a5 = $a5
set $before_a6 = $a6
set $before_a7 = $a7
set $before_s2 = $s2
set $before_s3 = $s3
set $before_s4 = $s4
set $before_s5 = $s5
set $before_s6 = $s6
set $before_s7 = $s7
set $before_s8 = $s8
set $before_s9 = $s9
set $before_s10 = $s10
set $before_s11 = $s11
set $before_t3 = $t3
set $before_t4 = $t4
set $before_t5 = $t5
set $before_t6 = $t6
set $old_epc = $sepc
set $old_status = $sstatus
printf "TRAP ENTRY\n"
p/x $pc
p/x $sp
p/x $sepc
p/x $sstatus
p/x $scause
thbreak *trap
continue
set $tf = (struct trapframe *)$a0
printf "C ENTRY AND FRAME\n"
p sizeof(struct trapframe)
p/x $a0
p/x $sp
p/x *$tf
if !(sizeof(struct trapframe) == 288 && $a0 == $sp && $sp == $before_sp - 288)
  printf "FAIL: frame layout or ABI argument\n"
  quit 1
end
if !($tf->gpr.sp == $before_sp && $tf->epc == $old_epc)
  printf "FAIL: saved sp or epc\n"
  quit 1
end
if !($tf->cause == 0x8000000000000005 && ($tf->status & 0x100) != 0)
  printf "FAIL: expected S-mode timer\n"
  quit 1
end
thbreak *__trapret
continue
printf "C RETURN\n"
p ticks
p/x $tf->epc
if !(ticks == 1 && $tf->epc == $old_epc)
  printf "FAIL: timer count or wrongly advanced timer epc\n"
  quit 1
end
thbreak *0xffffffffc0200cda
continue
printf "BEFORE SRET\n"
p/x $sp
p/x $sepc
p/x $sstatus
if !($ra == $before_ra)
  printf "FAIL: restored ra\n"
  quit 1
end
if !($sp == $before_sp)
  printf "FAIL: restored sp\n"
  quit 1
end
if !($gp == $before_gp)
  printf "FAIL: restored gp\n"
  quit 1
end
if !($tp == $before_tp)
  printf "FAIL: restored tp\n"
  quit 1
end
if !($t0 == $before_t0)
  printf "FAIL: restored t0\n"
  quit 1
end
if !($t1 == $before_t1)
  printf "FAIL: restored t1\n"
  quit 1
end
if !($t2 == $before_t2)
  printf "FAIL: restored t2\n"
  quit 1
end
if !($s0 == $before_s0)
  printf "FAIL: restored s0\n"
  quit 1
end
if !($s1 == $before_s1)
  printf "FAIL: restored s1\n"
  quit 1
end
if !($a0 == $before_a0)
  printf "FAIL: restored a0\n"
  quit 1
end
if !($a1 == $before_a1)
  printf "FAIL: restored a1\n"
  quit 1
end
if !($a2 == $before_a2)
  printf "FAIL: restored a2\n"
  quit 1
end
if !($a3 == $before_a3)
  printf "FAIL: restored a3\n"
  quit 1
end
if !($a4 == $before_a4)
  printf "FAIL: restored a4\n"
  quit 1
end
if !($a5 == $before_a5)
  printf "FAIL: restored a5\n"
  quit 1
end
if !($a6 == $before_a6)
  printf "FAIL: restored a6\n"
  quit 1
end
if !($a7 == $before_a7)
  printf "FAIL: restored a7\n"
  quit 1
end
if !($s2 == $before_s2)
  printf "FAIL: restored s2\n"
  quit 1
end
if !($s3 == $before_s3)
  printf "FAIL: restored s3\n"
  quit 1
end
if !($s4 == $before_s4)
  printf "FAIL: restored s4\n"
  quit 1
end
if !($s5 == $before_s5)
  printf "FAIL: restored s5\n"
  quit 1
end
if !($s6 == $before_s6)
  printf "FAIL: restored s6\n"
  quit 1
end
if !($s7 == $before_s7)
  printf "FAIL: restored s7\n"
  quit 1
end
if !($s8 == $before_s8)
  printf "FAIL: restored s8\n"
  quit 1
end
if !($s9 == $before_s9)
  printf "FAIL: restored s9\n"
  quit 1
end
if !($s10 == $before_s10)
  printf "FAIL: restored s10\n"
  quit 1
end
if !($s11 == $before_s11)
  printf "FAIL: restored s11\n"
  quit 1
end
if !($t3 == $before_t3)
  printf "FAIL: restored t3\n"
  quit 1
end
if !($t4 == $before_t4)
  printf "FAIL: restored t4\n"
  quit 1
end
if !($t5 == $before_t5)
  printf "FAIL: restored t5\n"
  quit 1
end
if !($t6 == $before_t6)
  printf "FAIL: restored t6\n"
  quit 1
end
if !($sepc == $old_epc && ($sstatus & 0x100) != 0 && ($sstatus & 2) == 0)
  printf "FAIL: pre-sret CSR state\n"
  quit 1
end
thbreak *$old_epc
si
printf "AFTER SRET\n"
p/x $pc
p/x $sp
p/x $sstatus
if !($pc == $old_epc && $sp == $before_sp)
  printf "FAIL: sret execution position or stack\n"
  quit 1
end
if !(($sstatus & 2) != 0 && ($sstatus & 0x100) == 0)
  printf "FAIL: sret SIE/SPP state\n"
  quit 1
end
printf "PASS: real timer frame, 31 writable GPRs, unchanged EPC and sret return\n"
detach
quit
