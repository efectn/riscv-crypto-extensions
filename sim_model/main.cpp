#include <stdio.h>
#include <stdlib.h>
#include <stdint.h>
#include <stdbool.h>
#include <string.h>

#include "Vcv32e40x_top.h"
#include "verilated.h"
#include "verilated_vcd_c.h"

// Memory functions
uint8_t *memory;

#define RETURN_STATUS_MMIO 0x10000000u
#define UART_MMIO 0x10000004u

uint32_t read_memory(uint32_t address, uint32_t mem_size) {
    if (memory == NULL) {
        printf("Memory is not initialized!");
    }

    if (address + 4 > mem_size) {
        printf("Read attempt is out of memory, address: 0x%X", address);
    }
    address &= ~0b11; // zero byte select bits

    return memory[address] | (memory[address + 1] << 8) | (memory[address + 2] << 16) | (memory[address + 3] << 24);
} 

void write_memory(uint32_t address, uint8_t byte_enable, uint32_t data, uint32_t mem_size) {
    byte_enable &= 0xF; // make sure that only first 4 bits are used

    if (memory == NULL) {
        printf("Memory is not initialized!");
    }

    if (address + 4 > mem_size) {
        printf("Write attempt is out of memory, address: 0x%X", address);
    }

    address &= ~0b11; // zero byte select bits

    for (int i = 0; i < 4; i++) {
        if (byte_enable & (1 << i)) {
            memory[address + i] = (data >> (i * 8)) & 0xFF;
        }
    }
}

void clean_characters(char* str, char c) {
    char* src = str;
    char* dst = str;

    while (*src) {
        if (*src != c) {
            *dst++ = *src;
        }
        src++;
    }
    *dst = '\0'; // Null-terminate the modified string
}

void load_program(uint8_t* memory, int memory_size, const char* program_path) {
    FILE* program_file = fopen(program_path, "r");
    if (program_file == NULL) {
        printf("The program file couldn't get read!");
        exit(1);
    }

    char line[128];
    uint32_t current_address = 0;

    while (fgets(line, sizeof(line), program_file) != NULL) {
        // Clean comment line
        char *comment = strstr(line, "//");
        if (comment != NULL) {
            *comment = '\0';
        }

        char *token = strtok(line, " \n\r\t");
        while (token != NULL) {
            // clean underscores
            clean_characters(token, '_');

            if (token[0] == '@') {
                // This is an address line
                current_address = 4 * strtoul(token + 1, NULL, 16); // VMEM uses word indexing, so multiply by 4 to get byte address
                printf("Setting current address to 0x%X\n", current_address);
            } else {
                // This is a data line
                uint32_t data = strtoul(token, NULL, 16);
                if (current_address < memory_size) {
                    // write memory lanes
                    memory[current_address++] = data & 0xFF;
                    memory[current_address++] = (data >> 8) & 0xFF;
                    memory[current_address++] = (data >> 16) & 0xFF;
                    memory[current_address++] = (data >> 24) & 0xFF;

                } else {
                    printf("Address out of bounds: 0x%X\n", current_address);
                }
            }

            token = strtok(NULL, " \n\r\t");
        }
    }

    fclose(program_file);
}

int main(int argc, char* argv[]) {
    // read vmem file line by one
    char line[128];
    char* word;
    int line_len;
    FILE* program_file;

    uint32_t current_address = 0;

    // handle command line arguments
    if (argc < 5) {
        printf("Usage: %s <trace_enable> <program.vmem> <mem_size> <max_cycle>\n", argv[0]);
        return 1;
    }

    uint32_t memory_size = atoi(argv[3]);
    char* program_path = argv[2];
    bool trace_enable = atoi(argv[1]) != 0;
    uint32_t max_cycle = atoi(argv[4]);

    memory = (uint8_t*)malloc(memory_size);
    if (memory == NULL) {
        printf("Failed to allocate memory of size %d\n", memory_size);
        return 1;
    }

    load_program(memory, memory_size, program_path);

    uint32_t cycle_count = 0;

    Verilated::commandArgs(argc, argv);
    Vcv32e40x_top* top = new Vcv32e40x_top;
    VerilatedVcdC* tfp = NULL;

    if (trace_enable) {
        Verilated::traceEverOn(true);
        tfp = new VerilatedVcdC;
        top->trace(tfp, 99);
        tfp->open("waveform.vcd");
    }
    
    top->clk_i = 0;
    top->rst_ni = 1;
    
    // In ideal memory system, err_i is always 0 and gnt_i is always 1
    top->instr_gnt_i = 1;
    top->data_gnt_i = 1;
    top->instr_err_i = 0;
    top->data_err_i = 0;

    bool prev_instr_req = false;
    uint32_t prev_instr_addr = 0;

    bool prev_data_req = false;
    bool prev_data_we = false;
    uint32_t prev_data_addr = 0;

    uint32_t sim_time = 0;

    bool program_done = false;
    uint8_t return_status = 0;

    while (cycle_count < max_cycle) {
        top->rst_ni = cycle_count > 5; // reset for first 5 cycles

        top->clk_i = 0; // falling edge

        // Return previous cycle's intruction mem fetch request with 1 cycle latency
        if (prev_instr_req) {
            uint32_t instr_data = read_memory(prev_instr_addr, memory_size);
            top->instr_rdata_i = instr_data;
            top->instr_rvalid_i = 1;
        } else {
            top->instr_rvalid_i = 0;
        }

        // Return previous cycle's data mem fetch request with 1 cycle latency
        if (prev_data_req) {
            if (!prev_data_we) {
                uint32_t data_data = read_memory(prev_data_addr, memory_size);
                top->data_rdata_i = data_data;
            }

            top->data_rvalid_i = 1; // we have to send rvalid i 1 no matter what operating we do
        } else {
            top->data_rvalid_i = 0;
        }

        prev_instr_req = false;
        prev_data_req = false;
        prev_data_we = false;

        top->eval();
        if (trace_enable) {
            tfp->dump(sim_time++);
        }

        if (top->instr_req_o && top->instr_gnt_i) {
            prev_instr_req = true;
            prev_instr_addr = top->instr_addr_o;
        }

            
        if (top->data_req_o && top->data_gnt_i) {
            prev_data_req = true;
            prev_data_addr = top->data_addr_o;

            if (top->data_we_o) {
                prev_data_we = true;
                if (top->data_addr_o == RETURN_STATUS_MMIO) {
                    return_status = top->data_wdata_o & 0xFF;
                    program_done = true;
                } else if (top->data_addr_o == UART_MMIO) {
                    char uart_char = top->data_wdata_o & 0xFF;
                    printf("%c", uart_char);
                    fflush(stdout); // Ensure immediate output
                } else {
                    write_memory(prev_data_addr, top->data_be_o, top->data_wdata_o, memory_size);
                }
            }
        }
        
        top->clk_i = 1; // rising edge
        top->eval();
        if (trace_enable) {
            tfp->dump(sim_time++);
        }

        if (program_done) {
            printf("Program finished with return status: %d\n", return_status);
            break;
        }

        // Simulate a cycle
        cycle_count++;
    }

    if (trace_enable) {
        tfp->close();
        delete tfp;
    }

    delete top;
    free(memory);

    if (!program_done) {
        fprintf(stderr, "Simulation timed out after %u cycles\n", max_cycle);
        return 1;
    }
    return return_status;
}
