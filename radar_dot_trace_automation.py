"""
Automate Quectel Radar Update Tool dot-trace workflow.

Author: Kawhi.He
"""

import argparse
import sys
import time
from pathlib import Path

from pywinauto import Desktop
from pywinauto.application import Application
from pywinauto.findwindows import ElementNotFoundError


EXE_PATH = r"F:\Firmware\Quectel_Radar_Update_Tool_V1.8.3\Quectel_Radar_Update_Tool_V1.8.3\Quectel_Radar_Update_Tool_V1.8.3.exe"
SUCCESS_LOG = "初始化LIN1成功!"


def log(message: str) -> None:
    """Print runtime progress with flushing for terminal visibility."""
    print(message, flush=True)


def wait_for_window(app: Application, timeout: int = 30):
    """
    Wait for the main window of the launched process.

    Args:
        app (Application): Started pywinauto application instance.
        timeout (int): Maximum wait time in seconds.

    Returns:
        WindowSpecification: Main window object.

    Raises:
        TimeoutError: If no ready and visible window is found.
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
    Switch to the target tab by its display name.

    Args:
        main_win (WindowSpecification): Main window object.
        tab_name (str): Tab title to click.

    Returns:
        None

    Raises:
        ElementNotFoundError: If target tab cannot be found.
    """
    tab = main_win.child_window(title=tab_name, control_type="TabItem")
    if not tab.exists(timeout=5):
        raise ElementNotFoundError(f"Tab not found: {tab_name}")

    tab.wrapper_object().click_input()


def click_button(main_win, button_name: str) -> None:
    """
    Click a button in the main window by exact text.

    Args:
        main_win (WindowSpecification): Main window object.
        button_name (str): Button text.

    Returns:
        None

    Raises:
        ElementNotFoundError: If button cannot be found.
    """
    button = main_win.child_window(title=button_name, control_type="Button")
    if not button.exists(timeout=5):
        raise ElementNotFoundError(f"Button not found: {button_name}")

    button.wrapper_object().click_input()


def collect_window_text(main_win) -> str:
    """
    Collect all visible descendant texts for log matching.

    Args:
        main_win (WindowSpecification): Main window object.

    Returns:
        str: Joined text content from descendants.
    """
    texts = []
    try:
        # Keep polling lightweight to avoid impacting target tool initialization.
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
    Poll UI text until expected log appears.

    Args:
        main_win (WindowSpecification): Main window object.
        expected_text (str): Log text to wait for.
        timeout (int): Maximum wait time in seconds.

    Returns:
        bool: True when expected text appears, otherwise False.
    """
    end_time = time.time() + timeout
    log(f"Waiting for log: {expected_text}")
    while time.time() < end_time:
        visible_text = collect_window_text(main_win)
        if expected_text in visible_text:
            log("Expected log detected.")
            return True
        time.sleep(0.5)
    log("Expected log not detected before timeout.")
    return False


def run_flow(exe_path: str) -> None:
    """
    Execute the full dot-trace automation flow.

    Args:
        exe_path (str): Absolute path to the target executable.

    Returns:
        None

    Raises:
        FileNotFoundError: If executable does not exist.
        RuntimeError: If log expectation is not met.
    """
    exe = Path(exe_path)
    if not exe.exists():
        raise FileNotFoundError(f"Executable does not exist: {exe}")

    log(f"Starting executable: {exe}")
    app = Application(backend="uia").start(str(exe), timeout=30)
    log("Executable started, waiting for main window...")
    main_win = wait_for_window(app, timeout=30)
    log("Main window found, focusing...")
    main_win.set_focus()

    log("Switching to 点迹 tab...")
    click_tab(main_win, "点迹")
    time.sleep(3)

    log("Clicking 初始化...")
    click_button(main_win, "初始化")
    if not wait_for_log(main_win, SUCCESS_LOG, timeout=60):
        raise RuntimeError(f"Did not find expected log within timeout: {SUCCESS_LOG}")

    log("Clicking 开始点迹采集...")
    click_button(main_win, "开始点迹采集")
    time.sleep(5)
    log("Clicking 停止点迹采集...")
    click_button(main_win, "停止点迹采集")
    log("Flow finished.")


def main() -> int:
    """
    Parse arguments and run automation.

    Args:
        None

    Returns:
        int: 0 if success, 1 if failure.
    """
    parser = argparse.ArgumentParser(description="Automate Quectel Radar dot-trace actions")
    parser.add_argument("--exe", default=EXE_PATH, help="Path to Quectel Radar Update Tool executable")
    args = parser.parse_args()

    try:
        run_flow(args.exe)
        print("Automation flow completed successfully.")
        return 0
    except Exception as exc:  # pylint: disable=broad-except
        print(f"Automation flow failed: {exc}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
