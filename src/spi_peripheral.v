// 1-bit Synchronizer
module sync #(
    parameter integer SYNC_LENGTH = 2
) (
    input  wire d, // Data bit in
    input  wire clk, // Clock
    input  wire rst_n, // Active-low reset signal
    output wire q // Data bit out
);
    // Create reg chain
    reg [SYNC_LENGTH-1:0] chain;

    // On clock rising edge
    integer i;
    always @(posedge clk or negedge rst_n) begin
        // Check if reset line is HIGH (i.e. not being reset)
        if (rst_n) begin
            // Advance the chain
            chain[0] <= d;
            for (i = 0; i < SYNC_LENGTH - 1; i = i + 1) begin
            // This is a clocked circuit; non-blocking assignment used
            chain[i+1] <= chain[i];
            end
        end
        // Otherwise (i.e. reset line is LOW; synchronizer resets)
        else begin
            // Set all chain bits to 0
            chain <= {SYNC_LENGTH{1'b0}};
        end
    end

    // Hard-wire end of chain to output
    assign q = chain[SYNC_LENGTH-1];

endmodule

// n-bit Synchronizer
module sync_n #(
    parameter integer SYNC_LENGTH = 3,
    parameter integer N = 8
) (
    input  wire [N-1:0] d, // Data in
    input  wire clk, // Clock
    input  wire rst_n, // Active-low reset signal
    output wire [N-1:0] q // Data out
);
    // Use a `generate` block to connect synchronizers
    genvar i;
    generate
        for (i = 0; i < N; i = i + 1) begin : gen_syncs
            sync #(.SYNC_LENGTH(SYNC_LENGTH)) sn (
                .d(d[i]),
                .clk(clk),
                .rst_n(rst_n),
                .q(q[i])
            );
        end
    endgenerate

endmodule

// SPI peripheral
module spi_peripheral (
    // SPI interface
    input wire COPI, // Receives instructions
    input wire nCS, // Chip select. Module only reacts when HIGH
    input wire SCLK, // Clock
    input wire rst_n, // Active-low reset signal
    // Output register values
    output wire [7:0] en_reg_out_7_0,
    output wire [7:0] en_reg_out_15_8,
    output wire [7:0] en_reg_pwm_7_0,
    output wire [7:0] en_reg_pwm_15_8,
    output wire [7:0] pwm_duty_cycle
);
    // Connect synchronizers to main clock. But where is the main clock?

    // Sample data on every rising clock edge
    always @(posedge SCLK) begin

    end
endmodule
