`default_nettype none
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
    always @(posedge clk or negedge rst_n) begin
        // Check if reset line is HIGH (i.e. not being reset)
        if (rst_n) begin
            // Advance the chain
            chain <= {chain[SYNC_LENGTH-2 : 0], d};
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
    parameter integer SYNC_LENGTH = 2,
    parameter integer N = 1
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

// Rising edge detector
module rise_trigger (
    input wire in, // Input to detect edge of
    input wire clk, // System clock input
    input wire rst_n, // Reset line
    output reg s_edge // Whether a positive edge occurred on the SPI clock line
);
    // Previous SPI clock level
    reg prev;

    // On every system clock edge or LOW reset line
    always @(posedge clk or negedge rst_n) begin
        // If not being reset
        if (rst_n) begin
            // Update the output depending on whether a rising edge occurred
            // i.e. prev = 0, curr = 1
            s_edge <= ~prev & in;
        end
        // If being reset
        else begin
            // Set initial value for output reg
            s_edge <= 0;
        end

        // Update previous state reg regardless of case
        prev <= in;
    end
endmodule

// 16-bit shift register
module shift_reg (
    input wire in, // Input bit
    input wire sclk, // SPI serial clock input
    input wire cs, // Chip select input. Only shifts when it is LOW
    input wire rst_n, // Reset line
    output reg [15:0] out, // Output is always 8-bit MSB first, for convenience
    output reg ready // HIGH when the output is ready to be read.
    // After you read data from it, remember to set `ready` to LOW.
);
    reg [3:0] count; // Current clock count

    // Wire for sclk rising edge detection output
    wire sclk_edge;

    // Connect rise trigger
    rise_trigger rt_sclk (
        .in(sclk),
        .clk(clk),
        .rst_n(rst_n),
        .s_edge(sclk_edge)
    );

    always @(posedge clk or negedge rst_n) begin
        // If the shift register is not being reset
        if (rst_n) begin
            // If the chip select line is LOW AND a sclk rising edge has been detected
            if (!cs & sclk_edge) begin
                // Do the shift
                out <= {out[14:0], in};

                // If the current count (before incrementing) is 15, schedule `ready` to turn on
                if (count == 4'd15) begin
                    ready <= 1'b1;
                end
                // Otherwise, the output is not ready
                else begin
                    ready <= 1'b0;
                end

                // Advance clock count
                count <= count + 1;
            end
        end
        else begin
            // Clear shift register on reset
            out <= 16'b0;
            // Clear ready bit
            ready <= 1'b0;
            // Reset bit count
            count <= 4'b0;
        end
    end
endmodule

// Register controller
module reg_controller (
    // Command bits (obtained from shift register)
    input wire [15:0] command,
    // Ready bit in
    input wire ready,
    // Reset line
    input wire rst_n,
    // Output register values
    output reg [7:0] en_reg_out_7_0, // output enables for uo_out[7:0]. Address: 0x00
    output reg [7:0] en_reg_out_15_8, // output enables for uio_out[7:0]. Address: 0x01
    output reg [7:0] en_reg_pwm_7_0, // pwm enables for uo_out[7:0]. Address: 0x02
    output reg [7:0] en_reg_pwm_15_8, // pwm enables for uio_out[7:0]. Address: 0x03
    output reg [7:0] pwm_duty_cycle // PWM duty cycle (0x00=0%, 0xFF=100%). Address: 0x04
);
    /*
        bit 0: read/write bit. SPI module only reacts when this is 1
        bits 2-8: register address to edit.
        bits 9-15: new value for register
    */

    // Wire for rising edge output for `ready`
    wire ready_edge;
    // Connect rise trigger
    rise_trigger rt_ready (
        .in(ready),
        .clk(clk),
        .rst_n(rst_n),
        .s_edge(ready_edge)
    );

    // Create a bus on the data byte
    wire [7:0] w_data;
    assign w_data = command[7:0];

    // Trigger when clock or reset
    always @(posedge clk or negedge rst_n) begin
        // If not being reset
        if (rst_n) begin
            // If the R/W bit is "write" AND a rising edge has been detected in `ready`
            if (command[15] & ready_edge) begin
                // Split cases based on address
                case (command[14:8])
                    7'h00: en_reg_out_7_0 <= w_data;
                    7'h01: en_reg_out_15_8 <= w_data;
                    7'h02: en_reg_pwm_7_0 <= w_data;
                    7'h03: en_reg_pwm_15_8 <= w_data;
                    7'h04: pwm_duty_cycle <= w_data;
                    default:; // No default action
                endcase
            end
        end
        // If being reset
        else begin
            // Reset registers
            en_reg_out_7_0 <= 8'b0;
            en_reg_out_15_8 <= 8'b0;
            en_reg_pwm_7_0 <= 8'b0;
            en_reg_pwm_15_8 <= 8'b0;
            pwm_duty_cycle <= 8'b0;
        end
    end
endmodule

// SPI peripheral
module spi_peripheral (
    // SPI interface
    input wire copi, // Receives instructions
    input wire ncs, // Chip select. Module only reacts when HIGH
    input wire sclk, // SPI clock
    input wire clk, // System clock
    input wire rst_n, // Active-low reset signal
    // Output register values
    output wire [7:0] en_reg_out_7_0, // output enables for uo_out[7:0]. Address: 0x00
    output wire [7:0] en_reg_out_15_8, // output enables for uio_out[7:0]. Address: 0x01
    output wire [7:0] en_reg_pwm_7_0, // pwm enables for uo_out[7:0]. Address: 0x02
    output wire [7:0] en_reg_pwm_15_8, // pwm enables for uio_out[7:0]. Address: 0x03
    output wire [7:0] pwm_duty_cycle // PWM duty cycle (0x00=0%, 0xFF=100%). Address: 0x04
);
    // Create wires for synced signals
    wire copi_s; // COPI
    wire ncs_s; // nCS
    wire sclk_s; // SPI clock

    // Synchronize SPI inputs using the system clock
    sync_n copi_sync (
        .d(copi),
        .clk(clk),
        .rst_n(rst_n),
        .q(copi_s)
    );
    sync_n ncs_sync (
        .d(ncs),
        .clk(clk),
        .rst_n(rst_n),
        .q(ncs_s)
    );
    sync_n sclk_sync (
        .d(sclk),
        .clk(clk),
        .rst_n(rst_n),
        .q(sclk_s)
    );

    // Parallel bit registers
    reg [15:0] data;

    // Parallel data ready wire
    wire ready;

    // Connect shift register to read data
    shift_reg sreg (
        .in(copi_s),
        .sclk(sclk_s),
        .cs(ncs_s),
        .rst_n(rst_n),
        .out(data),
        .ready(ready)
    );

    // Connect register controller
    reg_controller regc (
        .command(data),
        .ready(ready),
        .rst_n(rst_n),
        .en_reg_out_7_0(en_reg_out_7_0),
        .en_reg_out_15_8(en_reg_out_15_8),
        .en_reg_pwm_7_0(en_reg_pwm_7_0),
        .en_reg_pwm_15_8(en_reg_pwm_15_8),
        .pwm_duty_cycle(pwm_duty_cycle)
    );

endmodule
