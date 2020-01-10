
class OutOfLimitsException(Exception):
    def __init__(self, bottom_limit):
        self.bottom_limit = bottom_limit
