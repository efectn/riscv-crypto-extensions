module clmul_unit #(
  parameter int unsigned OP_WIDTH = 8,
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
  logic op_q;
  logic [31:0] rs1_q;
  logic [31:0] rs2_q;
  logic [63:0] stage0_q;
  clmul_fsm_stages_e state_q;


  logic [63:0] result_d;
  logic [63:0] stage0_d;

  // The ready_o signal is only asserted high when valid_o is low, which means we have no valid result or the pipeline is ready to consume the result, which makes ready_i high
  assign ready_o = (!valid_o || ready_i) && (state_q == IDLE || state_q == STAGE1);

  always_comb begin
    result_d = 64'd0;
    stage0_d = 64'd0;
    
    case (state_q)
      STAGE0: begin
        // at first stage, multiply least significant 16 bits
        for (int i = 0; i < 16; i++) begin
          if (rs2_q[i])
            stage0_d = stage0_d ^ ({32'b0, rs1_q} << i);
        end
      end
      STAGE1: begin
        // at second stage we are supposed to do XORing with highest 16 bits and then XOR previous result and this stage's result
        for (int i = 0; i < 16; i++) begin
          if (rs2_q[i + 16])
            stage0_d = stage0_d ^ ({32'b0, rs1_q} << i);
        end

        result_d = stage0_q ^ (stage0_d << 16);
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
      op_q <= 1'b0;
      stage0_q <= 64'd0;
    end else begin
      // consume the result if it is ready
      if (valid_o && ready_i)
        valid_o <= 1'b0;

      case (state_q)
        IDLE: begin
          // if we are ready to get new request, set buffered values
          if (ready_o && valid_i) begin
            op_q <= op_i[0];
            rs1_q <= rs1_i;
            rs2_q <= rs2_i;
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
            result_o <= op_q ? result_d[63:32] : result_d[31:0];

            // get new request if it is valid
            if (valid_i) begin
              op_q <= op_i[0];
              rs1_q <= rs1_i;
              rs2_q <= rs2_i;
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
