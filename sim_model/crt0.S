    .section .vectors, "ax", @progbits
    .balign 4
    j _trap

    .section .text.start, "ax", @progbits
    .globl _start
    .type _start, @function
_start:
    .option push
    .option norelax
    la gp, __global_pointer$
    .option pop
    la sp, __stack_top

    // .data is loaded directly into RAM by the VMEM loader
    la t0, __bss_start
    la t1, __bss_end
1:
    // clear the .bss section
    bgeu t0, t1, 2f
    sw zero, 0(t0)
    addi t0, t0, 4
    j 1b
2:
    call main

    // forward return value to the exit register
    li t0, 0x10000000
    sw a0, 0(t0)
3:
    j 3b
    .size _start, . - _start

    .type _trap, @function
_trap:
    // report an unexpected synchronous exception as failure
    li t0, 0x10000000
    li t1, 100
    sw t1, 0(t0)
4:
    j 4b
    .size _trap, . - _trap
