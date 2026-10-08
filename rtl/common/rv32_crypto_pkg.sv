// Shared definitions for RV32 scalar-crypto extensiob.
package rv32_crypto_pkg;
  parameter int unsigned XLEN = 32;
  // Covers the largest RV32 shift amount. AES32/SM4 use aux_i[1:0] for bs.
  parameter int unsigned CRYPTO_AUX_WIDTH = 5;

  typedef logic [XLEN-1:0] xlen_t;

  // Zbkb: bit manipulation instructions used by cryptographic code.
  typedef enum logic [3:0] {
    ROL,
    ROR,
    RORI,
    ANDN,
    ORN,
    XNOR,
    PACK,
    PACKH,
    BREV8,
    REV8,
    ZIP,
    UNZIP
  } bitmap_operand_e;

  // Zknh: SHA-256 and RV32 halves of SHA-512 transforms.
  typedef enum logic [3:0] {
    SHA256_SIGMA0,
    SHA256_SIGMA1,
    SHA256_SUM0,
    SHA256_SUM1,
    SHA512_SIGMA0H,
    SHA512_SIGMA0L,
    SHA512_SIGMA1H,
    SHA512_SIGMA1L,
    SHA512_SUM0,
    SHA512_SUM1
  } nist_operand_e;

  // Zksh: SM3 transforms.
  typedef enum logic {
    SM3P0,
    SM3P1
  } sm3_operand_e;

  typedef enum logic {
    XPERM4,
    XPERM8
  } xperm_operand_e;

  typedef enum logic [1:0] {
    IDLE,
    STAGE0,
    STAGE1
  } clmul_fsm_stages_e;
endpackage
