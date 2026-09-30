"""Simple proportional pan/tilt tracker."""


class LaserTracker:
    """Centers the target bbox in the frame with proportional control."""

    def __init__(self, pwm, pan_ch, tilt_ch, pan_start=90, tilt_start=90,
                 pan_limits=(0, 180), tilt_limits=(40, 140),
                 gain=30.0, dead_zone=0.05):
        self.pwm = pwm
        self.pan_ch = pan_ch
        self.tilt_ch = tilt_ch
        self.pan = pan_start
        self.tilt = tilt_start
        self.pan_limits = pan_limits
        self.tilt_limits = tilt_limits
        self.gain = gain
        self.dead_zone = dead_zone
        self.pwm.set_angle(self.pan_ch, self.pan)
        self.pwm.set_angle(self.tilt_ch, self.tilt)

    def update(self, bbox, frame_w, frame_h):
        x1, y1, x2, y2 = bbox
        err_x = ((x1 + x2) / 2 - frame_w / 2) / (frame_w / 2)   # -1 .. 1
        err_y = ((y1 + y2) / 2 - frame_h / 2) / (frame_h / 2)

        # NOTE: if it tracks AWAY from the person, flip the sign of these two lines
        if abs(err_x) > self.dead_zone:
            self.pan -= err_x * self.gain
        if abs(err_y) > self.dead_zone:
            self.tilt += err_y * self.gain

        self.pan = max(self.pan_limits[0], min(self.pan_limits[1], self.pan))
        self.tilt = max(self.tilt_limits[0], min(self.tilt_limits[1], self.tilt))

        self.pwm.set_angle(self.pan_ch, self.pan)
        self.pwm.set_angle(self.tilt_ch, self.tilt)
        return self.pan, self.tilt