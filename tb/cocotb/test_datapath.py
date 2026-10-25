import cocotb

from cocotb.clock import Clock
from cocotb.triggers import (
    Timer,
    RisingEdge,
    FallingEdge,
    ClockCycles,
    ReadOnly,
)

async def reset_values(dut):
    dut.rst_ni.value = 0 # Reset the DUT
    dut.op_i.value = 0
    dut.rs1_i.value = 0
    dut.rs2_i.value = 0
    dut.aux_i.value = 0
    dut.x_id_i.value = 0
    dut.unit_sel_i.value = 0
    dut.load_instruction_i.value = 0
    dut.start_unit_i.value = 0
    dut.consumer_ready_i.value = 0
    
    await ClockCycles(dut.clk_i, 3)
    await FallingEdge(dut.clk_i)
    
    dut.rst_ni.value = 1 # Release reset
    
    await Timer(1, unit="ns") # wait a bit

@cocotb.test()
async def datapath_test_input_loading(dut):
    clk = Clock(dut.clk_i, 10, unit="ns") # 100 MHz clock
    clk.start()
    
    await reset_values(dut) # Reset the DUT
    
    await FallingEdge(dut.clk_i)
    
    await Timer(1, unit = "ns")
    
    # test loading
    dut.rs1_i.value = 0x12345678
    dut.rs2_i.value = 0x87654321
    dut.aux_i.value = 0b11111
    dut.x_id_i.value = 0x1
    dut.unit_sel_i.value = 0x4 # pick xperm unit for now
    dut.load_instruction_i.value = 1
    
    await RisingEdge(dut.clk_i)
    await Timer(1, unit = "ns")
    
    assert dut.rs1_q.value == 0x12345678, f"Expected rs1_q to be 0x12345678, got {dut.rs1_q.value}"
    assert dut.rs2_q.value == 0x87654321, f"Expected rs2_q to be 0x87654321, got {dut.rs2_q.value}"
    assert dut.aux_q.value == 0b11111, f"Expected aux_q to be 0b11111, got {dut.aux_q.value}"
    assert dut.x_id_q.value == 0x1, f"Expected x_id_q to be 0x1, got {dut.x_id_q.value}"
    assert dut.unit_sel_q.value == 0x4, f"Expected unit_sel_q to be 0x4, got {dut.unit_sel_q.value}"
    
    dut.load_instruction_i.value = 0 # Clear load instruction signal
    dut.rs1_i.value = 0xFFFFFFFF
    dut.rs2_i.value = 0x00000000
    dut.aux_i.value = 0b00000
    dut.x_id_i.value = 0x0
    dut.unit_sel_i.value = 0x0
    
    await RisingEdge(dut.clk_i)
    await Timer(1, unit = "ns")
    
    assert dut.rs1_q.value == 0x12345678, f"Expected rs1_q to remain 0x12345678, got {dut.rs1_q.value}"
    assert dut.rs2_q.value == 0x87654321, f"Expected rs2_q to remain 0x87654321, got {dut.rs2_q.value}"
    assert dut.aux_q.value == 0b11111, f"Expected aux_q to remain 0b11111, got {dut.aux_q.value}"
    assert dut.x_id_q.value == 0x1, f"Expected x_id_q to remain 0x1, got {dut.x_id_q.value}"
    assert dut.unit_sel_q.value == 0x4, f"Expected unit_sel_q to remain 0x4, got {dut.unit_sel_q.value}"
    

@cocotb.test()
async def datapath_test(dut):
    clk = Clock(dut.clk_i, 10, unit="ns") # 100 MHz clock
    clk.start()
    
    await reset_values(dut) # Reset the DUT
    
    await FallingEdge(dut.clk_i)
    
    await Timer(1, unit = "ns")
    
    # test loading
    dut.rs1_i.value = 0x12345678
    dut.rs2_i.value = 0x87654321
    dut.aux_i.value = 0b11111
    dut.x_id_i.value = 0x1
    dut.unit_sel_i.value = 0x4 # pick xperm unit for now
    dut.load_instruction_i.value = 1
    
    await RisingEdge(dut.clk_i)
    await Timer(1, unit = "ns")
    
    assert dut.rs1_q.value == 0x12345678, f"Expected rs1_q to be 0x12345678, got {dut.rs1_q.value}"
    assert dut.rs2_q.value == 0x87654321, f"Expected rs2_q to be 0x87654321, got {dut.rs2_q.value}"
    assert dut.aux_q.value == 0b11111, f"Expected aux_q to be 0b11111, got {dut.aux_q.value}"
    assert dut.x_id_q.value == 0x1, f"Expected x_id_q to be 0x1, got {dut.x_id_q.value}"
    assert dut.unit_sel_q.value == 0x4, f"Expected unit_sel_q to be 0x4, got {dut.unit_sel_q.value}"
    
    assert dut.result_o.value == 0, f"Expected result_o to be 0, got {dut.result_o.value}"
    assert dut.result_valid_o.value == 0, f"Expected result_valid_o to be 0, got {dut.result_valid_o.value}"
    
    await FallingEdge(dut.clk_i)
    dut.load_instruction_i.value = 0 # Clear load instruction signal
    dut.start_unit_i.value = 1 # Start the unit
    
    await ClockCycles(dut.clk_i, 1)
    await Timer(1, unit = "ns")
    
    assert dut.result_valid_o.value == 1, f"Expected result_valid_o to be 1, got {dut.result_valid_o.value}"
    assert dut.unit_ready_o.value == 0, f"Expected unit_ready_o to be 0, got {dut.unit_ready_o.value}"
    assert dut.result_o.value == 0x01234567, f"Expected result_o to be 0x01234567, got {dut.result_o.value}"
    
    dut.start_unit_i.value = 0
    dut.consumer_ready_i.value = 1 # Indicate that the consumer is ready to accept the result
    
    await ClockCycles(dut.clk_i, 1)
  
    await Timer(1, unit = "ns")
    
    assert dut.result_valid_o.value == 0, f"Expected result_valid_o to be 0 after consumer ready, got {dut.result_valid_o.value}"
    assert dut.unit_ready_o.value == 1, f"Expected unit_ready_o to be 1 after consumer ready, got {dut.unit_ready_o.value}"
    assert dut.result_o.value == 0x0000000, f"Expected result_o to be 0 after consumer ready, got {dut.result_o.value}"
    
    await ClockCycles(dut.clk_i, 1)
    
@cocotb.test()
async def datapath_test_two_cycle_unit(dut):
    clk = Clock(dut.clk_i, 10, unit="ns") # 100 MHz clock
    clk.start()
    
    await reset_values(dut) # Reset the DUT
    
    await FallingEdge(dut.clk_i)
    
    await Timer(1, unit = "ns")
    
    # test loading
    dut.rs1_i.value = 0x12345678
    dut.rs2_i.value = 0x87654321
    dut.aux_i.value = 0b11111
    dut.x_id_i.value = 0x1
    dut.unit_sel_i.value = 0x2 # clmul unit selection
    dut.load_instruction_i.value = 1
    
    await RisingEdge(dut.clk_i)
    await Timer(1, unit = "ns")
    
    assert dut.rs1_q.value == 0x12345678, f"Expected rs1_q to be 0x12345678, got {dut.rs1_q.value}"
    assert dut.rs2_q.value == 0x87654321, f"Expected rs2_q to be 0x87654321, got {dut.rs2_q.value}"
    assert dut.aux_q.value == 0b11111, f"Expected aux_q to be 0b11111, got {dut.aux_q.value}"
    assert dut.x_id_q.value == 0x1, f"Expected x_id_q to be 0x1, got {dut.x_id_q.value}"
    assert dut.unit_sel_q.value == 0x2, f"Expected unit_sel_q to be 0x2, got {dut.unit_sel_q.value}"
    
    assert dut.result_o.value == 0, f"Expected result_o to be 0, got {dut.result_o.value}"
    assert dut.result_valid_o.value == 0, f"Expected result_valid_o to be 0, got {dut.result_valid_o.value}"
    
    await FallingEdge(dut.clk_i)
    dut.load_instruction_i.value = 0 # Clear load instruction signal
    dut.start_unit_i.value = 1 # Start the unit
    
    await ClockCycles(dut.clk_i, 1)
    await Timer(1, unit = "ns")
    
    assert dut.result_valid_o.value == 0, f"Expected result_valid_o to be 0, got {dut.result_valid_o.value}"
    assert dut.unit_ready_o.value == 0, f"Expected unit_ready_o to be 0, got {dut.unit_ready_o.value}"
    assert dut.result_o.value == 0x00000000, f"Expected result_o to be 0x00000000, got {dut.result_o.value}"
    
    dut.start_unit_i.value = 0
    
    await ClockCycles(dut.clk_i, 1)
  
    await Timer(1, unit = "ns")
    
    assert dut.result_valid_o.value == 0, f"Expected result_valid_o to be 0 after first cycle, got {dut.result_valid_o.value}"
    # todo: not sure about here, even if ready_i = 0 it becomes 1 between 2 cycles until we get valid_o 1, it needs to be investigated or checked during controller work
    assert dut.unit_ready_o.value == 1, f"Expected unit_ready_o to be 1 after first cycle, got {dut.unit_ready_o.value}" 
    assert dut.result_o.value == 0x00000000, f"Expected result_o to be 0x00000000 after first cycle, got {dut.result_o.value}"
        
    await ClockCycles(dut.clk_i, 2)
    await Timer(1, unit = "ns")
    
    assert dut.result_valid_o.value == 1, f"Expected result_valid_o to be 0, got {dut.result_valid_o.value}"
    assert dut.unit_ready_o.value == 0, f"Expected unit_ready_o to be 0, got {dut.unit_ready_o.value}"
    assert dut.result_o.value == 0x2B421178, f"Expected result_o to be 0 after consumer ready, got {dut.result_o.value}"
    
    dut.consumer_ready_i.value = 1 # Indicate that the consumer is ready to accept the result

    await ClockCycles(dut.clk_i, 1)
    await Timer(1, unit = "ns")
    
    assert dut.result_valid_o.value == 0, f"Expected result_valid_o to be 0 after consumer ready, got {dut.result_valid_o.value}"
    assert dut.unit_ready_o.value == 1, f"Expected unit_ready_o to be 1 after consumer ready, got {dut.unit_ready_o.value}"
    assert dut.result_o.value == 0x0000000, f"Expected result_o to be 0 after consumer ready, got {dut.result_o.value}"


@cocotb.test()
async def datapath_test_sequential_instructions(dut):
    clk = Clock(dut.clk_i, 10, unit="ns")  # 100 MHz clock
    clk.start()
    await reset_values(dut)  # Reset the DUT
    await FallingEdge(dut.clk_i)
    await Timer(1, unit="ns")

    # Load first instruction (CLMUL)
    dut.rs1_i.value = 0x12345678
    dut.rs2_i.value = 0x87654321
    dut.op_i.value = 0
    dut.aux_i.value = 0
    dut.x_id_i.value = 0x1
    dut.unit_sel_i.value = 0x2
    dut.load_instruction_i.value = 1

    await RisingEdge(dut.clk_i)
    await Timer(1, unit="ns")

    assert dut.x_id_o.value == 0x1, f"Expected x_id_o to be 0x1, got {dut.x_id_o.value}"
    assert dut.unit_sel_q.value == 0x2, f"Expected unit_sel_q to be 0x2, got {dut.unit_sel_q.value}"
    assert dut.result_valid_o.value == 0, f"Expected result_valid_o to be 0, got {dut.result_valid_o.value}"

    # Start the CLMUL unit
    await FallingEdge(dut.clk_i)
    dut.load_instruction_i.value = 0
    dut.start_unit_i.value = 1

    await RisingEdge(dut.clk_i)
    await Timer(1, unit="ns")
    dut.start_unit_i.value = 0

    # Wait for CLMUL result
    for _ in range(6):
        if dut.result_valid_o.value == 1:
            break
        await RisingEdge(dut.clk_i)
        await Timer(1, unit="ns")

    assert dut.result_valid_o.value == 1, f"Expected result_valid_o to be 1, got {dut.result_valid_o.value}"
    assert dut.result_o.value == 0x2B421178, f"Expected result_o to be 0x2B421178, got {dut.result_o.value}"
    assert dut.x_id_o.value == 0x1, f"Expected x_id_o to be 0x1, got {dut.x_id_o.value}"

    # Consume the first result
    await FallingEdge(dut.clk_i)
    dut.consumer_ready_i.value = 1

    await RisingEdge(dut.clk_i)
    await Timer(1, unit="ns")

    assert dut.result_valid_o.value == 0, f"Expected result_valid_o to be 0 after consumer ready, got {dut.result_valid_o.value}"
    assert dut.unit_ready_o.value == 1, f"Expected unit_ready_o to be 1 after consumer ready, got {dut.unit_ready_o.value}"
    assert dut.result_o.value == 0, f"Expected result_o to be 0 after consumer ready, got {dut.result_o.value}"

    # Load second instruction (XPERM)
    await FallingEdge(dut.clk_i)
    dut.consumer_ready_i.value = 0
    dut.rs1_i.value = 0x12345678
    dut.rs2_i.value = 0x87654321
    dut.op_i.value = 0
    dut.aux_i.value = 0b11111
    dut.x_id_i.value = 0x2
    dut.unit_sel_i.value = 0x4
    dut.load_instruction_i.value = 1

    await RisingEdge(dut.clk_i)
    await Timer(1, unit="ns")

    assert dut.x_id_o.value == 0x2, f"Expected x_id_o to be 0x2, got {dut.x_id_o.value}"
    assert dut.unit_sel_q.value == 0x4, f"Expected unit_sel_q to be 0x4, got {dut.unit_sel_q.value}"
    assert dut.result_valid_o.value == 0, f"Expected result_valid_o to be 0, got {dut.result_valid_o.value}"

    # Start the XPERM unit
    await FallingEdge(dut.clk_i)
    dut.load_instruction_i.value = 0
    dut.start_unit_i.value = 1

    await RisingEdge(dut.clk_i)
    await Timer(1, unit="ns")

    assert dut.result_valid_o.value == 1, f"Expected result_valid_o to be 1, got {dut.result_valid_o.value}"
    assert dut.result_o.value == 0x01234567, f"Expected result_o to be 0x01234567, got {dut.result_o.value}"
    assert dut.x_id_o.value == 0x2, f"Expected x_id_o to be 0x2, got {dut.x_id_o.value}"

    # Consume the second result
    await FallingEdge(dut.clk_i)
    dut.start_unit_i.value = 0
    dut.consumer_ready_i.value = 1

    await RisingEdge(dut.clk_i)
    await Timer(1, unit="ns")

    assert dut.result_valid_o.value == 0, f"Expected result_valid_o to be 0 after consumer ready, got {dut.result_valid_o.value}"
    assert dut.unit_ready_o.value == 1, f"Expected unit_ready_o to be 1 after consumer ready, got {dut.unit_ready_o.value}"
    assert dut.result_o.value == 0, f"Expected result_o to be 0 after consumer ready, got {dut.result_o.value}"
    
@cocotb.test()
async def datapath_test_reset_while_busy(dut):
    clk = Clock(dut.clk_i, 10, unit="ns")  # 100 MHz clock
    clk.start()
    await reset_values(dut)  # Reset the DUT
    await FallingEdge(dut.clk_i)
    await Timer(1, unit="ns")

    # Load CLMUL instruction
    dut.rs1_i.value = 0x12345678
    dut.rs2_i.value = 0x87654321
    dut.op_i.value = 0
    dut.aux_i.value = 0
    dut.x_id_i.value = 0x5
    dut.unit_sel_i.value = 0x2
    dut.load_instruction_i.value = 1

    await RisingEdge(dut.clk_i)
    await Timer(1, unit="ns")

    assert dut.rs1_q.value == 0x12345678, f"Expected rs1_q to be 0x12345678, got {dut.rs1_q.value}"
    assert dut.rs2_q.value == 0x87654321, f"Expected rs2_q to be 0x87654321, got {dut.rs2_q.value}"
    assert dut.x_id_o.value == 0x5, f"Expected x_id_o to be 0x5, got {dut.x_id_o.value}"
    assert dut.unit_sel_q.value == 0x2, f"Expected unit_sel_q to be 0x2, got {dut.unit_sel_q.value}"

    # Start the CLMUL unit
    await FallingEdge(dut.clk_i)
    dut.load_instruction_i.value = 0
    dut.start_unit_i.value = 1

    await RisingEdge(dut.clk_i)
    await Timer(1, unit="ns")

    assert dut.result_valid_o.value == 0, f"Expected result_valid_o to be 0, got {dut.result_valid_o.value}"
    assert dut.unit_ready_o.value == 0, f"Expected unit_ready_o to be 0, got {dut.unit_ready_o.value}"

    # Assert reset while CLMUL is busy
    await FallingEdge(dut.clk_i)
    dut.start_unit_i.value = 0
    dut.rst_ni.value = 0

    await Timer(1, unit="ns")

    assert dut.rs1_q.value == 0, f"Expected rs1_q to be 0 after reset, got {dut.rs1_q.value}"
    assert dut.rs2_q.value == 0, f"Expected rs2_q to be 0 after reset, got {dut.rs2_q.value}"
    assert dut.op_q.value == 0, f"Expected op_q to be 0 after reset, got {dut.op_q.value}"
    assert dut.aux_q.value == 0, f"Expected aux_q to be 0 after reset, got {dut.aux_q.value}"
    assert dut.x_id_q.value == 0, f"Expected x_id_q to be 0 after reset, got {dut.x_id_q.value}"
    assert dut.unit_sel_q.value == 0, f"Expected unit_sel_q to be 0 after reset, got {dut.unit_sel_q.value}"
    assert dut.result_valid_o.value == 0, f"Expected result_valid_o to be 0 after reset, got {dut.result_valid_o.value}"
    assert dut.result_o.value == 0, f"Expected result_o to be 0 after reset, got {dut.result_o.value}"
    assert dut.unit_ready_o.value == 0, f"Expected unit_ready_o to be 0 after reset, got {dut.unit_ready_o.value}"

    # Check that no result is generated during reset
    await ClockCycles(dut.clk_i, 2)
    await Timer(1, unit="ns")

    assert dut.result_valid_o.value == 0, f"Expected result_valid_o to remain 0 during reset, got {dut.result_valid_o.value}"
    assert dut.unit_ready_o.value == 0, f"Expected unit_ready_o to remain 0 during reset, got {dut.unit_ready_o.value}"
    assert dut.result_o.value == 0, f"Expected result_o to remain 0 during reset, got {dut.result_o.value}"

    # Release reset
    await FallingEdge(dut.clk_i)
    dut.rst_ni.value = 1
    await Timer(1, unit="ns")

    # check new xperm inputs are loaded after reset is held high
    dut.rs1_i.value = 0x12345678
    dut.rs2_i.value = 0x87654321
    dut.op_i.value = 0
    dut.aux_i.value = 0b11111
    dut.x_id_i.value = 0x6
    dut.unit_sel_i.value = 0x4
    dut.load_instruction_i.value = 1

    await RisingEdge(dut.clk_i)
    await Timer(1, unit="ns")

    assert dut.rs1_q.value == 0x12345678, f"Expected rs1_q to be 0x12345678, got {dut.rs1_q.value}"
    assert dut.rs2_q.value == 0x87654321, f"Expected rs2_q to be 0x87654321, got {dut.rs2_q.value}"
    assert dut.x_id_o.value == 0x6, f"Expected x_id_o to be 0x6, got {dut.x_id_o.value}"
    assert dut.unit_sel_q.value == 0x4, f"Expected unit_sel_q to be 0x4, got {dut.unit_sel_q.value}"
    assert dut.result_valid_o.value == 0, f"Expected result_valid_o to be 0, got {dut.result_valid_o.value}"
    
@cocotb.test()
async def datapath_test_operands_from_inputs(dut):
    clk = Clock(dut.clk_i, 10, unit="ns")  # 100 MHz clock
    clk.start()
    await reset_values(dut)  # Reset the DUT
    await FallingEdge(dut.clk_i)
    await Timer(1, unit="ns")

    # Load instruction with operands_from_inputs_i set to 1
    dut.rs1_i.value = 0x12345678
    dut.rs2_i.value = 0x87654321
    dut.op_i.value = 0
    dut.aux_i.value = 0b11111
    dut.x_id_i.value = 0x7
    dut.unit_sel_i.value = 0x4
    dut.operands_from_inputs_i.value = 1
    dut.load_instruction_i.value = 1
    dut.start_unit_i.value = 1

    await RisingEdge(dut.clk_i)
    await Timer(1, unit="ns")

    assert dut.rs1_q.value == 0x12345678, f"Expected rs1_q to be 0x12345678, got {dut.rs1_q.value}"
    assert dut.rs2_q.value == 0x87654321, f"Expected rs2_q to be 0x87654321, got {dut.rs2_q.value}"
    assert dut.op_q.value == 0, f"Expected op_q to be 0, got {dut.op_q.value}"
    assert dut.aux_q.value == 0b11111, f"Expected aux_q to be 0b11111, got {dut.aux_q.value}"
    assert dut.x_id_q.value == 0x7, f"Expected x_id_q to be 0x7, got {dut.x_id_q.value}"
    assert dut.unit_sel_q.value == 0x4, f"Expected unit_sel_q to be 0x4, got {dut.unit_sel_q.value}"
            
    # check result is generated correctly
    assert dut.result_valid_o.value == 1, f"Expected result_valid_o to be 1, got {dut.result_valid_o.value}"
    assert dut.result_o.value == 0x01234567, f"Expected result_o to be 0x01234567, got {dut.result_o.value}"
    
    await FallingEdge(dut.clk_i)
    await Timer(1, unit="ns")
    
    dut.consumer_ready_i.value = 1
    dut.start_unit_i.value = 0
    dut.load_instruction_i.value = 0
    dut.operands_from_inputs_i.value = 0
    
    await RisingEdge(dut.clk_i)
    await Timer(1, unit="ns")
    
    assert dut.result_valid_o.value == 0, f"Expected result_valid_o to be 0 after consumer ready, got {dut.result_valid_o.value}"
    assert dut.unit_ready_o.value == 1, f"Expected unit_ready_o to be 1 after consumer ready, got {dut.unit_ready_o.value}"