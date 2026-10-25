import random

import cocotb
from cocotb.triggers import Timer

BITMAP, CLMUL_UNIT, XPERM_UNIT, AES_UNIT, SM4_UNIT, SHA_UNIT, SM3_UNIT, INVALID = range(8)

BM = dict(zip(
    ("ROL", "ROR", "RORI", "ANDN", "ORN", "XNOR", "PACK", "PACKH",
     "BREV8", "REV8", "ZIP", "UNZIP"), range(12)
))
SHA = dict(zip(
    ("SHA256_SIGMA0", "SHA256_SIGMA1", "SHA256_SUM0", "SHA256_SUM1",
     "SHA512_SIGMA0H", "SHA512_SIGMA0L", "SHA512_SIGMA1H",
     "SHA512_SIGMA1L", "SHA512_SUM0", "SHA512_SUM1"), range(10)
))
AES: dict[str, int] = dict(zip(("AES32DSI", "AES32DSMI", "AES32ESI", "AES32ESMI"), range(4)))
SM4: dict[str, int] = {"SM4ED": 0, "SM4KS": 1}
SM3: dict[str, int] = {"SM3P0": 0, "SM3P1": 1}
XPERM: dict[str, int] = {"XPERM4": 0, "XPERM8": 1}
CLMUL_OP: dict[str, int] = {"CLMUL": 0, "CLMULH": 1}

def golden_decode(instr):
    opcode = instr & 0x7F
    funct3 = (instr >> 12) & 0x7
    funct7 = (instr >> 25) & 0x7F
    field20 = (instr >> 20) & 0x1F  # register rs2 OR a 5-bit immediate

    if opcode == 0x33:  # R-type (AES/SM4 use this opcode too)
        if funct3 == 0:
            funct5 = funct7 & 0x1F
            bs = funct7 >> 5

            aes_name = {
                0b10101: "AES32DSI", 0b10111: "AES32DSMI",
                0b10001: "AES32ESI", 0b10011: "AES32ESMI",
            }.get(funct5)
            if aes_name is not None:
                return aes_name, AES_UNIT, AES[aes_name], bs

            sm4_name = {0b11000: "SM4ED", 0b11010: "SM4KS"}.get(funct5)
            if sm4_name is not None:
                return sm4_name, SM4_UNIT, SM4[sm4_name], bs

            sha512_name = {
                0b0101110: "SHA512_SIGMA0H",
                0b0101010: "SHA512_SIGMA0L",
                0b0101111: "SHA512_SIGMA1H",
                0b0101011: "SHA512_SIGMA1L",
                0b0101000: "SHA512_SUM0",
                0b0101001: "SHA512_SUM1",
            }.get(funct7)
            if sha512_name is not None:
                return sha512_name, SHA_UNIT, SHA[sha512_name], 0

        if funct7 == 0b0010100:  # XPERM
            name = {0b010: "XPERM4", 0b100: "XPERM8"}.get(funct3)
            if name is not None:
                return name, XPERM_UNIT, XPERM[name], 0

        if funct7 == 0b0000101:  # CLMUL
            name = {0b001: "CLMUL", 0b011: "CLMULH"}.get(funct3)
            if name is not None:
                return name, CLMUL_UNIT, CLMUL_OP[name], 0

        # Zbkb R-type
        bitmap_name = {
            (0b0110000, 0b001): "ROL",  (0b0110000, 0b101): "ROR",
            (0b0100000, 0b111): "ANDN", (0b0100000, 0b110): "ORN",
            (0b0100000, 0b100): "XNOR", (0b0000100, 0b100): "PACK",
            (0b0000100, 0b111): "PACKH",
        }.get((funct7, funct3))
        if bitmap_name is not None:
            return bitmap_name, BITMAP, BM[bitmap_name], 0

    elif opcode == 0x13:  # I-type
        if funct7 == 0b0001000 and funct3 == 0b001:
            name = {
                0b00000: "SHA256_SUM0", 0b00001: "SHA256_SUM1",
                0b00010: "SHA256_SIGMA0", 0b00011: "SHA256_SIGMA1",
                0b01000: "SM3P0", 0b01001: "SM3P1",
            }.get(field20)
            if name is not None:
                unit = SM3_UNIT if name.startswith("SM3") else SHA_UNIT
                op = SM3[name] if unit == SM3_UNIT else SHA[name]
                return name, unit, op, 0

        # Zbkb I-type
        name = {
            (0b0110100, 0b101, 0b00111): "BREV8",
            (0b0110100, 0b101, 0b11000): "REV8",
            (0b0000100, 0b001, 0b01111): "ZIP",
            (0b0000100, 0b101, 0b01111): "UNZIP",
        }.get((funct7, funct3, field20))
        if name is not None:
            return name, BITMAP, BM[name], 0

        if funct7 == 0b0110000 and funct3 == 0b101:
            # Immediate/shamt is already in rs2_o (instr[24:20]).
            # This RTL does not send shamt over aux_o.
            return "RORI", BITMAP, BM["RORI"], 0

    return "ILLEGAL", INVALID, 0, 0

CASES = (
    ("AES32DSI", "bs", 0b10101, 0),
    ("AES32DSMI", "bs", 0b10111, 0),
    ("AES32ESI", "bs", 0b10001, 0),
    ("AES32ESMI", "bs", 0b10011, 0),
    ("SM4ED", "bs", 0b11000, 0),
    ("SM4KS", "bs", 0b11010, 0),
    ("SHA512_SIGMA0H", "r", 0b0101110, 0),
    ("SHA512_SIGMA0L", "r", 0b0101010, 0),
    ("SHA512_SIGMA1H", "r", 0b0101111, 0),
    ("SHA512_SIGMA1L", "r", 0b0101011, 0),
    ("SHA512_SUM0", "r", 0b0101000, 0),
    ("SHA512_SUM1", "r", 0b0101001, 0),
    ("SHA256_SIGMA0", "i", 0x102, 0b001),
    ("SHA256_SIGMA1", "i", 0x103, 0b001),
    ("SHA256_SUM0", "i", 0x100, 0b001),
    ("SHA256_SUM1", "i", 0x101, 0b001),
    ("SM3P0", "i", 0x108, 0b001),
    ("SM3P1", "i", 0x109, 0b001),
    ("XPERM4", "r", 0b0010100, 0b010),
    ("XPERM8", "r", 0b0010100, 0b100),
    ("CLMUL", "r", 0b0000101, 0b001),
    ("CLMULH", "r", 0b0000101, 0b011),
    ("ROL", "r", 0b0110000, 0b001),
    ("ROR", "r", 0b0110000, 0b101),
    ("ANDN", "r", 0b0100000, 0b111),
    ("ORN", "r", 0b0100000, 0b110),
    ("XNOR", "r", 0b0100000, 0b100),
    ("PACK", "r", 0b0000100, 0b100),
    ("PACKH", "r", 0b0000100, 0b111),
    ("BREV8", "i", 0x687, 0b101),
    ("REV8", "i", 0x698, 0b101),
    ("ZIP", "i", 0x08F, 0b001),
    ("UNZIP", "i", 0x08F, 0b101),
    ("RORI", "shift", 0b0110000, 0b101),
)
assert len(CASES) == 34
CASE_BY_NAME = {case[0]: case for case in CASES}


def make_instr(case, rd=1, rs1=2, rs2=3, bs=0, shamt=0):
    _, kind, field, funct3 = case
    opcode = 0x33 if kind in ("r", "bs") else 0x13
    instr = (rd << 7) | (rs1 << 15) | (funct3 << 12) | opcode
    if kind == "r":
        instr |= (field << 25) | (rs2 << 20)
    elif kind == "bs":
        instr |= (field << 25) | (bs << 30) | (rs2 << 20)
    elif kind == "i":
        instr |= field << 20
    elif kind == "shift":
        instr |= (field << 25) | (shamt << 20)
    else:
        raise ValueError(f"Unknown encoding kind: {kind}")
    return instr & 0xFFFFFFFF

async def check_word(dut, instr, expected_name=None):
    dut.instr_i.value = instr
    await Timer(1, unit="ns")  # purely combinational, no clock required

    name, unit, op, aux = golden_decode(instr)
    if expected_name is not None:
        assert name == expected_name, (
            f"Test vector 0x{instr:08x} should decode as {expected_name}, "
            f"but golden model says {name}"
        )

    # rs2_o ALWAYS contains instr[24:20], also when these bits are immediate.
    expected = {
        "rs1_o": (instr >> 15) & 31,
        "rs2_o": (instr >> 20) & 31,
        "rd_o": (instr >> 7) & 31,
        "aux_o": aux,
        "op_o": op,
        "unit_sel_o": unit,
        "is_illegal_o": int(unit == INVALID),
        "is_rori_o": int(name == "RORI"),
    }
    for signal, value in expected.items():
        actual = int(getattr(dut, signal).value)
        assert actual == value, (
            f"{name} instr=0x{instr:08x}: {signal}={actual}, expected {value}"
        )

@cocotb.test()
async def test_all_instructions(dut):
    for case in CASES:
        for rd, rs1, rs2 in ((0, 0, 0), (1, 2, 3), (31, 31, 31), (5, 5, 5)):
            instr = make_instr(case, rd=rd, rs1=rs1, rs2=rs2, bs=3, shamt=31)
            await check_word(dut, instr, case[0])

@cocotb.test()
async def test_all_immediates(dut):
    for case in CASES:
        if case[1] == "bs":
            for bs in range(4):
                await check_word(dut, make_instr(case, bs=bs), case[0])

    for shamt in range(32):
        instr = make_instr(CASE_BY_NAME["RORI"], shamt=shamt)
        await check_word(dut, instr, "RORI")
        assert int(dut.rs2_o.value) == shamt
        assert int(dut.aux_o.value) == 0

@cocotb.test()
async def test_random_registers(dut):
    rng = random.Random(0xA11CE)
    for case in CASES:
        for _ in range(100):
            instr = make_instr(
                case,
                rd=rng.randrange(32), rs1=rng.randrange(32), rs2=rng.randrange(32),
                bs=rng.randrange(4), shamt=rng.randrange(32),
            )
            await check_word(dut, instr, case[0])

@cocotb.test()
async def test_illegal_instructions(dut):
    for instr in (0, 0xFFFFFFFF, 0x00000013, 0x00000033,
                  0x00002003, 0x0000006F, 0x00000073):
        await check_word(dut, instr, "ILLEGAL")

    rng = random.Random(0xBAD5EED)
    illegal_count = 0
    for case in CASES:
        kind = case[1]
        fixed_bits = list(range(0, 7)) + list(range(12, 15))
        fixed_bits += list(range(25, 30 if kind == "bs" else 32))
        if kind == "i":
            fixed_bits += list(range(20, 25))
        for _ in range(50):
            instr = make_instr(
                case, rd=rng.randrange(32), rs1=rng.randrange(32),
                rs2=rng.randrange(32), bs=rng.randrange(4), shamt=rng.randrange(32)
            )
            mutated = instr ^ (1 << rng.choice(fixed_bits))
            if golden_decode(mutated)[0] == "ILLEGAL":
                illegal_count += 1
                await check_word(dut, mutated, "ILLEGAL")
    assert illegal_count > 100

@cocotb.test()
async def test_random_instructions(dut):
    rng = random.Random(0xDEADBEEF)
    for _ in range(5000):
        instr = rng.randrange(0xFFFFFFFF)
        await check_word(dut, instr)
