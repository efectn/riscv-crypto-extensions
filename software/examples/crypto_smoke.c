#include <stdint.h>
#include <riscv_bitmanip.h>
#include <riscv_crypto.h>

int main(void)
{
    volatile uint32_t *uart = (volatile uint32_t *)0x10000004u;

    // prevent potantial constant folding
    volatile uint32_t value = 0x12345678u, shift = 8;
    volatile uint32_t a = 0xbu, b = 0xdu;
    volatile uint32_t bytes = 0x11223344u, indices = 0x00010203u;
    volatile uint32_t zero = 0;
    
    int failed = 0;

    failed |= __riscv_ror_32(value, shift) != 0x78123456u; // ror
    failed |= __riscv_ror_32(value, 8) != 0x78123456u;     // rori
    failed |= __riscv_clmul_32(a, b) != 0x7fu;
    failed |= __riscv_xperm8_32(bytes, indices) != 0x44332211u;
    failed |= __riscv_sha256sum0(value) != 0x66146474u;
    failed |= __riscv_sm3p0(value) != 0xd6688234u;
    failed |= __riscv_aes32esi(zero, zero, 0) != 0x63u;
    failed |= __riscv_sm4ed(zero, zero, 0) != 0x5b5bd58eu;

    const char *message = failed ? "FAIL\n" : "PASS\n";
    while (*message)
        *uart = (uint8_t)*(message++);

    return failed;
}
