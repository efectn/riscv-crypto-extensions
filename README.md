# RTL Implementation of RISC-V Scalar Cryptography Extension

This project aims to implement the RISC-V Scalar Cryptography Extension (Zks) in RTL. The extension provides a set of instructions for performing cryptographic operations efficiently on RISC-V processors. RV32 instructions are the targetted subset and the implementation is done in SystemVerilog using CV32340X scalar core.

* All discrete units are tested using CocoTB tests located in [tb/cocotb](./tb/cocotb/) and more detailed instruction integration tests will eventually be added by comparing Spike and RTL simulation results after CV32E40X core integration.

* Zkn, Zks and Zkr subsets are currently planned to get implemented. All subsets will also get implemented according to the timing rules given in [Zkt extension specification](https://docs.riscv.org/reference/isa/v20260120/unpriv/scalar-crypto.html#crypto_scalar_zkt) section.

* It is planned to implement some PQC algorithms in the future after finalizing the Zks extension implementation.


## To-do List:

- [x] Implement crypto units
    - [x] AES unit
    - [x] SHA unit
    - [x] ShaMing hash unit 
    - [x] ShaMing crypto unit
    - [x] Xperm unit
    - [x] Clmul unit
    - [x] Bitmap unit
- [ ] Implement unit tests for each crypto unit
    - [ ] AES unit
    - [x] SHA unit
    - [x] ShaMing hash unit 
    - [ ] ShaMing crypto unit
    - [x] Xperm unit
    - [x] Clmul unit
    - [x] Bitmap unit
- [ ] Scalar core integration
    - [ ] Clone CV32E40X core and make it executable under Verilator with simple memory model
    - [ ] Investigate XIF interface and implement it as MVP
    - [ ] Create decoder unit for crypto co-processor
    - [ ] Improve XIF connection to core and memory model
- [ ] Integration tests