module crypto_coprocessor import rv32_crypto_pkg::*; #(
  parameter int unsigned OP_WIDTH = 4,
  parameter int unsigned AUX_WIDTH = 5,
  parameter int unsigned X_ID_WIDTH = 4,
  parameter int unsigned UNIT_NUM = 7
) (
    input logic clk_i,
    input logic rst_ni,

    // XIF Issue interface
    input  logic                  issue_valid_i,
    input  logic [X_ID_WIDTH-1:0] issue_id_i,
    input  logic [31:0]           issue_instr_i,
    input logic [31:0]            issue_rs1_i,
    input logic [31:0]            issue_rs2_i,
    output logic                  issue_ready_o,
    output logic                  issue_accept_o,
    output logic                  issue_writeback_o,

    // XIF commit interface
    input  logic                  commit_valid_i,
    input  logic [X_ID_WIDTH-1:0] commit_id_i,
    input  logic                  commit_kill_i,

    // XIF result interface
    input  logic                  result_ready_i,
    output logic                  result_valid_o,
    output logic [4:0]            result_rd_o,
    output logic                  result_we_o,
    output logic [X_ID_WIDTH-1:0] result_id_o,
    output logic [31:0]           result_data_o
);
    logic [4:0] rs2, rd;
    logic [AUX_WIDTH-1:0] aux;
    logic [OP_WIDTH-1:0] op;
    crypto_decoder_unit_sel_e unit_sel_decoder;
    logic [UNIT_NUM-1:0] unit_sel_onehot;
    logic decoder_illegal;
    logic is_rori; // rori is the only instruction using immediate during execution, so we only pass it as rs2 instead of another logic handling immediates
    logic unit_ready;
    logic datapath_result_valid;
    logic load_instruction, start_unit, consumer_ready, operands_from_inputs;

    // Define the decoder
    crypto_decoder decoder_i (
        .instr_i(issue_instr_i),
        .rs1_o(), // not used for now
        .rs2_o(rs2),
        .rd_o(rd),
        .aux_o(aux),
        .op_o(op),
        .unit_sel_o(unit_sel_decoder),
        .is_illegal_o(decoder_illegal),
        .is_rori_o(is_rori)
    );

    // Define the controller
    crypto_controller controller_i (
        .clk_i(clk_i),
        .rst_ni(rst_ni),

        // XIF issue interface
        .issue_valid_i(issue_valid_i),
        .issue_id_i(issue_id_i),
        .issue_rd_i(rd),
        .issue_ready_o(issue_ready_o),
        .issue_accept_o(issue_accept_o),
        .issue_writeback_o(issue_writeback_o),

        .decoder_illegal_i(decoder_illegal),

        // XIF commit interface
        .commit_valid_i(commit_valid_i),
        .commit_id_i(commit_id_i),
        .commit_kill_i(commit_kill_i),

        // XIF result interface
        .result_ready_i(result_ready_i),
        .result_valid_o(result_valid_o),
        .result_rd_o(result_rd_o),
        .result_we_o(result_we_o),

        // datapath -> controller
        .result_valid_i(datapath_result_valid),
        .unit_ready_i(unit_ready),

        // controller -> datapath
        .load_instruction_o(load_instruction),
        .start_unit_o(start_unit),
        .consumer_ready_o(consumer_ready),
        .operands_from_inputs_o(operands_from_inputs)
    );

    // Define the datapath
    crypto_datapath datapath_i (
        .clk_i(clk_i),
        .rst_ni(rst_ni),

        .rs1_i(issue_rs1_i),
        .rs2_i(is_rori ? {27'b0, rs2} : issue_rs2_i), // rori is edge case
        .op_i(op),
        .aux_i(aux),
        .x_id_i(issue_id_i), // comes from XIF issue interface
        .unit_sel_i(unit_sel_onehot), // datapath needs one-hotted unit selection

        // controller -> datapath
        .load_instruction_i(load_instruction),
        .start_unit_i(start_unit),
        .consumer_ready_i(consumer_ready),
        .operands_from_inputs_i(operands_from_inputs),

        // datapath -> controller
        .unit_ready_o(unit_ready),
        .result_valid_o(datapath_result_valid), // controller directly outputs this to XIF result interface during RUN state

        // XIF result interface
        .x_id_o(result_id_o),
        .result_o(result_data_o)
    );

    // Conver the decoder unit sel to one-hot encoding
    assign unit_sel_onehot = decoder_illegal ? {UNIT_NUM{1'b0}} : (1 << unit_sel_decoder);
endmodule
