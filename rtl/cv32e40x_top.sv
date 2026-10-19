module cv32e40x_top import cv32e40x_pkg::*; (
    input logic clk_i,
    input logic rst_ni,

    // Data memory ports
    output logic data_req_o,
    input  logic data_gnt_i,
    output logic [31:0] data_addr_o,
    output logic [3:0] data_be_o,
    output logic [31:0] data_wdata_o,
    output logic data_we_o,
    input  logic data_rvalid_i,
    input  logic [31:0] data_rdata_i,
    input  logic data_err_i,

    // Instruction memory ports
    output logic instr_req_o,
    input  logic instr_gnt_i,
    output logic [31:0] instr_addr_o,
    input  logic instr_rvalid_i,
    input  logic [31:0] instr_rdata_i,
    input  logic instr_err_i
);
    cv32e40x_if_xif #(
        .X_NUM_RS    (2),
        .X_ID_WIDTH  (4),
        .X_MEM_WIDTH (32),
        .X_RFR_WIDTH (32),
        .X_RFW_WIDTH (32)
    ) xif();

    cv32e40x_core #(
        .A_EXT                      (       A_NONE ),
        .B_EXT                      (       B_NONE ),
        .M_EXT                      (       M_NONE ),
        .X_EXT                      (            0 ),
        .DEBUG                      (            0 ), // TODO: Not sure about how to deal and use debugging sport. It might be useful or not?
        .DBG_NUM_TRIGGERS           (            0 ),
        .NUM_MHPMCOUNTERS           (            1 ),
        .PMA_NUM_REGIONS            (            0 ), // Disable PMA for now
        .CLIC                       (            0 ) // We don't need CLIC either
    ) u_core (
        // Clock and reset
        .clk_i                    (clk_i),
        .rst_ni                   (rst_ni),
        .scan_cg_en_i             (1'b0),

        // Configuration
        .boot_addr_i              (32'h0000_0100), // MTVEC + 256
        .mtvec_addr_i             (32'h0000_0000),
        .dm_halt_addr_i           (32'd0),
        .dm_exception_addr_i      (32'd0),
        .mhartid_i                (32'd0),
        .mimpid_patch_i           (4'd0),

        // Instruction memory interface
        .instr_req_o              (instr_req_o),
        .instr_gnt_i              (instr_gnt_i),
        .instr_addr_o             (instr_addr_o),
        .instr_memtype_o          (), // not impl
        .instr_prot_o             (), // not impl
        .instr_dbg_o              (), // not impl
        .instr_rvalid_i           (instr_rvalid_i),
        .instr_rdata_i            (instr_rdata_i),
        .instr_err_i              (instr_err_i),

        // Data memory interface
        .data_req_o               (data_req_o),
        .data_gnt_i               (data_gnt_i),
        .data_addr_o              (data_addr_o),
        .data_atop_o              (), // not impl
        .data_be_o                (data_be_o),
        .data_memtype_o           (), // not impl
        .data_prot_o              (), // not impl
        .data_dbg_o               (), // not impl
        .data_wdata_o             (data_wdata_o),
        .data_we_o                (data_we_o),
        .data_rvalid_i            (data_rvalid_i),
        .data_rdata_i             (data_rdata_i),
        .data_err_i               (data_err_i),
        .data_exokay_i            (1'b0),

        // Cycle, Time
        .mcycle_o                 (), // not impl
        .time_i                   (64'd0),

        // eXtension interface
        .xif_compressed_if        (xif.cpu_compressed),
        .xif_issue_if             (xif.cpu_issue),
        .xif_commit_if            (xif.cpu_commit),
        .xif_mem_if               (xif.cpu_mem),
        .xif_mem_result_if        (xif.cpu_mem_result),
        .xif_result_if            (xif.cpu_result),

        // Interrupt interface
        .irq_i                    (32'b0),

        .clic_irq_i               (1'b0),
        .clic_irq_id_i            (5'b0),
        .clic_irq_level_i         (8'b0),
        .clic_irq_priv_i          (2'b0),
        .clic_irq_shv_i           (1'b0),

        // Fencei flush handshake
        .fencei_flush_req_o       (),
        .fencei_flush_ack_i       (1'b1), // fence is not used, so hardwire it to 1 according to https://docs.openhwgroup.org/projects/cv32e40x-user-manual/en/stable/fencei.html

        // Debug interface
        .debug_req_i              (1'b0),
        .debug_havereset_o        (), // not impl
        .debug_running_o          (), // not impl
        .debug_halted_o           (), // not impl
        .debug_pc_valid_o         (), // not impl
        .debug_pc_o               (), // not impl

        // Special control signals
        .fetch_enable_i           (1'b1),
        .core_sleep_o             (), // not impl
        .wu_wfe_i                 (1'b0)
    );

    // Set all XIF signals to zero, as we will not have XIF for a while.
    assign xif.compressed_ready = 1'b0;
    assign xif.compressed_resp  = '0;
    assign xif.issue_ready      = 1'b0;
    assign xif.issue_resp       = '0;
    assign xif.mem_valid        = 1'b0;
    assign xif.mem_req          = '0;
    assign xif.result_valid     = 1'b0;
    assign xif.result           = '0;
endmodule
