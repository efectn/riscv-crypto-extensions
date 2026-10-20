module crypto_decoder import rv32_crypto_pkg::*; #(
  parameter int unsigned OP_WIDTH = 4,
  parameter int unsigned AUX_WIDTH = 5
) (
    input logic [31:0] instr_i,
    output logic [4:0] rs1_o,
    output logic [4:0] rs2_o,
    output logic [4:0] rd_o,
    output logic [AUX_WIDTH-1:0] aux_o,
    output logic [OP_WIDTH-1:0] op_o,
    output crypto_decoder_unit_sel_e unit_sel_o,
    output logic is_illegal_o
);
    localparam aes_opcode = 7'b0110011;
    localparam sha256_opcode = 7'b0010011;
    localparam sha512_opcode = 7'b0110011;
    localparam shangmi_crypto_opcode = 7'b0110011;
    localparam xperm_opcode = 7'b0110011;
    localparam xperm_funct7 = 7'b0010100;
    localparam clmul_opcode = 7'b0110011;
    localparam clmul_funct7 = 7'b0000101;
    localparam bitmap_opcode_rtype = 7'b0110011;
    localparam bitmap_opcode_itype = 7'b0010011;

    logic [6:0] opcode;
    logic [2:0] funct3;
    logic [6:0] funct7;
    logic [1:0] bs;

    always_comb begin
        unit_sel_o = INVALID;
        op_o = '0;
        aux_o = '0;
        
        // AES unit selection
        if (opcode == aes_opcode && funct3 == 3'b000) begin
            casez (funct7)
                // AES32DSI
                7'b??10101: begin
                    unit_sel_o = AES_CRYPTO;
                    op_o = AES32DSI;
                    aux_o = {3'b000, bs};
                end
                // AES32DSMI
                7'b??10111: begin
                    unit_sel_o = AES_CRYPTO;
                    op_o = AES32DSMI;
                    aux_o = {3'b000, bs};
                end
                // AES32ESI
                7'b??10001: begin
                    unit_sel_o = AES_CRYPTO;
                    op_o = AES32ESI;
                    aux_o = {3'b000, bs};
                end
                // AES32ESMI
                7'b??10011: begin
                    unit_sel_o = AES_CRYPTO;
                    op_o = AES32ESMI;
                    aux_o = {3'b000, bs};
                end
                // SM4KS
                7'b??11010: begin
                    unit_sel_o = SHANGMI_CRYPTO;
                    op_o = SM4KS;
                    aux_o = {3'b000, bs};
                end
                // SM4ED
                7'b??11000: begin
                    unit_sel_o = SHANGMI_CRYPTO;
                    op_o = SM4ED;
                    aux_o = {3'b000, bs};
                end
                // SHA512SIG0H
                7'b0101110: begin
                    unit_sel_o = NIST_HASH;
                    op_o = SHA512_SIGMA0H;
                end
                // SHA512SIG0L
                7'b0101010: begin
                    unit_sel_o = NIST_HASH;
                    op_o = SHA512_SIGMA0L;
                end
                // SHA512SIG1H
                7'b0101111: begin
                    unit_sel_o = NIST_HASH;
                    op_o = SHA512_SIGMA1H;
                end
                // SHA512SIG1L
                7'b0101011: begin
                    unit_sel_o = NIST_HASH;
                    op_o = SHA512_SIGMA1L;
                end
                //SHA512SUM0
                7'b0101000: begin
                    unit_sel_o = NIST_HASH;
                    op_o = SHA512_SUM0;
                end
                //SHA512SUM1
                7'b0101001: begin
                    unit_sel_o = NIST_HASH;
                    op_o = SHA512_SUM1;
                end
                default: begin
                end
            endcase
        end else if (opcode == sha256_opcode && funct3 == 3'b001 && funct7 == 7'b0001000) begin
            // SIG and SUM instructions for SHA-256
            case (rs2_o)
                // SHA256SIG0
                5'b00010: begin
                    unit_sel_o = NIST_HASH;
                    op_o = SHA256_SIGMA0;
                end
                // SHA256SIG1
                5'b00011: begin
                    unit_sel_o = NIST_HASH;
                    op_o = SHA256_SIGMA1;
                end
                //SHA256SUM0
                5'b00000: begin
                    unit_sel_o = NIST_HASH;
                    op_o = SHA256_SUM0;
                end
                //SHA256SUM1
                5'b00001: begin
                    unit_sel_o = NIST_HASH;
                    op_o = SHA256_SUM1;
                end
                // SM3P0
                5'b01000: begin
                    unit_sel_o = SHANGMI_HASH;
                    op_o = SM3P0;
                end
                // SM3P1
                5'b01001: begin
                    unit_sel_o = SHANGMI_HASH;
                    op_o = SM3P1;
                end
                default: begin
                end
            endcase
        end else if (opcode == xperm_opcode && funct7 == xperm_funct7) begin
            case (funct3)
                // XPERM4
                3'b010: begin
                    unit_sel_o = XPERM;
                    op_o = XPERM4;
                end
                // XPERM8
                3'b100: begin
                    unit_sel_o = XPERM;
                    op_o = XPERM8;
                end
                default: begin
                end
            endcase
        end else if (opcode == clmul_opcode && funct7 == clmul_funct7) begin
            case (funct3)
                // CLMUL
                3'b001: begin
                    unit_sel_o = CLMUL;
                    op_o = 4'd0;
                end
                // CLMULH
                3'b011: begin
                    unit_sel_o = CLMUL;
                    op_o = 4'd1;
                end
                default: begin
                end
            endcase
        end else if (opcode == bitmap_opcode_rtype) begin
            if (funct7 == 7'b0110000) begin
                case (funct3)
                    // ROL
                    3'b001: begin
                        unit_sel_o = BITMAP;
                        op_o = ROL;
                    end
                    // ROR
                    3'b101: begin
                        unit_sel_o = BITMAP;
                        op_o = ROR;
                    end
                    default: begin
                    end
                endcase
            end else if (funct7 == 7'b0100000) begin
                case (funct3)
                    3'b111: begin
                        unit_sel_o = BITMAP;
                        op_o = ANDN;
                    end
                    3'b110: begin
                        unit_sel_o = BITMAP;
                        op_o = ORN;
                    end
                    3'b100: begin
                        unit_sel_o = BITMAP;
                        op_o = XNOR;
                    end
                    default: begin
                    end
                endcase
            end else if (funct7 == 7'b0000100) begin
                case (funct3)
                    // PACK
                    3'b100: begin
                        unit_sel_o = BITMAP;
                        op_o = PACK;
                    end
                    // PACKH
                    3'b111: begin
                        unit_sel_o = BITMAP;
                        op_o = PACKH;
                    end
                    default: begin
                    end
                endcase
            end    
        end else if (opcode == bitmap_opcode_itype) begin
            if (funct7 == 7'b0110100 && funct3 == 3'b101) begin
                case (rs2_o)
                    // BREV8
                    5'b00111: begin
                        unit_sel_o = BITMAP;
                        op_o = BREV8;
                    end
                    // REV8
                    5'b11000: begin
                        unit_sel_o = BITMAP;
                        op_o = REV8;
                    end
                    default: begin
                    end
                endcase
            end else if (funct7 == 7'b0000100 && rs2_o == 5'b01111) begin
                case (funct3)
                    // ZIP
                    3'b001: begin
                        unit_sel_o = BITMAP;
                        op_o = ZIP;
                    end
                    // UNZIP
                    3'b101: begin
                        unit_sel_o = BITMAP;
                        op_o = UNZIP;
                    end
                    default: begin
                    end
                endcase
            end else if (funct7 == 7'b0110000 && funct3 == 3'b101) begin
                // RORI
                unit_sel_o = BITMAP;
                op_o = RORI;
            end
        end
    end

    assign is_illegal_o = (unit_sel_o == INVALID);
    assign {funct7, rs2_o, rs1_o, funct3, rd_o, opcode} = instr_i;
    assign bs = funct7[6:5];
endmodule
