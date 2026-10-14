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
class NISTHashOperands(Enum):
    SHA256_SIGMA0 = 0
    SHA256_SIGMA1 = 1
    SHA256_SUM0 = 2
    SHA256_SUM1 = 3
    SHA512_SIGMA0H = 4
    SHA512_SIGMA0L = 5
    SHA512_SIGMA1H = 6
    SHA512_SIGMA1L = 7
    SHA512_SUM0 = 8
    SHA512_SUM1 = 9
    
# Random test data element
class TestData:
    def __init__(self, rs1: int, rs2: int, expected_result: int):
        self.rs1 = rs1
        self.rs2 = rs2
        self.expected_result = expected_result

def ror32(x: int, n: int):
    x &= 0xFFFFFFFF
    n &= 31
    return ((x >> n) | (x << (32 - n))) & 0xFFFFFFFF

def golden_hash_unit(rs1: int, rs2: int, operand: NISTHashOperands):
    rs1 &= 0xFFFFFFFF
    rs2 &= 0xFFFFFFFF
    rd = 0

    if operand == NISTHashOperands.SHA256_SIGMA0:
        rd = ror32(rs1, 7) ^ ror32(rs1, 18) ^ (rs1 >> 3)

    elif operand == NISTHashOperands.SHA256_SIGMA1:
        rd = ror32(rs1, 17) ^ ror32(rs1, 19) ^ (rs1 >> 10)

    elif operand == NISTHashOperands.SHA256_SUM0:
        rd = ror32(rs1, 2) ^ ror32(rs1, 13) ^ ror32(rs1, 22)

    elif operand == NISTHashOperands.SHA256_SUM1:
        rd = ror32(rs1, 6) ^ ror32(rs1, 11) ^ ror32(rs1, 25)

    elif operand == NISTHashOperands.SHA512_SIGMA0H:
        rd = ((rs1 >> 1) ^ (rs1 >> 7) ^ (rs1 >> 8) ^
              (rs2 << 31) ^ (rs2 << 24))

    elif operand == NISTHashOperands.SHA512_SIGMA0L:
        rd = ((rs1 >> 1) ^ (rs1 >> 7) ^ (rs1 >> 8) ^
              (rs2 << 31) ^ (rs2 << 25) ^ (rs2 << 24))

    elif operand == NISTHashOperands.SHA512_SIGMA1H:
        rd = ((rs1 << 3) ^ (rs1 >> 6) ^ (rs1 >> 19) ^
              (rs2 >> 29) ^ (rs2 << 13))

    elif operand == NISTHashOperands.SHA512_SIGMA1L:
        rd = ((rs1 << 3) ^ (rs1 >> 6) ^ (rs1 >> 19) ^
              (rs2 >> 29) ^ (rs2 << 26) ^ (rs2 << 13))

    elif operand == NISTHashOperands.SHA512_SUM0:
        rd = ((rs1 << 25) ^ (rs1 << 30) ^ (rs1 >> 28) ^
              (rs2 >> 7) ^ (rs2 >> 2) ^ (rs2 << 4))

    elif operand == NISTHashOperands.SHA512_SUM1:
        rd = ((rs1 << 23) ^ (rs1 >> 14) ^ (rs1 >> 18) ^
              (rs2 >> 9) ^ (rs2 << 18) ^ (rs2 << 14))

    else:
        raise ValueError(f"Unsupported operand: {operand}")

    return rd & 0xFFFFFFFF

def generate_test_vectors(num_vectors: int, operand: NISTHashOperands):
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
async def nist_hash_unit_test_sha256sigma0(dut):
    clk = Clock(dut.clk_i, 10, unit="ns") # 100 MHz clock
    clk.start()
    
    await reset_values(dut) # Reset the DUT
    
    test_vectors = generate_test_vectors(50, NISTHashOperands.SHA256_SIGMA0)
    
    # Add specific edge case test vectors
    test_vectors.append(TestData(rs1=0xFFFFFFFF, rs2=0, expected_result=0x1FFFFFFF))
    test_vectors.append(TestData(rs1=0x00000001, rs2=0, expected_result=0x02004000))
    test_vectors.append(TestData(rs1=0, rs2=0, expected_result=0))

    
    # one-hot encoding test cases
    for bit in range(32):
        rs1 = 1 << bit

        expected = golden_hash_unit(
            rs1, 0, NISTHashOperands.SHA256_SIGMA0
        )

        test_vectors.append(
            TestData(rs1, 0, expected)
        )

    dut.ready_i.value = 1
    
    for vector in test_vectors:
        # wait for falling edge to pass data
        await FallingEdge(dut.clk_i)
        
        dut.valid_i.value = 1
        dut.op_i.value = int(NISTHashOperands.SHA256_SIGMA0.value)
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
async def nist_hash_unit_test_sha256sigma1(dut):
    clk = Clock(dut.clk_i, 10, unit="ns") # 100 MHz clock
    clk.start()
    await reset_values(dut) # Reset the DUT
    test_vectors = generate_test_vectors(50, NISTHashOperands.SHA256_SIGMA1)
    
    # Add specific edge case test vectors
    test_vectors.append(TestData(rs1=0xFFFFFFFF, rs2=0x00000000, expected_result=0x003FFFFF))
    test_vectors.append(TestData(rs1=0x80000000, rs2=0x00000000, expected_result=0x00205000))
    test_vectors.append(TestData(rs1=0x00000000, rs2=0x00000000, expected_result=0x00000000))

    # one-hot encoding test cases
    for bit in range(32):
        rs1 = 1 << bit

        expected = golden_hash_unit(
            rs1, 0, NISTHashOperands.SHA256_SIGMA1
        )

        test_vectors.append(
            TestData(rs1, 0, expected)
        )

    dut.ready_i.value = 1
    for vector in test_vectors:
        # wait for falling edge to pass data
        await FallingEdge(dut.clk_i)
        
        dut.valid_i.value = 1
        dut.op_i.value = int(NISTHashOperands.SHA256_SIGMA1.value)
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
async def nist_hash_unit_test_sha256sum0(dut):
    clk = Clock(dut.clk_i, 10, unit="ns") # 100 MHz clock
    clk.start()
    
    await reset_values(dut) # Reset the DUT
    
    test_vectors = generate_test_vectors(50, NISTHashOperands.SHA256_SUM0)
    
    # Add specific edge case test vectors
    test_vectors.append(TestData(rs1=0xFFFFFFFF, rs2=0x00000000, expected_result=0xFFFFFFFF))
    test_vectors.append(TestData(rs1=0x00000001, rs2=0x00000000, expected_result=0x40080400))
    test_vectors.append(TestData(rs1=0x00000000, rs2=0x00000000, expected_result=0x00000000))

# one-hot encoding test cases
    for bit in range(32):
        rs1 = 1 << bit

        expected = golden_hash_unit(
            rs1, 0, NISTHashOperands.SHA256_SUM0
        )

        test_vectors.append(
            TestData(rs1, 0, expected)
        )

    dut.ready_i.value = 1
    for vector in test_vectors:
        # wait for falling edge to pass data
        await FallingEdge(dut.clk_i)
        
        dut.valid_i.value = 1
        dut.op_i.value = int(NISTHashOperands.SHA256_SUM0.value)
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
async def nist_hash_unit_test_sha256sum1(dut):
    clk = Clock(dut.clk_i, 10, unit="ns") # 100 MHz clock
    clk.start()
    
    await reset_values(dut) # Reset the DUT
    
    test_vectors = generate_test_vectors(50, NISTHashOperands.SHA256_SUM1)
    
    # Add specific edge case test vectors
    test_vectors.append(TestData(rs1=0xFFFFFFFF, rs2=0x00000000, expected_result=0xFFFFFFFF))
    test_vectors.append(TestData(rs1=0x00000001, rs2=0x00000000, expected_result=0x04200080))
    test_vectors.append(TestData(rs1=0x00000000, rs2=0x00000000, expected_result=0x00000000))

    # one-hot encoding test cases
    for bit in range(32):
        rs1 = 1 << bit

        expected = golden_hash_unit(
            rs1, 0, NISTHashOperands.SHA256_SUM1
        )

        test_vectors.append(
            TestData(rs1, 0, expected)
        )

    dut.ready_i.value = 1
    for vector in test_vectors:
        # wait for falling edge to pass data
        await FallingEdge(dut.clk_i)
        
        dut.valid_i.value = 1
        dut.op_i.value = int(NISTHashOperands.SHA256_SUM1.value)
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
async def nist_hash_unit_test_sha512sigma0h(dut):
    clk = Clock(dut.clk_i, 10, unit="ns") # 100 MHz clock
    clk.start()
    
    await reset_values(dut) # Reset the DUT
    
    test_vectors = generate_test_vectors(50, NISTHashOperands.SHA512_SIGMA0H)
    
    # Add specific edge case test vectors
    test_vectors.append(TestData(rs1=0x00000000, rs2=0x00000001, expected_result=0x81000000))
    test_vectors.append(TestData(rs1=0x80000000, rs2=0x00000000, expected_result=0x41800000))
    test_vectors.append(TestData(rs1=0x00000000, rs2=0x00000000, expected_result=0x00000000))

    # one-hot encoding test cases
    for bit in range(32):
        for rs1, rs2 in [(1 << bit, 0), (0, 1 << bit)]:
            expected = golden_hash_unit(
                rs1, rs2, NISTHashOperands.SHA512_SIGMA0H
            )

            test_vectors.append(
                TestData(rs1, rs2, expected)
            )

    dut.ready_i.value = 1
    for vector in test_vectors:
        # wait for falling edge to pass data
        await FallingEdge(dut.clk_i)
        
        dut.valid_i.value = 1
        dut.op_i.value = int(NISTHashOperands.SHA512_SIGMA0H.value)
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
async def nist_hash_unit_test_sha512sigma0l(dut):
    clk = Clock(dut.clk_i, 10, unit="ns") # 100 MHz clock
    clk.start()
    
    await reset_values(dut) # Reset the DUT
    
    test_vectors = generate_test_vectors(50, NISTHashOperands.SHA512_SIGMA0L)
    
    # Add specific edge case test vectors
    test_vectors.append(TestData(rs1=0x00000000, rs2=0x00000001, expected_result=0x83000000))
    test_vectors.append(TestData(rs1=0x80000000, rs2=0x00000000, expected_result=0x41800000))
    test_vectors.append(TestData(rs1=0x00000000, rs2=0x00000000, expected_result=0x00000000))

    # one-hot encoding test cases
    for bit in range(32):
        for rs1, rs2 in [(1 << bit, 0), (0, 1 << bit)]:
            expected = golden_hash_unit(
                rs1, rs2, NISTHashOperands.SHA512_SIGMA0L
            )

            test_vectors.append(
                TestData(rs1, rs2, expected)
            )

    dut.ready_i.value = 1
    for vector in test_vectors:
        # wait for falling edge to pass data
        
        await FallingEdge(dut.clk_i)
        dut.valid_i.value = 1
        dut.op_i.value = int(NISTHashOperands.SHA512_SIGMA0L.value)
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
async def nist_hash_unit_test_sha512sigma1h(dut):
    clk = Clock(dut.clk_i, 10, unit="ns") # 100 MHz clock
    clk.start()
    
    await reset_values(dut) # Reset the DUT
    
    test_vectors = generate_test_vectors(50, NISTHashOperands.SHA512_SIGMA1H)
    
    # Add specific edge case test vectors
    test_vectors.append(TestData(rs1=0x00000000, rs2=0x00000001, expected_result=0x00002000))
    test_vectors.append(TestData(rs1=0x80000000, rs2=0x00000000, expected_result=0x02001000))
    test_vectors.append(TestData(rs1=0x00000000, rs2=0x00000000, expected_result=0x00000000))

    # one-hot encoding test cases
    for bit in range(32):
        for rs1, rs2 in [(1 << bit, 0), (0, 1 << bit)]:
            expected = golden_hash_unit(
                rs1, rs2, NISTHashOperands.SHA512_SIGMA1H
            )

            test_vectors.append(
                TestData(rs1, rs2, expected)
            )

    dut.ready_i.value = 1
    for vector in test_vectors:
        # wait for falling edge to pass data
        await FallingEdge(dut.clk_i)
        
        dut.valid_i.value = 1
        dut.op_i.value = int(NISTHashOperands.SHA512_SIGMA1H.value)
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
async def nist_hash_unit_test_sha512sigma1l(dut):
    clk = Clock(dut.clk_i, 10, unit="ns") # 100 MHz clock
    clk.start()
    
    await reset_values(dut) # Reset the DUT
    
    test_vectors = generate_test_vectors(50, NISTHashOperands.SHA512_SIGMA1L)
    
    # Add specific edge case test vectors
    test_vectors.append(TestData(rs1=0x00000000, rs2=0x00000001, expected_result=0x04002000))
    test_vectors.append(TestData(rs1=0x80000000, rs2=0x00000000, expected_result=0x02001000))
    test_vectors.append(TestData(rs1=0x00000000, rs2=0x00000000, expected_result=0x00000000))

    # one-hot encoding test cases
    for bit in range(32):
        for rs1, rs2 in [(1 << bit, 0), (0, 1 << bit)]:
            expected = golden_hash_unit(
                rs1, rs2, NISTHashOperands.SHA512_SIGMA1L
            )

            test_vectors.append(
                TestData(rs1, rs2, expected)
            )

    dut.ready_i.value = 1
    for vector in test_vectors:
        # wait for falling edge to pass data
        await FallingEdge(dut.clk_i)
        
        dut.valid_i.value = 1
        dut.op_i.value = int(NISTHashOperands.SHA512_SIGMA1L.value)
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
async def nist_hash_unit_test_sha512sum0(dut):
    clk = Clock(dut.clk_i, 10, unit="ns") # 100 MHz clock
    clk.start()
    
    await reset_values(dut) # Reset the DUT
    
    test_vectors = generate_test_vectors(50, NISTHashOperands.SHA512_SUM0)
    
    # Add specific edge case test vectors
    test_vectors.append(TestData(rs1=0x00000001, rs2=0x00000000, expected_result=0x42000000))
    test_vectors.append(TestData(rs1=0x00000000, rs2=0x00000001, expected_result=0x00000010))
    test_vectors.append(TestData(rs1=0x00000000, rs2=0x00000000, expected_result=0x00000000))

    # one-hot encoding test cases
    for bit in range(32):
        for rs1, rs2 in [(1 << bit, 0), (0, 1 << bit)]:
            expected = golden_hash_unit(
                rs1, rs2, NISTHashOperands.SHA512_SUM0
            )

            test_vectors.append(
                TestData(rs1, rs2, expected)
            )

    dut.ready_i.value = 1
    for vector in test_vectors:
        # wait for falling edge to pass data
        await FallingEdge(dut.clk_i)
        
        dut.valid_i.value = 1
        dut.op_i.value = int(NISTHashOperands.SHA512_SUM0.value)
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
async def nist_hash_unit_test_sha512sum1(dut):
    clk = Clock(dut.clk_i, 10, unit="ns") # 100 MHz clock
    clk.start()
    
    await reset_values(dut) # Reset the DUT
    
    test_vectors = generate_test_vectors(50, NISTHashOperands.SHA512_SUM1)
    
    # Add specific edge case test vectors
    test_vectors.append(TestData(rs1=0x00000001, rs2=0x00000000, expected_result=0x00800000))
    test_vectors.append(TestData(rs1=0x00000000, rs2=0x00000001, expected_result=0x00044000))
    test_vectors.append(TestData(rs1=0x00000000, rs2=0x00000000, expected_result=0x00000000))

    # one-hot encoding test cases
    for bit in range(32):
        for rs1, rs2 in [(1 << bit, 0), (0, 1 << bit)]:
            expected = golden_hash_unit(
                rs1, rs2, NISTHashOperands.SHA512_SUM1
            )

            test_vectors.append(
                TestData(rs1, rs2, expected)
            )

    dut.ready_i.value = 1
    for vector in test_vectors:
        # wait for falling edge to pass data
        await FallingEdge(dut.clk_i)
        
        dut.valid_i.value = 1
        dut.op_i.value = int(NISTHashOperands.SHA512_SUM1.value)
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
async def nist_hash_unit_test_handshake(dut):
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

    A = 0x02004000  # SHA256_SIGMA0(0x00000001, 0)
    B = 0x81000000  # SHA512_SIGMA0H(0, 1)
    C = 0x00000000  # SHA512_SUM1(0, 0)

    # valid_i = 0, ready_i = 1, no change but ready_o = 1
    await step(0, 1, NISTHashOperands.SHA256_SIGMA0.value, 0, 0,
               exp_ready=1, exp_valid=0)

    # valid_i = 1, ready_i = 0, able to get new request as ready_o = 1 and pipeline was empty
    await step(1, 0, NISTHashOperands.SHA256_SIGMA0.value, 0x00000001, 0,
               exp_ready=1, exp_valid=1, exp_result=A)

    # since ready_i is never asserted 1, not able to get new request, but valid_o is still 1 and result is still A
    for _ in range(3):
        await step(1, 0, NISTHashOperands.SHA512_SIGMA0H.value, 0, 1,
                   exp_ready=0, exp_valid=1, exp_result=A)

    # valid_i = 1, ready_i = 1, consume old result and get new result B
    await step(1, 1, NISTHashOperands.SHA512_SIGMA0H.value, 0, 1,
               exp_ready=1, exp_valid=1, exp_result=B)

    # valid_i = 0, ready_i = 1, input bubble
    await step(0, 1, NISTHashOperands.SHA256_SIGMA0.value, 0, 0,
               exp_ready=1, exp_valid=0)

    # valid_i = 1, ready_i = 0, new request C
    await step(1, 0, NISTHashOperands.SHA512_SUM1.value, 0, 0,
               exp_ready=1, exp_valid=1, exp_result=C)

    # valid_i = 0, ready_i = 0, still not consumed
    for _ in range(3):
        await step(0, 0, NISTHashOperands.SHA256_SIGMA0.value, 0, 0,
                   exp_ready=0, exp_valid=1, exp_result=C)

    # valid_i = 0, ready_i = 1, consume C and have empty pipeline
    await step(0, 1, NISTHashOperands.SHA256_SIGMA0.value, 0, 0,
               exp_ready=1, exp_valid=0)
