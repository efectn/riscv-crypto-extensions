// Summation is equal to XOR in GF(2^8) and multiplication is equal to AND.
// This module implements the MixColumn and InvMixColumn operations of AES algorithm.
module aes_mixcolumn (
  input logic [7:0] in_byte,
  output logic [31:0] out_word,
  input logic       inv_i
);
  // xtime is used to multiply a byte by 2 inside boundaries of Galois field.
  function automatic logic [7:0] xtime(input logic [7:0] b);
    return (b << 1) ^ (b[7] ? 8'h1B : 8'h00);
  endfunction

  logic [7:0] b0, b1, b2, b3;
  logic [7:0] x2, x4, x8;

  assign x2 = xtime(in_byte);
  assign x4 = xtime(x2);
  assign x8 = xtime(x4);

  always_comb begin
    // MixColumnInv operation for decoding
    if (inv_i) begin
      b0 = x8 ^ x4 ^ x2;
      b1 = x8 ^ in_byte;
      b2 = x8 ^ x4 ^ in_byte;
      b3 = x8 ^ x2 ^ in_byte;
    end else begin // MixColumn operation for encoding
      b0 = x2;
      b1 = in_byte;
      b2 = in_byte;
      b3 = x2 ^ in_byte;
    end
  end

  assign out_word = {b3, b2, b1, b0};
endmodule
