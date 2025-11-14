# SPDX-FileCopyrightText: © 2024 Tiny Tapeout
# SPDX-License-Identifier: Apache-2.0

import cocotb
from cocotb.utils import get_sim_time
from cocotb.clock import Clock
from cocotb.triggers import RisingEdge
from cocotb.triggers import ClockCycles
from cocotb.types import Logic
from cocotb.types import LogicArray

async def await_half_sclk(dut):
    """Wait for the SCLK signal to go high or low."""
    start_time = get_sim_time(unit="ns")
    while True:
        await ClockCycles(dut.clk, 1)
        # Wait for half of the SCLK period (10 us)
        if (start_time + 100*100*0.5) < get_sim_time(unit="ns"):
            break
    return

def ui_in_logicarray(ncs, bit, sclk):
    """Setup the ui_in value as a LogicArray."""
    return LogicArray(f"00000{ncs}{bit}{sclk}")

async def send_spi_transaction(dut, r_w, address, data):
    """
    Send an SPI transaction with format:
    - 1 bit for Read/Write
    - 7 bits for address
    - 8 bits for data
    
    Parameters:
    - r_w: boolean, True for write, False for read
    - address: int, 7-bit address (0-127)
    - data: LogicArray or int, 8-bit data
    """
    # Convert data to int if it's a LogicArray
    if isinstance(data, LogicArray):
        data_int = int(data)
    else:
        data_int = data
    # Validate inputs
    if address < 0 or address > 127:
        raise ValueError("Address must be 7-bit (0-127)")
    if data_int < 0 or data_int > 255:
        raise ValueError("Data must be 8-bit (0-255)")
    # Combine RW and address into first byte
    first_byte = (int(r_w) << 7) | address
    # Start transaction - pull CS low
    sclk = 0
    ncs = 0
    bit = 0
    # Set initial state with CS low
    dut.ui_in.value = ui_in_logicarray(ncs, bit, sclk)
    await ClockCycles(dut.clk, 1)
    # Send first byte (RW + Address)
    for i in range(8):
        bit = (first_byte >> (7-i)) & 0x1
        # SCLK low, set COPI
        sclk = 0
        dut.ui_in.value = ui_in_logicarray(ncs, bit, sclk)
        await await_half_sclk(dut)
        # SCLK high, keep COPI
        sclk = 1
        dut.ui_in.value = ui_in_logicarray(ncs, bit, sclk)
        await await_half_sclk(dut)
    # Send second byte (Data)
    for i in range(8):
        bit = (data_int >> (7-i)) & 0x1
        # SCLK low, set COPI
        sclk = 0
        dut.ui_in.value = ui_in_logicarray(ncs, bit, sclk)
        await await_half_sclk(dut)
        # SCLK high, keep COPI
        sclk = 1
        dut.ui_in.value = ui_in_logicarray(ncs, bit, sclk)
        await await_half_sclk(dut)
    # End transaction - return CS high
    sclk = 0
    ncs = 1
    bit = 0
    dut.ui_in.value = ui_in_logicarray(ncs, bit, sclk)
    await ClockCycles(dut.clk, 600)
    return ui_in_logicarray(ncs, bit, sclk)

@cocotb.test
async def test_spi(dut):
    dut._log.info("Start SPI test")

    # Set the clock period to 100 ns (10 MHz)
    clock = Clock(dut.clk, 100, unit="ns")
    cocotb.start_soon(clock.start())

    # Reset
    dut._log.info("Reset")
    dut.ena.value = 1
    ncs = 1
    bit = 0
    sclk = 0
    dut.ui_in.value = ui_in_logicarray(ncs, bit, sclk)
    dut.rst_n.value = 0
    await ClockCycles(dut.clk, 5)
    dut.rst_n.value = 1
    await ClockCycles(dut.clk, 5)

    dut._log.info("Test project behavior")
    dut._log.info("Write transaction, address 0x00, data 0xF0")
    ui_in_val = await send_spi_transaction(dut, 1, 0x00, 0xF0)  # Write transaction
    assert dut.uo_out.value == 0xF0, f"Expected 0xF0, got {dut.uo_out.value}"
    await ClockCycles(dut.clk, 1000) 

    dut._log.info("Write transaction, address 0x01, data 0xCC")
    ui_in_val = await send_spi_transaction(dut, 1, 0x01, 0xCC)  # Write transaction
    assert dut.uio_out.value == 0xCC, f"Expected 0xCC, got {dut.uio_out.value}"
    await ClockCycles(dut.clk, 100)

    dut._log.info("Write transaction, address 0x30 (invalid), data 0xAA")
    ui_in_val = await send_spi_transaction(dut, 1, 0x30, 0xAA)
    await ClockCycles(dut.clk, 100)

    dut._log.info("Read transaction (invalid), address 0x00, data 0xBE")
    ui_in_val = await send_spi_transaction(dut, 0, 0x30, 0xBE)
    assert dut.uo_out.value == 0xF0, f"Expected 0xF0, got {dut.uo_out.value}"
    await ClockCycles(dut.clk, 100)
    
    dut._log.info("Read transaction (invalid), address 0x41 (invalid), data 0xEF")
    ui_in_val = await send_spi_transaction(dut, 0, 0x41, 0xEF)
    await ClockCycles(dut.clk, 100)

    dut._log.info("Write transaction, address 0x02, data 0xFF")
    ui_in_val = await send_spi_transaction(dut, 1, 0x02, 0xFF)  # Write transaction
    await ClockCycles(dut.clk, 100)

    dut._log.info("Write transaction, address 0x04, data 0xCF")
    ui_in_val = await send_spi_transaction(dut, 1, 0x04, 0xCF)  # Write transaction
    await ClockCycles(dut.clk, 30000)

    dut._log.info("Write transaction, address 0x04, data 0xFF")
    ui_in_val = await send_spi_transaction(dut, 1, 0x04, 0xFF)  # Write transaction
    await ClockCycles(dut.clk, 30000)

    dut._log.info("Write transaction, address 0x04, data 0x00")
    ui_in_val = await send_spi_transaction(dut, 1, 0x04, 0x00)  # Write transaction
    await ClockCycles(dut.clk, 30000)

    dut._log.info("Write transaction, address 0x04, data 0x01")
    ui_in_val = await send_spi_transaction(dut, 1, 0x04, 0x01)  # Write transaction
    await ClockCycles(dut.clk, 30000)

    dut._log.info("SPI test completed successfully")

async def next_edge(dut, pos_edge):
    """
    `dut`: the DUT
    `pos_edge`: set to True to detect rising edges, and False to detect falling edges.
    """
    advance = (bool(dut.uo_out.value[0]) == pos_edge)
    while (bool(dut.uo_out.value[0]) != pos_edge) or advance:
        advance = False
        await dut.uo_out.value_change

@cocotb.test
async def test_pwm_freq(dut):
    dut._log.info("Start PWM Frequency test")
    # Set the clock period to 100 ns (10 MHz)
    clock = Clock(dut.clk, 100, unit="ns")
    cocotb.start_soon(clock.start())

    # Reset
    dut._log.info("Reset")
    dut.ena.value = 1
    ncs = 1
    bit = 0
    sclk = 0
    dut.ui_in.value = ui_in_logicarray(ncs, bit, sclk)
    dut.rst_n.value = 0
    await ClockCycles(dut.clk, 5)
    dut.rst_n.value = 1
    await ClockCycles(dut.clk, 5)

    dut._log.info("Test project behavior")
    dut._log.info("Init SPI module")
    # 1. Measure the time between two rising edges (i.e. period)
    # 1a. Enable outputs on uo_out[7:0], message (1, 0x00, 0xFF)
    await send_spi_transaction(dut, 1, 0x00, 0xFF)
    # 1b. Enable PWM on all these outputs, message (1, 0x02, 0xFF)
    await send_spi_transaction(dut, 1, 0x02, 0xFF)
    # 1c. Set PWM duty to 50%
    await send_spi_transaction(dut, 1, 0x04, 0x7F)

    for i in range(10):
        dut._log.info(f"Measuring period, iteration {i}")
        # 2. Wait for the next PWM rising edge on uo_out[0]
        await next_edge(dut, True)
        # Get the current sim time
        t_rising_edge1 = get_sim_time(unit='ms')

        # 3. Wait for the next PWM rising edge on uo_out[0]
        await next_edge(dut, True)
        #  Get the current sim time
        t_rising_edge2 = get_sim_time(unit='ms')

        dut._log.info("Computing frequency")
        # 4. Compute period (ms)
        period_ms = t_rising_edge2 - t_rising_edge1

        # 5. Compute frequency (kHz)
        f_khz = 1.0 / period_ms

        # 6. Check that frequency is between 2970-3030 Hz
        assert (f_khz >= 2.97 and f_khz <= 3.03), f"PWM frequency is measured to be {f_khz} KHz, which is outside the acceptable range of [2.97, 3.03] KHz."

    dut._log.info("PWM Frequency test completed successfully")

async def test_hold(dut, value: Logic):
    """
    `dut`: the DUT
    `value`: the logic value to test the hold for
    """
    ITERS = 3328
    for i in range(ITERS):
        # Assert PWM level
        assert dut.uo_out.value[0] == value, f"Expected PWM signal to hold at {value}, but got {dut.uo_out.value[0]} at iteration {i}"
        # Wait for 1 clock cycle
        await ClockCycles(dut.clk, 1)

@cocotb.test
async def test_pwm_duty(dut):
    dut._log.info("Start PWM Duty Cycle test")
    # Set the clock period to 100 ns (10 MHz)
    clock = Clock(dut.clk, 100, unit="ns")
    cocotb.start_soon(clock.start())

    # Reset
    dut._log.info("Reset")
    dut.ena.value = 1
    ncs = 1
    bit = 0
    sclk = 0
    dut.ui_in.value = ui_in_logicarray(ncs, bit, sclk)
    dut.rst_n.value = 0
    await ClockCycles(dut.clk, 5)
    dut.rst_n.value = 1
    await ClockCycles(dut.clk, 5)

    dut._log.info("Test project behavior")
    # 1a. Enable outputs on uo_out[7:0], message (1, 0x00, 0xFF)
    await send_spi_transaction(dut, 1, 0x00, 0xFF)
    # 1b. Enable PWM on all these outputs, message (1, 0x02, 0xFF)
    await send_spi_transaction(dut, 1, 0x02, 0xFF)

    # Do tests 10 times
    for i in range(10):
        dut._log.info(f"Iteration {i}")
        # 2. Test 0% duty
        dut._log.info("Test 0% Duty")
        await send_spi_transaction(dut, 1, 0x04, 0x00)
        await test_hold(dut, Logic(False))

        # 3. Test 50% duty
        dut._log.info("Test 50% Duty")
        await send_spi_transaction(dut, 1, 0x04, 0x7F)
        # Locate a negative edge first
        await next_edge(dut, False)
        # Then measure
        t_a = get_sim_time() # Starting step number
        await next_edge(dut, True) # Locate rising edge

        t_m = get_sim_time() # Level change step number
        await next_edge(dut, False) # Locate falling edge

        t_b = get_sim_time() # Ending step number
        # Calculate duty cycle
        duty = (t_b - t_m) / (t_b - t_a)
        # Check if duty is within +/- 1% of 0.5
        assert (duty >= 0.495 and duty <= 0.505), f"The calculated duty cycle is {duty}, which is outside +/- 1% of the expected value, 0.5"

        # 4. Test 100% duty
        dut._log.info("Test 100% Duty")
        await send_spi_transaction(dut, 1, 0x04, 0xFF)
        await test_hold(dut, Logic(True))

    dut._log.info("PWM Duty Cycle test completed successfully")
