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
    
    test_vectors = generate_test_vectors(50, BitmapOperands.ROL)
    
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
        
@cocotb.test()
async def bitmap_unit_test_ror(dut):
    clk = Clock(dut.clk_i, 10, unit="ns") # 100 MHz clock
    clk.start()
    
    await reset_values(dut) # Reset the DUT
    
    test_vectors = generate_test_vectors(50, BitmapOperands.ROR)
    
    # Add specific edge case test vectors
    test_vectors.append(TestData(rs1=0xFFFFFFFF, rs2=1,  expected_result=0xFFFFFFFF)) # All bits set
    test_vectors.append(TestData(rs1=0x00000001, rs2=31, expected_result=0x00000002)) # Single bit set
    test_vectors.append(TestData(rs1=0xAAAAAAAA, rs2=4,  expected_result=0xAAAAAAAA)) # Alternating bits
    test_vectors.append(TestData(rs1=0x12345678, rs2=0,  expected_result=0x12345678)) # Zero shift
    test_vectors.append(TestData(rs1=0x12345678, rs2=32, expected_result=0x12345678)) # Shift by 32
    test_vectors.append(TestData(rs1=0x12345678, rs2=33, expected_result=0x091A2B3C)) # Shift by 33
    test_vectors.append(TestData(rs1=0x12345678, rs2=63, expected_result=0x2468ACF0)) # Shift by 63
    test_vectors.append(TestData(rs1=0x80000000, rs2=1,  expected_result=0x40000000)) # MSB set
    
    dut.ready_i.value = 1
    
    for vector in test_vectors:
        # wait for falling edge to pass data
        await FallingEdge(dut.clk_i)
        
        dut.valid_i.value = 1
        dut.op_i.value = int(BitmapOperands.ROR.value)
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
async def bitmap_unit_test_andn(dut):
    clk = Clock(dut.clk_i, 10, unit="ns") # 100 MHz clock
    clk.start()
    
    await reset_values(dut) # Reset the DUT
    
    test_vectors = generate_test_vectors(50, BitmapOperands.ANDN)
    
    # Add specific edge case test vectors
    test_vectors.append(TestData(rs1=0xFFFFFFFF, rs2=0xFFFFFFFF, expected_result=0x00000000)) # ANDN with all bits set
    test_vectors.append(TestData(rs1=0x00000000, rs2=0xFFFFFFFF, expected_result=0x00000000)) # ANDN with rs1 all bits clear
    test_vectors.append(TestData(rs1=0xFFFFFFFF, rs2=0x00000000, expected_result=0xFFFFFFFF)) # ANDN with rs2 all bits clear
    test_vectors.append(TestData(rs1=0xAAAAAAAA, rs2=0x55555555, expected_result=0xAAAAAAAA)) # ANDN with alternating bits
    
    dut.ready_i.value = 1
    
    for vector in test_vectors:
        # wait for falling edge to pass data
        await FallingEdge(dut.clk_i)
        
        dut.valid_i.value = 1
        dut.op_i.value = int(BitmapOperands.ANDN.value)
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
async def bitmap_unit_test_orn(dut):
    clk = Clock(dut.clk_i, 10, unit="ns") # 100 MHz clock
    clk.start()
    
    await reset_values(dut) # Reset the DUT
    
    test_vectors = generate_test_vectors(50, BitmapOperands.ORN)
    
    # Add specific edge case test vectors
    test_vectors.append(TestData(rs1=0xFFFFFFFF, rs2=0xFFFFFFFF, expected_result=0xFFFFFFFF)) # ORN with all bits set
    test_vectors.append(TestData(rs1=0x00000000, rs2=0xFFFFFFFF, expected_result=0x00000000)) # ORN with rs1 all bits clear
    test_vectors.append(TestData(rs1=0xFFFFFFFF, rs2=0x00000000, expected_result=0xFFFFFFFF)) # ORN with rs2 all bits clear
    test_vectors.append(TestData(rs1=0xAAAAAAAA, rs2=0x55555555, expected_result=0xAAAAAAAA)) # ORN with alternating bits
    
    dut.ready_i.value = 1
    
    for vector in test_vectors:
        # wait for falling edge to pass data
        await FallingEdge(dut.clk_i)
        
        dut.valid_i.value = 1
        dut.op_i.value = int(BitmapOperands.ORN.value)
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
async def bitmap_unit_test_xnor(dut):
    clk = Clock(dut.clk_i, 10, unit="ns") # 100 MHz clock
    clk.start()
    
    await reset_values(dut) # Reset the DUT
    
    test_vectors = generate_test_vectors(50, BitmapOperands.XNOR)
    
    # Add specific edge case test vectors
    test_vectors.append(TestData(rs1=0xFFFFFFFF, rs2=0xFFFFFFFF, expected_result=0xFFFFFFFF)) # Both all ones
    test_vectors.append(TestData(rs1=0x00000000, rs2=0xFFFFFFFF, expected_result=0x00000000)) # Zero vs all ones
    test_vectors.append(TestData(rs1=0xFFFFFFFF, rs2=0x00000000, expected_result=0x00000000)) # All ones vs zero
    test_vectors.append(TestData(rs1=0xAAAAAAAA, rs2=0x55555555, expected_result=0x00000000)) # Opposite alternating bits
    test_vectors.append(TestData(rs1=0x00000000, rs2=0x00000000, expected_result=0xFFFFFFFF)) # Both zero
    test_vectors.append(TestData(rs1=0xAAAAAAAA, rs2=0xAAAAAAAA, expected_result=0xFFFFFFFF)) # Identical operands
    test_vectors.append(TestData(rs1=0x12345678, rs2=0xFFFFFFFF, expected_result=0x12345678)) # XNOR with all ones
    test_vectors.append(TestData(rs1=0x12345678, rs2=0x00000000, expected_result=0xEDCBA987)) # XNOR with zero
    
    dut.ready_i.value = 1
    
    for vector in test_vectors:
        # wait for falling edge to pass data
        await FallingEdge(dut.clk_i)
        
        dut.valid_i.value = 1
        dut.op_i.value = int(BitmapOperands.XNOR.value)
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
async def bitmap_unit_test_pack(dut):
    clk = Clock(dut.clk_i, 10, unit="ns") # 100 MHz clock
    clk.start()
    
    await reset_values(dut) # Reset the DUT
    
    test_vectors = generate_test_vectors(50, BitmapOperands.PACK)
    
    dut.ready_i.value = 1
    
    for vector in test_vectors:
        # wait for falling edge to pass data
        await FallingEdge(dut.clk_i)
        
        dut.valid_i.value = 1
        dut.op_i.value = int(BitmapOperands.PACK.value)
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
async def bitmap_unit_test_packh(dut):
    clk = Clock(dut.clk_i, 10, unit="ns") # 100 MHz clock
    clk.start()
    
    await reset_values(dut) # Reset the DUT
    
    test_vectors = generate_test_vectors(50, BitmapOperands.PACKH)
    
    dut.ready_i.value = 1
    
    for vector in test_vectors:
        # wait for falling edge to pass data
        await FallingEdge(dut.clk_i)
        
        dut.valid_i.value = 1
        dut.op_i.value = int(BitmapOperands.PACKH.value)
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
async def bitmap_unit_test_brev8(dut):
    clk = Clock(dut.clk_i, 10, unit="ns") # 100 MHz clock
    clk.start()
    
    await reset_values(dut) # Reset the DUT
    
    test_vectors = generate_test_vectors(50, BitmapOperands.BREV8)
    
    dut.ready_i.value = 1
    
    for vector in test_vectors:
        # wait for falling edge to pass data
        await FallingEdge(dut.clk_i)
        
        dut.valid_i.value = 1
        dut.op_i.value = int(BitmapOperands.BREV8.value)
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
async def bitmap_unit_test_rev8(dut):
    clk = Clock(dut.clk_i, 10, unit="ns") # 100 MHz clock
    clk.start()
    
    await reset_values(dut) # Reset the DUT
    
    test_vectors = generate_test_vectors(50, BitmapOperands.REV8)
    
    dut.ready_i.value = 1
    
    for vector in test_vectors:
        # wait for falling edge to pass data
        await FallingEdge(dut.clk_i)
        
        dut.valid_i.value = 1
        dut.op_i.value = int(BitmapOperands.REV8.value)
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
async def bitmap_unit_test_zip(dut):
    clk = Clock(dut.clk_i, 10, unit="ns") # 100 MHz clock
    clk.start()
    
    await reset_values(dut) # Reset the DUT
    
    test_vectors = generate_test_vectors(50, BitmapOperands.ZIP)
    
    dut.ready_i.value = 1
    
    for vector in test_vectors:
        # wait for falling edge to pass data
        await FallingEdge(dut.clk_i)
        
        dut.valid_i.value = 1
        dut.op_i.value = int(BitmapOperands.ZIP.value)
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
async def bitmap_unit_test_unzip(dut):
    clk = Clock(dut.clk_i, 10, unit="ns") # 100 MHz clock
    clk.start()
    
    await reset_values(dut) # Reset the DUT
    
    test_vectors = generate_test_vectors(50, BitmapOperands.UNZIP)
    
    dut.ready_i.value = 1
    
    for vector in test_vectors:
        # wait for falling edge to pass data
        await FallingEdge(dut.clk_i)
        
        dut.valid_i.value = 1
        dut.op_i.value = int(BitmapOperands.UNZIP.value)
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
async def bitmap_unit_test_handshake(dut):

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

        # Rising edge öncesi input ready
        assert int(dut.ready_o.value) == exp_ready

        await RisingEdge(dut.clk_i)
        await ReadOnly()

        # Rising edge sonrası output
        assert int(dut.valid_o.value) == exp_valid

        if exp_valid and exp_result is not None:
            assert int(dut.result_o.value) == exp_result

    A = 0x23456781  # ROL(0x12345678, 4)
    B = 0x40000000  # ROR(0x80000000, 1)
    C = 0xFFFFFFFF  # XNOR(0, 0)

    # valid_i = 0, ready_i = 1, no change but ready_o = 1
    await step(0, 1, BitmapOperands.ROL.value, 0, 0,
               exp_ready=1, exp_valid=0)

    # valid_i = 1, ready_i = 0, able to get new request as ready_o = 1 and pipeline was empty 
    await step(1, 0, BitmapOperands.ROL.value, 0x12345678, 4,
               exp_ready=1, exp_valid=1, exp_result=A)

    # since ready_i is never asserted 1, not able to get new request, but valid_o is still 1 and result is still A
    for _ in range(3):
        await step(1, 0, BitmapOperands.ROR.value, 0x80000000, 1,
                   exp_ready=0, exp_valid=1, exp_result=A)

    # valid_i = 1, ready_i = 1, consume old result and get new result B
    await step(1, 1, BitmapOperands.ROR.value, 0x80000000, 1,
               exp_ready=1, exp_valid=1, exp_result=B)

    # valid_i = 0, ready_i = 1, input bubble
    await step(0, 1, BitmapOperands.ROL.value, 0, 0,
               exp_ready=1, exp_valid=0)

    # valid_i = 1, ready_i = 0, new request C
    await step(1, 0, BitmapOperands.XNOR.value, 0, 0,
               exp_ready=1, exp_valid=1, exp_result=C)

    # valid_i = 0, ready_i = 0, still not consumed
    for _ in range(3):
        await step(0, 0, BitmapOperands.ROL.value, 0, 0,
                   exp_ready=0, exp_valid=1, exp_result=C)

    # valid_i = 0, ready_i = 1, consume C and have empty pipeline
    await step(0, 1, BitmapOperands.ROL.value, 0, 0,
               exp_ready=1, exp_valid=0)
