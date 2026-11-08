"""PWM servo call in the classic TurboPi signature, on the RRC board (servo 1 tilt, 2 pan)."""
from ._board import board


def setPWMServoPulse(servo_id, pulse, use_time=60):
    """servo_id 1-4, pulse 500-2500 us, use_time ms."""
    pulse = max(500, min(2500, int(pulse)))
    board().pwm_servo_set_position(max(0.02, use_time / 1000.0), [[int(servo_id), pulse]])
