

class Episode:
    def __init__(self, activity_type, start_time, end_time, location):
        self.activityType = activity_type
        self.startTime = start_time
        self.endTime = end_time
        self.duration = (end_time - start_time) / (60 * 60)
        self.location = location
        self.utility = 0
