
#!/usr/bin/env python3

import os
import re
import runpy
import shutil
import subprocess
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
ARCH_TESTS = HERE / "riscv-arch-tests"
CONFIG = HERE / "config"
WORK = ROOT / "build/act4"

EXTENSIONS = ("Zbkb", "Zbkc", "Zbkx", "Zknd", "Zkne", "Zknh", "Zksed", "Zksh")
MAX_CYCLES = 2_000_000
MEM_SIZE = 0x2000000
CROSS = os.getenv("CROSS_COMPILE", "riscv64-elf-")
SAIL = os.getenv("SAIL") or shutil.which("sail_riscv_sim") or str(ROOT / "build/tools/sail/bin/sail_riscv_sim")

def run(command, log, expected=(), timeout=120):
    with log.open("w") as output:
        subprocess.run(
            list(map(str, command)), cwd=ROOT, stdout=output,
            stderr=subprocess.STDOUT, check=True, timeout=timeout,
        )

    content = log.read_text()
    for message in expected:
        if message not in content:
            raise RuntimeError(f"Missing '{message}' in {log}")

def compile_test(test, output, defines, log):
    march = re.search(r"^# MARCH: (\S+)$", test.read_text(), re.M)
    if not march:
        raise ValueError(f"Missing MARCH in {test}")

    run([
        CROSS + "gcc", f"-march={march.group(1)}", "-mabi=ilp32",
        "-mcmodel=medany", "-O0", "-g", "-nostdlib", "-nostartfiles",
        "-static", "-fno-pic", "-fno-pie",
        "-Wl,--no-relax,--no-warn-rwx-segments",
        "-Wl,--defsym=__stack_size=128",
        f"-I{CONFIG}", f"-I{ARCH_TESTS / 'tests/env'}",
        f"-T{CONFIG / 'link.ld'}", "-DTEST_FLEN=0",
        f'-DTEST_FILE="{test.stem}"',
        *defines, str(test), "-o", output,
    ], log)

def run_test(test, process_signature):
    dest = WORK / test.parent.name / test.stem
    dest.mkdir(parents=True, exist_ok=True)

    elf = dest / f"{test.stem}.elf"
    sig_elf = dest / f"{test.stem}.sig.elf"
    signature = dest / f"{test.stem}.sig"
    vmem = dest / f"{test.stem}.vmem"

    compile_test(test, sig_elf, [
        "-DSIGNATURE",
        "-DSAIL_CLINT_BASE_ADDRESS=0x2000000",
        "-DSAIL_SIMPLE_INTERRUPT_GENERATOR_BASE_ADDRESS=0xc000000",
    ], dest / "compile-reference.log")

    signature.unlink(missing_ok=True)
    run([
        SAIL, "--config", CONFIG / "sail.json",
        "--test-signature", signature, "--signature-granularity", "4",
        "--inst-limit", MAX_CYCLES, sig_elf,
    ], dest / "sail.log", ("SUCCESS", "RVCP-SUMMARY: TEST SIGRUN"))

    if not signature.is_file() or not signature.read_text().strip():
        raise RuntimeError("Sail produced an empty signature")

    process_signature(signature, 32)

    compile_test(test, elf, [
        "-DRVTEST_SELFCHECK",
        f'-DSIGNATURE_FILE="{signature.with_suffix(".results")}"',
    ], dest / "compile-selfcheck.log")

    run([
        CROSS + "objcopy", "-O", "verilog",
        "--verilog-data-width=4", elf, vmem,
    ], dest / "objcopy.log")

    run([
        ROOT / "build/cv32e40x/Vcv32e40x_top",
        0, vmem, MEM_SIZE, MAX_CYCLES,
    ], dest / "rtl.log", (
        "Program finished with return status: 0",
        "RVCP-SUMMARY: TEST PASSED",
    ))

def main():
    tests = sorted(
        test for ext in EXTENSIONS
        for test in (ARCH_TESTS / "tests/rv32i" / ext).glob("*.S")
    )
    if not tests:
        raise SystemExit("No tests found; initialize the ACT4 submodule")

    WORK.mkdir(parents=True, exist_ok=True)
    print("Building CV32E40X + crypto simulator...", flush=True)
    run(["make", "cv32e40x-build"], WORK / "simulator-build.log", timeout=600)

    process_signature = runpy.run_path(
        str(ARCH_TESTS / "framework/src/act/sig_modify.py")
    )["process_signature_file"]

    failed = 0
    for test in tests:
        try:
            run_test(test, process_signature)
            print(f"PASS {test.stem}", flush=True)
        except (subprocess.SubprocessError, OSError, RuntimeError, ValueError) as exc:
            failed += 1
            print(f"FAIL {test.stem}: {exc}\n  Logs: {WORK / test.parent.name / test.stem}", flush=True)

    print(f"{len(tests) - failed}/{len(tests)} passed. Logs: {WORK}")
    return int(failed > 0)


if __name__ == "__main__":
    raise SystemExit(main())
