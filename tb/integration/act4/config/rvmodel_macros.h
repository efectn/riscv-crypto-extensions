// SPDX-License-Identifier: Apache-2.0
#ifndef CV32E40X_CRYPTO_RVMODEL_MACROS_H
#define CV32E40X_CRYPTO_RVMODEL_MACROS_H

#define STANDARD_SM_SUPPORTED
#define RVMODEL_DATA_SECTION
#define RVMODEL_MTVEC_ALIGN 7
#define RVMODEL_INTERRUPT_LATENCY 1
#define RVMODEL_TIMER_INT_SOON_DELAY 10000

// sim_model/main.cpp: zero means success; nonzero means failure.
#define RVMODEL_HALT_PASS \
    LI(t0, 0x10000000); \
    sw zero, 0(t0); \
    1: j 1b
#define RVMODEL_HALT_FAIL \
    LI(t0, 0x10000000); \
    LI(t1, 1); \
    sw t1, 0(t0); \
    1: j 1b

#define RVMODEL_IO_INIT(_R1, _R2, _R3)
#define RVMODEL_IO_WRITE_STR(_R1, _R2, _R3, _STR_PTR) \
    LI(_R2, 0x10000004); \
    1: lbu _R1, 0(_STR_PTR); \
    beqz _R1, 2f; \
    sw _R1, 0(_R2); \
    addi _STR_PTR, _STR_PTR, 1; \
    j 1b; \
    2:

#endif
