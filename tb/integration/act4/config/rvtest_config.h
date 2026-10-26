// SPDX-License-Identifier: Apache-2.0
// Minimal ACT4 environment for the standalone RV32 M and scalar crypto runner.
// Privileged, counter, and interrupt suites are outside its scope.
#ifndef CV32E40X_CRYPTO_RVTEST_CONFIG_H
#define CV32E40X_CRYPTO_RVTEST_CONFIG_H
#define UDB_MXLEN 32
#define UDB_MXLEN_32
#define UDB_NUM_PMP_ENTRIES 0
#define UDB_MTVEC_MODES_0
#define UDB_MTVEC_MODES_1
#define UDB_MTVEC_BASE_ALIGNMENT_DIRECT 128
#define UDB_MTVEC_BASE_ALIGNMENT_VECTORED 128
#define UDB_MCOUNTINHIBIT_IMPLEMENTED
#define I_SUPPORTED
#define M_SUPPORTED
#define ZMMUL_SUPPORTED
#define C_SUPPORTED
#define ZICSR_SUPPORTED
#define ZIFENCEI_SUPPORTED
#define SM_SUPPORTED
#define SM1P12P0_SUPPORTED
#define ZBKB_SUPPORTED
#define ZBKC_SUPPORTED
#define ZBKX_SUPPORTED
#define ZKND_SUPPORTED
#define ZKNE_SUPPORTED
#define ZKNH_SUPPORTED
#define ZKSED_SUPPORTED
#define ZKSH_SUPPORTED
#endif
