module crypto_controller import cv32e40x_pkg::*; import rv32_crypto_pkg::*; #(
  parameter int unsigned OP_WIDTH = 4,
  parameter int unsigned AUX_WIDTH = 5,
  parameter int unsigned X_ID_WIDTH = 4,
  parameter int unsigned UNIT_NUM = 7
) (
    input logic clk_i,
    input logic rst_ni,

    // XIF issue interface
    input  logic                  issue_valid_i,
    input  logic [X_ID_WIDTH-1:0] issue_id_i,
    input  logic [4:0]            issue_rd_i,
    input  logic                  decoder_illegal_i,

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

    // Datapath interface
    input logic result_valid_i, // from datapath
    input logic unit_ready_i, // from datapath

    output logic load_instruction_o, // to datapath
    output logic start_unit_o, // to datapath
    output logic consumer_ready_o, // to datapath
    output logic operands_from_inputs_o // to datapath
);
    logic [1:0] state_q;
    logic [1:0] state_d;

    logic [X_ID_WIDTH-1:0] issue_id_q;
    logic [4:0] result_rd_q; 

    always_ff @(posedge clk_i or negedge rst_ni) begin
        if (!rst_ni) begin
            state_q <= CONTROLLER_IDLE;
            result_rd_q <= 5'd0;
            issue_id_q <= 4'd0;
        end else begin
            state_q <= state_d;

            if (load_instruction_o) begin
                result_rd_q <= issue_rd_i;
                issue_id_q <= issue_id_i;
            end
        end
    end

    always_comb begin
        state_d = state_q;

        operands_from_inputs_o = 1'b0;
        load_instruction_o     = 1'b0;
        start_unit_o           = 1'b0;
        consumer_ready_o       = 1'b0;
        issue_accept_o    = 1'b0;
        issue_writeback_o = 1'b0;
        result_valid_o = 1'b0;
        result_we_o    = 1'b0;
        result_rd_o    = '0;
        
        case (state_q)
            CONTROLLER_IDLE: begin
                if (issue_valid_i && !decoder_illegal_i) begin
                    if (commit_valid_i && !commit_kill_i && commit_id_i == issue_id_i) begin
                        state_d = CONTROLLER_RUN;
                        start_unit_o = 1'b1;
                        operands_from_inputs_o = 1'b1;
                        load_instruction_o = 1'b1;
                    end else if (commit_valid_i && commit_kill_i && commit_id_i == issue_id_i) begin
                        state_d = CONTROLLER_IDLE;
                    end else begin
                        load_instruction_o = 1'b1;
                        state_d = CONTROLLER_WAIT_COMMIT;
                    end

                    issue_accept_o = 1'b1;
                    issue_writeback_o = 1'b1;
                end
            end

            CONTROLLER_WAIT_COMMIT: begin
                if (commit_valid_i && commit_id_i == issue_id_q && !commit_kill_i) begin
                    state_d = CONTROLLER_RUN;
                    start_unit_o = 1'b1;
                end else if (commit_valid_i && commit_id_i == issue_id_q && commit_kill_i) begin
                    state_d = CONTROLLER_IDLE;
                end
            end

            CONTROLLER_RUN: begin
                start_unit_o = 1'b0;
                result_valid_o = result_valid_i; // directly get it from datapath
                consumer_ready_o = result_ready_i; // from top cv32e40x_pkg
                result_rd_o = result_rd_q;
                result_we_o = 1'b1;

                // todo: also accept new instruction in the future to reduce 1 cycle latency between 2 crypto instructions
                if (result_valid_i && result_ready_i) begin // hadnshare: result_valid_o && result_ready_i
                    state_d = CONTROLLER_IDLE;
                end
            end

            default: begin
                state_d = CONTROLLER_IDLE;
            end
        endcase
    end

    assign issue_ready_o = (state_q == CONTROLLER_IDLE) && rst_ni;
endmodule
