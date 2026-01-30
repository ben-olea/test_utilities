@echo off
echo Building Olea Head Controller executable...
echo.

REM Use system Python
where python >nul 2>&1
if %errorlevel% neq 0 (
    echo ERROR: Python not found in PATH
    pause
    exit /b 1
)

REM Install dependencies
echo Installing dependencies...
python -m pip install pyinstaller pillow --quiet

REM Create icon if it doesn't exist
if not exist camera_icon.ico (
    echo Creating icon...
    python create_icon.py
)

REM Build the executable with no console window and icon
echo Building executable...
python -m PyInstaller --onefile --noconsole --icon=camera_icon.ico --name "Olea Head Controller" camera_led_control.py

echo.
echo Build complete! Executable is in the 'dist' folder.
pause
