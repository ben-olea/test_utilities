# Test Hub

RP2040-based USB Hub Testing Device firmware for controlling and testing 4-port USB hubs with power switching and GPIO control capabilities.

## Overview

Test Hub provides remote control of USB hub hardware through a serial command interface, enabling automated testing and manual control of:

- 4 independent power switches
- 4 USB port enable switches
- GPIO up/down lines
- 4 GPU device control pairs

## Hardware

| Component | Pins |
|-----------|------|
| Power Switches (PWR_SW_EN_1-4) | 23, 1, 25, 24 |
| USB Port Enable (USBPE_EN_1-4) | 9, 0, 10, 11 |
| GPIO Up/Down | 20, 15 |
| GPU_1 (Down/Up) | 18, 19 |
| GPU_2 (Down/Up) | 17, 16 |
| GPU_3 (Down/Up) | 6, 5 |
| GPU_4 (Down/Up) | 8, 7 |

**Board:** Generic RP2040 (Raspberry Pi Pico)

## Serial Communication

- **Baud Rate:** 115,200
- **USB VID/PID:** 0x01ea / 0xfaaa
- **Manufacturer:** Olea
- **Product:** TEST_HUB

## Commands

### Query Hub ID
```
#ID?
```
Response: `$:HUB:0000`

### USB/Power Control
```
#USB,{PWR},{USB_PE},{GPIO_U},{GPIO_D}
```
Each parameter is a 4-digit binary string (one digit per port, 0=off, 1=on).

**Examples:**
```
#USB,1111,1111,0000,0000    # Enable all power and USB ports
#USB,1000,1000,0000,0000    # Enable only port 1
#USB,0000,0000,0000,0000    # Disable all
```

### Read GPIO Status
```
#GUD
```
Returns the state of GPIO up/down pins.

## Arduino IDE Setup

1. Install Arduino IDE with RP2040/Pico support
2. Select board: **Generic RP2040**
3. Configure settings:
   - Flash Size: 2MB (no FS)
   - CPU Speed: 200 MHz
   - Upload Method: Default (UF2)
   - USB Stack: Pico SDK

See `test_hub arduino settings.png` for reference.

## Upload

### Arduino Settings: 
- Device: Generic RP2040
- Boot stage 2: Generic SPI/4

1. Connect RP2040 board via USB
2. Open `test_hub.ino` in Arduino IDE
3. Select the correct COM port
4. Click Upload

Alternatively, copy `build/rp2040.rp2040.generic/test_hub.ino.uf2` directly to the RP2040 when in bootloader mode.

## Build Artifacts

Pre-built firmware is available in `build/rp2040.rp2040.generic/`:
- `test_hub.ino.uf2` - UF2 format for direct upload
- `test_hub.ino.bin` - Binary image
- `test_hub.ino.elf` - ELF with debug symbols

## License

Internal use.
