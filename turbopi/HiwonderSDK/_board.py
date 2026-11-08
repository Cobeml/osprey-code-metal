"""One shared Board on the serial port, loaded from the rover's own ros_robot_controller_sdk.py."""
import importlib
import os
import sys

RRC_DIRS = (os.environ.get("RRC_SDK", ""), "/home/pi/board_demo", "/home/pi/demo")
_board = None


def board():
    global _board
    if _board is None:
        for d in RRC_DIRS:
            if d and os.path.isfile(os.path.join(d, "ros_robot_controller_sdk.py")) and d not in sys.path:
                sys.path.append(d)
        try:
            rrc = importlib.import_module("ros_robot_controller_sdk")
        except ImportError as e:
            raise SystemExit("ros_robot_controller_sdk.py not found (looked in %s); set RRC_SDK=<folder> (%s)"
                             % (", ".join(d for d in RRC_DIRS if d), e))
        _board = rrc.Board()
    return _board
