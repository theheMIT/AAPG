import json


def load_dataset(f_name):
    with open(f_name) as fmsActivityDiaries:
        fms = json.load(fmsActivityDiaries)
    return fms


def get_start_time(activity_diary):
    start_time = activity_diary[0]['startTime']
    return start_time


def check_activity_type(episode, activity_types):
    if episode['activity'] not in activity_types:
        activity_types.append(episode['activity'])
    return activity_types


def add_episode(episode, sequence, activity_types):
    sequence.append(activity_types.index(episode['activity']))
    return


def add_duration(episode, durations, start_time):
    durations.append([int((episode['startTime'] - start_time) / 60), int((episode['endTime'] - start_time) / 60),
                      int((episode['endTime'] - episode['startTime']) / 60)])
    return durations


def determine_day_breaks(day_breaks, durations):
    day = 1
    day_breaks[:] = [0]
    for episode in range(len(durations)):
        if durations[episode][1] / 1440 > day:
            day_breaks.append(episode)
            day += 1
    day_breaks.append(len(durations) - 1)
    return day_breaks


def get_trip_duration(episode, trip_durations):
    trip_durations.append(episode['duration'])
    return trip_durations


def get_travel_times(alternatives, mode):
    if alternatives == 'Foot travel distance less than 500m':
        if mode == "Foot":
            travel_time = 3
        else:
            travel_time = 15
    else:
        for alternative in alternatives:
            try:
                if alternative['activity'] == mode:
                    travel_time = alternative['duration']
            except KeyError:
                travel_time = 888
    return travel_time


# Update cost functions for each mode as needed
def get_travel_costs(alternatives, mode):
    if alternatives == 'Foot travel distance less than 500m':
        if mode == 'Foot':
            travel_cost = 0
        elif mode == 'Bus' or mode == 'LRT/MRT':
            travel_cost = 0.77
        else:
            travel_cost = 2
    else:
        for alternative in alternatives:
            try:
                if alternative['activity'] == "Foot" and alternative['activity'] == mode:
                    travel_cost = 0
                elif alternative['activity'] == "Car/Van" and alternative['activity'] == mode:  # Parking cost should be included as function of activity time
                    travel_cost = 2 + 0.14 * alternative['travelModeDist']['Car/Van'] / 1000
                elif alternative['activity'] == "Bus" and alternative['activity'] == mode:
                    travel_cost = 0.77 + 0.1 * alternative['travelModeDist']['Bus'] / 1000
                elif alternative['activity'] == "LRT/MRT" and alternative['activity'] == mode:
                    travel_cost = 0.77 + 0.1 * (alternative['travelModeDist']['Bus'] +
                                                alternative['travelModeDist']['LRT/MRT']) / 1000
            except KeyError:
                travel_cost = 888
    return travel_cost

