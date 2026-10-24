from enum import Enum

import cocotb

from cocotb.clock import Clock
from cocotb.triggers import (
    Timer,
    RisingEdge,
    FallingEdge,
    ClockCycles,
    ReadOnly,
)

class States(Enum):
    IDLE = 0
    WAIT_COMMIT = 1
    RUN = 2

async def reset_values(dut):
    dut.rst_ni.value = 0 # Reset the DUT
    dut.issue_valid_i.value = 0
    dut.issue_id_i.value = 0
    dut.issue_rd_i.value = 0
    dut.decoder_illegal_i.value = 0
    dut.commit_valid_i.value = 0
    dut.commit_id_i.value = 0
    dut.commit_kill_i.value = 0
    dut.result_ready_i.value = 0
    dut.result_valid_i.value = 0
    dut.unit_ready_i.value = 0
    
    await ClockCycles(dut.clk_i, 3)
    await FallingEdge(dut.clk_i)
    
    dut.rst_ni.value = 1 # Release reset
    
    await Timer(1, unit="ns") # wait a bit

@cocotb.test()
async def test_controller_right_case(dut):
    clk = Clock(dut.clk_i, 10, unit="ns") # 100 MHz clock
    clk.start()
    
    await reset_values(dut) # Reset the DUT
    
    await FallingEdge(dut.clk_i)
    
    await Timer(1, unit = "ns")
    
    # check initial state is IDLE
    assert dut.state_d.value == States.IDLE.value
    assert dut.state_q.value == States.IDLE.value

    dut.issue_valid_i.value = 1
    dut.issue_rd_i.value = 10
    dut.issue_id_i.value = 5
    dut.decoder_illegal_i.value = 0
    
    await ReadOnly()
    
    assert dut.state_d.value == States.WAIT_COMMIT.value
    assert dut.issue_ready_o.value == 1

    await FallingEdge(dut.clk_i)
    await Timer(1, unit = "ns")
    
    dut.issue_valid_i.value = 0
    
    await RisingEdge(dut.clk_i)
    await Timer(1, unit = "ns")
    
    assert dut.state_q.value == States.WAIT_COMMIT.value
    
    dut.commit_valid_i.value = 1
    dut.commit_id_i.value = 5
    dut.commit_kill_i.value = 0
    
    await ReadOnly()
    
    assert dut.state_d.value == States.RUN.value
    assert dut.start_unit_o.value == 1
    
    await RisingEdge(dut.clk_i)
    await Timer(1, unit = "ns")
    
    assert dut.state_q.value == States.RUN.value
    await ReadOnly()
    
    assert dut.start_unit_o.value == 0
    assert dut.consumer_ready_o.value == 0
    assert dut.operands_from_inputs_o.value == 0
    assert dut.result_valid_o.value == 0
    
    assert dut.result_rd_o.value == 10
    assert dut.result_we_o.value == 1
    
    await FallingEdge(dut.clk_i)
    
    dut.result_ready_i.value = 1
    
    await ClockCycles(dut.clk_i, 1)
    await Timer(1, unit = "ns")
    
    assert dut.consumer_ready_o.value == 1
    
    dut.result_valid_i.value = 1
    
    await ReadOnly()
    
    assert dut.state_d.value == States.IDLE.value
    assert dut.result_valid_o.value == 1
    
    # consume the result
    await RisingEdge(dut.clk_i)
    await Timer(1, unit = "ns")
    
    assert dut.state_q.value == States.IDLE.value
    
@cocotb.test()
async def test_controller_issue_valid_sametime(dut):
    clk = Clock(dut.clk_i, 10, unit="ns") # 100 MHz clock
    clk.start()
    
    await reset_values(dut) # Reset the DUT
    
    await FallingEdge(dut.clk_i)
    
    await Timer(1, unit = "ns")
    
    # check initial state is IDLE
    assert dut.state_d.value == States.IDLE.value
    assert dut.state_q.value == States.IDLE.value

    dut.issue_valid_i.value = 1
    dut.issue_rd_i.value = 10
    dut.issue_id_i.value = 5
    dut.decoder_illegal_i.value = 0
    dut.commit_valid_i.value = 1
    dut.commit_id_i.value = 5
    dut.commit_kill_i.value = 0
    
    await ReadOnly()
    
    assert dut.state_d.value == States.RUN.value
    assert dut.start_unit_o.value == 1
    assert dut.operands_from_inputs_o.value == 1
    assert dut.load_instruction_o.value == 1
    
    await RisingEdge(dut.clk_i)
    await Timer(1, unit = "ns")
    
    assert dut.state_q.value == States.RUN.value
    assert dut.start_unit_o.value == 0
    assert dut.operands_from_inputs_o.value == 0
    assert dut.result_valid_o.value == 0
    assert dut.consumer_ready_o.value == 0
    assert dut.result_rd_o.value == 10
    assert dut.result_we_o.value == 1
    
    await FallingEdge(dut.clk_i)
    await Timer(1, unit = "ns")
    
    dut.issue_valid_i.value = 0
    dut.result_valid_i.value = 1
    dut.result_ready_i.value = 1
    
    await ReadOnly()
    
    await RisingEdge(dut.clk_i)
    await Timer(1, unit = "ns")
    
    assert dut.state_q.value == States.IDLE.value
    
    # kill commit and issue at the same time
    dut.issue_valid_i.value = 1
    dut.issue_rd_i.value = 20
    dut.issue_id_i.value = 6
    dut.decoder_illegal_i.value = 0
    dut.commit_valid_i.value = 1
    dut.commit_id_i.value = 6
    dut.commit_kill_i.value = 1
    
    await RisingEdge(dut.clk_i)
    await Timer(1, unit = "ns")
    
    assert dut.state_q.value == States.IDLE.value
    assert dut.start_unit_o.value == 0
    assert dut.operands_from_inputs_o.value == 0
    assert dut.load_instruction_o.value == 0
    
    # no matter commit is denied, the issue is still accepted
    assert dut.issue_ready_o.value == 1
    assert dut.issue_writeback_o.value == 1

@cocotb.test()
async def test_controller_commit_kill(dut):
    clk = Clock(dut.clk_i, 10, unit="ns") # 100 MHz clock
    clk.start()
    
    await reset_values(dut) # Reset the DUT
    
    await FallingEdge(dut.clk_i)
    
    await Timer(1, unit = "ns")
    
    # check initial state is IDLE
    assert dut.state_d.value == States.IDLE.value
    assert dut.state_q.value == States.IDLE.value

    dut.issue_valid_i.value = 1
    dut.issue_rd_i.value = 10
    dut.issue_id_i.value = 5
    dut.decoder_illegal_i.value = 0
    
    await ReadOnly()
    
    assert dut.state_d.value == States.WAIT_COMMIT.value
    assert dut.issue_ready_o.value == 1
    
    await RisingEdge(dut.clk_i)
    await Timer(1, unit = "ns")
    
    assert dut.state_q.value == States.WAIT_COMMIT.value
    
    await ReadOnly()
    
    await FallingEdge(dut.clk_i)
    await Timer(1, unit = "ns")
    
    dut.commit_valid_i.value = 1
    dut.commit_id_i.value = 5
    dut.commit_kill_i.value = 1
    dut.issue_valid_i.value = 0
    
    await RisingEdge(dut.clk_i)
    await Timer(1, unit = "ns")
    
    assert dut.state_q.value == States.IDLE.value

@cocotb.test()
async def test_controller_result_backpressure(dut):
    clk = Clock(dut.clk_i, 10, unit="ns")
    clk.start()
    await reset_values(dut)

    # Issue and commit at the same cycle
    await FallingEdge(dut.clk_i)
    dut.issue_valid_i.value = 1
    dut.issue_id_i.value = 5
    dut.issue_rd_i.value = 10
    dut.commit_valid_i.value = 1
    dut.commit_id_i.value = 5
    dut.commit_kill_i.value = 0
    await Timer(1, unit="ns")

    assert dut.issue_accept_o.value == 1
    assert dut.load_instruction_o.value == 1
    assert dut.start_unit_o.value == 1

    await RisingEdge(dut.clk_i)
    await Timer(1, unit="ns")
    assert dut.state_q.value == States.RUN.value

    # Result is valid but core is not ready
    await FallingEdge(dut.clk_i)
    dut.issue_valid_i.value = 0
    dut.commit_valid_i.value = 0
    dut.result_valid_i.value = 1
    dut.result_ready_i.value = 0
    await Timer(1, unit="ns")

    for _ in range(3):
        assert dut.state_q.value == States.RUN.value
        assert dut.state_d.value == States.RUN.value
        assert dut.result_valid_o.value == 1
        assert dut.result_we_o.value == 1
        assert dut.result_rd_o.value == 10
        assert dut.consumer_ready_o.value == 0

        await RisingEdge(dut.clk_i)
        await Timer(1, unit="ns")
        assert dut.state_q.value == States.RUN.value
        await FallingEdge(dut.clk_i)

    # Core becomes ready and consumes the result
    dut.result_ready_i.value = 1
    await Timer(1, unit="ns")

    assert dut.consumer_ready_o.value == 1
    assert dut.result_valid_o.value == 1
    assert dut.state_d.value == States.IDLE.value

    await RisingEdge(dut.clk_i)
    await Timer(1, unit="ns")

    assert dut.state_q.value == States.IDLE.value
    assert dut.result_valid_o.value == 0
    assert dut.consumer_ready_o.value == 0
    assert dut.issue_ready_o.value == 1

@cocotb.test()
async def test_controller_illegal_instruction(dut):
    clk = Clock(dut.clk_i, 10, unit="ns")
    clk.start()
    await reset_values(dut)

    # Issue an illegal instruction
    await FallingEdge(dut.clk_i)
    dut.issue_valid_i.value = 1
    dut.issue_id_i.value = 5
    dut.issue_rd_i.value = 10
    dut.decoder_illegal_i.value = 1
    await Timer(1, unit="ns")

    assert dut.issue_accept_o.value == 0
    assert dut.state_d.value == States.IDLE.value

    await RisingEdge(dut.clk_i)
    await Timer(1, unit="ns")
    assert dut.state_q.value == States.IDLE.value
    
@cocotb.test()
async def test_controller_commit_id_mismatch(dut):
    clk = Clock(dut.clk_i, 10, unit="ns")
    clk.start()
    await reset_values(dut)

    # Issue a valid instruction
    await FallingEdge(dut.clk_i)
    dut.issue_valid_i.value = 1
    dut.issue_id_i.value = 5
    dut.issue_rd_i.value = 10
    dut.decoder_illegal_i.value = 0
    await Timer(1, unit="ns")

    assert dut.issue_accept_o.value == 1
    assert dut.state_d.value == States.WAIT_COMMIT.value

    await RisingEdge(dut.clk_i)
    await Timer(1, unit="ns")
    assert dut.state_q.value == States.WAIT_COMMIT.value

    # Commit with a different ID
    await FallingEdge(dut.clk_i)
    dut.commit_valid_i.value = 1
    dut.commit_id_i.value = 6
    dut.commit_kill_i.value = 0
    await Timer(1, unit="ns")

    assert dut.state_d.value == States.WAIT_COMMIT.value

    await RisingEdge(dut.clk_i)
    await Timer(1, unit="ns")
    
    assert dut.state_q.value == States.WAIT_COMMIT.value

@cocotb.test()
async def test_controller_busy_wrong_commit(dut):
    clk = Clock(dut.clk_i, 10, unit="ns")
    clk.start()
    await reset_values(dut)

    # Issue the first instruction
    await FallingEdge(dut.clk_i)
    dut.issue_valid_i.value = 1
    dut.issue_id_i.value = 5
    dut.issue_rd_i.value = 10
    await Timer(1, unit="ns")

    assert dut.issue_ready_o.value == 1
    assert dut.issue_accept_o.value == 1
    assert dut.load_instruction_o.value == 1

    await RisingEdge(dut.clk_i)
    await Timer(1, unit="ns")
    assert dut.state_q.value == States.WAIT_COMMIT.value

    # Try issuing another instruction while busy
    await FallingEdge(dut.clk_i)
    dut.issue_valid_i.value = 1
    dut.issue_id_i.value = 6
    dut.issue_rd_i.value = 20
    dut.commit_valid_i.value = 1
    dut.commit_id_i.value = 6
    dut.commit_kill_i.value = 0
    await Timer(1, unit="ns")

    assert dut.issue_ready_o.value == 0
    assert dut.issue_accept_o.value == 0
    assert dut.load_instruction_o.value == 0
    assert dut.start_unit_o.value == 0
    assert dut.state_d.value == States.WAIT_COMMIT.value

    await RisingEdge(dut.clk_i)
    await Timer(1, unit="ns")

    assert dut.state_q.value == States.WAIT_COMMIT.value
    assert dut.issue_id_q.value == 5
    assert dut.result_rd_q.value == 10

    # Commit the original instruction
    await FallingEdge(dut.clk_i)
    dut.issue_valid_i.value = 0
    dut.commit_id_i.value = 5
    await Timer(1, unit="ns")

    assert dut.start_unit_o.value == 1
    assert dut.state_d.value == States.RUN.value

    await RisingEdge(dut.clk_i)
    await Timer(1, unit="ns")

    assert dut.state_q.value == States.RUN.value
    assert dut.issue_ready_o.value == 0
    assert dut.result_rd_o.value == 10


@cocotb.test()
async def test_controller_issue_while_running(dut):
    clk = Clock(dut.clk_i, 10, unit="ns")
    clk.start()
    await reset_values(dut)

    # Issue and commit the first instruction
    await FallingEdge(dut.clk_i)
    dut.issue_valid_i.value = 1
    dut.issue_id_i.value = 5
    dut.issue_rd_i.value = 10
    dut.decoder_illegal_i.value = 0
    dut.commit_valid_i.value = 1
    dut.commit_id_i.value = 5
    dut.commit_kill_i.value = 0
    await Timer(1, unit="ns")

    assert dut.issue_ready_o.value == 1
    assert dut.issue_accept_o.value == 1
    assert dut.load_instruction_o.value == 1
    assert dut.start_unit_o.value == 1
    assert dut.operands_from_inputs_o.value == 1

    await RisingEdge(dut.clk_i)
    await Timer(1, unit="ns")
    assert dut.state_q.value == States.RUN.value

    # Try issuing new instructions while the unit is running
    for new_id, new_rd, result_valid in [(6, 20, 0), (7, 21, 1)]:
        await FallingEdge(dut.clk_i)
        dut.issue_valid_i.value = 1
        dut.issue_id_i.value = new_id
        dut.issue_rd_i.value = new_rd
        dut.commit_valid_i.value = 0
        dut.result_valid_i.value = result_valid
        dut.result_ready_i.value = 0
        await Timer(1, unit="ns")

        assert dut.issue_ready_o.value == 0
        assert dut.issue_accept_o.value == 0
        assert dut.issue_writeback_o.value == 0
        assert dut.load_instruction_o.value == 0
        assert dut.start_unit_o.value == 0
        assert dut.operands_from_inputs_o.value == 0
        assert dut.state_d.value == States.RUN.value
        assert dut.result_rd_o.value == 10
        assert dut.result_valid_o.value == result_valid

        await RisingEdge(dut.clk_i)
        await Timer(1, unit="ns")

        assert dut.state_q.value == States.RUN.value
        assert dut.issue_id_q.value == 5
        assert dut.result_rd_q.value == 10

    # Consume the result while another issue is still pending
    await FallingEdge(dut.clk_i)
    dut.result_ready_i.value = 1
    await Timer(1, unit="ns")

    assert dut.result_valid_o.value == 1
    assert dut.consumer_ready_o.value == 1
    assert dut.issue_ready_o.value == 0
    assert dut.issue_accept_o.value == 0
    assert dut.load_instruction_o.value == 0
    assert dut.state_d.value == States.IDLE.value

    await RisingEdge(dut.clk_i)
    await Timer(1, unit="ns")

    assert dut.state_q.value == States.IDLE.value
    assert dut.issue_ready_o.value == 1


@cocotb.test()
async def test_controller_delayed_commit(dut):
    clk = Clock(dut.clk_i, 10, unit="ns")
    clk.start()
    await reset_values(dut)

    # Issue an instruction
    await FallingEdge(dut.clk_i)
    dut.issue_valid_i.value = 1
    dut.issue_id_i.value = 5
    dut.issue_rd_i.value = 10
    await Timer(1, unit="ns")

    assert dut.load_instruction_o.value == 1
    assert dut.issue_accept_o.value == 1

    await RisingEdge(dut.clk_i)
    await Timer(1, unit="ns")
    assert dut.state_q.value == States.WAIT_COMMIT.value

    # Wait for commit with invalid commit signals
    for commit_id, commit_kill in [(6, 0), (6, 1), (5, 1), (5, 0)]:
        await FallingEdge(dut.clk_i)
        dut.issue_valid_i.value = 0
        dut.commit_valid_i.value = 0
        dut.commit_id_i.value = commit_id
        dut.commit_kill_i.value = commit_kill
        await Timer(1, unit="ns")

        assert dut.state_d.value == States.WAIT_COMMIT.value
        assert dut.start_unit_o.value == 0

        await RisingEdge(dut.clk_i)
        await Timer(1, unit="ns")
        assert dut.state_q.value == States.WAIT_COMMIT.value

    # Commit the instruction
    await FallingEdge(dut.clk_i)
    dut.commit_valid_i.value = 1
    dut.commit_id_i.value = 5
    dut.commit_kill_i.value = 0
    await Timer(1, unit="ns")

    assert dut.start_unit_o.value == 1
    assert dut.state_d.value == States.RUN.value

    await RisingEdge(dut.clk_i)
    await Timer(1, unit="ns")

    assert dut.state_q.value == States.RUN.value
    assert dut.issue_id_q.value == 5
    assert dut.result_rd_q.value == 10