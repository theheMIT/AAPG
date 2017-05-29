import sequenceComparison
import math
import numpy as np
from scipy.optimize import minimize
from functools import partial


def pattern_utility(agent, pattern, existing_pattern):
    su = sequence_utility(agent, pattern.dailyDurations)
    tu = travel_utility(agent, pattern)
    cu = change_utility(agent, pattern, existing_pattern)

    utility = su + tu + cu

    return utility


def sequence_utility(agent, daily_durations):
    utility = 0
    for activity_type in range(len(daily_durations)):
        if activity_type in agent.mandatoryActivityTypes:
            duration = sum(d for d in daily_durations[activity_type])
            if duration > agent.parameters[activity_type][1]:
                utility += agent.parameters[activity_type][0] * math.log2(agent.parameters[activity_type][2] *
                                                                          (duration - agent.parameters[activity_type][1]))
            else:
                utility -= 1000
        else:
            for duration in daily_durations[activity_type]:
                if duration > agent.parameters[activity_type][1]:
                    utility += agent.parameters[activity_type][0] * math.log2(agent.parameters[activity_type][2] *
                                                                              (duration - agent.parameters[activity_type][1]))
    return utility


def trip_utility(agent, trip):
    return agent.betaTravelTime[trip.mode] * trip.duration + agent.betaTravelCost[trip.mode] * trip.cost


def travel_utility(agent, pattern):
    utility = 0
    for trip in pattern.trips:
        utility += trip_utility(agent, trip)
    return utility


def change_utility(agent, new_pattern, existing_pattern):
    utility = 0
    comparison_dictionary = sequenceComparison.comparison_dictionary(new_pattern, existing_pattern, agent.activityTypes)
    for episode in range(len(new_pattern.sequence)):
        if episode in list(comparison_dictionary.keys()):
            utility -= agent.specificActivityInertia[new_pattern.sequence[episode].activityType] / agent.flexibility * \
                       ((new_pattern.sequence[episode].startTime -
                         existing_pattern.sequence[comparison_dictionary[episode]].startTime) / 60 ** 2) ** 2
    return utility


def optimize_activities(new_pattern, existing_pattern, agent):

    comparison_dictionary = sequenceComparison.comparison_dictionary(new_pattern, existing_pattern, agent.activityTypes)

    success = True

    adj = 0  # duration adjustment for 1st episode each day to account for overlapping constraints

    for day in range(new_pattern.days):

        new_day_travel_time = new_pattern.get_daily_travel_time(day)
        existing_day_travel_time = existing_pattern.get_daily_travel_time(day)
        existing_day_episode_time = existing_pattern.get_daily_episode_time(day)

        # Determine episode times for new sequence
        new_durations = []
        matched_new_episodes = list(comparison_dictionary.keys())
        for episode in range(new_pattern.dayBreaks[day], new_pattern.dayBreaks[day + 1] + 1):
            if episode in matched_new_episodes:
                new_durations.append(existing_pattern.sequence[comparison_dictionary[episode]].duration)
            else:
                new_durations.append(existing_pattern.newEpisodeDuration[new_pattern.sequence[episode].activityType])
        total_new_duration = sum(d for d in new_durations)
        adjust = -(total_new_duration + new_day_travel_time - existing_day_episode_time -
                   existing_day_travel_time)
        for index in range(len(new_durations)):
            new_durations[index] += adjust * new_durations[index] / total_new_duration

        constraints = ({'type': 'eq', 'fun': lambda x: np.array([sum(x) + new_day_travel_time -
                                                                 existing_day_episode_time -
                                                                 existing_day_travel_time])})
        bounds = []
        if adjust < 0:
            for episode in range(len(new_durations)):
                    bounds.append([0.1, min(max(new_durations[episode], 0.1), 24)])
        else:
            for episode in range(len(new_durations)):
                bounds.append([new_durations[episode], 25])

        uaa = partial(utility_after_adjustment, day=day, comparison_dictionary=comparison_dictionary,
                      new_pattern=new_pattern, existing_pattern=existing_pattern, agent=agent, adj=adj)

        results = minimize(uaa, np.array(new_durations), constraints=constraints, bounds=tuple(bounds))
        adj = results.x[-1] - existing_pattern.sequence[comparison_dictionary[new_pattern.dayBreaks[day + 1]]].duration

        if not results.success:
            if results.message != 'Positive directional derivative for linesearch' \
                    and results.message != 'Iteration limit exceeded' \
                    and results.message != 'Inequality constraints incompatible':
                raise Exception('Unexpected optimization error.')
            if abs(sum(results.x) + new_day_travel_time - existing_day_episode_time - existing_day_travel_time) > 0.1:
                success = False
                break
    if success:
        return new_pattern
    else:
        return None


def utility_after_adjustment(new_durations, day, comparison_dictionary, new_pattern, existing_pattern, agent, adj):
    utility = 0

    for index in range(len(new_durations)):
        episode = index + new_pattern.dayBreaks[day]
        if index == 0:
            new_pattern.sequence[episode].duration = new_durations[index] + adj
            new_pattern.sequence[episode].endTime = new_pattern.sequence[episode].startTime + new_durations[
                                                                                                  index] * 60 ** 2 + adj
        else:
            new_pattern.sequence[episode].duration = new_durations[index]
            new_pattern.sequence[episode].endTime = new_pattern.sequence[episode].startTime + \
                                                    new_durations[index] * 60 ** 2
        if episode + 1 < len(new_pattern.sequence):
            new_pattern.sequence[episode + 1].startTime = new_pattern.sequence[episode].endTime + \
                                                         new_pattern.trips[episode].duration * 60 ** 2
    new_pattern.update_day_patterns()
    new_pattern.daily_durations(agent.activityTypes)

    for index in range(len(new_durations)):
        episode = index + new_pattern.dayBreaks[day]
        if episode != 0 and episode in list(comparison_dictionary.keys()):
            p = float(agent.specificActivityInertia[new_pattern.sequence[episode].activityType] / agent.flexibility *
                      ((new_pattern.sequence[episode].startTime -
                        existing_pattern.sequence[comparison_dictionary[episode]].startTime) / 60 ** 2) ** 2)
            utility += p

    for activity_type in range(len(agent.activityTypes)):
        if activity_type in agent.mandatoryActivityTypes:
            duration = sum(d for d in new_pattern.dailyDurations[activity_type])
            if duration > agent.parameters[activity_type][1]:
                u = float(agent.parameters[activity_type][0] * math.log2(agent.parameters[activity_type][2] *
                                                                         (duration - agent.parameters[activity_type][1])))
            else:
                u = 1000
        else:
            duration = new_pattern.dailyDurations[activity_type][day]
            if duration > agent.parameters[activity_type][1]:
                u = float(agent.parameters[activity_type][0] * math.log2(agent.parameters[activity_type][2] *
                                                                         (duration - agent.parameters[activity_type][1])))
            else:
                u = 0
        utility -= u
    return utility
