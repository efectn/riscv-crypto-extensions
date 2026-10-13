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
class BitmapOperands(Enum):
    ROL = 0
    ROR = 1
    RORI = 2
    ANDN = 3
    ORN = 4
    XNOR = 5
    PACK = 6
    PACKH = 7
    BREV8 = 8
    REV8 = 9
    ZIP = 10
    UNZIP = 11
    
# Random test data element
class TestData:
    def __init__(self, rs1: int, rs2: int, expected_result: int):
        self.rs1 = rs1
        self.rs2 = rs2
        self.expected_result = expected_result
    
# Simple golden model for RISC-V Zbkb extension instructions generated in accordance with the RISC-V spec.
def golden_bitmap_unit(rs1: int, rs2 : int, operand : BitmapOperands):
    rs1 &= 0xFFFFFFFF # mask upper 32 bits
    rs2 &= 0xFFFFFFFF # mask upper 32 bits
    
    rd = 0
    shamt = rs2 & 0x1F
    
    if operand == BitmapOperands.ROL:
        rd = ((rs1 << shamt) | (rs1 >> (32 - shamt))) & 0xFFFFFFFF
    elif operand == BitmapOperands.ROR or operand == BitmapOperands.RORI:        
        rd = ((rs1 >> shamt) | (rs1 << (32 - shamt))) & 0xFFFFFFFF
    elif operand == BitmapOperands.ANDN:
        rd = rs1 & ~rs2
    elif operand == BitmapOperands.ORN:
        rd = rs1 | ~rs2
    elif operand == BitmapOperands.XNOR:
        rd = ~(rs1 ^ rs2) & 0xFFFFFFFF
    elif operand == BitmapOperands.PACK:
        rd = (rs1 & 0xFFFF) | ((rs2 & 0xFFFF) << 16)
    elif operand == BitmapOperands.PACKH:
        rd = (rs1 & 0xFF) | ((rs2 & 0xFF) << 8)
    elif operand == BitmapOperands.BREV8:
        for i in range(4):
            byte = (rs1 >> (8 * i)) & 0xFF
            reversed_byte = int(f"{byte:08b}"[::-1], 2)
            rd |= reversed_byte << (8 * i)
    elif operand == BitmapOperands.REV8:
        rd = ((rs1 & 0x000000FF) << 24) | ((rs1 & 0x0000FF00) << 8) | ((rs1 & 0x00FF0000) >> 8) | ((rs1 & 0xFF000000) >> 24)
    elif operand == BitmapOperands.ZIP:
        for i in range(16):
            rd |= ((rs1 >> i) & 1) << (2 * i)
            rd |= ((rs1 >> (i + 16)) & 1) << (2 * i + 1)
    elif operand == BitmapOperands.UNZIP:
        for i in range(16):
            rd |= ((rs1 >> (2 * i)) & 1) << i
            rd |= ((rs1 >> (2 * i + 1)) & 1) << (i + 16)    
    else:
        raise ValueError(f"Unsupported operand: {operand}")
    
    return rd & 0xFFFFFFFF

def generate_test_vectors(num_vectors: int, operand: BitmapOperands):
    import random
    random.seed(0x5678_9ABC) # TODO: Make this a parameter
    
    vectors = []
    for _ in range(num_vectors):
        rs1 = random.getrandbits(32)
        rs2 = random.getrandbits(32)
        expected_result = golden_bitmap_unit(rs1, rs2, operand)
        vectors.append(TestData(rs1, rs2, expected_result))
    return vectors

async def reset_values(dut):
    dut.rst_ni.value = 0 # Reset the DUT
    dut.valid_i.value = 0
    dut.ready_i.value = 0
    dut.op_i.value = 0
    dut.rs1_i.value = 0
    dut.rs2_i.value = 0
    dut.aux_i.value = 0
    
    await ClockCycles(dut.clk_i, 3)
    await FallingEdge(dut.clk_i)
    
    dut.rst_ni.value = 1 # Release reset
    
    await Timer(1, unit="ns") # wait a bit
    
    assert int(dut.ready_o.value) == 1, "DUT not ready after reset"
    
@cocotb.test()
async def bitmap_unit_test_rol(dut):
    clk = Clock(dut.clk_i, 10, unit="ns") # 100 MHz clock
    clk.start()
    
    await reset_values(dut) # Reset the DUT
    
    test_vectors = generate_test_vectors(10, BitmapOperands.ROL)
    
    # Add specific edge case test vectors
    test_vectors.append(TestData(rs1=0xFFFFFFFF, rs2=1, expected_result=0xFFFFFFFF)) # ROL with all bits set
    test_vectors.append(TestData(rs1=0x00000001, rs2=31, expected_result=0x80000000)) # ROL with single bit set
    test_vectors.append(TestData(rs1=0xAAAAAAAA, rs2=4, expected_result=0xAAAAAAAA)) # ROL with alternating bits
    test_vectors.append(TestData(rs1=0x12345678, rs2=0, expected_result=0x12345678)) # ROL with zero shift amount
    test_vectors.append(TestData(rs1=0x12345678, rs2=32, expected_result=0x12345678)) # ROL with shift amount equal to word size
    test_vectors.append(TestData(rs1=0x12345678, rs2=33, expected_result=0x2468ACF0)) # ROL with shift amount greater than word size
    test_vectors.append(TestData(rs1=0x12345678, rs2=63, expected_result=0x091A2B3C)) # ROL with shift amount much greater than word size
    
    dut.ready_i.value = 1
    
    for vector in test_vectors:
        # wait for falling edge to pass data
        await FallingEdge(dut.clk_i)
        
        dut.valid_i.value = 1
        dut.op_i.value = int(BitmapOperands.ROL.value)
        dut.rs1_i.value = vector.rs1
        dut.rs2_i.value = vector.rs2
        dut.aux_i.value = 0
        
        await Timer(1, unit="ns") # wait 1ns to staiblize
        
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
        