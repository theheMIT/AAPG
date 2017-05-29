import classEpisode
import classTrip


class Pattern:
    def __init__(self):
        self.sequence = []
        self.trips = []
        self.dayBreaks = []
        self.dailyDurations = []
        self.averageEffectiveDuration = []
        self.newEpisodeDuration = []
        self.startTime = 0
        self.days = 0
        self.activityPattern = []
        self.dayPatterns = []

    # For creating a new pattern

    def add_episode(self, episode):
        self.sequence.append(episode)
        self.advance_day(episode)

    def add_trip(self, trip):
        self.trips.append(trip)

    def advance_day(self, activity):
        if len(self.sequence) == 1:
            self.startTime = activity.startTime
        if (activity.endTime - self.startTime) / 86400 >= self.days:
            self.dayBreaks.append(self.sequence.index(activity))
        if (activity.endTime - self.startTime) / 86400 > self.days:
            self.days += 1

    # For generating new patterns

    def insert_episode(self, index, episode):
        self.sequence.insert(index, episode)
        for db in range(len(self.dayBreaks)):
            if self.dayBreaks[db] >= index:
                self.dayBreaks[db] += 1

    def remove_episode(self, index):
        self.sequence.pop(index)
        episodes_removed = 1
        if self.sequence[index - 1] == self.sequence[index] and index + 1 not in self.dayBreaks:
            self.sequence.pop(index)
            episodes_removed = 2
        for db in range(len(self.dayBreaks)):
            if self.dayBreaks[db] >= index:
                self.dayBreaks[db] -= episodes_removed

    def remove_adjacent(self, episodes):
        sequence = self.sequence
        day_breaks = self.dayBreaks

        for episode in episodes:
            pop_id = -1
            if sequence[episode].activityType == sequence[episode - 1].activityType \
                    and not (episode in day_breaks and episode - 1 in day_breaks):
                if episode not in day_breaks:
                    pop_id = episode
                else:
                    pop_id = episode

            elif episode + 1 < len(sequence):
                if sequence[episode].activityType == sequence[episode + 1].activityType \
                        and not (episode in day_breaks and episode - 1 in day_breaks):
                    if episode not in day_breaks:
                        pop_id = episode
                    else:
                        pop_id = episode - 1

            if pop_id != -1:
                sequence.pop(pop_id)
                for ep in range(len(episodes)):
                    if episodes[ep] > pop_id:
                        episodes[ep] -= 1

                for db in range(len(day_breaks)):
                    if day_breaks[db] > pop_id:
                        day_breaks[db] -= 1
                self.remove_adjacent(episodes)

    # For calculating and updating statistics

    def get_daily_travel_time(self, day):
        travel_time = 0
        for trip in range(self.dayBreaks[day], self.dayBreaks[day + 1]):
            travel_time += self.trips[trip].duration
        return travel_time

    def get_daily_episode_time(self, day):
        episode_time = 0
        for episode in range(self.dayBreaks[day], self.dayBreaks[day + 1] + 1):
            episode_time += self.sequence[episode].duration
        return episode_time

    def update_day_patterns(self):
        self.dayPatterns = []
        day = 0
        self.dayPatterns.append([])
        time_of_day = 0
        for episode in self.sequence:
            if time_of_day + episode.duration < 24:
                self.dayPatterns[day].append(episode)
                time_of_day += episode.duration
            else:
                self.dayPatterns[day].append(classEpisode.Episode(episode.activityType, episode.startTime,
                                                                  self.startTime + (day + 1) * 86400,
                                                                  episode.location))
                day += 1
                self.dayPatterns.append([])
                self.dayPatterns[day].append(classEpisode.Episode(episode.activityType,
                                                                  self.startTime + day * 86400,
                                                                  episode.endTime,
                                                                  episode.location))
                time_of_day += episode.duration - 24

            if episode != self.sequence[-1]:
                trip = self.trips[self.sequence.index(episode)]
                if time_of_day + trip.duration < 24:
                    self.dayPatterns[day].append(trip)
                    time_of_day += trip.duration
                else:
                    self.dayPatterns[day].append(classTrip.Trip(trip.mode, episode.endTime,
                                                                self.startTime + (day + 1) * 86400,
                                                                trip.cost, trip.origin, trip.destination))
                    day += 1
                    self.dayPatterns.append([])
                    self.dayPatterns[day].append(classTrip.Trip(trip.mode, self.startTime + day * 86400,
                                                                self.startTime + (day - 1) * 86400 +
                                                                (time_of_day + trip.duration) * 60 ** 2,
                                                                trip.cost, trip.origin, trip.destination))
                    time_of_day += trip.duration - 24

    def daily_durations(self, activity_types):
        self.dailyDurations = [[0 for j in range(self.days)] for i in range(len(activity_types))]
        for day in range(self.days):
            for episode in self.dayPatterns[day]:
                if isinstance(episode, classEpisode.Episode):
                    self.dailyDurations[episode.activityType][day] += episode.duration

    def average_effective_durations(self, activity_types, mandatory_activity_types):
        for activity_type in range(len(activity_types)):
            if activity_type in mandatory_activity_types:
                self.averageEffectiveDuration.append(sum(d for d in self.dailyDurations[activity_type]))
            else:
                effective_episodes = 0
                for day in range(self.days):
                    if self.dailyDurations[activity_type][day] > 0:
                        effective_episodes += 1
                self.averageEffectiveDuration.append(sum(d for d in self.dailyDurations[activity_type])
                                                     / effective_episodes)

    def new_episode_duration(self, agent):
        # Total durations by activity type not including day break episodes
        durations = {}
        episodes = {}
        for episode in self.sequence:
            if self.sequence.index(episode) not in self.dayBreaks:
                if episode.activityType in list(durations.keys()):
                    durations[episode.activityType] += episode.duration
                    episodes[episode.activityType] += 1
                else:
                    durations[episode.activityType] = episode.duration
                    episodes[episode.activityType] = 1
        for activity_type in range(len(agent.activityTypes)):
            if activity_type in list(durations.keys()):
                self.newEpisodeDuration.append(durations[activity_type] / episodes[activity_type])
            else:
                self.newEpisodeDuration.append(1)

    def print(self, agent):
        for day in range(self.days):
            time_of_day = 0
            title_str = 'Day ' + str(day + 1) + '         '
            start_str = '   start      '
            dur_str = '   duration   '
            for activity in self.dayPatterns[day]:
                if isinstance(activity, classEpisode.Episode):
                    char = min(len(str(agent.activityTypes[activity.activityType])), 4)
                    title_str += str(agent.activityTypes[activity.activityType])[:char] + ' ' * (7 - char)
                else:
                    char = min(len(str(agent.modes[activity.mode])), 4)
                    title_str += str(agent.modes[activity.mode])[:char] + ' ' * (7 - char)

                start_str += str(round(time_of_day, 2)) + ' ' * (7 - len(str(round(time_of_day, 2))))
                dur_str += str(round(activity.duration, 2)) + ' ' * (7 - len(str(round(activity.duration, 2))))

                time_of_day += activity.duration

            print(title_str)
            print(start_str)
            print(dur_str)
            print(' ')


def remove_duplicate_sequences(list_of_patterns):
    unique_list = []
    duplicate = False
    for pattern1 in list_of_patterns:
        for pattern2 in unique_list:
            if pattern1.sequence == pattern2.sequence:
                duplicate = True
        if not duplicate:
            unique_list.append(pattern1)
    return unique_list

