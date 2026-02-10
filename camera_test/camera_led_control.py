import json
import time
import tkinter as tk
from tkinter import ttk, messagebox
import cv2
from PIL import Image, ImageTk
import serial
import serial.tools.list_ports
import ctypes
import subprocess
import threading
from datetime import datetime


class device_info_t(ctypes.Structure):
    """Olea Head device info structure"""
    _pack_ = 1
    _fields_ = [
        ('device_name', ctypes.c_uint16),
        ('firmware_version_major', ctypes.c_uint16),
        ('firmware_version_minor', ctypes.c_uint16),
        ('firmware_version_patch', ctypes.c_uint16),
        ('serial_number_h', ctypes.c_uint64),
        ('serial_number_l', ctypes.c_uint64),
        ('hardware_version', ctypes.c_uint16),
    ]


class led_config_t(ctypes.Structure):
    """Olea Head LED configuration structure"""
    _pack_ = 1
    _fields_ = [
        ('ramp_time_ms', ctypes.c_uint16),
        ('frequency', ctypes.c_uint16),
        ('brightness', ctypes.c_uint8 * 25),
    ]

    @staticmethod
    def led_config_all():
        """Create default LED config: 1000Hz frequency, 50 brightness for all 25 LEDs"""
        brightness_array = (ctypes.c_uint8 * 25)(*([50] * 25))
        return led_config_t(
            ramp_time_ms=0,
            frequency=1000,
            brightness=brightness_array
        )


class CameraLEDController:
    def __init__(self, root):
        self.root = root
        self.root.title("Olea Head Controller")
        self.root.geometry("1200x1000")

        # Host controller connection
        self.host_controller_conn = None
        self.HOST_CONTROLLER_VID = 0x01ea
        self.HOST_CONTROLLER_PID = 0xfaaa

        # Olea Head connection
        self.olea_head_port = None  # Port name for open/close per transaction
        self.olea_head_conn = None  # Temporary connection during transaction
        self.OLEA_HEAD_VID = 0x01ea
        self.OLEA_HEAD_PID = 0x1235

        # Olea Head Commands
        self.HEAD_CMD_LED_EN = 0x02
        self.HEAD_CMD_CAMERA_EN = 0x03
        self.HEAD_CMD_LED_CONFIG = 0x04
        self.HEAD_CMD_DEVICE_INFO = 0x05

        # Camera capture state
        self.camera_running = False
        self.camera = None

        # Available cameras list
        self.available_cameras = []

        # Configure dark theme
        self.configure_dark_theme()

        # Setup UI
        self.setup_ui()

    def configure_dark_theme(self):
        """Configure dark theme for the application"""
        # Dark color scheme
        bg_color = '#1e1e1e'           # Dark background
        fg_color = '#e0e0e0'           # Light text
        button_bg = '#0e639c'          # Blue buttons
        button_hover = '#1177bb'       # Lighter blue on hover
        entry_bg = '#3c3c3c'           # Entry/combobox background

        # Set root window background
        self.root.configure(bg=bg_color)

        # Create and configure style
        style = ttk.Style()

        # Configure TFrame
        style.configure('TFrame', background=bg_color)

        # Configure TLabelframe
        style.configure('TLabelframe', background=bg_color, foreground=fg_color)
        style.configure('TLabelframe.Label', background=bg_color, foreground=fg_color, font=('Arial', 9, 'bold'))

        # Configure TLabel
        style.configure('TLabel', background=bg_color, foreground=fg_color, font=('Arial', 9))

        # Configure TButton
        style.configure('TButton', background=button_bg, foreground='#000000', borderwidth=1, relief='flat')
        style.map('TButton',
                  background=[('disabled', '#555555'), ('active', button_hover), ('pressed', button_bg)],
                  foreground=[('disabled', '#888888'), ('active', '#000000')])

        # Configure TCombobox
        style.configure('TCombobox',
                       fieldbackground=entry_bg,
                       background=entry_bg,
                       foreground='#000000',
                       arrowcolor=fg_color,
                       borderwidth=1)
        style.map('TCombobox',
                 fieldbackground=[('readonly', entry_bg)],
                 selectbackground=[('readonly', entry_bg)],
                 selectforeground=[('readonly', '#000000')])

    def setup_ui(self):
        # Initialize status_var early (needed by refresh methods)
        self.status_var = tk.StringVar(value="Ready")

        # Main container
        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))

        # Configure grid weights
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)
        main_frame.columnconfigure(0, weight=1)
        main_frame.columnconfigure(1, weight=0)
        main_frame.rowconfigure(2, weight=1)

        # Host Controller frame
        host_frame = ttk.LabelFrame(main_frame, text="Host Controller", padding="5")
        host_frame.grid(row=0, column=0, sticky=(tk.W, tk.E), pady=(0, 10))

        ttk.Label(host_frame, text="Device:").grid(row=0, column=0, padx=5)
        self.host_device_label = ttk.Label(host_frame, text="VID:0x01EA PID:0xFAAA", width=30)
        self.host_device_label.grid(row=0, column=1, padx=5)

        ttk.Button(host_frame, text="Detect", command=self.detect_host_controller).grid(row=0, column=2, padx=5)
        ttk.Button(host_frame, text="Power ON", command=self.host_power_on).grid(row=0, column=3, padx=5)
        ttk.Button(host_frame, text="Power OFF", command=self.host_power_off).grid(row=0, column=4, padx=5)

        self.host_status_label = ttk.Label(host_frame, text="Not Connected", foreground="#f44336")
        self.host_status_label.grid(row=0, column=5, padx=10)

        # Auto-detect host controller on startup
        self.detect_host_controller()

        # Olea Head frame
        olea_frame = ttk.LabelFrame(main_frame, text="Olea Head", padding="5")
        olea_frame.grid(row=1, column=0, sticky=(tk.W, tk.E), pady=(0, 10))

        # Row 0: Device info and detect
        ttk.Label(olea_frame, text="Device:").grid(row=0, column=0, padx=5)
        self.olea_device_label = ttk.Label(olea_frame, text="VID:0x01EA PID:0x1235", width=30)
        self.olea_device_label.grid(row=0, column=1, padx=5)

        ttk.Button(olea_frame, text="Detect", command=self.detect_olea_head).grid(row=0, column=2, padx=5)

        self.olea_status_label = ttk.Label(olea_frame, text="Not Connected", foreground="#f44336")
        self.olea_status_label.grid(row=0, column=3, padx=10)

        # Row 1-2: Commands (stacked)
        self.btn_led_on = ttk.Button(olea_frame, text="LED ON", command=lambda: self.olea_cmd_led_en(True), width=10, state='disabled')
        self.btn_led_on.grid(row=1, column=0, padx=5, pady=(5, 0))
        self.btn_led_off = ttk.Button(olea_frame, text="LED OFF", command=lambda: self.olea_cmd_led_en(False), width=10, state='disabled')
        self.btn_led_off.grid(row=2, column=0, padx=5, pady=(0, 5))

        self.btn_cam_on = ttk.Button(olea_frame, text="Camera ON", command=lambda: self.olea_cmd_camera_en(True), width=15, state='disabled')
        self.btn_cam_on.grid(row=1, column=1, padx=5, pady=(5, 0))
        self.btn_cam_off = ttk.Button(olea_frame, text="Camera OFF", command=lambda: self.olea_cmd_camera_en(False), width=15, state='disabled')
        self.btn_cam_off.grid(row=2, column=1, padx=5, pady=(0, 5))

        self.btn_get_info = ttk.Button(olea_frame, text="Get Info", command=self.olea_cmd_get_info, width=10, state='disabled')
        self.btn_get_info.grid(row=1, column=2, rowspan=2, padx=5, pady=5)

        self.btn_test_all = ttk.Button(olea_frame, text="Test All", command=self.start_test_all, width=10)
        self.btn_test_all.grid(row=1, column=3, rowspan=2, padx=5, pady=5)

        # Row 3: Camera selection
        ttk.Label(olea_frame, text="Camera:").grid(row=3, column=0, padx=5, pady=(5, 0))
        self.camera_var = tk.StringVar()
        self.camera_combo = ttk.Combobox(olea_frame, textvariable=self.camera_var, width=30, state='readonly')
        self.camera_combo.grid(row=3, column=1, padx=5, pady=(5, 0))

        ttk.Button(olea_frame, text="Detect", command=self.refresh_cameras, width=10).grid(row=3, column=2, padx=5, pady=(5, 0))
        self.btn_cam_start = ttk.Button(olea_frame, text="Start", command=self.start_selected_camera, width=10, state='disabled')
        self.btn_cam_start.grid(row=3, column=3, padx=5, pady=(5, 0))
        self.btn_cam_stop = ttk.Button(olea_frame, text="Stop", command=self.stop_camera, width=10, state='disabled')
        self.btn_cam_stop.grid(row=3, column=4, padx=5, pady=(5, 0))

        self.camera_detected_label = ttk.Label(olea_frame, text="Not Detected", foreground="#f44336")
        self.camera_detected_label.grid(row=3, column=5, padx=10, pady=(5, 0))

        self.camera_status_label = ttk.Label(olea_frame, text="", foreground="#f44336")
        self.camera_status_label.grid(row=3, column=6, padx=5, pady=(5, 0))

        # Refresh cameras on startup
        #self.refresh_cameras()

        # Auto-detect Olea Head on startup
        #self.detect_olea_head()

        # Device Info frame (right side)
        info_frame = ttk.LabelFrame(main_frame, text="Device Info", padding="5")
        info_frame.grid(row=0, column=1, rowspan=5, sticky=(tk.N, tk.S, tk.E, tk.W), padx=(10, 0), pady=(0, 10))

        self.device_info_text = tk.Text(info_frame, height=30, width=50, bg='#2d2d2d', fg='#e0e0e0',
                                        font=('Consolas', 9), wrap=tk.WORD)
        self.device_info_text.grid(row=0, column=0, sticky=(tk.N, tk.S, tk.E, tk.W))
        self.device_info_text.insert(tk.END, "Click 'Get Info' to\nretrieve device info")

        # Camera display
        camera_frame = ttk.LabelFrame(main_frame, text="Camera Feed", padding="5")
        camera_frame.grid(row=2, column=0, sticky=(tk.W, tk.E, tk.N, tk.S), pady=(0, 10))
        camera_frame.columnconfigure(0, weight=1)
        camera_frame.rowconfigure(0, weight=1)

        self.camera_label = tk.Label(camera_frame, bg='#1e1e1e', borderwidth=2, relief='solid', width=640, height=480)
        self.camera_label.grid(row=0, column=0)

        # Info row with timestamp and clarity
        info_frame = ttk.Frame(camera_frame)
        info_frame.grid(row=1, column=0, sticky=(tk.W, tk.E), padx=5, pady=(2, 0))

        self.timestamp_label = ttk.Label(info_frame, text="", foreground="#ff4444", font=('Consolas', 10, 'bold'))
        self.timestamp_label.pack(side=tk.LEFT)

        self.clarity_label = ttk.Label(info_frame, text="", foreground="#4caf50", font=('Consolas', 10, 'bold'))
        self.clarity_label.pack(side=tk.LEFT, padx=(20, 0))

        # Serial Traffic Log frame
        log_frame = ttk.LabelFrame(main_frame, text="Serial Traffic", padding="5")
        log_frame.grid(row=3, column=0, sticky=(tk.W, tk.E), pady=(0, 10))
        log_frame.columnconfigure(0, weight=1)

        # Text widget for serial log with scrollbar
        log_scroll = ttk.Scrollbar(log_frame)
        log_scroll.grid(row=0, column=1, sticky=(tk.N, tk.S))

        self.serial_log = tk.Text(log_frame, height=6, width=70, bg='#2d2d2d', fg='#00ff00',
                                  font=('Consolas', 9), yscrollcommand=log_scroll.set)
        self.serial_log.grid(row=0, column=0, sticky=(tk.W, tk.E))
        log_scroll.config(command=self.serial_log.yview)

        # Clear button
        ttk.Button(log_frame, text="Clear", command=self.clear_serial_log, width=8).grid(row=1, column=0, pady=(5, 0), sticky=tk.W)

        # Status bar
        status_bar = tk.Label(main_frame, textvariable=self.status_var, relief=tk.SUNKEN, anchor=tk.W,
                             bg='#2d2d2d', fg='#e0e0e0', font=('Arial', 9), padx=5, pady=2)
        status_bar.grid(row=4, column=0, sticky=(tk.W, tk.E), pady=(5, 0))

    def log_serial(self, device, direction, data):
        """Log serial traffic to the log window"""
        timestamp = datetime.now().strftime("%H:%M:%S.%f")[:-3]
        arrow = "TX>" if direction == "tx" else "RX<"

        # Format data as hex if bytes, otherwise as string
        if isinstance(data, bytes):
            data_str = data.hex(' ').upper()
        else:
            data_str = str(data).strip()

        log_entry = f"[{timestamp}] {device} {arrow} {data_str}\n"
        self.serial_log.insert(tk.END, log_entry)
        self.serial_log.see(tk.END)  # Auto-scroll to bottom

    def clear_serial_log(self):
        """Clear the serial traffic log"""
        self.serial_log.delete(1.0, tk.END)

    def get_all_camera_devices(self):
        """Get list of all video input devices using WMI"""
        cameras = []
        try:
            # Query WMI for all video input devices (imaging devices)
            cmd = 'powershell -Command "Get-WmiObject Win32_PnPEntity | Where-Object { $_.PNPClass -eq \'Camera\' -or $_.PNPClass -eq \'Image\' } | Select-Object -ExpandProperty Name"'
            result = subprocess.run(cmd, capture_output=True, text=True, shell=True, timeout=5)
            if result.returncode == 0:
                for line in result.stdout.strip().split('\n'):
                    if line.strip():
                        cameras.append(line.strip())
        except Exception:
            pass
        return cameras

    def refresh_cameras(self):
        """Refresh the list of available cameras, filtering for USB Camera devices"""
        self.available_cameras = []

        # Get all camera device names from WMI
        all_camera_names = self.get_all_camera_devices()
        print(f"All camera devices found: {all_camera_names}")

        # Match USB cameras by name and assign index based on WMI order
        for i, cam_name in enumerate(all_camera_names):
            print(f"Camera at index {i}: {cam_name}")
            if "USB CAMERA" in cam_name.upper():
                self.available_cameras.append({'index': i, 'name': cam_name})
                print(f"Added USB Camera: {cam_name} at index {i}")

        camera_list = [cam['name'] for cam in self.available_cameras]
        self.camera_combo['values'] = camera_list

        if camera_list:
            self.camera_combo.current(0)
            self.camera_detected_label.config(text="Detected", foreground="#4caf50")
            self.status_var.set(f"Found {len(camera_list)} USB Camera(s)")
            # Enable camera buttons
            self.btn_cam_start.config(state='normal')
            self.btn_cam_stop.config(state='normal')
        else:
            self.camera_detected_label.config(text="Not Detected", foreground="#f44336")
            self.status_var.set("No USB Camera found")
            # Disable camera buttons
            self.btn_cam_start.config(state='disabled')
            self.btn_cam_stop.config(state='disabled')

    def start_selected_camera(self):
        """Capture a single image from the camera selected in the dropdown"""
        if not self.available_cameras:
            messagebox.showerror("Error", "No cameras available!")
            return

        selection_idx = self.camera_combo.current()
        if selection_idx < 0:
            messagebox.showerror("Error", "Please select a camera!")
            return

        camera_index = self.available_cameras[selection_idx]['index']
        self.start_camera(camera_index)

    def detect_host_controller(self):
        """Detect and connect to host controller by VID/PID"""
        # Close existing connection if any
        if self.host_controller_conn and self.host_controller_conn.is_open:
            self.host_controller_conn.close()
            self.host_controller_conn = None

        # Search for device with matching VID/PID
        ports = serial.tools.list_ports.comports()
        for port in ports:
            if port.vid == self.HOST_CONTROLLER_VID and port.pid == self.HOST_CONTROLLER_PID:
                try:
                    self.host_controller_conn = serial.Serial(
                        port=port.device,
                        baudrate=9600,
                        timeout=2
                    )
                    self.host_status_label.config(text="Connected", foreground="#4caf50")
                    self.host_device_label.config(text=f"{port.device} - {port.description}")
                    self.status_var.set(f"Host controller connected on {port.device}")
                    return
                except Exception as e:
                    self.status_var.set(f"Host controller error: {str(e)}")

        # Device not found
        self.host_status_label.config(text="Not Connected", foreground="#f44336")
        self.host_device_label.config(text="VID:0x01EA PID:0xFAAA")
        self.status_var.set("Host controller not found")

    def host_power_on(self):
        """Send power on command to host controller"""
        if not self.host_controller_conn or not self.host_controller_conn.is_open:
            messagebox.showerror("Error", "Host controller not connected!")
            return

        try:
            command = "#USB:1111,1111,0000,0000\n"
            self.host_controller_conn.write(command.encode())
            self.log_serial("HOST", "tx", command.strip())
            # Read any response
            response = self.host_controller_conn.readline()
            if response:
                self.log_serial("HOST", "rx", response.decode('utf-8', errors='replace').strip())
            self.status_var.set("Host Controller: Power ON sent")
        except Exception:
            self.detect_host_controller()
            self.status_var.set("Power ON failed, re-detecting host controller")

    def host_power_off(self):
        """Send power off command to host controller"""
        if not self.host_controller_conn or not self.host_controller_conn.is_open:
            messagebox.showerror("Error", "Host controller not connected!")
            return

        try:
            command = "#USB:0000,0000,0000,0000\n"
            self.host_controller_conn.write(command.encode())
            self.log_serial("HOST", "tx", command.strip())
            # Read any response
            response = self.host_controller_conn.readline()
            if response:
                self.log_serial("HOST", "rx", response.decode('utf-8', errors='replace').strip())
            self.status_var.set("Host Controller: Power OFF sent")

            # Reset Olea Head to not detected
            self.olea_head_port = None
            self.olea_status_label.config(text="Not Detected", foreground="#f44336")
            self.olea_device_label.config(text="VID:0x01EA PID:0x1235")
            self.btn_led_on.config(state='disabled')
            self.btn_led_off.config(state='disabled')
            self.btn_cam_on.config(state='disabled')
            self.btn_cam_off.config(state='disabled')
            self.btn_get_info.config(state='disabled')

            # Reset camera to not detected
            self.reset_camera_state()
        except Exception:
            self.detect_host_controller()
            self.status_var.set("Power OFF failed, re-detecting host controller")

    def detect_olea_head(self):
        """Detect Olea Head by VID/PID and verify with get_info command"""
        self.olea_head_port = None

        # Search for all devices with matching VID/PID
        ports = serial.tools.list_ports.comports()
        matching_ports = [p for p in ports if p.vid == self.OLEA_HEAD_VID and p.pid == self.OLEA_HEAD_PID]

        # Try each matching port and verify with get_info command
        for port in matching_ports:
            conn = None
            try:
                conn = serial.Serial(
                    port=port.device,
                    baudrate=115200,
                    timeout=1,
                    write_timeout=0.5
                )
                tx_data = bytes([self.HEAD_CMD_DEVICE_INFO, 0x0])
                conn.write(tx_data)
                conn.flush()
                response = conn.read(ctypes.sizeof(device_info_t))
                print(f"Testing port {port.device}, received {len(response)} bytes. excpected {ctypes.sizeof(device_info_t)} bytes.")

                if len(response) >= ctypes.sizeof(device_info_t):
                    # print the device name from the response for debugging
                    c_info = device_info_t.from_buffer_copy(response)
                    print(f"Received device info response: device_name={c_info.device_name}, firmware_version={c_info.firmware_version_major}.{c_info.firmware_version_minor}.{c_info.firmware_version_patch}, serial_number={(c_info.serial_number_h << 64) | c_info.serial_number_l:x}, hardware_version={c_info.hardware_version}")

                    print(f'Olea head found on port {port.device}')
                    # Got valid response - this is the correct port
                    conn.close()
                    self.olea_head_port = port.device
                    self.olea_status_label.config(text="Detected", foreground="#4caf50")
                    self.olea_device_label.config(text=f"{port.device} - {port.description}")
                    self.status_var.set(f"Olea Head detected on {port.device}")
                    # Enable buttons
                    self.btn_led_on.config(state='normal')
                    self.btn_led_off.config(state='normal')
                    self.btn_cam_on.config(state='normal')
                    self.btn_cam_off.config(state='normal')
                    self.btn_get_info.config(state='normal')
                    return
            except Exception:
                return False
            finally:
                # Always close connection
                if conn and conn.is_open:
                    try:
                        conn.close()
                    except Exception:
                        False

        # Device not found - disable buttons
        self.olea_status_label.config(text="Not Detected", foreground="#f44336")
        self.olea_device_label.config(text="VID:0x01EA PID:0x1235")
        self.btn_led_on.config(state='disabled')
        self.btn_led_off.config(state='disabled')
        self.btn_cam_on.config(state='disabled')
        self.btn_cam_off.config(state='disabled')
        self.btn_get_info.config(state='disabled')
        self.reset_camera_state()
        self.status_var.set("Olea Head not found")

    def olea_send_command(self, cmd_byte, write=False, data=None, retries=3):
        """Send a command to Olea Head (opens and closes connection for each transaction)

        Args:
            cmd_byte: Command byte to send
            write: If True, send 0x1 (write flag), if False send 0x0 (read flag)
            data: Optional data bytes to send after command
            retries: Number of retry attempts (default 3)
        """
        if not self.olea_head_port:
            self.status_var.set("Error: Olea Head not detected")
            return None

        for attempt in range(retries):
            conn = None
            try:
                # Open connection
                conn = serial.Serial(
                    port=self.olea_head_port,
                    baudrate=115200,
                    timeout=2,
                    write_timeout=0.5,
                )

                rw_flag = 0x01 if write else 0x00
                if data is not None:
                    tx_data = bytes([cmd_byte, rw_flag]) + data
                else:
                    tx_data = bytes([cmd_byte, rw_flag])
                conn.write(tx_data)
                self.log_serial("OLEA", "tx", tx_data)

                # Store connection temporarily for read operations
                self.olea_head_conn = conn
                return True
            except Exception:
                if conn and conn.is_open:
                    try:
                        conn.close()
                    except Exception:
                        pass
                # Wait 1 second before retry (except on last attempt)
                if attempt < retries - 1:
                    time.sleep(1)

        # All retries failed - re-detect Olea Head
        self.detect_olea_head()
        self.status_var.set(f"Command failed after {retries} attempts, re-detecting Olea Head")
        return None

    def olea_close_connection(self):
        """Close the Olea Head connection after a transaction"""
        if self.olea_head_conn and self.olea_head_conn.is_open:
            try:
                self.olea_head_conn.close()
            except Exception:
                pass
        self.olea_head_conn = None

    def olea_cmd_led_en(self, enable):
        """Send LED enable/disable command (0x02)"""
        if enable:
            # Send LED config first when turning on
            config = led_config_t.led_config_all()
            config_data = bytes(config)
            if not self.olea_send_command(self.HEAD_CMD_LED_CONFIG, write=True, data=config_data):
                return
            self.olea_close_connection()

        # Send command with uint16 enable value (little-endian)
        data = (1 if enable else 0).to_bytes(2, 'little')
        if self.olea_send_command(self.HEAD_CMD_LED_EN, write=True, data=data):
            state = "ON" if enable else "OFF"
            self.status_var.set(f"Olea Head: LED {state}")
        self.olea_close_connection()

    def olea_cmd_camera_en(self, enable):
        """Send camera enable/disable command (0x03)"""
        # Send command with uint16 enable value (little-endian)
        data = (1 if enable else 0).to_bytes(2, 'little')
        if self.olea_send_command(self.HEAD_CMD_CAMERA_EN, write=True, data=data):
            state = "ON" if enable else "OFF"
            self.status_var.set(f"Olea Head: Camera {state}")
            if not enable:
                self.reset_camera_state()
        self.olea_close_connection()

    def get_hardware_revision_str(self, val):
        """Convert hardware version number to string format (e.g., A.1)"""
        try:
            top_val = val // 100
            minor_val = val % 100
            if top_val > 0:
                major_letter = chr(0x40 + top_val)
                return f'{major_letter}.{minor_val}'
        except Exception:
            pass
        return "x.x"

    def olea_cmd_get_info(self):
        """Send get device info command (0x05) and read response"""
        if not self.olea_head_port:
            messagebox.showerror("Error", "Olea Head not detected!")
            return

        # Device name mapping
        device_name_dict = {
            0: 'Olea_Hub',
            1: 'Olea_Head',
        }

        conn = None
        try:
            # Open connection
            conn = serial.Serial(
                port=self.olea_head_port,
                baudrate=115200,
                timeout=3,
            )

            tx_data = bytes([self.HEAD_CMD_DEVICE_INFO, 0x0])
            self.log_serial("OLEA", "tx", tx_data)
            conn.write(tx_data)

            # Read response (device_info_t struct size)
            response = conn.read(ctypes.sizeof(device_info_t))

            if len(response) > 0:
                self.log_serial("OLEA", "rx", response)

            if len(response) >= ctypes.sizeof(device_info_t):
                # Decode using ctypes structure
                c_info = device_info_t.from_buffer_copy(response)

                # Build device info dictionary
                device_info = {
                    'device': device_name_dict.get(c_info.device_name, f'Unknown({c_info.device_name})'),
                    'serial_number': f'{hex((c_info.serial_number_h << 64) | c_info.serial_number_l)[2:]}',
                    'firmware_version': f'{c_info.firmware_version_major}.{c_info.firmware_version_minor}.{c_info.firmware_version_patch}',
                    'hardware_version': self.get_hardware_revision_str(c_info.hardware_version),
                }

                # Update device info text box
                self.device_info_text.delete(1.0, tk.END)
                self.device_info_text.insert(tk.END, f"Device: {device_info['device']}\n")
                self.device_info_text.insert(tk.END, f"Hardware Version: {device_info['hardware_version']}\n")
                self.device_info_text.insert(tk.END, f"Firmware Version: {device_info['firmware_version']}\n")
                self.device_info_text.insert(tk.END, f"Serial Number: {device_info['serial_number']}\n")

                self.status_var.set(f"Device info retrieved: {device_info['device']}")
            else:
                self.status_var.set("Olea Head: No response or incomplete data")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to get info: {str(e)}")
        finally:
            # Close connection
            if conn and conn.is_open:
                conn.close()

    def start_camera(self, camera_index=0):
        """Open camera and start capturing images every second"""
        # Stop existing camera if running
        if self.camera and self.camera.isOpened():
            self.camera.release()

        self.camera = cv2.VideoCapture(camera_index, cv2.CAP_DSHOW)
        if not self.camera.isOpened():
            messagebox.showerror("Error", f"Could not open camera {camera_index}!")
            self.status_var.set("Camera not available")
            self.camera_status_label.config(text="Failed", foreground="#f44336")
            self.camera = None
            return

        # Set camera resolution to 640x480
        self.camera.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
        self.camera.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)

        self.camera_running = True
        self.camera_status_label.config(text="Running", foreground="#4caf50")
        self.status_var.set(f"Camera {camera_index} started")
        self.capture_image()

    def capture_image(self):
        """Capture a single image and schedule the next capture"""
        if not self.camera_running or not self.camera:
            return

        ret, frame = self.camera.read()
        if not ret or frame is None:
            self.camera_status_label.config(text="Error", foreground="#f44336")
            self.status_var.set("Failed to capture image")
            self.camera_running = False
            return

        # Verify frame size and resize preserving aspect ratio
        h, w = frame.shape[:2]
        if w != 640 or h != 480:
            scale = min(640 / w, 480 / h)
            new_w = int(w * scale)
            new_h = int(h * scale)
            frame = cv2.resize(frame, (new_w, new_h))

        # Update timestamp label
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        self.timestamp_label.config(text=timestamp)

        # Calculate image clarity using Laplacian variance
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        laplacian_var = cv2.Laplacian(gray, cv2.CV_64F).var()
        clarity_pct = min(100, (laplacian_var / 500) * 100)
        self.clarity_label.config(text=f"Clarity: {clarity_pct:.1f}%")

        # Convert BGR to RGB and display
        frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        img = Image.fromarray(frame_rgb)
        photo = ImageTk.PhotoImage(image=img)
        self.camera_label.config(image=photo)
        self.camera_label.image = photo

        # Schedule next capture in 1 second
        if self.camera_running:
            self.root.after(100, self.capture_image)

    def reset_camera_state(self):
        """Reset camera UI to not detected state"""
        self.camera_running = False
        if self.camera and self.camera.isOpened():
            self.camera.release()
        self.camera = None
        self.available_cameras = []
        self.camera_combo['values'] = []
        self.camera_combo.set('')
        self.camera_detected_label.config(text="Not Detected", foreground="#f44336")
        self.camera_status_label.config(text="", foreground="#f44336")
        self.btn_cam_start.config(state='disabled')
        self.btn_cam_stop.config(state='disabled')
        self.timestamp_label.config(text="")
        self.clarity_label.config(text="")

    def stop_camera(self):
        """Stop the periodic camera capture and release device"""
        self.camera_running = False
        if self.camera and self.camera.isOpened():
            self.camera.release()
        self.camera = None
        self.camera_status_label.config(text="Stopped", foreground="#f44336")
        self.status_var.set("Camera stopped")

    def start_test_all(self):
        """Start the full test sequence in a background thread"""
        self.btn_test_all.config(state='disabled')
        self.device_info_text.delete(1.0, tk.END)
        self.device_info_text.insert(tk.END, "=== TEST ALL SEQUENCE ===\n\n")
        # Clear camera feed
        self.camera_label.config(image='')
        self.camera_label.image = None
        self.timestamp_label.config(text="")
        self.clarity_label.config(text="")
        thread = threading.Thread(target=self.test_all_sequence, daemon=True)
        thread.start()

    def test_log(self, message, status=None):
        """Log a message to device info panel (thread-safe)"""
        def update():
            if status == "OK":
                self.device_info_text.insert(tk.END, f"{message} ... OK\n")
            elif status == "FAIL":
                self.device_info_text.insert(tk.END, f"{message} ... FAIL\n")
            else:
                self.device_info_text.insert(tk.END, f"{message}\n")
            self.device_info_text.see(tk.END)
        self.root.after(0, update)

    def test_all_sequence(self):
        """Run the full test sequence"""
        try:
            # Step 1: Power OFF
            self.test_log("Step 1: Power OFF")
            if self.host_controller_conn and self.host_controller_conn.is_open:
                try:
                    command = "#USB:0000,0000,0000,0000\n"
                    self.host_controller_conn.write(command.encode())
                    self.test_log("  Power OFF command sent", "OK")
                except Exception as e:
                    self.test_log(f"  Power OFF failed: {e}", "FAIL")
                    self.test_cleanup()
                    return
            else:
                self.test_log("  Host controller not connected", "FAIL")
                self.test_cleanup()
                return

            # Wait 2 seconds
            self.test_log("  Waiting 2 seconds...")
            time.sleep(2)

            # Step 2: Power ON
            self.test_log("\nStep 2: Power ON")
            try:
                command = "#USB:1111,1111,0000,0000\n"
                self.host_controller_conn.write(command.encode())
                self.test_log("  Power ON command sent", "OK")
            except Exception as e:
                self.test_log(f"  Power ON failed: {e}", "FAIL")
                self.test_cleanup()
                return

            # Wait 3 seconds
            self.test_log("  Waiting 3 seconds...")
            time.sleep(3)

            # Step 3: Detect Olea Head (5 second timeout)
            self.test_log("\nStep 3: Detect Olea Head (5s timeout)")
            olea_detected = False
            start_time = time.time()
            while time.time() - start_time < 5:
                # Call detect function
                self.detect_olea_head()
                time.sleep(1)
                print(f"Checking olea_head_port: {self.olea_head_port}")
                if self.olea_head_port:
                    olea_detected = True
                    break

            if not olea_detected:
                self.test_log("  Olea Head not detected", "FAIL")
                self.test_cleanup()
                return
            self.test_log(f"  Olea Head found on {self.olea_head_port}", "OK")

            # Step 4: Get Info
            self.test_log("\nStep 4: Get Device Info")
            device_name_dict = {0: 'Olea_Hub', 1: 'Olea_Head'}
            try:
                conn = serial.Serial(port=self.olea_head_port, baudrate=115200, timeout=3)
                tx_data = bytes([self.HEAD_CMD_DEVICE_INFO, 0x0])
                conn.write(tx_data)
                response = conn.read(ctypes.sizeof(device_info_t))
                conn.close()
                if len(response) >= ctypes.sizeof(device_info_t):
                    c_info = device_info_t.from_buffer_copy(response)
                    device_name = device_name_dict.get(c_info.device_name, f'Unknown({c_info.device_name})')
                    fw_version = f'{c_info.firmware_version_major}.{c_info.firmware_version_minor}.{c_info.firmware_version_patch}'
                    hw_version = self.get_hardware_revision_str(c_info.hardware_version)
                    serial_num = f'{hex((c_info.serial_number_h << 64) | c_info.serial_number_l)[2:]}'
                    self.test_log("  Device info received", "OK")
                    self.test_log(f"    Device: {device_name}")
                    self.test_log(f"    HW Version: {hw_version}")
                    self.test_log(f"    FW Version: {fw_version}")
                    self.test_log(f"    Serial: {serial_num}")
                else:
                    self.test_log("  No response from device", "FAIL")
                    self.test_cleanup()
                    return
            except Exception as e:
                self.test_log(f"  Get Info failed: {e}", "FAIL")
                self.test_cleanup()
                return

            # Step 5: LED ON
            self.test_log("\nStep 5: LED ON")
            try:
                conn = serial.Serial(port=self.olea_head_port, baudrate=115200, timeout=3)
                # Send LED config first
                config = led_config_t.led_config_all()
                config_data = bytes(config)
                conn.write(bytes([self.HEAD_CMD_LED_CONFIG, 0x01]) + config_data)
                time.sleep(0.1)
                # Send LED ON
                led_on_data = (1).to_bytes(2, 'little')
                conn.write(bytes([self.HEAD_CMD_LED_EN, 0x01]) + led_on_data)
                conn.close()
                self.test_log("  LED ON command sent", "OK")
            except Exception as e:
                self.test_log(f"  LED ON failed: {e}", "FAIL")
                self.test_cleanup()
                return

            # Step 6: Camera ON (Olea Head camera enable)
            self.test_log("\nStep 6: Camera ON (Olea Head)")
            try:
                conn = serial.Serial(port=self.olea_head_port, baudrate=115200, timeout=3)
                cam_on_data = (1).to_bytes(2, 'little')
                conn.write(bytes([self.HEAD_CMD_CAMERA_EN, 0x01]) + cam_on_data)
                conn.close()
                self.test_log("  Camera ON command sent", "OK")
            except Exception as e:
                self.test_log(f"  Camera ON failed: {e}", "FAIL")
                self.test_cleanup()
                return

            # Step 7: Detect USB Camera (10 second timeout)
            self.test_log("\nStep 7: Detect USB Camera (10s timeout)")
            camera_detected = False
            camera_index = None
            start_time = time.time()
            while time.time() - start_time < 10:
                all_camera_names = self.get_all_camera_devices()
                for i, name in enumerate(all_camera_names):
                    if "USB CAMERA" in name:
                        camera_index = i
                        camera_detected = True
                        break
                if camera_detected:
                    break
                time.sleep(1)

            if not camera_detected:
                self.test_log("  USB Camera not detected", "FAIL")
                self.test_cleanup()
                return
            self.test_log(f"  USB Camera found at index {camera_index}", "OK")

            # Step 8: Start camera and take snapshot
            self.test_log("\nStep 8: Start Camera & Snapshot")
            try:
                cap = cv2.VideoCapture(camera_index, cv2.CAP_DSHOW)
                if not cap.isOpened():
                    self.test_log("  Failed to open camera", "FAIL")
                    self.test_cleanup()
                    return
                # Set camera resolution to 640x480
                cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
                cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)

                # Take two frames, use the second one (better exposure/focus)
                cap.read()  # Discard first frame

                ret, frame = cap.read()  # Use second frame
                cap.release()
                if ret and frame is not None:
                    h, w = frame.shape[:2]
                    self.test_log(f"  Frame size: {w}x{h}")
                    if w != 640 or h != 480:
                        self.test_log(f"  WARNING: Frame is not 640x480", "FAIL")
                    # Display snapshot on UI
                    self.display_test_snapshot(frame)
                    self.test_log("  Snapshot displayed", "OK")
                else:
                    self.test_log("  Failed to capture frame", "FAIL")
                    self.test_cleanup()
                    return
            except Exception as e:
                self.test_log(f"  Camera capture failed: {e}", "FAIL")
                self.test_cleanup()
                return

            # Step 9: Cleanup - Camera OFF, LED OFF, Power OFF
            self.test_log("\nStep 9: Cleanup")
            self.test_cleanup(show_log=True)

            self.test_log("\n=== TEST COMPLETE ===")
            self.test_log("All tests passed!", "OK")

        except Exception as e:
            self.test_log(f"\nUnexpected error: {e}", "FAIL")
            self.test_cleanup()
        finally:
            self.root.after(0, lambda: self.btn_test_all.config(state='normal'))

    def display_test_snapshot(self, frame):
        """Display a snapshot on the camera feed UI with timestamp and clarity (thread-safe)"""
        # Resize frame preserving aspect ratio
        h, w = frame.shape[:2]
        scale = min(640 / w, 480 / h)
        new_w = int(w * scale)
        new_h = int(h * scale)
        frame_resized = cv2.resize(frame, (new_w, new_h))

        # Calculate clarity
        gray = cv2.cvtColor(frame_resized, cv2.COLOR_BGR2GRAY)
        laplacian_var = cv2.Laplacian(gray, cv2.CV_64F).var()
        clarity_pct = min(100, (laplacian_var / 500) * 100)

        # Convert BGR to RGB
        frame_rgb = cv2.cvtColor(frame_resized, cv2.COLOR_BGR2RGB)

        # Convert to PIL Image
        img = Image.fromarray(frame_rgb)

        # Get timestamp
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        def update_ui():
            # Convert to PhotoImage
            photo = ImageTk.PhotoImage(image=img)
            self.camera_label.config(image=photo)
            self.camera_label.image = photo
            # Update labels
            self.timestamp_label.config(text=timestamp)
            self.clarity_label.config(text=f"Clarity: {clarity_pct:.1f}%")

        self.root.after(0, update_ui)

    def test_cleanup(self, show_log=False):
        """Cleanup after test - turn off camera, LED, and power"""
        try:
            if self.olea_head_port:
                conn = serial.Serial(port=self.olea_head_port, baudrate=115200, timeout=1)
                # Camera OFF
                cam_off_data = (0).to_bytes(2, 'little')
                conn.write(bytes([self.HEAD_CMD_CAMERA_EN, 0x01]) + cam_off_data)
                if show_log:
                    self.test_log("  Camera OFF", "OK")
                time.sleep(0.1)
                # LED OFF
                led_off_data = (0).to_bytes(2, 'little')
                conn.write(bytes([self.HEAD_CMD_LED_EN, 0x01]) + led_off_data)
                if show_log:
                    self.test_log("  LED OFF", "OK")
                conn.close()
        except Exception as e:
            if show_log:
                self.test_log(f"  Olea cleanup error: {e}", "FAIL")

        try:
            if self.host_controller_conn and self.host_controller_conn.is_open:
                command = "#USB:0000,0000,0000,0000\n"
                self.host_controller_conn.write(command.encode())
                if show_log:
                    self.test_log("  Power OFF", "OK")
        except Exception as e:
            if show_log:
                self.test_log(f"  Power OFF error: {e}", "FAIL")

    def cleanup(self):
        """Cleanup resources before closing"""
        self.camera_running = False
        if self.camera and self.camera.isOpened():
            self.camera.release()
        self.camera = None

        if self.host_controller_conn and self.host_controller_conn.is_open:
            self.host_controller_conn.close()

        # Send power off commands to Olea Head before closing
        if self.olea_head_port:
            conn = None
            try:
                conn = serial.Serial(
                    port=self.olea_head_port,
                    baudrate=115200,
                    timeout=1,
                )
                # Turn off LED
                led_off_data = (0).to_bytes(2, 'little')
                conn.write(bytes([self.HEAD_CMD_LED_EN, 0x01]) + led_off_data)
                # Turn off Camera
                cam_off_data = (0).to_bytes(2, 'little')
                conn.write(bytes([self.HEAD_CMD_CAMERA_EN, 0x01]) + cam_off_data)
            except Exception:
                pass
            finally:
                if conn and conn.is_open:
                    try:
                        conn.close()
                    except Exception:
                        pass

        cv2.destroyAllWindows()


def main():
    root = tk.Tk()
    app = CameraLEDController(root)

    # Handle window close
    def on_closing():
        app.cleanup()
        root.destroy()

    root.protocol("WM_DELETE_WINDOW", on_closing)
    root.mainloop()


if __name__ == "__main__":
    main()
