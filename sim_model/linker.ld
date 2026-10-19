OUTPUT_ARCH(riscv)
ENTRY(_start)

MEMORY
{
    RAM (rwx) : ORIGIN = 0, LENGTH = __memory_size
}

SECTIONS
{
    .vectors 0 : { KEEP(*(.vectors)) } > RAM
    .text 0x100 : {
        KEEP(*(.text.start))
        *(.text .text.*)
    } > RAM

    .rodata : { *(.rodata .rodata.*) } > RAM

    .data : {
        . = ALIGN(4);
        __global_pointer$ = . + 0x800;
        *(.sdata .sdata.* .data .data.*)
    } > RAM

    .bss (NOLOAD) : {
        . = ALIGN(4);
        __bss_start = .;
        *(.sbss .sbss.* .bss .bss.* COMMON)
        . = ALIGN(4);
        __bss_end = .;
    } > RAM

    __stack_top = (ORIGIN(RAM) + LENGTH(RAM)) & ~15;
    __stack_bottom = __stack_top - 4096;
    
    ASSERT(__bss_end <= __stack_bottom, "Program overlaps the 4 KiB stack")
    /DISCARD/ : { *(.comment .eh_frame .eh_frame.*) }
}
