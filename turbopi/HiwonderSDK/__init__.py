"""Compatibility shim for Hiwonder's Pi 5 / ROS 2 TurboPi image.

That image has no host-side HiwonderSDK package: the expansion board is driven through
ros_robot_controller_sdk.py (serial, /dev/rrc), which ships in ~/board_demo. This package gives
scout_client.py the two calls it expects, built on that file:
  HiwonderSDK.mecanum.MecanumChassis().set_velocity(speed, direction_deg, yaw)
  HiwonderSDK.Board.setPWMServoPulse(servo_id, pulse_us, move_ms)
Only one process may own the board: stop Hiwonder's ROS container first (docker stop turbopi).
"""
