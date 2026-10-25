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
        .X_EXT                      (            1 ),
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

    crypto_coprocessor crypto_coprocessor_i (
        .clk_i(clk_i),
        .rst_ni(rst_ni),

        // XIF issue interface
        .issue_valid_i(xif.issue_valid),
        .issue_id_i(xif.issue_req.id),
        .issue_instr_i(xif.issue_req.instr),
        .issue_rs1_i(xif.issue_req.rs[0]),
        .issue_rs2_i(xif.issue_req.rs[1]),
        .issue_ready_o(xif.issue_ready),
        .issue_accept_o(xif.issue_resp.accept),
        .issue_writeback_o(xif.issue_resp.writeback),

        // XIF commit interface
        .commit_valid_i(xif.commit_valid),
        .commit_id_i(xif.commit.id),
        .commit_kill_i(xif.commit.commit_kill),

        // XIF result interface
        .result_ready_i(xif.result_ready),
        .result_valid_o(xif.result_valid),
        .result_rd_o(xif.result.rd),
        .result_we_o(xif.result.we),
        .result_id_o(xif.result.id),
        .result_data_o(xif.result.data)
    );

    // Set unnecessary XIF signals to zero
    assign xif.compressed_ready = 1'b0;
    assign xif.compressed_resp  = '0;
    assign xif.mem_valid        = 1'b0;
    assign xif.mem_req          = '0;
    assign xif.issue_resp.dualwrite = 1'b0;
    assign xif.issue_resp.dualread  = '0;
    assign xif.issue_resp.loadstore = 1'b0;
    assign xif.issue_resp.ecswrite  = 1'b0;
    assign xif.issue_resp.exc       = 1'b0;
    assign xif.result.ecsdata = '0;
    assign xif.result.ecswe   = '0;
    assign xif.result.exc     = 1'b0;
    assign xif.result.exccode = '0;
    assign xif.result.err     = 1'b0;
    assign xif.result.dbg     = 1'b0;
endmodule
