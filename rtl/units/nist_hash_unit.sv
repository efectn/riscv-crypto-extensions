module nist_hash_unit #(
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

  logic [31:0] result_d;

  logic [4:0] shamt; 
  assign shamt = rs2_i[4:0];

  // The ready_o signal is only asserted high when valid_o is low, which means we have no valid result or the pipeline is ready to consume the result, which makes ready_i high
  assign ready_o = !valid_o || ready_i;

  always_comb begin
    result_d = 32'd0;
    
    case (op_i[3:0])
      SHA256_SIGMA0: result_d = ror(rs1_i, 5'd7) ^ ror(rs1_i, 5'd18) ^ (rs1_i >> 3);
      SHA256_SIGMA1: result_d = ror(rs1_i, 5'd17) ^ ror(rs1_i, 5'd19) ^ (rs1_i >> 10);
      SHA256_SUM0: result_d = ror(rs1_i, 5'd2) ^ ror(rs1_i, 5'd13) ^ ror(rs1_i, 5'd22);
      SHA256_SUM1: result_d = ror(rs1_i, 5'd6) ^ ror(rs1_i, 5'd11) ^ ror(rs1_i, 5'd25);
      SHA512_SIGMA0H: result_d = (rs1_i >> 1) ^ (rs1_i >> 7) ^ (rs1_i >> 8) ^ (rs2_i << 31) ^ (rs2_i << 24);
      SHA512_SIGMA0L: result_d = (rs1_i >> 1) ^ (rs1_i >> 7) ^ (rs1_i >> 8) ^ (rs2_i << 31) ^ (rs2_i << 25) ^ (rs2_i << 24);
      SHA512_SIGMA1H: result_d = (rs1_i << 3) ^ (rs1_i >> 6) ^ (rs1_i >> 19) ^ (rs2_i >> 29) ^ (rs2_i << 13);
      SHA512_SIGMA1L: result_d = (rs1_i << 3) ^ (rs1_i >> 6) ^ (rs1_i >> 19) ^ (rs2_i >> 29) ^ (rs2_i << 26) ^ (rs2_i << 13);
      SHA512_SUM0: result_d = (rs1_i << 25) ^ (rs1_i << 30) ^ (rs1_i >> 28) ^ (rs2_i >> 7) ^ (rs2_i >> 2) ^ (rs2_i << 4);
      SHA512_SUM1: result_d = (rs1_i << 23) ^ (rs1_i >> 14) ^ (rs1_i >> 18) ^ (rs2_i >> 9) ^ (rs2_i << 18) ^ (rs2_i << 14);
      default: result_d = 32'd0;
    endcase
  end

  always_ff @(posedge clk_i or negedge rst_ni) begin
    if (!rst_ni) begin
      valid_o  <= 1'b0;
      result_o <= '0;
    end else if (ready_o) begin
      // Retiring an old result and accepting a new request share this edge.
      valid_o <= valid_i;
      if (valid_i) begin
        result_o <= result_d;
      end
    end
  end
endmodule
