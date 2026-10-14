SIM := verilator
TOPLEVEL_LANG := verilog

PWD := $(shell pwd)
RTL_DIR := $(PWD)/rtl
TB_DIR := $(PWD)/tb/cocotb
BUILD_DIR := $(PWD)/build
WAVE_DIR := $(PWD)/waves

TEST ?= bitmap_unit
# Enable an FST waveform for supported simulators with `make test WAVES=1`.
WAVES ?= 0

# Packages always appear before the unit that imports them.
ifeq ($(TEST),bitmap_unit)
  TOPLEVEL := bitmap_unit
  MODULE := test_bitmap_unit
  VERILOG_SOURCES := $(RTL_DIR)/common/rv32_crypto_pkg.sv $(RTL_DIR)/common/rv32_utils_pkg.sv $(RTL_DIR)/units/bitmap_unit.sv
else ifeq ($(TEST),nist_hash_unit)
  TOPLEVEL := nist_hash_unit
  MODULE := test_nist_hash_unit
  VERILOG_SOURCES := $(RTL_DIR)/common/rv32_crypto_pkg.sv $(RTL_DIR)/common/rv32_utils_pkg.sv $(RTL_DIR)/units/nist_hash_unit.sv
else ifeq ($(TEST),shaming_hash_unit)
  TOPLEVEL := shaming_hash_unit
  MODULE := test_shaming_hash_unit
  VERILOG_SOURCES := $(RTL_DIR)/common/rv32_crypto_pkg.sv $(RTL_DIR)/common/rv32_utils_pkg.sv $(RTL_DIR)/units/shaming_hash_unit.sv
else ifeq ($(TEST),shaming_crypto_unit)
  TOPLEVEL := shaming_crypto_unit
  MODULE := test_shaming_crypto_unit
  VERILOG_SOURCES := $(RTL_DIR)/common/rv32_crypto_pkg.sv $(RTL_DIR)/common/rv32_utils_pkg.sv $(RTL_DIR)/units/misc/sm4_sbox.sv $(RTL_DIR)/units/shaming_crypto_unit.sv
else ifeq ($(TEST),clmul_unit)
  TOPLEVEL := clmul_unit
  MODULE := test_clmul_unit
  VERILOG_SOURCES := $(RTL_DIR)/common/rv32_crypto_pkg.sv $(RTL_DIR)/common/rv32_utils_pkg.sv $(RTL_DIR)/units/clmul_unit.sv
else ifeq ($(TEST),xperm_unit)
  TOPLEVEL := xperm_unit
  MODULE := test_xperm_unit
  VERILOG_SOURCES := $(RTL_DIR)/common/rv32_crypto_pkg.sv $(RTL_DIR)/common/rv32_utils_pkg.sv $(RTL_DIR)/units/xperm_unit.sv
else
  $(error Unknown test: $(TEST))
endif

SIM_BUILD := $(BUILD_DIR)/sim_$(TEST)
COCOTB_RESULTS_FILE := $(BUILD_DIR)/results_$(TEST).xml
WAVE_FILE := $(WAVE_DIR)/$(TEST).fst
export PYTHONPATH := $(TB_DIR):$(PYTHONPATH)
export COCOTB_RESOLVE_X := ZEROS

EXTRA_ARGS := -Wall -Wno-UNUSEDPARAM --timescale 1ns/1ps
EXTRA_ARGS += -I$(RTL_DIR)/common -I$(RTL_DIR)/units

ifeq ($(WAVES),1)
EXTRA_ARGS += --trace --trace-fst --trace-structs
SIM_ARGS += --trace --trace-file $(WAVE_FILE)
endif

.PHONY: all test bitmap nist-hash sm3-hash clmul xperm wave list distclean help
all: test

test:
	@mkdir -p $(BUILD_DIR) $(WAVE_DIR) $(SIM_BUILD)
	$(MAKE) sim SIM=$(SIM) TOPLEVEL_LANG=$(TOPLEVEL_LANG) TOPLEVEL=$(TOPLEVEL) COCOTB_TEST_MODULES=$(MODULE) VERILOG_SOURCES="$(VERILOG_SOURCES)" SIM_BUILD=$(SIM_BUILD) COCOTB_RESULTS_FILE=$(COCOTB_RESULTS_FILE) EXTRA_ARGS="$(EXTRA_ARGS)" SIM_ARGS="$(SIM_ARGS)"

bitmap:
	$(MAKE) test TEST=bitmap_unit

nist-hash:
	$(MAKE) test TEST=nist_hash_unit

sm3-hash:
	$(MAKE) test TEST=shaming_hash_unit

clmul:
	$(MAKE) test TEST=clmul_unit

xperm:
	$(MAKE) test TEST=xperm_unit

wave:
	@if [ -f $(WAVE_FILE) ]; then gtkwave $(WAVE_FILE); else echo "$(WAVE_FILE) not found. Run: make test TEST=$(TEST) WAVES=1"; fi

list:
	@echo "Available tests:"
	@echo "  make bitmap"
	@echo "  make nist-hash"
	@echo "  make sm3-hash"
	@echo "  make clmul"
	@echo "  make xperm"
	@echo "  make test TEST=bitmap_unit WAVES=1  # generate an FST waveform"

distclean:
	rm -rf $(BUILD_DIR) $(WAVE_DIR) sim_build __pycache__ tb/cocotb/__pycache__
	rm -f results.xml dump.vcd *.vcd *.fst

help: list

include $(shell cocotb-config --makefiles)/Makefile.sim
