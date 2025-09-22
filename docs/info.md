<!---

This file is used to generate your project datasheet. Please fill in the information below and delete any unused
sections.

You can also include images in this folder and reference them in the markdown. Each image must be less than
512 kb in size, and the combined size of all images must be less than 1 MB.
-->
# Bryan's UWASIC Onboarding Project

## How it works

The project can be controlled by an SPI controller,
and its pin map are as follows:

- `ui_in[1]` goes to `COPI` (Controller Out, Peripheral In)
- `ui_in[2]` goes to `nCS` (Chip Select)
- `ui_in[0]` goes to `SCLK` (Serial Clock)

## How to test

The `cocotb` python module is used to test all chip components in this project.

## External hardware

None that I know of. Everything here is done via software.
