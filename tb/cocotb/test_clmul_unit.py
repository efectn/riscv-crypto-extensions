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
class ClmulOperands(Enum):
    CLMUL = 0
    CLMULH = 1
    
# Random test data element
class TestData:
    def __init__(self, rs1: int, rs2: int, expected_result: int):
        self.rs1 = rs1
        self.rs2 = rs2
        self.expected_result = expected_result
    
# Simple golden model for RISC-V Zbkc extension instructions
def golden_clmul_unit(rs1: int, rs2: int, operand: ClmulOperands):
    rs1 &= 0xFFFFFFFF
    rs2 &= 0xFFFFFFFF
    rd = 0

    for i in range(32):
        if (rs2 >> i) & 1:
            rd ^= rs1 << i

    if operand == ClmulOperands.CLMUL:
        rd = rd & 0xFFFFFFFF

    elif operand == ClmulOperands.CLMULH:
        rd = (rd >> 32) & 0xFFFFFFFF

    else:
        raise ValueError(f"Unsupported operand: {operand}")

    return rd & 0xFFFFFFFF

def generate_test_vectors(num_vectors: int, operand: ClmulOperands):
    import random
    random.seed(0x5678_9ABC) # TODO: Make this a parameter
    
    vectors = []
    for _ in range(num_vectors):
        rs1 = random.getrandbits(32)
        rs2 = random.getrandbits(32)
        expected_result = golden_clmul_unit(rs1, rs2, operand)
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
    dut.op_q.value = 0
    dut.rs1_q.value = 0
    dut.rs2_q.value = 0
    dut.state_q.value = 0
    dut.stage0_q.value = 0
    dut.stage0_d.value = 0

    await ClockCycles(dut.clk_i, 3)
    await FallingEdge(dut.clk_i)
    
    dut.rst_ni.value = 1 # Release reset
    
    await Timer(1, unit="ns") # wait a bit
    
    assert int(dut.ready_o.value) == 1, "DUT not ready after reset"
    
@cocotb.test()
async def clmul_unit_test_clmul(dut):
    clk = Clock(dut.clk_i, 10, unit="ns") # 100 MHz clock
    clk.start()
    
    await reset_values(dut) # Reset the DUT
    
    test_vectors = generate_test_vectors(50, ClmulOperands.CLMUL)
    
    # Add specific edge case test vectors
    test_vectors.append(TestData(rs1=0x00000000, rs2=0xFFFFFFFF, expected_result=0x00000000)) # Zero operand
    test_vectors.append(TestData(rs1=0xFFFFFFFF, rs2=0x00000001, expected_result=0xFFFFFFFF)) # Multiply by one
    test_vectors.append(TestData(rs1=0x00000003, rs2=0x00000003, expected_result=0x00000005)) # XOR instead of normal multiplication
    test_vectors.append(TestData(rs1=0x80000000, rs2=0x80000000, expected_result=0x00000000)) # Product only in upper 32 bits
    test_vectors.append(TestData(rs1=0xFFFFFFFF, rs2=0xFFFFFFFF, expected_result=0x55555555)) # All bits set
    test_vectors.append(TestData(rs1=0x12345678, rs2=0x9ABCDEF0, expected_result=0x5CD25A80)) # Mixed bit pattern

    dut.ready_i.value = 1
    
    for vector in test_vectors:
        # wait for falling edge to pass data
        await FallingEdge(dut.clk_i)
        
        dut.valid_i.value = 1
        dut.op_i.value = int(ClmulOperands.CLMUL.value)
        dut.rs1_i.value = vector.rs1
        dut.rs2_i.value = vector.rs2
        dut.aux_i.value = 0
        
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
async def clmul_unit_test_clmulh(dut):
    clk = Clock(dut.clk_i, 10, unit="ns") # 100 MHz clock
    clk.start()
    
    await reset_values(dut) # Reset the DUT
    
    test_vectors = generate_test_vectors(50, ClmulOperands.CLMULH)
    
    # Add specific edge case test vectors
    test_vectors.append(TestData(rs1=0x00000000, rs2=0xFFFFFFFF, expected_result=0x00000000)) # Zero operand
    test_vectors.append(TestData(rs1=0xFFFFFFFF, rs2=0x00000001, expected_result=0x00000000)) # Multiply by one
    test_vectors.append(TestData(rs1=0x80000000, rs2=0x80000000, expected_result=0x40000000)) # Both MSBs set
    test_vectors.append(TestData(rs1=0x80000000, rs2=0x00000002, expected_result=0x00000001)) # First bit crossing into upper 32 bits
    test_vectors.append(TestData(rs1=0xFFFFFFFF, rs2=0xFFFFFFFF, expected_result=0x55555555)) # All bits set
    test_vectors.append(TestData(rs1=0x12345678, rs2=0x9ABCDEF0, expected_result=0x08860E94)) # Mixed bit pattern
    
    dut.ready_i.value = 1
    
    for vector in test_vectors:
        # wait for falling edge to pass data
        await FallingEdge(dut.clk_i)
        
        dut.valid_i.value = 1
        dut.op_i.value = int(ClmulOperands.CLMULH.value)
        dut.rs1_i.value = vector.rs1
        dut.rs2_i.value = vector.rs2
        dut.aux_i.value = 0
        
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
async def clmul_unit_test_handshake(dut):

    Clock(dut.clk_i, 10, unit="ns").start()
    await reset_values(dut)

    # simple one-cycle result checking
    async def step(valid, ready, op, rs1, rs2, exp_ready, exp_valid, exp_result=None):
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

    A = 0x00000005  # CLMUL(0x00000003, 0x00000003)
    B = 0x40000000  # CLMULH(0x80000000, 0x80000000)
    C = 0x00000000  # CLMUL(0x00000000, 0xFFFFFFFF)

    # valid_i = 0, ready_i = 1, no change but ready_o = 1
    await step(0, 1, ClmulOperands.CLMUL.value, 0, 0,
               exp_ready=1, exp_valid=0)

    # valid_i = 1, ready_i = 0, able to get new request as ready_o = 1 and pipeline was empty
    await step(1, 0, ClmulOperands.CLMUL.value, 3, 3,
               exp_ready=1, exp_valid=0)

    # STAGE0, not able to get new request
    await step(1, 0, ClmulOperands.CLMULH.value, 0x80000000, 0x80000000,
               exp_ready=0, exp_valid=0)

    # STAGE1, result A becomes valid and new request B is accepted
    await step(1, 0, ClmulOperands.CLMULH.value, 0x80000000, 0x80000000,
               exp_ready=1, exp_valid=1, exp_result=A)

    # since ready_i is never asserted 1, not able to get new request, but valid_o is still 1 and result is still A
    await step(0, 0, ClmulOperands.CLMUL.value, 0, 0,
               exp_ready=0, exp_valid=1, exp_result=A)

    for _ in range(3):
        await step(0, 0, ClmulOperands.CLMUL.value, 0, 0,
                   exp_ready=0, exp_valid=1, exp_result=A)

    # valid_i = 1, ready_i = 1, consume old result and get new result B
    await step(1, 1, ClmulOperands.CLMUL.value, 0, 0xFFFFFFFF,
               exp_ready=1, exp_valid=1, exp_result=B)

    # valid_i = 0, ready_i = 0, still not consumed
    for _ in range(3):
        await step(0, 0, ClmulOperands.CLMUL.value, 0, 0,
                   exp_ready=0, exp_valid=1, exp_result=B)

    # valid_i = 0, ready_i = 1, consume B and produce C
    await step(0, 1, ClmulOperands.CLMUL.value, 0, 0,
               exp_ready=1, exp_valid=1, exp_result=C)

    # valid_i = 0, ready_i = 0, still not consumed
    for _ in range(3):
        await step(0, 0, ClmulOperands.CLMUL.value, 0, 0,
                   exp_ready=0, exp_valid=1, exp_result=C)

    # valid_i = 0, ready_i = 1, consume C and have empty pipeline
    await step(0, 1, ClmulOperands.CLMUL.value, 0, 0,
               exp_ready=1, exp_valid=0)