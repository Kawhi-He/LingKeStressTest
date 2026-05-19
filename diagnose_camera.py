"""
Diagnose available camera indices and frame brightness.

Author: Kawhi.He
"""

import time

import cv2


def main() -> None:
    """
    Print camera index availability and first-frame brightness.

    Args:
        None

    Returns:
        None
    """
    for idx in range(5):
        cap = cv2.VideoCapture(idx, cv2.CAP_DSHOW)
        opened = cap.isOpened()
        ok = False
        shape = None
        mean = None

        if opened:
            for _ in range(10):
                ret, frame = cap.read()
                if ret and frame is not None:
                    ok = True
                    shape = frame.shape
                    mean = float(frame.mean())
                    break
                time.sleep(0.1)

        cap.release()
        print(f"idx={idx}, opened={opened}, ok={ok}, shape={shape}, mean={mean}", flush=True)


if __name__ == "__main__":
    main()
