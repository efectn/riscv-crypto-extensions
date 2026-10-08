package rv32_utils_pkg;
    function automatic logic[31:0] rol(logic[31:0] val, logic[4:0] shamt);
        if (shamt == 5'd0)
            return val;

        return (val << shamt) | (val >> (6'd32 - shamt));    
    endfunction

    function automatic logic[31:0] ror(logic[31:0] val, logic[4:0] shamt);
        if (shamt == 5'd0)
            return val;

        return (val >> shamt) | (val << (6'd32 - shamt));    
    endfunction
    
endpackage
