

class Trip:
    def __init__(self, mode, start_time, end_time, cost, origin, destination):
        self.mode = mode
        self.startTime = start_time
        self.endTime = end_time
        self.duration = (end_time - start_time) / (60 * 60)
        self.cost = cost
        self.origin = origin
        self.destination = destination
        self.utility = 0
