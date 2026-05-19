"""
Camera recording script using ffmpeg DirectShow capture.

Author: Kawhi.He
"""

import argparse
import os
import re
import subprocess
from datetime import datetime

from imageio_ffmpeg import get_ffmpeg_exe


DEFAULT_CAMERA_DEVICE = "RGB Camera"


def list_dshow_video_devices(ffmpeg_exe: str) -> list[str]:
    """
    List DirectShow video capture device names.

    Args:
        ffmpeg_exe (str): ffmpeg executable path.

    Returns:
        list[str]: Available video device names.
    """
    cmd = [ffmpeg_exe, "-hide_banner", "-list_devices", "true", "-f", "dshow", "-i", "dummy"]
    result = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="ignore", check=False)

    devices = []
    for line in result.stderr.splitlines():
        if "(video)" not in line:
            continue
        match = re.search(r'"(.+?)"', line)
        if match:
            devices.append(match.group(1))
    return devices


def record_camera(duration: int = 5, output_dir: str | None = None, device_name: str | None = None) -> bool:
    """
    Record camera video to MP4 by ffmpeg DirectShow.

    Args:
        duration (int): Duration of recording in seconds.
        output_dir (str | None): Output directory path.
        device_name (str | None): DirectShow camera name. Uses first video device when not provided.

    Returns:
        bool: True if recording succeeded, otherwise False.
    """
    if output_dir is None:
        output_dir = os.path.dirname(os.path.abspath(__file__))
    os.makedirs(output_dir, exist_ok=True)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_file = os.path.join(output_dir, f"camera_record_{timestamp}.mp4")

    ffmpeg_exe = get_ffmpeg_exe()
    selected_device = device_name if device_name else DEFAULT_CAMERA_DEVICE

    print(f"Using camera: {selected_device}")
    print(f"Output file: {output_file}")

    video_size = "640x480"
    framerate = 15
    print(f"Using mode: {video_size} @ {framerate}fps")
    ffmpeg_norm = ffmpeg_exe.replace("\\", "/")
    ff_cmd = (
        f'& "{ffmpeg_norm}" -y -hide_banner -f dshow '
        f'-thread_queue_size 512 -rtbufsize 256M -vcodec mjpeg '
        f'-framerate {framerate} -video_size {video_size} -i "video={selected_device}" '
        f'-t {duration} -c:v libx264 -preset ultrafast -pix_fmt yuv420p '
        f'-movflags +faststart "{output_file}"'
    )

    result = subprocess.run(["powershell", "-Command", ff_cmd], check=False)
    if result.returncode != 0:
        print("Error: ffmpeg recording failed")
        devices = list_dshow_video_devices(ffmpeg_exe)
        if devices:
            print("Available devices:")
            for item in devices:
                print(f"- {item}")
        return False

    file_size = os.path.getsize(output_file) if os.path.exists(output_file) else 0
    if file_size <= 0:
        print("Error: Output file is empty")
        return False

    print(f"Recording completed, size={file_size} bytes")
    print(f"Video saved to: {output_file}")
    return True


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Record camera video by ffmpeg")
    parser.add_argument("--duration", type=int, default=5, help="Recording duration in seconds")
    parser.add_argument("--device", default=None, help="DirectShow video device name")
    args = parser.parse_args()

    record_camera(duration=args.duration, device_name=args.device)
