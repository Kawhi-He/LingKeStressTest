"""
Case-based log collector for Quectel radar dot-trace and camera recording.

Author: Kawhi.He
"""

import argparse
import re
import shutil
import subprocess
import sys
import threading
import time
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

from imageio_ffmpeg import get_ffmpeg_exe
from pywinauto.application import Application
from pywinauto.findwindows import ElementNotFoundError

EXE_PATH = r"F:\Firmware\Quectel_Radar_Update_Tool_V1.8.3\Quectel_Radar_Update_Tool_V1.8.3\Quectel_Radar_Update_Tool_V1.8.3.exe"
SUCCESS_LOG = "初始化LIN1成功!"
VIDEO_MIN_SIZE = 200 * 1024
CSV_MIN_SIZE = 100 * 1024
VIDEO_EXT = ".mp4"
DEFAULT_CAMERA_DEVICE = "RGB Camera"


@dataclass
class RecorderResult:
    """
    Camera recorder execution result.

    Args:
        output_file (Path): Generated video file path.
        frame_count (int): Number of frames written.
        error (str | None): Error message when recording fails.

    Returns:
        None
    """

    output_file: Path
    frame_count: int
    error: str | None


def log(message: str) -> None:
    """
    Print runtime progress message.

    Args:
        message (str): Message to print.

    Returns:
        None
    """
    print(message, flush=True)


def wait_for_window(app: Application, timeout: int = 30):
    """
    Wait for the main window after process launch.

    Args:
        app (Application): Launched pywinauto application instance.
        timeout (int): Maximum wait time in seconds.

    Returns:
        WindowSpecification: The first visible ready top window.

    Raises:
        TimeoutError: If no ready window appears before timeout.
    """
    end_time = time.time() + timeout
    last_error = None

    while time.time() < end_time:
        try:
            main_win = app.top_window()
            main_win.wait("visible ready", timeout=1)
            return main_win
        except Exception as exc:  # pylint: disable=broad-except
            last_error = exc
            time.sleep(0.5)

    raise TimeoutError(f"Failed to find main window within {timeout}s: {last_error}")


def click_tab(main_win, tab_name: str) -> None:
    """
    Click a tab item by title.

    Args:
        main_win (WindowSpecification): Main window object.
        tab_name (str): Tab text to select.

    Returns:
        None

    Raises:
        ElementNotFoundError: If tab is missing.
    """
    tab = main_win.child_window(title=tab_name, control_type="TabItem")
    if not tab.exists(timeout=5):
        raise ElementNotFoundError(f"Tab not found: {tab_name}")
    tab.wrapper_object().click_input()


def click_button(main_win, button_name: str) -> None:
    """
    Click a button by title.

    Args:
        main_win (WindowSpecification): Main window object.
        button_name (str): Button text.

    Returns:
        None

    Raises:
        ElementNotFoundError: If button is missing.
    """
    button = main_win.child_window(title=button_name, control_type="Button")
    if not button.exists(timeout=5):
        raise ElementNotFoundError(f"Button not found: {button_name}")
    button.wrapper_object().click_input()


def collect_window_text(main_win) -> str:
    """
    Collect text from likely text-bearing controls.

    Args:
        main_win (WindowSpecification): Main window object.

    Returns:
        str: Aggregated visible text content.
    """
    texts = []
    try:
        for ctype in ("Text", "Edit", "Document"):
            for ctrl in main_win.descendants(control_type=ctype):
                txt = ctrl.window_text().strip()
                if txt:
                    texts.append(txt)
    except Exception:  # pylint: disable=broad-except
        pass

    return "\n".join(texts)


def wait_for_log(main_win, expected_text: str, timeout: int = 60) -> bool:
    """
    Wait until expected log text appears.

    Args:
        main_win (WindowSpecification): Main window object.
        expected_text (str): Target log text.
        timeout (int): Maximum wait seconds.

    Returns:
        bool: True when text appears, otherwise False.
    """
    end_time = time.time() + timeout
    log(f"Waiting for log: {expected_text}")
    while time.time() < end_time:
        if expected_text in collect_window_text(main_win):
            return True
        time.sleep(0.5)
    return False


def open_and_prepare_tool(exe_path: Path):
    """
    Launch tool and finish initialization steps before data collection.

    Args:
        exe_path (Path): Executable path.

    Returns:
        tuple[Application, WindowSpecification]: Application and main window.

    Raises:
        FileNotFoundError: If executable does not exist.
        RuntimeError: If initialization log is not detected.
    """
    if not exe_path.exists():
        raise FileNotFoundError(f"Executable does not exist: {exe_path}")

    log(f"Starting executable: {exe_path}")
    app = Application(backend="uia").start(str(exe_path), timeout=30)
    main_win = wait_for_window(app, timeout=30)
    main_win.set_focus()

    log("Switching to 点迹 tab...")
    click_tab(main_win, "点迹")
    time.sleep(3)

    log("Clicking 初始化...")
    click_button(main_win, "初始化")
    if not wait_for_log(main_win, SUCCESS_LOG, timeout=60):
        raise RuntimeError(f"Did not find expected log: {SUCCESS_LOG}")

    log("Initialization completed.")
    return app, main_win


def sanitize_case_id(case_id: str) -> str:
    """
    Replace invalid path characters in case_id.

    Args:
        case_id (str): Raw case identifier.

    Returns:
        str: Filesystem-safe case id.
    """
    invalid_chars = '<>:"/\\|?*'
    value = case_id.strip()
    for ch in invalid_chars:
        value = value.replace(ch, "_")
    return value


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


def start_ffmpeg_recording(output_file: Path, camera_device: str | None) -> tuple[subprocess.Popen | None, str, str | None]:
    """
    Start ffmpeg camera recording process.

    Args:
        output_file (Path): Video output path.
        camera_device (str | None): Preferred camera name.

    Returns:
        tuple[subprocess.Popen | None, str, str | None]: Process, selected camera name, and error message.
    """
    ffmpeg_exe = get_ffmpeg_exe()
    selected = camera_device if camera_device else DEFAULT_CAMERA_DEVICE

    ffmpeg_norm = ffmpeg_exe.replace("\\", "/")
    ff_cmd = (
        f'& "{ffmpeg_norm}" -y -hide_banner -f dshow '
        f'-thread_queue_size 512 -rtbufsize 256M -vcodec mjpeg '
        f'-framerate 15 -video_size 640x480 -i "video={selected}" '
        f'-c:v libx264 -preset ultrafast -pix_fmt yuv420p '
        f'-movflags +faststart "{str(output_file)}"'
    )

    process = subprocess.Popen(
        ["powershell", "-Command", ff_cmd],
        stdin=subprocess.PIPE,
        text=True,
    )
    time.sleep(1)
    if process.poll() is not None:
        devices = list_dshow_video_devices(ffmpeg_exe)
        if devices:
            return None, selected, f"ffmpeg exited immediately, available devices: {devices}"
        return None, selected, "ffmpeg exited immediately"

    return process, selected, None


def stop_ffmpeg_recording(process: subprocess.Popen) -> str:
    """
    Stop ffmpeg recording process gracefully.

    Args:
        process (subprocess.Popen): ffmpeg process.

    Returns:
        str: ffmpeg stderr output.
    """
    try:
        if process.stdin:
            process.stdin.write("q\n")
            process.stdin.flush()
    except Exception:  # pylint: disable=broad-except
        pass

    try:
        process.wait(timeout=10)
        return ""
    except Exception:  # pylint: disable=broad-except
        process.kill()
        process.wait(timeout=5)
        return ""


def find_latest_csv(base_dir: Path, start_ts: float) -> Path | None:
    """
    Locate the latest CSV generated after a given timestamp.

    Args:
        base_dir (Path): Directory to search.
        start_ts (float): Start timestamp in seconds.

    Returns:
        Path | None: Latest matching CSV file path.
    """
    candidates = []
    for csv_file in base_dir.glob("*.csv"):
        mtime = csv_file.stat().st_mtime
        if mtime >= start_ts - 1:
            candidates.append(csv_file)

    if not candidates:
        return None

    candidates.sort(key=lambda p: p.stat().st_mtime, reverse=True)
    return candidates[0]


def move_and_validate(case_dir: Path, video_file: Path, csv_file: Path) -> tuple[bool, str]:
    """
    Move output files into case directory and validate size constraints.

    Args:
        case_dir (Path): Destination case directory.
        video_file (Path): Source video file.
        csv_file (Path): Source CSV file.

    Returns:
        tuple[bool, str]: Validation pass state and status message.
    """
    case_dir.mkdir(parents=True, exist_ok=True)

    target_video = case_dir / video_file.name
    target_csv = case_dir / csv_file.name

    if target_video.exists():
        target_video.unlink()
    if target_csv.exists():
        target_csv.unlink()

    shutil.move(str(video_file), str(target_video))
    shutil.move(str(csv_file), str(target_csv))

    video_size = target_video.stat().st_size
    csv_size = target_csv.stat().st_size

    if video_size < VIDEO_MIN_SIZE:
        return False, f"Video too small: {video_size} bytes (< {VIDEO_MIN_SIZE})"
    if csv_size < CSV_MIN_SIZE:
        return False, f"CSV too small: {csv_size} bytes (< {CSV_MIN_SIZE})"

    return True, "log已存放--PASS"


def run_case_loop(main_win, work_dir: Path, camera_device: str | None) -> None:
    """
    Repeatedly collect logs by case_id until user exits.

    Args:
        main_win (WindowSpecification): Prepared tool main window.
        work_dir (Path): Working directory for generated artifacts.

    Returns:
        None
    """
    while True:
        case_id = input("请输入case_id (输入 q 退出): ").strip()
        if case_id.lower() in {"q", "quit", "exit"}:
            log("Collector exited by user.")
            break
        if not case_id:
            log("case_id不能为空，请重新输入。")
            continue

        safe_case_id = sanitize_case_id(case_id)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        video_file = work_dir / f"{safe_case_id}_{timestamp}{VIDEO_EXT}"

        ffmpeg_proc = None
        should_exit_after_case = False
        collection_started = False

        session_start_ts = time.time()
        ffmpeg_proc, selected_camera, ffmpeg_error = start_ffmpeg_recording(video_file, camera_device)
        if ffmpeg_proc is None:
            log(f"采集失败: {ffmpeg_error}")
            continue
        log(f"Camera recording started: {selected_camera}")

        try:
            log("Clicking 开始点迹采集...")
            click_button(main_win, "开始点迹采集")
            collection_started = True

            stop_text = input("再次按下回车以停止采集并保存文件(输入q并回车表示本轮结束后退出): ").strip()
            if stop_text.lower() in {"q", "quit", "exit"}:
                should_exit_after_case = True
        finally:
            ffmpeg_stderr = stop_ffmpeg_recording(ffmpeg_proc)

            if collection_started:
                try:
                    log("Clicking 停止点迹采集...")
                    click_button(main_win, "停止点迹采集")
                except Exception as exc:  # pylint: disable=broad-except
                    log(f"停止点迹采集按钮点击失败: {exc}")

            if ffmpeg_stderr and "error" in ffmpeg_stderr.lower():
                log(f"ffmpeg警告/错误: {ffmpeg_stderr.splitlines()[-1]}")

        if not video_file.exists():
            log("采集失败: 未生成视频文件")
            if should_exit_after_case:
                log("Collector exited by user.")
                break
            continue

        csv_file = find_latest_csv(work_dir, session_start_ts)
        if csv_file is None:
            log("采集失败: 未找到本次采集生成的CSV文件")
            if should_exit_after_case:
                log("Collector exited by user.")
                break
            continue

        case_dir = work_dir / safe_case_id
        ok, message = move_and_validate(case_dir, video_file, csv_file)
        log(message)
        if not ok:
            log("log存放完成，但大小校验失败")

        if should_exit_after_case:
            log("Collector exited by user.")
            break


def main() -> int:
    """
    Parse arguments and run collector main loop.

    Args:
        None

    Returns:
        int: 0 when exited normally, 1 when startup fails.
    """
    parser = argparse.ArgumentParser(description="Case-based log collector for radar dot-trace")
    parser.add_argument("--exe", default=EXE_PATH, help="Path to Quectel radar tool executable")
    parser.add_argument("--work-dir", default=str(Path(__file__).resolve().parent), help="Working directory for output files")
    parser.add_argument("--camera-device", default=None, help="DirectShow camera device name")
    args = parser.parse_args()

    try:
        _, main_win = open_and_prepare_tool(Path(args.exe))
        run_case_loop(
            main_win,
            Path(args.work_dir).resolve(),
            camera_device=args.camera_device,
        )
        return 0
    except Exception as exc:  # pylint: disable=broad-except
        log(f"Program failed: {exc}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
