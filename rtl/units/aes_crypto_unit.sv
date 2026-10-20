module aes_crypto_unit #(
  parameter int unsigned OP_WIDTH = 4,
  parameter int unsigned AUX_WIDTH = 5
) (
  input  logic                 clk_i,
  input  logic                 rst_ni,

  input  logic                 valid_i, // valid_i indicates that the request is valid and the unit should sample the inputs
  output logic                 ready_o, // ready_o indicates that the unit can accept new request
  input  logic [OP_WIDTH-1:0]  op_i, // op_is is used to differentiate the operations in the unit
  input  logic [31:0]          rs1_i, // rs1_i is the first source operand
  input  logic [31:0]          rs2_i, // rs2_i is the second source operand or the immediate
  input  logic [AUX_WIDTH-1:0] aux_i, // aux_i is the auxiliary input, which can be used to pass shamt, enable bits etc.
  output logic                 valid_o, // valid_o indicates that the unit has a valid result to be consumed
  input  logic                 ready_i, // ready_i indicates that the consumer is ready to accept the result
  output logic [31:0]          result_o // result_o is the output of the unit, which is the result of the operation
);

  import rv32_utils_pkg::*;
  import rv32_crypto_pkg::*;

  // Buffer some inputs and middle values for FSM logic
  logic [1:0] op_q;
  logic [31:0] rs1_q;
  logic [31:0] rs2_q;
  logic [AUX_WIDTH-1:0] aux_q;
  logic [31:0] stage0_q;
  clmul_fsm_stages_e state_q;

  logic [31:0] result_d;
  logic [31:0] stage0_d;

  logic [4:0] shamt;
  assign shamt = {aux_q[1:0], 3'd0};

  logic [7:0] sbox_in;
  logic [7:0] sbox_out;

  logic [31:0] mixcolumn_result;

  assign sbox_in = rs2_q[shamt +: 8]; // rs2_q[shamt + 8 : shamt] identical to (rs2_q >> shamt)[7:0]

  aes_sbox sbox_inst (
    .in_byte(sbox_in),
    .out_byte(sbox_out),
    .inv_i(op_q == AES32DSMI || op_q == AES32DSI)
  );

  aes_mixcolumn mixcolumn_inst (
    .in_byte(stage0_q[7:0]),
    .out_word(mixcolumn_result),
    .inv_i(op_q == AES32DSMI)
  );

  // The ready_o signal is only asserted high when valid_o is low, which means we have no valid result or the pipeline is ready to consume the result, which makes ready_i high
  assign ready_o = (!valid_o || ready_i) && (state_q == IDLE || state_q == STAGE1);

  always_comb begin
    result_d = 32'd0;
    stage0_d = 32'd0;
    
    case (state_q)
      STAGE0: begin
        stage0_d = {24'd0, sbox_out};
      end

      STAGE1: begin
        // MixColumn and MixColumnInv for middle-round instructions
        case (op_q)
          AES32DSMI: begin
            result_d = mixcolumn_result;
          end
          AES32ESMI: begin
            result_d = mixcolumn_result;
          end
          default: begin
            result_d = stage0_q;
          end
        endcase

        result_d = rol(result_d, $unsigned(shamt)) ^ rs1_q;
      end

      default: begin
      end
    endcase
  end

  always_ff @(posedge clk_i or negedge rst_ni) begin
    if (!rst_ni) begin
      valid_o  <= 1'b0;
      result_o <= '0;
      state_q  <= IDLE;
      rs1_q <= 32'd0;
      rs2_q <= 32'd0;
      aux_q <= 5'd0;
      op_q <= 2'b0;
      stage0_q <= 32'd0;
    end else begin
      // consume the result if it is ready
      if (valid_o && ready_i)
        valid_o <= 1'b0;

      case (state_q)
        IDLE: begin
          // if we are ready to get new request, set buffered values
          if (ready_o && valid_i) begin
            op_q <= op_i[1:0];
            rs1_q <= rs1_i;
            rs2_q <= rs2_i;
            aux_q <= aux_i;
            state_q <= STAGE0;
          end
        end
        STAGE0: begin
          stage0_q <= stage0_d;
          state_q <= STAGE1;
        end
        STAGE1: begin
          // retire the old result if it is ready
          if (ready_o) begin
            valid_o <= 1'b1;
            result_o <= result_d;

            // get new request if it is valid
            if (valid_i) begin
              op_q <= op_i[1:0];
              rs1_q <= rs1_i;
              rs2_q <= rs2_i;
              aux_q <= aux_i;
              state_q <= STAGE0;
            end else begin
              state_q <= IDLE;
            end
          end
        end
        default: state_q <= IDLE;
      endcase
    end
  end
endmodule
