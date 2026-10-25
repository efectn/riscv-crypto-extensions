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

CV32_DIR := $(RTL_DIR)/cv32e40x
CV32_BUILD := $(BUILD_DIR)/cv32e40x
VERILATOR_JOBS ?= $(shell nproc)
CV32_INTERFACES := $(CV32_DIR)/rtl/cv32e40x_if_c_obi.sv $(CV32_DIR)/rtl/cv32e40x_if_xif.sv
CV32_SOURCES := $(CV32_DIR)/rtl/include/cv32e40x_pkg.sv $(CV32_INTERFACES) \
	$(filter-out $(CV32_INTERFACES),$(wildcard $(CV32_DIR)/rtl/*.sv)) \
	$(CV32_DIR)/bhv/cv32e40x_sim_clock_gate.sv
VMEM ?=
MEM_SIZE ?= 65536
MAX_CYCLE ?= 10000
TRACE ?= 0

CROSS_COMPILE ?= riscv64-elf-
FW_CC := $(CROSS_COMPILE)gcc
FW_OBJCOPY := $(CROSS_COMPILE)objcopy
APP ?= software/examples/add.c
FW_BUILD := $(BUILD_DIR)/firmware
FW_NAME := $(basename $(notdir $(APP)))
FW_ELF := $(FW_BUILD)/$(FW_NAME).elf
FW_VMEM := $(FW_BUILD)/$(FW_NAME).vmem
FW_FLAGS := -march=rv32i -mabi=ilp32 -O2 -g -ffreestanding -fno-builtin \
	-fno-pic -fno-pie -fno-stack-protector -msmall-data-limit=0 \
	-ffunction-sections -fdata-sections -Wall -Wextra

TESTS := bitmap_unit nist_hash_unit shangmi_hash_unit aes_crypto_unit \
         shangmi_crypto_unit clmul_unit xperm_unit decoder datapath controller coprocessor

ifeq ($(filter $(TEST),$(TESTS)),)
$(error Unknown test: $(TEST))
endif

TOPLEVEL := $(TEST)
MODULE := test_$(TEST)

ifeq ($(TEST),datapath)
TOPLEVEL := crypto_datapath
VERILOG_SOURCES := $(CV32_DIR)/rtl/include/cv32e40x_pkg.sv \
    $(RTL_DIR)/common/rv32_crypto_pkg.sv $(RTL_DIR)/common/rv32_utils_pkg.sv \
    $(wildcard $(RTL_DIR)/units/misc/*.sv) $(wildcard $(RTL_DIR)/units/*.sv) \
    $(RTL_DIR)/crypto_datapath.sv
else ifeq ($(TEST),controller)
TOPLEVEL := crypto_controller
VERILOG_SOURCES := $(CV32_DIR)/rtl/include/cv32e40x_pkg.sv \
	$(RTL_DIR)/common/rv32_crypto_pkg.sv \
    $(RTL_DIR)/crypto_controller.sv
else ifeq ($(TEST),coprocessor)
TOPLEVEL := crypto_coprocessor
VERILOG_SOURCES := $(CV32_DIR)/rtl/include/cv32e40x_pkg.sv \
    $(RTL_DIR)/common/rv32_crypto_pkg.sv \
    $(RTL_DIR)/common/rv32_utils_pkg.sv \
    $(wildcard $(RTL_DIR)/units/misc/*.sv) \
    $(wildcard $(RTL_DIR)/units/*.sv) \
    $(RTL_DIR)/crypto_decoder.sv \
    $(RTL_DIR)/crypto_controller.sv \
    $(RTL_DIR)/crypto_datapath.sv \
    $(RTL_DIR)/crypto_coprocessor.sv
else
EXTRA_SOURCES_aes_crypto_unit := units/misc/aes_mixcolumn.sv units/misc/aes_sbox.sv
EXTRA_SOURCES_shangmi_crypto_unit := units/misc/sm4_sbox.sv
ifeq ($(TEST),decoder)
TOPLEVEL := crypto_decoder
UNIT_SOURCE := crypto_decoder.sv
else
UNIT_SOURCE := units/$(TEST).sv
endif

# Packages always appear before the unit that imports them.
VERILOG_SOURCES := $(addprefix $(RTL_DIR)/, \
    common/rv32_crypto_pkg.sv common/rv32_utils_pkg.sv \
    $(EXTRA_SOURCES_$(TEST)) $(UNIT_SOURCE))
endif

SIM_BUILD := $(BUILD_DIR)/sim_$(TEST)$(if $(filter 1,$(WAVES)),_waves)
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

.PHONY: all test bitmap nist-hash sm3-hash clmul xperm wave list distclean help cv32e40x-build cv32e40x-run
.PHONY: firmware firmware-run FORCE
all: test

test:
	@mkdir -p $(BUILD_DIR) $(WAVE_DIR) $(SIM_BUILD)
	$(MAKE) sim SIM=$(SIM) TOPLEVEL_LANG=$(TOPLEVEL_LANG) TOPLEVEL=$(TOPLEVEL) COCOTB_TEST_MODULES=$(MODULE) VERILOG_SOURCES="$(VERILOG_SOURCES)" SIM_BUILD=$(SIM_BUILD) COCOTB_RESULTS_FILE=$(COCOTB_RESULTS_FILE) EXTRA_ARGS="$(EXTRA_ARGS)" SIM_ARGS="$(SIM_ARGS)"

cv32e40x-build:
	@test -f $(CV32_DIR)/rtl/include/cv32e40x_pkg.sv || { echo "CV32E40X sources missing; run: git submodule update --init --recursive"; exit 1; }
	$(SIM) --cc --exe --build -j $(VERILATOR_JOBS) --trace -Wno-fatal \
		--top-module cv32e40x_top --Mdir $(CV32_BUILD) \
		$(CV32_SOURCES) $(RTL_DIR)/cv32e40x_top.sv $(PWD)/sim_model/main.cpp

cv32e40x-run:
	@test -n "$(VMEM)" || { echo "Specify a program: make cv32e40x-run VMEM=path/to/program.vmem"; exit 1; }
	$(MAKE) cv32e40x-build
	$(CV32_BUILD)/Vcv32e40x_top $(TRACE) "$(VMEM)" $(MEM_SIZE) $(MAX_CYCLE)

# APP accepts C, preprocessed assembly (.S), or plain assembly (.s).
firmware: $(FW_VMEM)

$(FW_ELF): $(APP) sim_model/crt0.S sim_model/linker.ld FORCE
	@mkdir -p $(FW_BUILD)
	$(FW_CC) $(FW_FLAGS) -nostdlib -nostartfiles -static \
		-Wl,--defsym=__memory_size=$(MEM_SIZE) -T sim_model/linker.ld \
		-Wl,--gc-sections,-Map,$(FW_BUILD)/$(FW_NAME).map \
		sim_model/crt0.S $(APP) -o $@

$(FW_VMEM): $(FW_ELF)
	$(FW_OBJCOPY) -O verilog --verilog-data-width=4 $< $@

firmware-run: MAX_CYCLE = 20000
firmware-run: firmware
	$(MAKE) cv32e40x-run VMEM=$(FW_VMEM) MAX_CYCLE=$(MAX_CYCLE)

wave:
	@if [ -f $(WAVE_FILE) ]; then gtkwave $(WAVE_FILE); else echo "$(WAVE_FILE) not found. Run: make test TEST=$(TEST) WAVES=1"; fi

list:
	@echo "  make test TEST=datapath  # run the cocotb datapath test"
	@echo "  make test TEST=controller  # run the cocotb controller test"
	@echo "  make test TEST=bitmap_unit WAVES=1  # generate an FST waveform"
	@echo "  make cv32e40x-build  # build the CV32E40X C++ simulator"
	@echo "  make cv32e40x-run VMEM=program.vmem [TRACE=1] [MEM_SIZE=65536] [MAX_CYCLE=1000]"
	@echo "  make firmware [APP=software/examples/add.c] [CROSS_COMPILE=riscv64-elf-]"
	@echo "  make firmware-run [APP=path/to/program.c|.S|.s] [MAX_CYCLE=20000]"

distclean:
	rm -rf $(BUILD_DIR) $(WAVE_DIR) sim_build __pycache__ tb/cocotb/__pycache__
	rm -f results.xml dump.vcd *.vcd *.fst

help: list

# The standalone C++ simulator does not require cocotb.
ifneq ($(strip $(MAKECMDGOALS)),)
ifeq ($(strip $(filter-out cv32e40x-build cv32e40x-run firmware firmware-run help list,$(MAKECMDGOALS))),)
SKIP_COCOTB := 1
endif
endif
ifneq ($(SKIP_COCOTB),1)
include $(shell cocotb-config --makefiles)/Makefile.sim
endif
