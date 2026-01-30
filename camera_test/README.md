# Camera & LED Controller

A Python GUI application for viewing USB camera feed and controlling LEDs via serial communication.

## Features

- Real-time camera feed display (640x480 @ ~30 FPS)
- Serial port auto-detection and connection
- Control 2 LEDs with ON/OFF buttons
- Status indicators for connection and commands

## Installation

1. Install Python dependencies:
```bash
pip install -r requirements.txt
```

## Usage

1. Run the application:
```bash
python camera_led_control.py
```

2. Connect your USB camera (the app will auto-detect camera 0)

3. Select your serial port from the dropdown and click "Connect"

4. Use the LED control buttons to send commands

## Serial Commands

The application sends the following byte commands:

- `0x01` - LED 1 ON
- `0x02` - LED 1 OFF
- `0x03` - LED 2 ON
- `0x04` - LED 2 OFF

## Arduino Example Code

If you're using an Arduino to control the LEDs, here's sample code to receive the commands:

```cpp
const int LED1_PIN = 9;
const int LED2_PIN = 10;

void setup() {
  Serial.begin(9600);
  pinMode(LED1_PIN, OUTPUT);
  pinMode(LED2_PIN, OUTPUT);
}

void loop() {
  if (Serial.available() > 0) {
    byte command = Serial.read();

    switch(command) {
      case 0x01:  // LED 1 ON
        digitalWrite(LED1_PIN, HIGH);
        break;
      case 0x02:  // LED 1 OFF
        digitalWrite(LED1_PIN, LOW);
        break;
      case 0x03:  // LED 2 ON
        digitalWrite(LED2_PIN, HIGH);
        break;
      case 0x04:  // LED 2 OFF
        digitalWrite(LED2_PIN, LOW);
        break;
    }
  }
}
```

## Troubleshooting

- **Camera not opening**: Make sure no other application is using the camera
- **Serial port not found**: Check device manager and ensure drivers are installed
- **Connection failed**: Verify baud rate (9600) matches your device settings
