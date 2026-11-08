"""Mecanum chassis on the RRC board, same interface as Hiwonder's mecanum.MecanumChassis.

Inverse kinematics for a 4-wheel mecanum base; motor numbering and signs follow the TurboPi
board (1 front-left, 2 front-right, 3 rear-left, 4 rear-right; left motors are mirrored).
direction: 90 = forward, 270 = backward, 0 = right; angular_rate > 0 = clockwise (right turn).
"""
import math

from ._board import board


def _duty(v):
    return max(-100, min(100, int(v)))


class MecanumChassis:
    def __init__(self, a=67, b=59, wheel_diameter=65):
        self.a, self.b, self.wheel_diameter = a, b, wheel_diameter
        self.velocity = self.direction = self.angular_rate = 0

    def reset_motors(self):
        board().set_motor_duty([[1, 0], [2, 0], [3, 0], [4, 0]])
        self.velocity = self.direction = self.angular_rate = 0

    def set_velocity(self, velocity, direction, angular_rate, fake=False):
        r = math.radians(direction)
        vx, vy = velocity * math.cos(r), velocity * math.sin(r)
        vp = -angular_rate * (self.a + self.b)
        v1, v2, v3, v4 = vy + vx - vp, vy - vx + vp, vy - vx - vp, vy + vx + vp
        if fake:
            return
        board().set_motor_duty([[1, -_duty(v1)], [2, _duty(v2)], [3, -_duty(v3)], [4, _duty(v4)]])
        self.velocity, self.direction, self.angular_rate = velocity, direction, angular_rate
