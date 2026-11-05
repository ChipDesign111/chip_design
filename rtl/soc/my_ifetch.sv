// Instruction fetch buffer: a few fully-associative lines with sequential
// prefetch.
//
// The CPU's instruction port is OBI-like: req/addr in, gnt, then data with
// valid (at least one cycle after the grant). Served straight from a
// single-beat AXI adapter every fetch costs two cycles end to end, because the
// adapter can only accept a new address once the previous response is back.
// The firmware is sequential almost everywhere, so instead of one word per AXI
// transaction this unit fetches an aligned LINE_WORDS-word line with one INCR
// burst and serves the whole line: a buffered line is granted in the request
// cycle itself and returns data one cycle later, so back-to-back fetches leave
// at 1 instruction per cycle. While the core runs inside a line, the line
// after it is prefetched, which hides the burst latency.
//
// SLOTS lines are kept and replaced by least-recently-used order, so a loop
// whose body spans up to SLOTS lines keeps all of its lines resident and pays
// the burst only on the first iteration; a two-entry buffer (just "current"
// and "next") would evict the line a backward branch returns to and refetch it
// every iteration.
//
// Only the read channels are used. Bursts are issued for addresses inside the
// boot ROM and the SRAM, the two regions the core executes from (both are
// served by axi2mem, which supports INCR bursts); everything else - the debug
// module's halt area in particular, which holds a single halting instruction -
// is fetched a word at a time so no target ever sees a burst it cannot serve.
module my_ifetch #(
    parameter type axi_req_t = logic,
    parameter type axi_rsp_t = logic,
    // Words per line (burst length) and number of buffered lines.
    parameter int unsigned LINE_WORDS  = 4,
    parameter int unsigned SLOTS       = 4,
    parameter logic [31:0] SRAM_BASE   = 32'h8000_0000,
    parameter logic [31:0] SRAM_LENGTH = 32'h0000_2000,
    parameter logic [31:0] BOOT_BASE   = 32'h0001_0000,
    parameter logic [31:0] BOOT_LENGTH = 32'h0001_0000
) (
    input  logic        clk_i,
    input  logic        rst_ni,
    // Instruction port (CPU side)
    input  logic        req_i,
    input  logic [31:0] addr_i,
    output logic        gnt_o,
    output logic        valid_o,
    output logic [31:0] rdata_o,
    // AXI read port
    output axi_req_t    axi_req_o,
    input  axi_rsp_t    axi_resp_i
);

    localparam int unsigned LINE_W     = $clog2(LINE_WORDS);   // word offset bits
    localparam int unsigned LINE_BYTES = LINE_WORDS * 4;
    localparam int unsigned IDX_LSB    = 2;
    localparam int unsigned IDX_MSB    = IDX_LSB + LINE_W - 1;
    localparam int unsigned SLOT_W     = (SLOTS > 1) ? $clog2(SLOTS) : 1;
    localparam logic [LINE_W-1:0] LAST_IDX = (LINE_WORDS - 1);

    typedef enum logic [1:0] {F_IDLE, F_AR, F_R} fill_state_t;

    // ---------------------------------------------------------------- lines
    logic [LINE_WORDS-1:0][31:0] sdata_q [SLOTS];
    logic [31:0]         stag_q  [SLOTS];
    logic [LINE_W-1:0]   slen_q  [SLOTS];
    logic [SLOTS-1:0]    svalid_q;
    logic [1:0]          sage_q  [SLOTS];      // 0 = most recently used

    logic [SLOT_W-1:0]   last_q;               // slot of the last hit

    // ---------------------------------------------------------------- fill
    fill_state_t         fstate_q;
    logic [31:0]         fill_addr_q;
    logic [LINE_W-1:0]   fill_cnt_q;
    logic [LINE_W-1:0]   fill_len_q;
    logic [SLOT_W-1:0]   fill_slot_q;

    // -------------------------------------------------------------- request
    wire [31:0]       req_line = {addr_i[31:IDX_MSB+1], {(IDX_MSB+1){1'b0}}};
    wire [LINE_W-1:0] req_idx  = addr_i[IDX_MSB:IDX_LSB];

    logic [SLOTS-1:0] hit_vec;
    logic [SLOT_W-1:0] hit_sel;
    always_comb begin
        hit_vec = '0;
        for (int hi = 0; hi < SLOTS; hi++)
            hit_vec[hi] = svalid_q[hi] && (stag_q[hi] == req_line) && (req_idx <= slen_q[hi]);
        hit_sel = '0;
        for (int hs = SLOTS - 1; hs >= 0; hs--)
            if (hit_vec[hs]) hit_sel = SLOT_W'(hs);
    end

    wire hit = |hit_vec;

    assign gnt_o = req_i & hit;

    wire miss = req_i & ~hit;

    // ------------------------------------------------------------- victim
    // Lowest priority is an invalid slot; otherwise the largest age wins.
    logic [SLOT_W-1:0] victim;
    logic [2:0]        victim_age;
    always_comb begin
        victim     = '0;
        victim_age = '0;
        for (int vi = 0; vi < SLOTS; vi++) begin
            if ((svalid_q[vi] ? {1'b0, sage_q[vi]} : 3'b111) >= victim_age) begin
                victim_age = svalid_q[vi] ? {1'b0, sage_q[vi]} : 3'b111;
                victim     = SLOT_W'(vi);
            end
        end
    end

    // -------------------------------------------------------- region checks
    function automatic logic burst_ok(input logic [31:0] word_addr);
        logic [31:0] base;
        base = {word_addr[31:IDX_MSB+1], {(IDX_MSB+1){1'b0}}};
        return (((base >= SRAM_BASE) && ((base + LINE_BYTES) <= (SRAM_BASE + SRAM_LENGTH))) ||
                ((base >= BOOT_BASE) && ((base + LINE_BYTES) <= (BOOT_BASE + BOOT_LENGTH))));
    endfunction

    // ------------------------------------------------------------ prefetch
    // One line ahead of the line the core is currently executing, and only if
    // it is not buffered already: a loop then generates no extra traffic at all.
    wire [31:0] pf_line = stag_q[last_q] + LINE_BYTES;
    logic       pf_present;
    always_comb begin
        pf_present = 1'b0;
        for (int pi = 0; pi < SLOTS; pi++)
            if (svalid_q[pi] && (stag_q[pi] == pf_line)) pf_present = 1'b1;
    end

    wire start_miss = miss && (fstate_q == F_IDLE);
    wire start_pf   = !start_miss && (fstate_q == F_IDLE) && svalid_q[last_q] &&
                      !pf_present && burst_ok(pf_line);
    wire do_start   = start_miss || start_pf;

    wire [31:0]       start_addr = start_miss ? req_line : pf_line;
    wire [LINE_W-1:0] start_len  = start_miss ? (burst_ok(req_line) ? LAST_IDX : '0)
                                              : LAST_IDX;

    // The fill address is presented in the cycle it is decided so the AR
    // handshake can complete immediately.
    wire       ar_active = (fstate_q == F_AR) || do_start;
    wire [31:0] ar_addr  = (fstate_q == F_AR) ? fill_addr_q : start_addr;
    wire [LINE_W-1:0] ar_len = (fstate_q == F_AR) ? fill_len_q : start_len;
    wire       ar_ready  = axi_resp_i.ar_ready;

    // ------------------------------------------------------------ AXI drive
    always_comb begin
        axi_req_o            = '0;
        axi_req_o.ar_valid   = ar_active;
        axi_req_o.ar.addr    = ar_addr;
        axi_req_o.ar.len     = {{(8-LINE_W){1'b0}}, ar_len};
        axi_req_o.ar.size    = 3'b010;               // 4 bytes per beat
        axi_req_o.ar.burst   = axi_pkg::BURST_INCR;
        axi_req_o.ar.cache   = axi_pkg::CACHE_MODIFIABLE;
        axi_req_o.ar.id      = '0;
        axi_req_o.ar.prot    = 3'b0;
        axi_req_o.ar.region  = 4'b0;
        axi_req_o.ar.lock    = 1'b0;
        axi_req_o.ar.qos     = 4'b0;
        axi_req_o.ar.user    = '0;
        axi_req_o.r_ready    = (fstate_q == F_R);
    end

    // ------------------------------------------------------------ response
    always_ff @(posedge clk_i or negedge rst_ni) begin
        if (~rst_ni) begin
            valid_o <= 1'b0;
            rdata_o <= '0;
        end else begin
            valid_o <= gnt_o;
            if (gnt_o)
                rdata_o <= sdata_q[hit_sel][req_idx];
        end
    end

    // ------------------------------------------------------- fill + buffers
    always_ff @(posedge clk_i or negedge rst_ni) begin
        if (~rst_ni) begin
            fstate_q    <= F_IDLE;
            fill_addr_q <= '0;
            fill_cnt_q  <= '0;
            fill_len_q  <= '0;
            fill_slot_q <= '0;
            last_q      <= '0;
            svalid_q    <= '0;
            for (int ri = 0; ri < SLOTS; ri++) begin
                sdata_q[ri] <= '0;
                stag_q[ri]  <= '0;
                slen_q[ri]  <= '0;
                sage_q[ri]  <= 2'd3;
            end
        end else begin
            // Age: every hit makes its slot the most recent one.
            for (int ui = 0; ui < SLOTS; ui++) begin
                if (hit_vec[ui])
                    sage_q[ui] <= 2'd0;
                else if (hit && (sage_q[ui] != 2'd3))
                    sage_q[ui] <= sage_q[ui] + 2'd1;
            end
            if (hit) last_q <= hit_sel;

            case (fstate_q)
                F_IDLE: begin
                    if (do_start) begin
                        fill_addr_q <= start_addr;
                        fill_len_q  <= start_len;
                        fill_cnt_q  <= '0;
                        fill_slot_q <= victim;
                        // The victim is invalidated while its words are written
                        // one beat at a time, so a partially filled line can
                        // never be hit. Its tag is written up front so that the
                        // line can be hit the moment its first word lands.
                        stag_q[victim]   <= start_addr;
                        slen_q[victim]   <= '0;
                        svalid_q[victim] <= 1'b0;
                        sage_q[victim]   <= 2'd1;
                        fstate_q    <= ar_ready ? F_R : F_AR;
                    end
                end

                F_AR: begin
                    if (ar_ready)
                        fstate_q <= F_R;
                end

                F_R: begin
                    if (axi_resp_i.r_valid) begin
                        sdata_q[fill_slot_q][fill_cnt_q] <= axi_resp_i.r.data;
                        // Publish every word the moment it lands instead of
                        // waiting for r.last: the core can hit a word it has
                        // already received while the rest of the line is still
                        // streaming in. A miss at word k then costs the burst
                        // only up to beat k (and a prefetch that beats the core
                        // to a new line costs the core nothing at all), rather
                        // than always the full line.
                        svalid_q[fill_slot_q] <= 1'b1;
                        slen_q[fill_slot_q]   <= fill_cnt_q;

                        if (axi_resp_i.r.last) begin
                            fstate_q             <= F_IDLE;
                        end else begin
                            fill_cnt_q <= fill_cnt_q + 1'b1;
                        end
                    end
                end

                default: fstate_q <= F_IDLE;
            endcase
        end
    end

endmodule
