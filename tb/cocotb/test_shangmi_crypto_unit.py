import cocotb

from cocotb.clock import Clock
from cocotb.triggers import (
    Timer,
    RisingEdge,
    FallingEdge,
    ClockCycles,
    ReadOnly,
)

from enum import Enum
class ShangmiCryptoOperands(Enum):
    SM4ED = 0
    SM4KS = 1
    
# Random test data element
class TestData:
    def __init__(self, rs1: int, rs2: int, expected_result: int, bs: int = 0):
        self.rs1 = rs1
        self.rs2 = rs2
        self.expected_result = expected_result
        self.bs = bs

SM4_SBOX = (
    0xD6, 0x90, 0xE9, 0xFE, 0xCC, 0xE1, 0x3D, 0xB7, 0x16, 0xB6, 0x14, 0xC2, 0x28, 0xFB, 0x2C, 0x05,
    0x2B, 0x67, 0x9A, 0x76, 0x2A, 0xBE, 0x04, 0xC3, 0xAA, 0x44, 0x13, 0x26, 0x49, 0x86, 0x06, 0x99,
    0x9C, 0x42, 0x50, 0xF4, 0x91, 0xEF, 0x98, 0x7A, 0x33, 0x54, 0x0B, 0x43, 0xED, 0xCF, 0xAC, 0x62,
    0xE4, 0xB3, 0x1C, 0xA9, 0xC9, 0x08, 0xE8, 0x95, 0x80, 0xDF, 0x94, 0xFA, 0x75, 0x8F, 0x3F, 0xA6,
    0x47, 0x07, 0xA7, 0xFC, 0xF3, 0x73, 0x17, 0xBA, 0x83, 0x59, 0x3C, 0x19, 0xE6, 0x85, 0x4F, 0xA8,
    0x68, 0x6B, 0x81, 0xB2, 0x71, 0x64, 0xDA, 0x8B, 0xF8, 0xEB, 0x0F, 0x4B, 0x70, 0x56, 0x9D, 0x35,
    0x1E, 0x24, 0x0E, 0x5E, 0x63, 0x58, 0xD1, 0xA2, 0x25, 0x22, 0x7C, 0x3B, 0x01, 0x21, 0x78, 0x87,
    0xD4, 0x00, 0x46, 0x57, 0x9F, 0xD3, 0x27, 0x52, 0x4C, 0x36, 0x02, 0xE7, 0xA0, 0xC4, 0xC8, 0x9E,
    0xEA, 0xBF, 0x8A, 0xD2, 0x40, 0xC7, 0x38, 0xB5, 0xA3, 0xF7, 0xF2, 0xCE, 0xF9, 0x61, 0x15, 0xA1,
    0xE0, 0xAE, 0x5D, 0xA4, 0x9B, 0x34, 0x1A, 0x55, 0xAD, 0x93, 0x32, 0x30, 0xF5, 0x8C, 0xB1, 0xE3,
    0x1D, 0xF6, 0xE2, 0x2E, 0x82, 0x66, 0xCA, 0x60, 0xC0, 0x29, 0x23, 0xAB, 0x0D, 0x53, 0x4E, 0x6F,
    0xD5, 0xDB, 0x37, 0x45, 0xDE, 0xFD, 0x8E, 0x2F, 0x03, 0xFF, 0x6A, 0x72, 0x6D, 0x6C, 0x5B, 0x51,
    0x8D, 0x1B, 0xAF, 0x92, 0xBB, 0xDD, 0xBC, 0x7F, 0x11, 0xD9, 0x5C, 0x41, 0x1F, 0x10, 0x5A, 0xD8,
    0x0A, 0xC1, 0x31, 0x88, 0xA5, 0xCD, 0x7B, 0xBD, 0x2D, 0x74, 0xD0, 0x12, 0xB8, 0xE5, 0xB4, 0xB0,
    0x89, 0x69, 0x97, 0x4A, 0x0C, 0x96, 0x77, 0x7E, 0x65, 0xB9, 0xF1, 0x09, 0xC5, 0x6E, 0xC6, 0x84,
    0x18, 0xF0, 0x7D, 0xEC, 0x3A, 0xDC, 0x4D, 0x20, 0x79, 0xEE, 0x5F, 0x3E, 0xD7, 0xCB, 0x39, 0x48
)

def rol32(x: int, n: int):
    x &= 0xFFFFFFFF
    n &= 31
    return ((x << n) | (x >> (32 - n))) & 0xFFFFFFFF

# Simple golden model for RISC-V Zksed extension instructions
def golden_shangmi_crypto_unit(rs1: int, rs2: int, bs: int, operand: ShangmiCryptoOperands):
    rs1 &= 0xFFFFFFFF
    rs2 &= 0xFFFFFFFF
    bs &= 0x3
    rd = 0

    shamt = bs * 8
    sb_in = (rs2 >> shamt) & 0xFF
    x = SM4_SBOX[sb_in]

    if operand == ShangmiCryptoOperands.SM4ED:
        y = (x ^ (x << 8) ^ (x << 2) ^
             (x << 18) ^ ((x & 0x3F) << 26) ^
             ((x & 0xC0) << 10))
    elif operand == ShangmiCryptoOperands.SM4KS:
        y = (x ^ ((x & 0x07) << 29) ^
             ((x & 0xFE) << 7) ^
             ((x & 0x01) << 23) ^
             ((x & 0xF8) << 13))
    else:
        raise ValueError(f"Unsupported operand: {operand}")

    return (rs1 ^ rol32(y, shamt)) & 0xFFFFFFFF

def generate_test_vectors(num_vectors: int, operand: ShangmiCryptoOperands):
    import random
    random.seed(0x5678_9ABC) # TODO: Make this a parameter
    
    vectors = []
    for _ in range(num_vectors):
        rs1 = random.getrandbits(32)
        rs2 = random.getrandbits(32)
        bs = random.randint(0, 3)
        expected_result = golden_shangmi_crypto_unit(rs1, rs2, bs, operand)
        vectors.append(TestData(rs1, rs2, expected_result, bs))
    return vectors

async def reset_values(dut):
    dut.rst_ni.value = 0 # Reset the DUT
    dut.valid_i.value = 0
    dut.ready_i.value = 0
    dut.op_i.value = 0
    dut.rs1_i.value = 0
    dut.rs2_i.value = 0
    dut.aux_i.value = 0
    dut.op_q.value = 0
    dut.rs1_q.value = 0
    dut.rs2_q.value = 0
    dut.state_q.value = 0
    dut.stage0_q.value = 0
    dut.stage0_d.value = 0
    dut.sbox_in.value = 0

    await ClockCycles(dut.clk_i, 3)
    await FallingEdge(dut.clk_i)
    
    dut.rst_ni.value = 1 # Release reset
    
    await Timer(1, unit="ns") # wait a bit
    
    assert int(dut.ready_o.value) == 1, "DUT not ready after reset"
    
@cocotb.test()
async def shangmi_crypto_unit_test_sm4ed(dut):
    clk = Clock(dut.clk_i, 10, unit="ns") # 100 MHz clock
    clk.start()
    
    await reset_values(dut) # Reset the DUT
    
    test_vectors = generate_test_vectors(50, ShangmiCryptoOperands.SM4ED)
    
    # Add specific edge case test vectors
    test_vectors.append(TestData(rs1=0x00000000, rs2=0x00000000, expected_result=0x5B5BD58E, bs=0)) # Zero input
    test_vectors.append(TestData(rs1=0x00000000, rs2=0x0000FF00, expected_result=0x21496821, bs=1)) # S-box input FF
    test_vectors.append(TestData(rs1=0xFFFFFFFF, rs2=0x00000000, expected_result=0x2A71A4A4, bs=2)) # XOR with all ones
    test_vectors.append(TestData(rs1=0x00000000, rs2=0x80000000, expected_result=0x42ABABE9, bs=3)) # Highest byte selection
    test_vectors.append(TestData(rs1=0x12345678, rs2=0xDEADBEEF, expected_result=0x402B1B35, bs=2)) # Mixed bit pattern
    
    for bs in range(4):
        for byte in range(256):
            rs1 = 0
            rs2 = byte << (bs * 8) # sbox input is byte >> (bs * 8) in verilog model, so we just do the inverse here to have all possible sbox inputs

            expected = golden_shangmi_crypto_unit(
                rs1, rs2, bs, ShangmiCryptoOperands.SM4ED
            )

            test_vectors.append(
                TestData(rs1, rs2, expected, bs)
            )

    dut.ready_i.value = 1
    
    for vector in test_vectors:
        # wait for falling edge to pass data
        await FallingEdge(dut.clk_i)
        
        dut.valid_i.value = 1
        dut.op_i.value = int(ShangmiCryptoOperands.SM4ED.value)
        dut.rs1_i.value = vector.rs1
        dut.rs2_i.value = vector.rs2
        dut.aux_i.value = vector.bs
        
        await Timer(1, unit="ns") # wait 1ns to staiblize
        
        # IDLE -> STAGE0
        await RisingEdge(dut.clk_i)
        await ReadOnly() # wait for FF writing
        
        # STAGE0 -> STAGE1
        await RisingEdge(dut.clk_i)
        await ReadOnly() # wait for FF writig
        
        await FallingEdge(dut.clk_i)
        dut.valid_i.value = 0 # Deassert valid input after one cycle
                        
        await RisingEdge(dut.clk_i)
        await ReadOnly() # wait for FF writing

        assert dut.valid_o.value == 1, "valid_o should be 1"
        assert dut.ready_o.value == 1, "ready_o should be 1"
        assert dut.result_o.value == vector.expected_result, "result is not correct"

    await FallingEdge(dut.clk_i)
    dut.valid_i.value = 0
    
    await RisingEdge(dut.clk_i)
    await ReadOnly() # wait FF write
    assert dut.valid_o.value == 0, "valid_o should be 0" # ensure that valid output is asserted low

@cocotb.test()
async def shangmi_crypto_unit_test_sm4ks(dut):
    clk = Clock(dut.clk_i, 10, unit="ns") # 100 MHz clock
    clk.start()
    
    await reset_values(dut) # Reset the DUT
    
    test_vectors = generate_test_vectors(50, ShangmiCryptoOperands.SM4KS)
    
    # Add specific edge case test vectors
    test_vectors.append(TestData(rs1=0x00000000, rs2=0x00000000, expected_result=0xC01A6BD6, bs=0)) # Zero input
    test_vectors.append(TestData(rs1=0x00000000, rs2=0x0000FF00, expected_result=0x09244800, bs=1)) # S-box input FF
    test_vectors.append(TestData(rs1=0xFFFFFFFF, rs2=0x00000000, expected_result=0x94293FE5, bs=2)) # XOR with all ones
    test_vectors.append(TestData(rs1=0x00000000, rs2=0x80000000, expected_result=0xEA401D75, bs=3)) # Highest byte selection
    test_vectors.append(TestData(rs1=0x12345678, rs2=0xDEADBEEF, expected_result=0x3B6736F2, bs=2)) # Mixed bit pattern    

    for bs in range(4):
        for byte in range(256):
            rs1 = 0
            rs2 = byte << (bs * 8) # sbox input is byte >> (bs * 8) in verilog model, so we just do the inverse here to have all possible sbox inputs

            expected = golden_shangmi_crypto_unit(
                rs1, rs2, bs, ShangmiCryptoOperands.SM4KS
            )

            test_vectors.append(
                TestData(rs1, rs2, expected, bs)
            )

    dut.ready_i.value = 1
    
    for vector in test_vectors:
        # wait for falling edge to pass data
        await FallingEdge(dut.clk_i)
        
        dut.valid_i.value = 1
        dut.op_i.value = int(ShangmiCryptoOperands.SM4KS.value)
        dut.rs1_i.value = vector.rs1
        dut.rs2_i.value = vector.rs2
        dut.aux_i.value = vector.bs
        
        await Timer(1, unit="ns") # wait 1ns to staiblize
        
        # IDLE -> STAGE0
        await RisingEdge(dut.clk_i)
        await ReadOnly() # wait for FF writing
        
        # STAGE0 -> STAGE1
        await RisingEdge(dut.clk_i)
        await ReadOnly() # wait for FF writig
        
        await FallingEdge(dut.clk_i)
        dut.valid_i.value = 0 # Deassert valid input after one cycle
                        
        await RisingEdge(dut.clk_i)
        await ReadOnly() # wait for FF writing

        assert dut.valid_o.value == 1, "valid_o should be 1"
        assert dut.ready_o.value == 1, "ready_o should be 1"
        assert dut.result_o.value == vector.expected_result, "result is not correct"

    await FallingEdge(dut.clk_i)
    dut.valid_i.value = 0
    
    await RisingEdge(dut.clk_i)
    await ReadOnly() # wait FF write
    assert dut.valid_o.value == 0, "valid_o should be 0" # ensure that valid output is asserted low
    

@cocotb.test()
async def shangmi_crypto_unit_test_handshake(dut):
    Clock(dut.clk_i, 10, unit="ns").start()
    await reset_values(dut)

    # simple one-cycle result checking
    async def step(valid, ready, op, rs1, rs2, bs, exp_ready, exp_valid, exp_result=None):
        await FallingEdge(dut.clk_i)

        dut.valid_i.value = valid
        dut.ready_i.value = ready
        dut.op_i.value = op
        dut.rs1_i.value = rs1
        dut.rs2_i.value = rs2
        dut.aux_i.value = bs

        await Timer(1, unit="ns")

        # Rising edge öncesi input ready
        assert int(dut.ready_o.value) == exp_ready

        await RisingEdge(dut.clk_i)
        await ReadOnly()

        # Rising edge sonrası output
        assert int(dut.valid_o.value) == exp_valid

        if exp_valid and exp_result is not None:
            assert int(dut.result_o.value) == exp_result

    A = 0x5B5BD58E  # SM4ED(0, 0, bs=0)
    B = 0xEA401D75  # SM4KS(0, 0x80000000, bs=3)
    C = 0x00000000  # SM4ED(A, 0, bs=0)

    # valid_i = 0, ready_i = 1, no change but ready_o = 1
    await step(0, 1, ShangmiCryptoOperands.SM4ED.value, 0, 0, 0,
               exp_ready=1, exp_valid=0)

    # valid_i = 1, ready_i = 0, able to get new request as ready_o = 1 and pipeline was empty
    await step(1, 0, ShangmiCryptoOperands.SM4ED.value, 0, 0, 0,
               exp_ready=1, exp_valid=0)

    # STAGE0, not able to get new request
    await step(1, 0, ShangmiCryptoOperands.SM4KS.value, 0, 0x80000000, 3,
               exp_ready=0, exp_valid=0)

    # STAGE1, result A becomes valid and new request B is accepted
    await step(1, 0, ShangmiCryptoOperands.SM4KS.value, 0, 0x80000000, 3,
               exp_ready=1, exp_valid=1, exp_result=A)

    # since ready_i is never asserted 1, not able to get new request, but valid_o is still 1 and result is still A
    await step(0, 0, ShangmiCryptoOperands.SM4ED.value, 0, 0, 0,
               exp_ready=0, exp_valid=1, exp_result=A)

    for _ in range(3):
        await step(0, 0, ShangmiCryptoOperands.SM4ED.value, 0, 0, 0,
                   exp_ready=0, exp_valid=1, exp_result=A)

    # valid_i = 1, ready_i = 1, consume old result and get new result B
    await step(1, 1, ShangmiCryptoOperands.SM4ED.value, A, 0, 0,
               exp_ready=1, exp_valid=1, exp_result=B)

    # valid_i = 0, ready_i = 0, still not consumed
    for _ in range(3):
        await step(0, 0, ShangmiCryptoOperands.SM4ED.value, 0, 0, 0,
                   exp_ready=0, exp_valid=1, exp_result=B)

    # valid_i = 0, ready_i = 1, consume B and produce C
    await step(0, 1, ShangmiCryptoOperands.SM4ED.value, 0, 0, 0,
               exp_ready=1, exp_valid=1, exp_result=C)

    # valid_i = 0, ready_i = 0, still not consumed
    for _ in range(3):
        await step(0, 0, ShangmiCryptoOperands.SM4ED.value, 0, 0, 0,
                   exp_ready=0, exp_valid=1, exp_result=C)

    # valid_i = 0, ready_i = 1, consume C and have empty pipeline
    await step(0, 1, ShangmiCryptoOperands.SM4ED.value, 0, 0, 0,
               exp_ready=1, exp_valid=0)