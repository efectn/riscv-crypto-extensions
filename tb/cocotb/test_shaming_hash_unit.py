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
class ShaMingHashOperands(Enum):
    SM3P0 = 0
    SM3P1 = 1
    
# Random test data element
class TestData:
    def __init__(self, rs1: int, rs2: int, expected_result: int):
        self.rs1 = rs1
        self.rs2 = rs2
        self.expected_result = expected_result

def rol32(x: int, n: int):
    x &= 0xFFFFFFFF
    n &= 31
    return ((x << n) | (x >> (32 - n))) & 0xFFFFFFFF

def golden_hash_unit(rs1: int, rs2: int, operand: ShaMingHashOperands):
    rs1 &= 0xFFFFFFFF
    rs2 &= 0xFFFFFFFF
    rd = 0

    if operand == ShaMingHashOperands.SM3P0:
        rd = rs1 ^ rol32(rs1, 9) ^ rol32(rs1, 17)

    elif operand == ShaMingHashOperands.SM3P1:
        rd = rs1 ^ rol32(rs1, 15) ^ rol32(rs1, 23)

    else:
        raise ValueError(f"Unsupported operand: {operand}")

    return rd & 0xFFFFFFFF

def generate_test_vectors(num_vectors: int, operand: ShaMingHashOperands):
    import random
    random.seed(0x5678_9ABC) # TODO: Make this a parameter
    
    vectors = []
    for _ in range(num_vectors):
        rs1 = random.getrandbits(32)
        rs2 = random.getrandbits(32)
        expected_result = golden_hash_unit(rs1, rs2, operand)
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
async def shaming_hash_unit_test_sm3p0(dut):
    clk = Clock(dut.clk_i, 10, unit="ns") # 100 MHz clock
    clk.start()
    
    await reset_values(dut) # Reset the DUT
    
    test_vectors = generate_test_vectors(50, ShaMingHashOperands.SM3P0)
    
    # Add specific edge case test vectors
    test_vectors.append(TestData(rs1=0x00000000, rs2=0, expected_result=0x00000000)) # Zero input
    test_vectors.append(TestData(rs1=0xFFFFFFFF, rs2=0, expected_result=0xFFFFFFFF)) # All bits set
    test_vectors.append(TestData(rs1=0x00000001, rs2=0, expected_result=0x00020201)) # Only LSB set
    test_vectors.append(TestData(rs1=0x80000000, rs2=0, expected_result=0x80010100)) # Only MSB set
    test_vectors.append(TestData(rs1=0x12345678, rs2=0, expected_result=0xD6688234)) # Mixed bit pattern
    
    # one-hot encoding test cases
    for bit in range(32):
        rs1 = 1 << bit

        expected = golden_hash_unit(
            rs1, 0, ShaMingHashOperands.SM3P0
        )

        test_vectors.append(
            TestData(rs1, 0, expected)
        )

    dut.ready_i.value = 1
    
    for vector in test_vectors:
        # wait for falling edge to pass data
        await FallingEdge(dut.clk_i)
        
        dut.valid_i.value = 1
        dut.op_i.value = int(ShaMingHashOperands.SM3P0.value)
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
async def shaming_hash_unit_test_sm3p1(dut):
    clk = Clock(dut.clk_i, 10, unit="ns") # 100 MHz clock
    clk.start()
    
    await reset_values(dut) # Reset the DUT
    
    test_vectors = generate_test_vectors(50, ShaMingHashOperands.SM3P1)
    
    # Add specific edge case test vectors
    test_vectors.append(TestData(rs1=0x00000000, rs2=0, expected_result=0x00000000)) # Zero input
    test_vectors.append(TestData(rs1=0xFFFFFFFF, rs2=0, expected_result=0xFFFFFFFF)) # All bits set
    test_vectors.append(TestData(rs1=0x00000001, rs2=0, expected_result=0x00808001)) # Only LSB set
    test_vectors.append(TestData(rs1=0x80000000, rs2=0, expected_result=0x80404000)) # Only MSB set
    test_vectors.append(TestData(rs1=0x12345678, rs2=0, expected_result=0x05014549)) # Mixed bit pattern
    
    # one-hot encoding test cases
    for bit in range(32):
        rs1 = 1 << bit

        expected = golden_hash_unit(
            rs1, 0, ShaMingHashOperands.SM3P1
        )

        test_vectors.append(
            TestData(rs1, 0, expected)
        )

    dut.ready_i.value = 1
    
    for vector in test_vectors:
        # wait for falling edge to pass data
        await FallingEdge(dut.clk_i)
        
        dut.valid_i.value = 1
        dut.op_i.value = int(ShaMingHashOperands.SM3P1.value)
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
async def hash_unit_test_handshake(dut):

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

    A = 0xD6688234  # SM3P0(0x12345678)
    B = 0x80404000  # SM3P1(0x80000000)
    C = 0x00000000  # SM3P0(0x00000000)

    # valid_i = 0, ready_i = 1, no change but ready_o = 1
    await step(0, 1, ShaMingHashOperands.SM3P0.value, 0, 0,
               exp_ready=1, exp_valid=0)

    # valid_i = 1, ready_i = 0, able to get new request as ready_o = 1 and pipeline was empty
    await step(1, 0, ShaMingHashOperands.SM3P0.value, 0x12345678, 4,
               exp_ready=1, exp_valid=1, exp_result=A)

    # since ready_i is never asserted 1, not able to get new request, but valid_o is still 1 and result is still A
    for _ in range(3):
        await step(1, 0, ShaMingHashOperands.SM3P1.value, 0x80000000, 1,
                   exp_ready=0, exp_valid=1, exp_result=A)

    # valid_i = 1, ready_i = 1, consume old result and get new result B
    await step(1, 1, ShaMingHashOperands.SM3P1.value, 0x80000000, 1,
               exp_ready=1, exp_valid=1, exp_result=B)

    # valid_i = 0, ready_i = 1, input bubble
    await step(0, 1, ShaMingHashOperands.SM3P0.value, 0, 0,
               exp_ready=1, exp_valid=0)

    # valid_i = 1, ready_i = 0, new request C
    await step(1, 0, ShaMingHashOperands.SM3P0.value, 0, 0,
               exp_ready=1, exp_valid=1, exp_result=C)

    # valid_i = 0, ready_i = 0, still not consumed
    for _ in range(3):
        await step(0, 0, ShaMingHashOperands.SM3P0.value, 0, 0,
                   exp_ready=0, exp_valid=1, exp_result=C)

    # valid_i = 0, ready_i = 1, consume C and have empty pipeline
    await step(0, 1, ShaMingHashOperands.SM3P0.value, 0, 0,
               exp_ready=1, exp_valid=0)