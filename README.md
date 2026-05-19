# LingKeStressTest

Quectel Radar Stress Testing Toolset - Automate radar dot-trace testing and data collection for vehicle radar systems.

## Overview

LingKeStressTest is a comprehensive testing automation suite for Quectel Radar modules. It provides tools for:

- **Automated Radar Testing**: Automate the Quectel Radar Update Tool workflow for dot-trace testing
- **Video Recording**: Capture synchronized camera footage during radar testing
- **Log Collection**: Automatically collect and organize test results and logs
- **Camera Diagnostics**: Detect and diagnose available video capture devices

## Features

✅ Automated UI automation for Quectel Radar Update Tool  
✅ DirectShow camera capture with ffmpeg  
✅ Synchronized video and radar dot-trace data collection  
✅ Intelligent log file collection and organization  
✅ Camera device detection and diagnostics  

## Project Structure

```
├── radar_dot_trace_automation.py    # Automate radar update tool workflow
├── camera_record.py                 # DirectShow camera recording
├── case_log_collector.py            # Integrated test case log collector
├── diagnose_camera.py               # Camera device diagnostics
├── README.md                        # This file
└── .gitignore                       # Git ignore rules
```

## Requirements

### System Requirements
- Windows OS (DirectShow support)
- Python 3.8+
- Quectel Radar Update Tool V1.8.3+

### Python Dependencies
```
pywinauto>=0.9.3        # UI automation
imageio-ffmpeg>=0.4.8   # FFmpeg integration
opencv-python>=4.5.0    # Camera diagnostics
```

Install dependencies:
```bash
pip install pywinauto imageio-ffmpeg opencv-python
```

## Usage

### 1. Diagnose Available Cameras

Check available camera devices and their status:

```bash
python diagnose_camera.py
```

Output shows camera index availability and frame brightness levels.

### 2. Record Camera Video

Record video from a DirectShow camera device:

```bash
python camera_record.py -o video.mp4
```

**Options:**
- `-d, --device`: Camera device name (default: "RGB Camera")
- `-o, --output`: Output video file path
- `-r, --resolution`: Video resolution WxH (default: 1280x720)
- `-f, --fps`: Frames per second (default: 30)
- `-t, --timeout`: Recording timeout in seconds

### 3. Automate Radar Dot-Trace Testing

Run automated radar testing with the Update Tool:

```bash
python radar_dot_trace_automation.py
```

Monitors the radar update tool's progress and logs results.

### 4. Run Complete Test Case with Log Collection

Collect integrated test data including video and dot-trace logs:

```bash
python case_log_collector.py -o test_results/
```

**Options:**
- `-o, --output`: Output directory for test results
- `-c, --cases`: Number of test cases to run
- `--camera-device`: Camera device name
- `--camera-timeout`: Camera recording timeout

This script will:
- Launch the Quectel Radar Update Tool
- Start camera recording
- Collect dot-trace logs
- Organize results in timestamped directories
- Validate output file sizes (minimum thresholds)

## Configuration

### Radar Update Tool Path

Edit the `EXE_PATH` constant in the scripts to match your installation:

```python
EXE_PATH = r"F:\Firmware\Quectel_Radar_Update_Tool_V1.8.3\...exe"
```

### Camera Device

Default camera device is "RGB Camera". List available devices:

```bash
ffmpeg -list_devices true -f dshow -i dummy
```

## Output

Test results are organized by timestamp:

```
test_results/
├── 2024-01-15_10-30-45/
│   ├── video.mp4
│   ├── dot_trace_001.csv
│   ├── dot_trace_002.csv
│   └── test_log.txt
```

## Author

Kawhi.He

## License

Internal Use Only