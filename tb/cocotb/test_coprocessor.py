import cocotb

from cocotb.clock import Clock
from cocotb.triggers import Timer, RisingEdge, FallingEdge, ClockCycles

async def reset_values(dut):
    dut.rst_ni.value = 0
    dut.issue_valid_i.value = 0
    dut.issue_id_i.value = 0
    dut.issue_instr_i.value = 0
    dut.issue_rs1_i.value = 0
    dut.issue_rs2_i.value = 0
    dut.commit_valid_i.value = 0
    dut.commit_id_i.value = 0
    dut.commit_kill_i.value = 0
    dut.result_ready_i.value = 0

    await ClockCycles(dut.clk_i, 3)
    await FallingEdge(dut.clk_i)
    dut.rst_ni.value = 1
    await Timer(1, unit="ns")

@cocotb.test()
async def test_coprocessor_xperm_delayed_commit(dut):
    clk = Clock(dut.clk_i, 10, unit="ns")
    clk.start()
    await reset_values(dut)  # Reset the DUT
    await FallingEdge(dut.clk_i)
    await Timer(1, unit="ns")

    # Issue XPERM4 without commit
    dut.issue_valid_i.value = 1
    dut.issue_id_i.value = 5
    dut.issue_instr_i.value = 0x2820A533  # xperm4 x10, x1, x2
    dut.issue_rs1_i.value = 0x12345678
    dut.issue_rs2_i.value = 0x87654321
    await Timer(1, unit="ns")

    assert dut.issue_ready_o.value == 1
    assert dut.issue_accept_o.value == 1
    assert dut.issue_writeback_o.value == 1

    await RisingEdge(dut.clk_i)
    await Timer(1, unit="ns")
    assert dut.issue_ready_o.value == 0
    assert dut.result_valid_o.value == 0

    # Wrong commit ID must not start the instruction
    await FallingEdge(dut.clk_i)
    await Timer(1, unit="ns")
    dut.issue_valid_i.value = 0
    dut.commit_valid_i.value = 1
    dut.commit_id_i.value = 6
    dut.commit_kill_i.value = 1
    await RisingEdge(dut.clk_i)
    await Timer(1, unit="ns")
    assert dut.issue_ready_o.value == 0
    assert dut.result_valid_o.value == 0

    # New instruction must not be accepted during WAIT_COMMIT
    await FallingEdge(dut.clk_i)
    await Timer(1, unit="ns")
    dut.commit_valid_i.value = 0
    dut.issue_valid_i.value = 1
    dut.issue_id_i.value = 6
    dut.issue_instr_i.value = 0x0A2095B3  # clmul x11, x1, x2
    dut.issue_rs1_i.value = 0xFFFFFFFF
    dut.issue_rs2_i.value = 0xFFFFFFFF
    await Timer(1, unit="ns")
    assert dut.issue_ready_o.value == 0
    assert dut.issue_accept_o.value == 0
    await RisingEdge(dut.clk_i)
    await Timer(1, unit="ns")
    assert dut.result_valid_o.value == 0

    # Commit the original XPERM4 instruction
    await FallingEdge(dut.clk_i)
    await Timer(1, unit="ns")
    dut.issue_valid_i.value = 0
    dut.commit_valid_i.value = 1
    dut.commit_id_i.value = 5
    dut.commit_kill_i.value = 0
    await RisingEdge(dut.clk_i)
    await Timer(1, unit="ns")
    assert dut.issue_ready_o.value == 0
    assert dut.result_valid_o.value == 1
    assert dut.result_we_o.value == 1
    assert dut.result_id_o.value == 5
    assert dut.result_rd_o.value == 10
    assert dut.result_data_o.value == 0x01234567

    # Consume the result
    await FallingEdge(dut.clk_i)
    await Timer(1, unit="ns")
    dut.commit_valid_i.value = 0
    dut.result_ready_i.value = 1
    await RisingEdge(dut.clk_i)
    await Timer(1, unit="ns")
    assert dut.issue_ready_o.value == 1
    assert dut.result_valid_o.value == 0

@cocotb.test()
async def test_coprocessor_xperm_same_cycle(dut):
    clk = Clock(dut.clk_i, 10, unit="ns")
    clk.start()
    await reset_values(dut)  # Reset the DUT
    await FallingEdge(dut.clk_i)
    await Timer(1, unit="ns")

    # Issue and commit XPERM4 in the same cycle
    dut.issue_valid_i.value = 1
    dut.issue_id_i.value = 3
    dut.issue_instr_i.value = 0x2820A633  # xperm4 x12, x1, x2
    dut.issue_rs1_i.value = 0x12345678
    dut.issue_rs2_i.value = 0x87654321
    dut.commit_valid_i.value = 1
    dut.commit_id_i.value = 3
    dut.commit_kill_i.value = 0
    dut.result_ready_i.value = 1
    await Timer(1, unit="ns")

    assert dut.issue_ready_o.value == 1
    assert dut.issue_accept_o.value == 1
    assert dut.issue_writeback_o.value == 1

    await RisingEdge(dut.clk_i)
    await Timer(1, unit="ns")
    assert dut.issue_ready_o.value == 0
    assert dut.result_valid_o.value == 1
    assert dut.result_we_o.value == 1
    assert dut.result_id_o.value == 3
    assert dut.result_rd_o.value == 12
    assert dut.result_data_o.value == 0x01234567

    # Result handshake happens at the next rising edge
    await FallingEdge(dut.clk_i)
    await Timer(1, unit="ns")
    dut.issue_valid_i.value = 0
    dut.commit_valid_i.value = 0
    await RisingEdge(dut.clk_i)
    await Timer(1, unit="ns")
    assert dut.issue_ready_o.value == 1
    assert dut.result_valid_o.value == 0

@cocotb.test()
async def test_coprocessor_clmul_same_cycle(dut):
    clk = Clock(dut.clk_i, 10, unit="ns")
    clk.start()
    await reset_values(dut)  # Reset the DUT
    await FallingEdge(dut.clk_i)
    await Timer(1, unit="ns")

    # Issue and commit CLMUL in the same cycle
    dut.issue_valid_i.value = 1
    dut.issue_id_i.value = 4
    dut.issue_instr_i.value = 0x0A209733  # clmul x14, x1, x2
    dut.issue_rs1_i.value = 0x12345678
    dut.issue_rs2_i.value = 0x87654321
    dut.commit_valid_i.value = 1
    dut.commit_id_i.value = 4
    dut.result_ready_i.value = 1
    await Timer(1, unit="ns")
    assert dut.issue_ready_o.value == 1
    assert dut.issue_accept_o.value == 1

    await RisingEdge(dut.clk_i)  # CLMUL: IDLE -> STAGE0
    await Timer(1, unit="ns")
    assert dut.issue_ready_o.value == 0
    assert dut.result_valid_o.value == 0

    # CLMUL first calculation stage
    await FallingEdge(dut.clk_i)
    await Timer(1, unit="ns")
    dut.issue_valid_i.value = 0
    dut.commit_valid_i.value = 0
    await RisingEdge(dut.clk_i)  # STAGE0 -> STAGE1
    await Timer(1, unit="ns")
    assert dut.issue_ready_o.value == 0
    assert dut.result_valid_o.value == 0

    # CLMUL second calculation stage produces result
    await RisingEdge(dut.clk_i)  # STAGE1 -> IDLE
    await Timer(1, unit="ns")
    assert dut.issue_ready_o.value == 0
    assert dut.result_valid_o.value == 1
    assert dut.result_we_o.value == 1
    assert dut.result_id_o.value == 4
    assert dut.result_rd_o.value == 14
    assert dut.result_data_o.value == 0x2B421178

    # Consume the result
    await RisingEdge(dut.clk_i)
    await Timer(1, unit="ns")
    assert dut.issue_ready_o.value == 1
    assert dut.result_valid_o.value == 0

@cocotb.test()
async def test_coprocessor_issue_commit_kill_same_cycle(dut):
    clk = Clock(dut.clk_i, 10, unit="ns")
    clk.start()
    await reset_values(dut)  # Reset the DUT
    await FallingEdge(dut.clk_i)
    await Timer(1, unit="ns")

    # Issue and kill the same instruction at once
    dut.issue_valid_i.value = 1
    dut.issue_id_i.value = 7
    dut.issue_instr_i.value = 0x2820A7B3  # xperm4 x15, x1, x2
    dut.issue_rs1_i.value = 0x12345678
    dut.issue_rs2_i.value = 0x87654321
    dut.commit_valid_i.value = 1
    dut.commit_id_i.value = 7
    dut.commit_kill_i.value = 1
    await Timer(1, unit="ns")
    assert dut.issue_ready_o.value == 1
    assert dut.issue_accept_o.value == 1
    assert dut.issue_writeback_o.value == 1

    await RisingEdge(dut.clk_i)
    await Timer(1, unit="ns")
    assert dut.issue_ready_o.value == 1
    assert dut.result_valid_o.value == 0

    # Killed instruction must not produce any result
    await FallingEdge(dut.clk_i)
    await Timer(1, unit="ns")
    dut.issue_valid_i.value = 0
    dut.commit_valid_i.value = 0
    dut.commit_kill_i.value = 0
    for _ in range(3):
        await RisingEdge(dut.clk_i)
        await Timer(1, unit="ns")
        assert dut.issue_ready_o.value == 1
        assert dut.result_valid_o.value == 0

@cocotb.test()
async def test_coprocessor_delayed_commit_kill(dut):
    clk = Clock(dut.clk_i, 10, unit="ns")
    clk.start()
    await reset_values(dut)  # Reset the DUT
    await FallingEdge(dut.clk_i)
    await Timer(1, unit="ns")

    # Issue CLMUL and wait for commit
    dut.issue_valid_i.value = 1
    dut.issue_id_i.value = 8
    dut.issue_instr_i.value = 0x0A209833  # clmul x16, x1, x2
    dut.issue_rs1_i.value = 0x12345678
    dut.issue_rs2_i.value = 0x87654321
    await RisingEdge(dut.clk_i)
    await Timer(1, unit="ns")
    assert dut.issue_ready_o.value == 0
    assert dut.result_valid_o.value == 0

    # Kill the pending instruction before dispatch
    await FallingEdge(dut.clk_i)
    await Timer(1, unit="ns")
    dut.issue_valid_i.value = 0
    dut.commit_valid_i.value = 1
    dut.commit_id_i.value = 8
    dut.commit_kill_i.value = 1
    await RisingEdge(dut.clk_i)
    await Timer(1, unit="ns")
    assert dut.issue_ready_o.value == 1
    assert dut.result_valid_o.value == 0

    await FallingEdge(dut.clk_i)
    await Timer(1, unit="ns")
    dut.commit_valid_i.value = 0
    dut.commit_kill_i.value = 0
    for _ in range(4):
        await RisingEdge(dut.clk_i)
        await Timer(1, unit="ns")
        assert dut.issue_ready_o.value == 1
        assert dut.result_valid_o.value == 0

@cocotb.test()
async def test_coprocessor_busy_issue_and_backpressure(dut):
    clk = Clock(dut.clk_i, 10, unit="ns")
    clk.start()
    await reset_values(dut)  # Reset the DUT
    await FallingEdge(dut.clk_i)
    await Timer(1, unit="ns")

    # Start CLMUL with result backpressure enabled
    dut.issue_valid_i.value = 1
    dut.issue_id_i.value = 9
    dut.issue_instr_i.value = 0x0A2098B3  # clmul x17, x1, x2
    dut.issue_rs1_i.value = 0x13579BDF
    dut.issue_rs2_i.value = 0x2468ACE0
    dut.commit_valid_i.value = 1
    dut.commit_id_i.value = 9
    dut.result_ready_i.value = 0
    await RisingEdge(dut.clk_i)
    await Timer(1, unit="ns")
    assert dut.issue_ready_o.value == 0
    assert dut.result_valid_o.value == 0

    # Try another issue while CLMUL is still running
    await FallingEdge(dut.clk_i)
    await Timer(1, unit="ns")
    dut.issue_valid_i.value = 1
    dut.issue_id_i.value = 10
    dut.issue_instr_i.value = 0x2820A933  # xperm4 x18, x1, x2
    dut.issue_rs1_i.value = 0xFFFFFFFF
    dut.issue_rs2_i.value = 0x87654321
    dut.commit_valid_i.value = 1
    dut.commit_id_i.value = 10
    dut.commit_kill_i.value = 1
    await Timer(1, unit="ns")
    assert dut.issue_ready_o.value == 0
    assert dut.issue_accept_o.value == 0
    assert dut.issue_writeback_o.value == 0
    await RisingEdge(dut.clk_i)
    await Timer(1, unit="ns")
    assert dut.issue_ready_o.value == 0
    assert dut.result_valid_o.value == 0

    # Original CLMUL result must be preserved despite the new issue
    await FallingEdge(dut.clk_i)
    await Timer(1, unit="ns")
    dut.commit_valid_i.value = 0
    dut.commit_kill_i.value = 0
    await RisingEdge(dut.clk_i)
    await Timer(1, unit="ns")
    assert dut.issue_ready_o.value == 0
    assert dut.result_valid_o.value == 1
    assert dut.result_we_o.value == 1
    assert dut.result_id_o.value == 9
    assert dut.result_rd_o.value == 17
    assert dut.result_data_o.value == 0x062587A0

    # Hold the result for multiple cycles
    for _ in range(3):
        await RisingEdge(dut.clk_i)
        await Timer(1, unit="ns")
        assert dut.issue_ready_o.value == 0
        assert dut.issue_accept_o.value == 0
        assert dut.result_valid_o.value == 1
        assert dut.result_id_o.value == 9
        assert dut.result_rd_o.value == 17
        assert dut.result_data_o.value == 0x062587A0

    # Consume the first result, while the second issue is still being requested
    await FallingEdge(dut.clk_i)
    await Timer(1, unit="ns")
    dut.result_ready_i.value = 1
    assert dut.issue_ready_o.value == 0
    await RisingEdge(dut.clk_i)
    await Timer(1, unit="ns")
    assert dut.issue_ready_o.value == 1
    assert dut.result_valid_o.value == 0

    # The pending XPERM request is accepted on the next edge
    await FallingEdge(dut.clk_i)
    await Timer(1, unit="ns")
    dut.commit_valid_i.value = 1
    dut.commit_id_i.value = 10
    await Timer(1, unit="ns")
    assert dut.issue_ready_o.value == 1
    assert dut.issue_accept_o.value == 1
    await RisingEdge(dut.clk_i)
    await Timer(1, unit="ns")
    assert dut.result_valid_o.value == 1
    assert dut.result_id_o.value == 10
    assert dut.result_rd_o.value == 18
    assert dut.result_data_o.value == 0x0FFFFFFF

    await FallingEdge(dut.clk_i)
    await Timer(1, unit="ns")
    dut.issue_valid_i.value = 0
    dut.commit_valid_i.value = 0
    await RisingEdge(dut.clk_i)
    await Timer(1, unit="ns")
    assert dut.issue_ready_o.value == 1
    assert dut.result_valid_o.value == 0

@cocotb.test()
async def test_coprocessor_two_sequential_instructions(dut):
    clk = Clock(dut.clk_i, 10, unit="ns")
    clk.start()
    await reset_values(dut)  # Reset the DUT
    await FallingEdge(dut.clk_i)
    await Timer(1, unit="ns")

    # First instruction: XPERM4
    dut.issue_valid_i.value = 1
    dut.issue_id_i.value = 1
    dut.issue_instr_i.value = 0x2820AA33  # xperm4 x20, x1, x2
    dut.issue_rs1_i.value = 0x12345678
    dut.issue_rs2_i.value = 0x87654321
    dut.commit_valid_i.value = 1
    dut.commit_id_i.value = 1
    dut.result_ready_i.value = 1
    await RisingEdge(dut.clk_i)
    await Timer(1, unit="ns")
    assert dut.result_valid_o.value == 1
    assert dut.result_id_o.value == 1
    assert dut.result_rd_o.value == 20
    assert dut.result_data_o.value == 0x01234567

    # Present CLMUL while XPERM result is still pending
    await FallingEdge(dut.clk_i)
    await Timer(1, unit="ns")
    dut.issue_valid_i.value = 1
    dut.issue_id_i.value = 2
    dut.issue_instr_i.value = 0x0A209AB3  # clmul x21, x1, x2
    dut.issue_rs1_i.value = 0x13579BDF
    dut.issue_rs2_i.value = 0x2468ACE0
    dut.commit_valid_i.value = 1
    dut.commit_id_i.value = 2
    await Timer(1, unit="ns")
    assert dut.issue_ready_o.value == 0
    assert dut.issue_accept_o.value == 0

    # First result is consumed; the second issue cannot be accepted at this edge
    await RisingEdge(dut.clk_i)
    await Timer(1, unit="ns")
    assert dut.issue_ready_o.value == 1
    assert dut.result_valid_o.value == 0

    # Second issue is accepted on the next rising edge
    await RisingEdge(dut.clk_i)
    await Timer(1, unit="ns")
    assert dut.issue_ready_o.value == 0
    assert dut.result_valid_o.value == 0

    await FallingEdge(dut.clk_i)
    await Timer(1, unit="ns")
    dut.issue_valid_i.value = 0
    dut.commit_valid_i.value = 0
    await RisingEdge(dut.clk_i)
    await Timer(1, unit="ns")
    assert dut.result_valid_o.value == 0

    await RisingEdge(dut.clk_i)
    await Timer(1, unit="ns")
    assert dut.result_valid_o.value == 1
    assert dut.result_we_o.value == 1
    assert dut.result_id_o.value == 2
    assert dut.result_rd_o.value == 21
    assert dut.result_data_o.value == 0x062587A0

    await RisingEdge(dut.clk_i)
    await Timer(1, unit="ns")
    assert dut.issue_ready_o.value == 1
    assert dut.result_valid_o.value == 0

@cocotb.test()
async def test_coprocessor_two_sequential_same_unit(dut):
    clk = Clock(dut.clk_i, 10, unit="ns")
    clk.start()
    await reset_values(dut)  # Reset the DUT
    await FallingEdge(dut.clk_i)
    await Timer(1, unit="ns")

    # First XPERM4 instruction
    dut.issue_valid_i.value = 1
    dut.issue_id_i.value = 11
    dut.issue_instr_i.value = 0x2820AB33  # xperm4 x22, x1, x2
    dut.issue_rs1_i.value = 0x12345678
    dut.issue_rs2_i.value = 0x87654321
    dut.commit_valid_i.value = 1
    dut.commit_id_i.value = 11
    dut.result_ready_i.value = 1
    await RisingEdge(dut.clk_i)
    await Timer(1, unit="ns")
    assert dut.result_valid_o.value == 1
    assert dut.result_id_o.value == 11
    assert dut.result_rd_o.value == 22
    assert dut.result_data_o.value == 0x01234567

    # Consume first result
    await FallingEdge(dut.clk_i)
    await Timer(1, unit="ns")
    dut.issue_valid_i.value = 0
    dut.commit_valid_i.value = 0
    await RisingEdge(dut.clk_i)
    await Timer(1, unit="ns")
    assert dut.issue_ready_o.value == 1
    assert dut.result_valid_o.value == 0

    # Second XPERM4 must use the new operands and metadata
    await FallingEdge(dut.clk_i)
    await Timer(1, unit="ns")
    dut.issue_valid_i.value = 1
    dut.issue_id_i.value = 12
    dut.issue_instr_i.value = 0x2820ABB3  # xperm4 x23, x1, x2
    dut.issue_rs1_i.value = 0x89ABCDEF
    dut.issue_rs2_i.value = 0x01234567
    dut.commit_valid_i.value = 1
    dut.commit_id_i.value = 12
    await Timer(1, unit="ns")
    assert dut.issue_ready_o.value == 1
    assert dut.issue_accept_o.value == 1
    await RisingEdge(dut.clk_i)
    await Timer(1, unit="ns")
    assert dut.issue_ready_o.value == 0
    assert dut.result_valid_o.value == 1
    assert dut.result_id_o.value == 12
    assert dut.result_rd_o.value == 23
    assert dut.result_data_o.value == 0xFEDCBA98

    await FallingEdge(dut.clk_i)
    await Timer(1, unit="ns")
    dut.issue_valid_i.value = 0
    dut.commit_valid_i.value = 0
    await RisingEdge(dut.clk_i)
    await Timer(1, unit="ns")
    assert dut.issue_ready_o.value == 1
    assert dut.result_valid_o.value == 0

@cocotb.test()
async def test_coprocessor_rori_immediate(dut):
    clk = Clock(dut.clk_i, 10, unit="ns")  # 100 MHz clock
    clk.start()
    await reset_values(dut)  # Reset the DUT
    await FallingEdge(dut.clk_i)
    await Timer(1, unit="ns")

    # RORI shamt=5 must use immediate bits, not issue_rs2_i
    dut.issue_valid_i.value = 1
    dut.issue_id_i.value = 13
    dut.issue_instr_i.value = 0x6050DC13  # rori x24, x1, 5
    dut.issue_rs1_i.value = 0x12345678
    dut.issue_rs2_i.value = 0x0000000F
    dut.commit_valid_i.value = 1
    dut.commit_id_i.value = 13
    dut.result_ready_i.value = 1
    await Timer(1, unit="ns")
    assert dut.issue_accept_o.value == 1
    await RisingEdge(dut.clk_i)
    await Timer(1, unit="ns")
    assert dut.result_valid_o.value == 1
    assert dut.result_we_o.value == 1
    assert dut.result_id_o.value == 13
    assert dut.result_rd_o.value == 24
    assert dut.result_data_o.value == 0xC091A2B3

    await FallingEdge(dut.clk_i)
    await Timer(1, unit="ns")
    dut.issue_valid_i.value = 0
    dut.commit_valid_i.value = 0
    await RisingEdge(dut.clk_i)
    await Timer(1, unit="ns")
    assert dut.issue_ready_o.value == 1
    assert dut.result_valid_o.value == 0

@cocotb.test()
async def test_coprocessor_illegal_instruction(dut):
    clk = Clock(dut.clk_i, 10, unit="ns")  # 100 MHz clock
    clk.start()
    await reset_values(dut)  # Reset the DUT
    await FallingEdge(dut.clk_i)
    await Timer(1, unit="ns")

    # Unsupported instruction must be rejected by decoder/controller
    dut.issue_valid_i.value = 1
    dut.issue_id_i.value = 14
    dut.issue_instr_i.value = 0xFFFFFFFF
    dut.issue_rs1_i.value = 0x12345678
    dut.issue_rs2_i.value = 0x87654321
    dut.commit_valid_i.value = 1
    dut.commit_id_i.value = 14
    await Timer(1, unit="ns")
    assert dut.issue_ready_o.value == 1
    assert dut.issue_accept_o.value == 0
    assert dut.issue_writeback_o.value == 0

    await RisingEdge(dut.clk_i)
    await Timer(1, unit="ns")
    assert dut.issue_ready_o.value == 1
    assert dut.result_valid_o.value == 0

    await FallingEdge(dut.clk_i)
    await Timer(1, unit="ns")
    dut.issue_valid_i.value = 0
    dut.commit_valid_i.value = 0
    for _ in range(2):
        await RisingEdge(dut.clk_i)
        await Timer(1, unit="ns")
        assert dut.issue_ready_o.value == 1
        assert dut.result_valid_o.value == 0
