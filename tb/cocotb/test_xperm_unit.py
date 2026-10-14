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
class XPermOperands(Enum):
    XPERM4 = 0
    XPERM8 = 1
    
# Random test data element
class TestData:
    def __init__(self, rs1: int, rs2: int, expected_result: int):
        self.rs1 = rs1
        self.rs2 = rs2
        self.expected_result = expected_result
    
# Simple golden model for RISC-V Zbkx permutation instructions
def golden_bitmap_unit(rs1: int, rs2 : int, operand : XPermOperands):
    rs1 &= 0xFFFFFFFF # mask upper 32 bits
    rs2 &= 0xFFFFFFFF # mask upper 32 bits
    
    rd = 0
    
    if operand == XPermOperands.XPERM4:
        for i in range(8):
            sel = (rs2 >> (i * 4)) & 0xF
            if sel < 8:
                rd |= ((rs1 >> (sel * 4)) & 0xF) << (i * 4)
    elif operand == XPermOperands.XPERM8:        
        for i in range(4):
            sel = (rs2 >> (i * 8)) & 0xFF
            if sel < 4:
                rd |= ((rs1 >> (sel * 8)) & 0xFF) << (i * 8)
    else:
        raise ValueError(f"Unsupported operand: {operand}")
    
    return rd & 0xFFFFFFFF

def generate_test_vectors(num_vectors: int, operand: XPermOperands):
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
async def xperm_unit_test_xperm4(dut):
    clk = Clock(dut.clk_i, 10, unit="ns") # 100 MHz clock
    clk.start()
    
    await reset_values(dut) # Reset the DUT
    
    test_vectors = generate_test_vectors(50, XPermOperands.XPERM4)
    
    # Add specific edge case test vectors
    test_vectors.append(TestData(rs1=0x89ABCDEF, rs2=0x76543210, expected_result=0x89ABCDEF)) # Identity permutation
    test_vectors.append(TestData(rs1=0x89ABCDEF, rs2=0x01234567, expected_result=0xFEDCBA98)) # Reverse nibble order
    test_vectors.append(TestData(rs1=0x89ABCDEF, rs2=0x77777777, expected_result=0x88888888)) # Repeat highest valid index (7)
    test_vectors.append(TestData(rs1=0x89ABCDEF, rs2=0x88888888, expected_result=0x00000000)) # First invalid index (8)
    test_vectors.append(TestData(rs1=0x89ABCDEF, rs2=0xF7E6D5C4, expected_result=0x08090A0B)) # Mixed valid and invalid indices
    
    dut.ready_i.value = 1
    
    for vector in test_vectors:
        # wait for falling edge to pass data
        await FallingEdge(dut.clk_i)
        
        dut.valid_i.value = 1
        dut.op_i.value = int(XPermOperands.XPERM4.value)
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

@cocotb.test()
async def xperm_unit_test_xperm8(dut):
    clk = Clock(dut.clk_i, 10, unit="ns") # 100 MHz clock
    clk.start()
    
    await reset_values(dut) # Reset the DUT
    
    test_vectors = generate_test_vectors(50, XPermOperands.XPERM8)
    
    # Add specific edge case test vectors
    test_vectors.append(TestData(rs1=0x11223344, rs2=0x03020100, expected_result=0x11223344)) # Identity permutation
    test_vectors.append(TestData(rs1=0x11223344, rs2=0x00010203, expected_result=0x44332211)) # Reverse byte order
    test_vectors.append(TestData(rs1=0x11223344, rs2=0x00000000, expected_result=0x44444444)) # Repeat index 0
    test_vectors.append(TestData(rs1=0x11223344, rs2=0x04040404, expected_result=0x00000000)) # First invalid index (4)
    test_vectors.append(TestData(rs1=0x11223344, rs2=0xFF02AA01, expected_result=0x00220033)) # Mixed valid and invalid indices
    
    dut.ready_i.value = 1
    
    for vector in test_vectors:
        # wait for falling edge to pass data
        await FallingEdge(dut.clk_i)
        
        dut.valid_i.value = 1
        dut.op_i.value = int(XPermOperands.XPERM8.value)
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

@cocotb.test()
async def xperm_unit_test_handshake(dut):
    Clock(dut.clk_i, 10, unit="ns").start()
    await reset_values(dut)

    # simple one-cycle result checking
    async def step(valid, ready, op, rs1, rs2,
                   exp_ready, exp_valid, exp_result=None):

        await FallingEdge(dut.clk_i)

        dut.valid_i.value = valid
        dut.ready_i.value = ready
        dut.op_i.value = op
        dut.rs1_i.value = rs1
        dut.rs2_i.value = rs2
        dut.aux_i.value = 0

        await Timer(1, unit="ns")

        assert int(dut.ready_o.value) == exp_ready

        await RisingEdge(dut.clk_i)
        await ReadOnly()

        assert int(dut.valid_o.value) == exp_valid

        if exp_valid and exp_result is not None:
            assert int(dut.result_o.value) == exp_result

    A = 0x89ABCDEF  # XPERM4(0x89ABCDEF, 0x76543210)
    B = 0x44332211  # XPERM8(0x11223344, 0x00010203)
    C = 0x00000000  # XPERM4(0x89ABCDEF, 0x88888888)

    # valid_i = 0, ready_i = 1, no change but ready_o = 1
    await step(0, 1, XPermOperands.XPERM4.value, 0, 0,
               exp_ready=1, exp_valid=0)

    # valid_i = 1, ready_i = 0, able to get new request as ready_o = 1 and pipeline was empty
    await step(1, 0, XPermOperands.XPERM4.value, 0x89ABCDEF, 0x76543210,
               exp_ready=1, exp_valid=1, exp_result=A)

    # since ready_i is never asserted 1, not able to get new request, but valid_o is still 1 and result is still A
    for _ in range(3):
        await step(1, 0, XPermOperands.XPERM8.value, 0x11223344, 0x00010203,
                   exp_ready=0, exp_valid=1, exp_result=A)

    # valid_i = 1, ready_i = 1, consume old result and get new result B
    await step(1, 1, XPermOperands.XPERM8.value, 0x11223344, 0x00010203,
               exp_ready=1, exp_valid=1, exp_result=B)

    # valid_i = 0, ready_i = 1, input bubble
    await step(0, 1, XPermOperands.XPERM4.value, 0, 0,
               exp_ready=1, exp_valid=0)

    # valid_i = 1, ready_i = 0, new request C
    await step(1, 0, XPermOperands.XPERM4.value, 0x89ABCDEF, 0x88888888,
               exp_ready=1, exp_valid=1, exp_result=C)

    # valid_i = 0, ready_i = 0, still not consumed
    for _ in range(3):
        await step(0, 0, XPermOperands.XPERM4.value, 0, 0,
                   exp_ready=0, exp_valid=1, exp_result=C)

    # valid_i = 0, ready_i = 1, consume C and have empty pipeline
    await step(0, 1, XPermOperands.XPERM4.value, 0, 0,
               exp_ready=1, exp_valid=0)