# Olea Head Controller

A Python/tkinter GUI application for testing and controlling Olea Head devices with integrated camera feed display, LED control, and automated test sequences.

## Features

- **Host Controller Integration**: Power ON/OFF control via USB serial (VID:0x01EA PID:0xFAAA)
- **Olea Head Control**: LED and camera enable/disable commands (VID:0x01EA PID:0x1235)
- **Live Camera Feed**: Real-time USB camera display with DirectShow backend
- **Image Clarity Detection**: Laplacian variance-based sharpness percentage
- **Device Info Retrieval**: Read firmware version, hardware version, and serial number
- **Test All Sequence**: Automated full device test with power cycling and verification
- **Serial Traffic Log**: Real-time TX/RX monitoring for debugging
- **Dark Theme UI**: Modern dark interface with status indicators

## Requirements

- Python 3.8+
- Windows OS (uses DirectShow for camera, WMI for device enumeration)

### Python Dependencies

```
opencv-python
pillow
pyserial
```

## Installation

1. Install Python dependencies:
```bash
pip install opencv-python pillow pyserial
```

2. Run the application:
```bash
python camera_led_control.py
```

## Building Standalone Executable

Run the build script to create a standalone `.exe` with no console window:

```bash
build_exe.bat
```

This will:
1. Install PyInstaller and Pillow
2. Generate a camera icon (`camera_icon.ico`)
3. Build `Olea Head Controller.exe` in the `dist/` folder

## Hardware Requirements

### Host Controller
- **VID/PID**: 0x01EA / 0xFAAA
- **Baud Rate**: 9600
- **Commands**: ASCII text with newline terminator
  - Power ON: `#USB:1111,1111,0000,0000\n`
  - Power OFF: `#USB:0000,0000,0000,0000\n`

### Olea Head
- **VID/PID**: 0x01EA / 0x1235
- **Baud Rate**: 115200
- **Protocol**: Binary commands with ctypes structures

#### Commands

| Command | Byte | Description |
|---------|------|-------------|
| LED Enable | 0x02 | Enable/disable LED (uint16 payload) |
| Camera Enable | 0x03 | Enable/disable camera (uint16 payload) |
| LED Config | 0x04 | Configure LED brightness/frequency |
| Device Info | 0x05 | Read device information |

### USB Camera
- Must contain "USB CAMERA" in device name (WMI enumeration)
- DirectShow compatible

## Test All Sequence

The "Test All" button runs an automated 9-step test:

1. **Power OFF** - Send power off to Host Controller
2. **Power ON** - Send power on, wait 3 seconds
3. **Detect Olea Head** - 5 second timeout for device enumeration
4. **Get Device Info** - Read and display firmware/hardware info
5. **LED ON** - Enable LEDs with default configuration
6. **Camera ON** - Send camera enable command
7. **Detect USB Camera** - 10 second timeout for camera enumeration
8. **Capture Snapshot** - Take image, display with clarity percentage
9. **Cleanup** - Turn off camera, LED, and power

## Project Structure

```
camera_test/
├── camera_led_control.py   # Main application
├── create_icon.py          # Icon generator script
├── build_exe.bat           # Build script for executable
├── camera_icon.ico         # Application icon (generated)
├── .gitignore
└── README.md
```

## Troubleshooting

- **Host Controller not found**: Verify USB connection and VID/PID (0x01EA/0xFAAA)
- **Olea Head not detected**: Check USB connection, ensure device is powered
- **Camera not opening**: Close other applications using the camera
- **App hanging on detect**: Serial timeout issues - device may not be responding
- **No USB Camera found**: Camera must have "USB CAMERA" in its WMI device name

## License

Internal use.
