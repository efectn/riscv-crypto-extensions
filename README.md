# RTL Implementation of RISC-V Scalar Cryptography Extension

This project aims to implement the RISC-V Scalar Cryptography Extension (Zks) in RTL. The extension provides a set of instructions for performing cryptographic operations efficiently on RISC-V processors. RV32 instructions are the targetted subset and the implementation is done in SystemVerilog using CV32340X scalar core.

* All discrete units are tested using CocoTB tests located in [tb/cocotb](./tb/cocotb/) and more detailed instruction integration tests will eventually be added by comparing Spike and RTL simulation results after CV32E40X core integration.

* Zkn, Zks and Zkr subsets are currently planned to get implemented. All subsets will also get implemented according to the timing rules given in [Zkt extension specification](https://docs.riscv.org/reference/isa/v20260120/unpriv/scalar-crypto.html#crypto_scalar_zkt) section.

* It is planned to implement some PQC algorithms in the future after finalizing the Zks extension implementation.

## Project Structure

```
├── rtl/                    # SystemVerilog sources
│   ├── common/             # Shared packages and helper functions
│   └── units/              # Crypto units and S-box helpers
│       ├── misc/           # AES and SM4 helper modules
│       ├── aes_crypto_unit.sv
│       ├── bitmap_unit.sv
│       ├── clmul_unit.sv
│       ├── nist_hash_unit.sv
│       ├── shangmi_crypto_unit.sv
│       ├── shangmi_hash_unit.sv
│       └── xperm_unit.sv
├── tb/
│   └── cocotb/             # Cocotb unit tests and test helpers
├── sim/                    # Simulator file lists
├── Makefile                # Test and waveform commands
├── LICENSE
└── README.md
```

## To-do List:

- [x] Implement crypto units
    - [x] AES unit
    - [x] SHA unit
    - [x] Shangmi hash unit
    - [x] Shangmi crypto unit
    - [x] Xperm unit
    - [x] Clmul unit
    - [x] Bitmap unit
- [x] Implement unit tests for each crypto unit
    - [x] AES unit
    - [x] SHA unit
    - [x] Shangmi hash unit
    - [x] Shangmi crypto unit
    - [x] Xperm unit
    - [x] Clmul unit
    - [x] Bitmap unit
- [ ] Scalar core integration
    - [ ] **Clone CV32E40X core and make it executable under Verilator with simple memory model**
    - [ ] Investigate XIF interface and implement it with simple dummy interface
    - [ ] Create decoder unit for crypto co-processor
    - [ ] Create datapath including all the subunits
        - [ ] Test datapath with mock signals.
    - [ ] Implement controller unit for crypto co-processor
        - [ ] Imlement it as simple FSM like IDLE -> WAIT_COMMIT -> DISPATCH -> RUN states with only one outstanding instruction at a time
        - [ ] Improve controller to support multiple outstanding instructions by adding FIFO, scoreboard etc.
        - [ ] Test controller with mock signals
    - [ ] Integrate decoder, datapath and controller units to create a complete crypto co-processor
        - [ ] Test crypto co-processor with mock signals.
        - [ ] Connect it to real XIF interface and test it with real signals using the CV32E40X core
    - [ ] Improve XIF connection to core and memory model
- [ ] Integration tests
