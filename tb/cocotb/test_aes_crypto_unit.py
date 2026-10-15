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

class AESOperands(Enum):
    AES32DSI = 0
    AES32DSMI = 1
    AES32ESI = 2
    AES32ESMI = 3

class TestData:
    def __init__(self, rs1: int, rs2: int, expected_result: int, bs: int = 0):
        self.rs1 = rs1
        self.rs2 = rs2
        self.expected_result = expected_result
        self.bs = bs

AES_SBOX = (
    0x63, 0x7C, 0x77, 0x7B, 0xF2, 0x6B, 0x6F, 0xC5, 0x30, 0x01, 0x67, 0x2B, 0xFE, 0xD7, 0xAB, 0x76,
    0xCA, 0x82, 0xC9, 0x7D, 0xFA, 0x59, 0x47, 0xF0, 0xAD, 0xD4, 0xA2, 0xAF, 0x9C, 0xA4, 0x72, 0xC0,
    0xB7, 0xFD, 0x93, 0x26, 0x36, 0x3F, 0xF7, 0xCC, 0x34, 0xA5, 0xE5, 0xF1, 0x71, 0xD8, 0x31, 0x15,
    0x04, 0xC7, 0x23, 0xC3, 0x18, 0x96, 0x05, 0x9A, 0x07, 0x12, 0x80, 0xE2, 0xEB, 0x27, 0xB2, 0x75,
    0x09, 0x83, 0x2C, 0x1A, 0x1B, 0x6E, 0x5A, 0xA0, 0x52, 0x3B, 0xD6, 0xB3, 0x29, 0xE3, 0x2F, 0x84,
    0x53, 0xD1, 0x00, 0xED, 0x20, 0xFC, 0xB1, 0x5B, 0x6A, 0xCB, 0xBE, 0x39, 0x4A, 0x4C, 0x58, 0xCF,
    0xD0, 0xEF, 0xAA, 0xFB, 0x43, 0x4D, 0x33, 0x85, 0x45, 0xF9, 0x02, 0x7F, 0x50, 0x3C, 0x9F, 0xA8,
    0x51, 0xA3, 0x40, 0x8F, 0x92, 0x9D, 0x38, 0xF5, 0xBC, 0xB6, 0xDA, 0x21, 0x10, 0xFF, 0xF3, 0xD2,
    0xCD, 0x0C, 0x13, 0xEC, 0x5F, 0x97, 0x44, 0x17, 0xC4, 0xA7, 0x7E, 0x3D, 0x64, 0x5D, 0x19, 0x73,
    0x60, 0x81, 0x4F, 0xDC, 0x22, 0x2A, 0x90, 0x88, 0x46, 0xEE, 0xB8, 0x14, 0xDE, 0x5E, 0x0B, 0xDB,
    0xE0, 0x32, 0x3A, 0x0A, 0x49, 0x06, 0x24, 0x5C, 0xC2, 0xD3, 0xAC, 0x62, 0x91, 0x95, 0xE4, 0x79,
    0xE7, 0xC8, 0x37, 0x6D, 0x8D, 0xD5, 0x4E, 0xA9, 0x6C, 0x56, 0xF4, 0xEA, 0x65, 0x7A, 0xAE, 0x08,
    0xBA, 0x78, 0x25, 0x2E, 0x1C, 0xA6, 0xB4, 0xC6, 0xE8, 0xDD, 0x74, 0x1F, 0x4B, 0xBD, 0x8B, 0x8A,
    0x70, 0x3E, 0xB5, 0x66, 0x48, 0x03, 0xF6, 0x0E, 0x61, 0x35, 0x57, 0xB9, 0x86, 0xC1, 0x1D, 0x9E,
    0xE1, 0xF8, 0x98, 0x11, 0x69, 0xD9, 0x8E, 0x94, 0x9B, 0x1E, 0x87, 0xE9, 0xCE, 0x55, 0x28, 0xDF,
    0x8C, 0xA1, 0x89, 0x0D, 0xBF, 0xE6, 0x42, 0x68, 0x41, 0x99, 0x2D, 0x0F, 0xB0, 0x54, 0xBB, 0x16
)

AES_INV_SBOX = [0] * 256

for i, value in enumerate(AES_SBOX):
    AES_INV_SBOX[value] = i


def rol32(x: int, n: int):
    x &= 0xFFFFFFFF
    n &= 31
    return ((x << n) | (x >> (32 - n))) & 0xFFFFFFFF


def gf_mul(a: int, b: int):
    rd = 0

    for _ in range(8):
        if b & 1:
            rd ^= a

        carry = a & 0x80
        a = (a << 1) & 0xFF

        if carry:
            a ^= 0x1B

        b >>= 1

    return rd & 0xFF


# Simple golden model for RISC-V Zkne/Zknd extension instructions
def golden_aes_crypto_unit(rs1: int, rs2: int, bs: int, operand: AESOperands):
    rs1 &= 0xFFFFFFFF
    rs2 &= 0xFFFFFFFF
    bs &= 0x3
    rd = 0

    shamt = bs * 8
    sb_in = (rs2 >> shamt) & 0xFF

    if operand == AESOperands.AES32ESI:
        x = AES_SBOX[sb_in]
        y = x

    elif operand == AESOperands.AES32ESMI:
        x = AES_SBOX[sb_in]
        y = (gf_mul(x, 2) |
             (x << 8) |
             (x << 16) |
             (gf_mul(x, 3) << 24))

    elif operand == AESOperands.AES32DSI:
        x = AES_INV_SBOX[sb_in]
        y = x

    elif operand == AESOperands.AES32DSMI:
        x = AES_INV_SBOX[sb_in]
        y = (gf_mul(x, 14) |
             (gf_mul(x, 9) << 8) |
             (gf_mul(x, 13) << 16) |
             (gf_mul(x, 11) << 24))

    else:
        raise ValueError(f"Unsupported operand: {operand}")

    rd = rs1 ^ rol32(y, shamt)

    return rd & 0xFFFFFFFF

def generate_test_vectors(num_vectors: int, operand: AESOperands):
    import random
    random.seed(0x5678_9ABC) # TODO: Make this a parameter
    
    vectors = []
    for _ in range(num_vectors):
        rs1 = random.getrandbits(32)
        rs2 = random.getrandbits(32)
        bs = random.randint(0, 3)
        expected_result = golden_aes_crypto_unit(rs1, rs2, bs, operand)
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
async def aes_crypto_unit_test_aes32dsi(dut):
    clk = Clock(dut.clk_i, 10, unit="ns") # 100 MHz clock
    clk.start()
    
    await reset_values(dut) # Reset the DUT
    
    test_vectors = generate_test_vectors(50, AESOperands.AES32DSI)
    
    # Add specific edge case test vectors
    test_vectors.append(TestData(rs1=0x00000000, rs2=0x00000063, expected_result=0x00000000, bs=0)) # Inverse S-box output zero
    test_vectors.append(TestData(rs1=0x00000000, rs2=0x00000000, expected_result=0x00000052, bs=0)) # Zero input
    test_vectors.append(TestData(rs1=0x00000000, rs2=0x00630000, expected_result=0x00000000, bs=2)) # Byte selection
    test_vectors.append(TestData(rs1=0x12345678, rs2=0xDEADBEEF, expected_result=0x8E345678, bs=3)) # Mixed bit pattern
    
    for bs in range(4):
        for byte in range(256):
            rs1 = 0
            rs2 = byte << (bs * 8) # sbox input is byte >> (bs * 8) in verilog model, so we just do the inverse here to have all possible sbox inputs

            expected = golden_aes_crypto_unit(
                rs1, rs2, bs, AESOperands.AES32DSI
            )

            test_vectors.append(
                TestData(rs1, rs2, expected, bs)
            )

    dut.ready_i.value = 1
    
    for vector in test_vectors:
        # wait for falling edge to pass data
        await FallingEdge(dut.clk_i)
        
        dut.valid_i.value = 1
        dut.op_i.value = int(AESOperands.AES32DSI.value)
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
async def aes_crypto_unit_test_aes32dsmi(dut):
    clk = Clock(dut.clk_i, 10, unit="ns") # 100 MHz clock
    clk.start()
    
    await reset_values(dut) # Reset the DUT
    
    test_vectors = generate_test_vectors(50, AESOperands.AES32DSMI)
    
    # Add specific edge case test vectors
    test_vectors.append(TestData(rs1=0x00000000, rs2=0x00000000, expected_result=0x50A7F451, bs=0)) # Zero input
    test_vectors.append(TestData(rs1=0x00000000, rs2=0x00000063, expected_result=0x00000000, bs=0)) # Inverse S-box output zero
    test_vectors.append(TestData(rs1=0x00000000, rs2=0x63000000, expected_result=0x00000000, bs=3)) # Byte selection
    test_vectors.append(TestData(rs1=0x12345678, rs2=0xDEADBEEF, expected_result=0xCAA4BEC0, bs=2)) # Mixed bit pattern    
    
    for bs in range(4):
        for byte in range(256):
            rs1 = 0
            rs2 = byte << (bs * 8) # sbox input is byte >> (bs * 8) in verilog model, so we just do the inverse here to have all possible sbox inputs

            expected = golden_aes_crypto_unit(
                rs1, rs2, bs, AESOperands.AES32DSMI
            )

            test_vectors.append(
                TestData(rs1, rs2, expected, bs)
            )

    dut.ready_i.value = 1
    
    for vector in test_vectors:
        # wait for falling edge to pass data
        await FallingEdge(dut.clk_i)
        
        dut.valid_i.value = 1
        dut.op_i.value = int(AESOperands.AES32DSMI.value)
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
async def aes_crypto_unit_test_aes32esi(dut):
    clk = Clock(dut.clk_i, 10, unit="ns") # 100 MHz clock
    clk.start()
    
    await reset_values(dut) # Reset the DUT
    
    test_vectors = generate_test_vectors(50, AESOperands.AES32ESI)
    
    # Add specific edge case test vectors
    test_vectors.append(TestData(rs1=0x00000000, rs2=0x00000000, expected_result=0x00000063, bs=0)) # Zero input
    test_vectors.append(TestData(rs1=0x00000000, rs2=0x00005300, expected_result=0x0000ED00, bs=1)) # S-box input 53
    test_vectors.append(TestData(rs1=0xFFFFFFFF, rs2=0x000000FF, expected_result=0xFFFFFFE9, bs=0)) # XOR with all ones
    test_vectors.append(TestData(rs1=0x12345678, rs2=0xDEADBEEF, expected_result=0x12A15678, bs=2)) # Mixed bit pattern
    
    for bs in range(4):
        for byte in range(256):
            rs1 = 0
            rs2 = byte << (bs * 8) # sbox input is byte >> (bs * 8) in verilog model, so we just do the inverse here to have all possible sbox inputs

            expected = golden_aes_crypto_unit(
                rs1, rs2, bs, AESOperands.AES32ESI
            )

            test_vectors.append(
                TestData(rs1, rs2, expected, bs)
            )

    dut.ready_i.value = 1
    
    for vector in test_vectors:
        # wait for falling edge to pass data
        await FallingEdge(dut.clk_i)
        
        dut.valid_i.value = 1
        dut.op_i.value = int(AESOperands.AES32ESI.value)
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
async def aes_crypto_unit_test_aes32esmi(dut):
    clk = Clock(dut.clk_i, 10, unit="ns") # 100 MHz clock
    clk.start()
    
    await reset_values(dut) # Reset the DUT
    
    test_vectors = generate_test_vectors(50, AESOperands.AES32ESMI)
    
    # Add specific edge case test vectors
    test_vectors.append(TestData(rs1=0x00000000, rs2=0x00000000, expected_result=0xA56363C6, bs=0)) # Zero input
    test_vectors.append(TestData(rs1=0x00000000, rs2=0x00005300, expected_result=0xEDEDC12C, bs=1)) # Partial MixColumns
    test_vectors.append(TestData(rs1=0xFFFFFFFF, rs2=0xFF000000, expected_result=0xD3C5E9E9, bs=3)) # XOR with all ones
    test_vectors.append(TestData(rs1=0x12345678, rs2=0xDEADBEEF, expected_result=0x8705F2ED, bs=2)) # Mixed bit pattern    
    
    for bs in range(4):
        for byte in range(256):
            rs1 = 0
            rs2 = byte << (bs * 8) # sbox input is byte >> (bs * 8) in verilog model, so we just do the inverse here to have all possible sbox inputs

            expected = golden_aes_crypto_unit(
                rs1, rs2, bs, AESOperands.AES32ESMI
            )

            test_vectors.append(
                TestData(rs1, rs2, expected, bs)
            )

    dut.ready_i.value = 1
    
    for vector in test_vectors:
        # wait for falling edge to pass data
        await FallingEdge(dut.clk_i)
        
        dut.valid_i.value = 1
        dut.op_i.value = int(AESOperands.AES32ESMI.value)
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
async def aes_unit_test_handshake(dut):

    Clock(dut.clk_i, 10, unit="ns").start()
    await reset_values(dut)

    # simple one-cycle result checking
    async def step(valid, ready, op, rs1, rs2, bs,
                   exp_ready, exp_valid, exp_result=None):

        await FallingEdge(dut.clk_i)

        dut.valid_i.value = valid
        dut.ready_i.value = ready
        dut.op_i.value = op
        dut.rs1_i.value = rs1
        dut.rs2_i.value = rs2
        dut.aux_i.value = bs

        await Timer(1, unit="ns")

        assert int(dut.ready_o.value) == exp_ready

        await RisingEdge(dut.clk_i)
        await ReadOnly()

        assert int(dut.valid_o.value) == exp_valid

        if exp_valid and exp_result is not None:
            assert int(dut.result_o.value) == exp_result

    A = 0x00000063  # AES32ESI(0, 0, bs=0)
    B = 0x2CEDEDC1  # AES32ESMI(0, 0x53, bs=0)
    C = 0x00000000  # AES32DSI(0, 0x63, bs=0)
    D = 0x5150A7F4  # AES32DSMI(0, 0, bs=3)

    # valid_i = 0, ready_i = 1, no change but ready_o = 1
    await step(0, 1, AESOperands.AES32ESI.value, 0, 0, 0,
               exp_ready=1, exp_valid=0)

    # valid_i = 1, ready_i = 0, able to get new request as ready_o = 1 and pipeline was empty
    await step(1, 0, AESOperands.AES32ESI.value, 0, 0, 0,
               exp_ready=1, exp_valid=0)

    # STAGE0, not able to get new request
    await step(1, 0, AESOperands.AES32ESMI.value, 0, 0x53, 0,
               exp_ready=0, exp_valid=0)

    # STAGE1, result A becomes valid and new request B is accepted
    await step(1, 0, AESOperands.AES32ESMI.value, 0, 0x53, 0,
               exp_ready=1, exp_valid=1, exp_result=A)

    # since ready_i is never asserted 1, not able to get new request, but valid_o is still 1 and result is still A
    await step(0, 0, AESOperands.AES32ESI.value, 0, 0, 0,
               exp_ready=0, exp_valid=1, exp_result=A)

    for _ in range(3):
        await step(0, 0, AESOperands.AES32ESI.value, 0, 0, 0,
                   exp_ready=0, exp_valid=1, exp_result=A)

    # valid_i = 1, ready_i = 1, consume old result and get new result B
    await step(1, 1, AESOperands.AES32DSI.value, 0, 0x63, 0,
               exp_ready=1, exp_valid=1, exp_result=B)

    # valid_i = 0, ready_i = 0, still not consumed
    await step(0, 0, AESOperands.AES32ESI.value, 0, 0, 0,
               exp_ready=0, exp_valid=1, exp_result=B)

    # valid_i = 1, ready_i = 1, consume old result and get new result C
    await step(1, 1, AESOperands.AES32DSMI.value, 0, 0, 3,
               exp_ready=1, exp_valid=1, exp_result=C)

    # valid_i = 0, ready_i = 0, still not consumed
    await step(0, 0, AESOperands.AES32ESI.value, 0, 0, 0,
               exp_ready=0, exp_valid=1, exp_result=C)

    for _ in range(3):
        await step(0, 0, AESOperands.AES32ESI.value, 0, 0, 0,
                   exp_ready=0, exp_valid=1, exp_result=C)

    # valid_i = 0, ready_i = 1, consume C and produce D
    await step(0, 1, AESOperands.AES32ESI.value, 0, 0, 0,
               exp_ready=1, exp_valid=1, exp_result=D)

    # valid_i = 0, ready_i = 0, still not consumed
    for _ in range(3):
        await step(0, 0, AESOperands.AES32ESI.value, 0, 0, 0,
                   exp_ready=0, exp_valid=1, exp_result=D)

    # valid_i = 0, ready_i = 1, consume D and have empty pipeline
    await step(0, 1, AESOperands.AES32ESI.value, 0, 0, 0,
               exp_ready=1, exp_valid=0)
