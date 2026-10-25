module crypto_datapath import cv32e40x_pkg::*; #(
  parameter int unsigned OP_WIDTH = 4,
  parameter int unsigned AUX_WIDTH = 5,
  parameter int unsigned X_ID_WIDTH = 4,
  parameter int unsigned UNIT_NUM = 7
) (
    input logic clk_i,
    input logic rst_ni,

    input logic [31:0] rs1_i,
    input logic [31:0] rs2_i,
    input logic [OP_WIDTH-1:0] op_i,
    input logic [AUX_WIDTH-1:0] aux_i,
    input logic [X_ID_WIDTH-1:0] x_id_i,
    input logic [UNIT_NUM-1:0] unit_sel_i,

    input logic load_instruction_i,
    input logic start_unit_i,
    input logic consumer_ready_i,
    input logic operands_from_inputs_i,

    output logic [31:0] result_o,
    output logic [X_ID_WIDTH-1:0] x_id_o,

    output logic result_valid_o,
    output logic unit_ready_o
);
    logic [31:0] rs1_q;
    logic [31:0] rs2_q;
    logic [OP_WIDTH-1:0] op_q;
    logic [AUX_WIDTH-1:0] aux_q;
    logic [X_ID_WIDTH-1:0] x_id_q;
    logic [UNIT_NUM-1:0] unit_sel_q;

    logic [31:0] unit_results [UNIT_NUM-1:0];
    logic [UNIT_NUM-1:0] unit_valids;
    logic [UNIT_NUM-1:0] unit_readies;

    logic [31:0] rs1_mux;
    logic [31:0] rs2_mux;
    logic [AUX_WIDTH-1:0] aux_mux;
    logic [OP_WIDTH-1:0] op_mux;
    logic [UNIT_NUM-1:0] unit_sel_mux;
    
    // load inputs into the registers when load_instruction_i asserted high
    always_ff @(posedge clk_i or negedge rst_ni) begin
        if (!rst_ni) begin
            rs1_q <= 32'd0;
            rs2_q <= 32'd0;
            op_q <= {OP_WIDTH{1'b0}};
            aux_q <= {AUX_WIDTH{1'b0}};
            x_id_q <= {X_ID_WIDTH{1'b0}};
            unit_sel_q <= {UNIT_NUM{1'b0}};
        end else begin
            if (load_instruction_i) begin
                rs1_q <= rs1_i;
                rs2_q <= rs2_i;
                op_q <= op_i;
                aux_q <= aux_i;
                x_id_q <= x_id_i;
                unit_sel_q <= unit_sel_i;
            end
        end
    end

    // operands MUX
    always_comb begin
        if (operands_from_inputs_i) begin
            rs1_mux = rs1_i;
            rs2_mux = rs2_i;
            aux_mux = aux_i;
            op_mux = op_i;
            unit_sel_mux = unit_sel_i;
        end else begin
            rs1_mux = rs1_q;
            rs2_mux = rs2_q;
            aux_mux = aux_q;
            op_mux = op_q;
            unit_sel_mux = unit_sel_q;
        end
    end

    // result MUX
    always_comb begin
        result_o = 32'd0;
        result_valid_o = 1'b0;
        
        for (int i = 0; i < UNIT_NUM; i++) begin
            if (unit_sel_q[i] && unit_valids[i]) begin
                result_o = unit_results[i];
                result_valid_o = 1'b1;
            end
        end
    end

    // define the units
    bitmap_unit #(
        .OP_WIDTH(OP_WIDTH),
        .AUX_WIDTH(AUX_WIDTH)
    ) bitmap_unit (
        .clk_i(clk_i),
        .rst_ni(rst_ni),
        .valid_i(unit_sel_mux[0] & start_unit_i & unit_readies[0]),
        .ready_o(unit_readies[0]),
        .op_i(op_mux),
        .rs1_i(rs1_mux),
        .rs2_i(rs2_mux),
        .aux_i(aux_mux),
        .valid_o(unit_valids[0]),
        .ready_i(consumer_ready_i & unit_sel_mux[0] & unit_valids[0]),
        .result_o(unit_results[0])
    );

    clmul_unit #(
        .OP_WIDTH(OP_WIDTH),
        .AUX_WIDTH(AUX_WIDTH)
    ) clmul_unit (
        .clk_i(clk_i),
        .rst_ni(rst_ni),
        .valid_i(unit_sel_mux[1] & start_unit_i & unit_readies[1]),
        .ready_o(unit_readies[1]),
        .op_i(op_mux),
        .rs1_i(rs1_mux),
        .rs2_i(rs2_mux),
        .aux_i(aux_mux),
        .valid_o(unit_valids[1]),
        .ready_i(consumer_ready_i & unit_sel_mux[1] & unit_valids[1]),
        .result_o(unit_results[1])
    );

    xperm_unit #(
        .OP_WIDTH(OP_WIDTH),
        .AUX_WIDTH(AUX_WIDTH)
    ) xperm_unit (
        .clk_i(clk_i),
        .rst_ni(rst_ni),
        .valid_i(unit_sel_mux[2] & start_unit_i & unit_readies[2]),
        .ready_o(unit_readies[2]),
        .op_i(op_mux),
        .rs1_i(rs1_mux),
        .rs2_i(rs2_mux),
        .aux_i(aux_mux),
        .valid_o(unit_valids[2]),
        .ready_i(consumer_ready_i & unit_sel_mux[2] & unit_valids[2]),
        .result_o(unit_results[2])
    );

    aes_crypto_unit #(
        .OP_WIDTH(OP_WIDTH),
        .AUX_WIDTH(AUX_WIDTH)
    ) aes_crypto_unit (
        .clk_i(clk_i),
        .rst_ni(rst_ni),
        .valid_i(unit_sel_mux[3] & start_unit_i & unit_readies[3]),
        .ready_o(unit_readies[3]),
        .op_i(op_mux),
        .rs1_i(rs1_mux),
        .rs2_i(rs2_mux),
        .aux_i(aux_mux),
        .valid_o(unit_valids[3]),
        .ready_i(consumer_ready_i & unit_sel_mux[3] & unit_valids[3]),
        .result_o(unit_results[3])
    );

    shangmi_crypto_unit #(
        .OP_WIDTH(OP_WIDTH),
        .AUX_WIDTH(AUX_WIDTH)
    ) shangmi_crypto_unit (
        .clk_i(clk_i),
        .rst_ni(rst_ni),
        .valid_i(unit_sel_mux[4] & start_unit_i & unit_readies[4]),
        .ready_o(unit_readies[4]),
        .op_i(op_mux),
        .rs1_i(rs1_mux),
        .rs2_i(rs2_mux),
        .aux_i(aux_mux),
        .valid_o(unit_valids[4]),
        .ready_i(consumer_ready_i & unit_sel_mux[4] & unit_valids[4]),
        .result_o(unit_results[4])
    );

    nist_hash_unit #(
        .OP_WIDTH(OP_WIDTH),
        .AUX_WIDTH(AUX_WIDTH)
    ) nist_hash_unit (
        .clk_i(clk_i),
        .rst_ni(rst_ni),
        .valid_i(unit_sel_mux[5] & start_unit_i & unit_readies[5]),
        .ready_o(unit_readies[5]),
        .op_i(op_mux),
        .rs1_i(rs1_mux),
        .rs2_i(rs2_mux),
        .aux_i(aux_mux),
        .valid_o(unit_valids[5]),
        .ready_i(consumer_ready_i & unit_sel_mux[5] & unit_valids[5]),
        .result_o(unit_results[5])
    );

    shangmi_hash_unit #(
        .OP_WIDTH(OP_WIDTH),
        .AUX_WIDTH(AUX_WIDTH)
    ) shangmi_hash_unit (
        .clk_i(clk_i),
        .rst_ni(rst_ni),
        .valid_i(unit_sel_mux[6] & start_unit_i & unit_readies[6]),
        .ready_o(unit_readies[6]),
        .op_i(op_mux),
        .rs1_i(rs1_mux),
        .rs2_i(rs2_mux),
        .aux_i(aux_mux),
        .valid_o(unit_valids[6]),
        .ready_i(consumer_ready_i & unit_sel_mux[6] & unit_valids[6]),
        .result_o(unit_results[6])
    );

    assign unit_ready_o = |(unit_sel_mux & unit_readies); // send readiness of selected to controller
    assign x_id_o = x_id_q;
endmodule
