import importFMS
import classAgent
import classPattern
import classEpisode
import classTrip
import csv
import utility
import copy


# ************************************************* PROGRAM VARIABLES *************************************************

# openHours = [[0, 1440], [540, 1020], [600, 1440], [420, 1440], [660, 1320]]
# privateVehicleModes = ["Bike", "Driv"]


# *************************************************** LOAD FMS DATA ***************************************************

fms = importFMS.load_dataset('FMSStops_net_mtz_timeline_with_alternatives.json')

postalCodes = []
activityLocations = {}

for user in range(len(fms)):
    if user == 96:
        activityDiary = fms[user]['activities']
        agent = classAgent.Agent()
        existingPattern = classPattern.Pattern()

        for activity in activityDiary:
            if activity['activityType'] == 'stop':
                importFMS.check_activity_type(activity, agent.activityTypes)

                episode = classEpisode.Episode(agent.activityTypes.index(activity['activity']), activity['startTime'],
                                               activity['endTime'], activity['postalCode'])
                existingPattern.add_episode(episode)

                if agent.activityTypes.index(activity['activity']) not in list(activityLocations.keys()):
                    activityLocations[agent.activityTypes.index(activity['activity'])] = [activity['postalCode']]
                else:
                    activityLocations[agent.activityTypes.index(activity['activity'])].append(activity['postalCode'])
                postalCodes.append(activity['postalCode'])

            if activity['activityType'] == 'travel':
                trip = classTrip.Trip(agent.modes.index(activity['activity']), activity['startTime'],
                                      activity['endTime'], 0, activity['postalCodePrev'], activity['postalCode'])
                existingPattern.add_trip(trip)

        existingPattern.update_day_patterns()
        existingPattern.daily_durations(agent.activityTypes)
        existingPattern.average_effective_durations(agent.activityTypes, agent.mandatoryActivityTypes)
        existingPattern.new_episode_duration(agent)
        agent.pattern = existingPattern

travelTimes = [[[600 for i in range(len(agent.modes))] for j in range(len(postalCodes))] for k in range(len(postalCodes))]
ttEntries = [[[0 for i in range(len(agent.modes))] for j in range(len(postalCodes))] for k in range(len(postalCodes))]
travelCosts = [[[600 for i in range(len(agent.modes))] for j in range(len(postalCodes))] for k in range(len(postalCodes))]
tcEntries = [[[0 for i in range(len(agent.modes))] for j in range(len(postalCodes))] for k in range(len(postalCodes))]
for user in range(len(fms)):
    activityDiary = fms[user]['activities']
    for episode in range(len(activityDiary)):
        if activityDiary[episode]['activityType'] == 'travel':
            origin = activityDiary[episode]['postalCodePrev']
            destination = activityDiary[episode]['postalCode']
            if origin in postalCodes and destination in postalCodes:
                for mode in agent.modes:
                    tt = importFMS.get_travel_times(activityDiary[episode]['travelAlt'], mode)
                    tc = importFMS.get_travel_costs(activityDiary[episode]['travelAlt'], mode)

                    o = postalCodes.index(origin)
                    d = postalCodes.index(destination)
                    travelTimes[o][d][agent.modes.index(mode)] = (ttEntries[o][d][agent.modes.index(mode)] *
                                                                  travelTimes[o][d][agent.modes.index(mode)] + tt) / \
                                                                 (ttEntries[o][d][agent.modes.index(mode)] + 1)
                    ttEntries[o][d][agent.modes.index(mode)] += 1
                    travelCosts[o][d][agent.modes.index(mode)] = (tcEntries[o][d][agent.modes.index(mode)] *
                                                                  travelCosts[o][d][agent.modes.index(mode)] + tc) / \
                                                                 (tcEntries[o][d][agent.modes.index(mode)] + 1)
                    tcEntries[o][d][agent.modes.index(mode)] += 1

for trip in existingPattern.trips:
    trip.cost = travelCosts[postalCodes.index(trip.origin)][postalCodes.index(trip.destination)][trip.mode]

# ****************************************** PARAMETER DETERMINATION ************************************************

agent.determine_parameters()
print(agent.parameters)


# ********************************************** NEW PATTERN GENERATION ***********************************************
localMaxFound = False
iteration = 0
baselineUtility = 0
baselinePattern = copy.deepcopy(existingPattern)

while not localMaxFound:
    iteration += 1
    newPatterns = []

    newPattern = copy.deepcopy(baselinePattern)
    newPattern.activityPattern = []
    newPattern.trips = []
    newPatterns.append(newPattern)

    print('__________________________________ Iteration ', iteration, '__________________________________')

    # _________________________________________ Generate New Sequences __________________________________________
    # New sequence by insertion
    for activityType in range(len(agent.activityTypes)):
        for index in range(1, len(baselinePattern.sequence) - 1):
            if baselinePattern.sequence[index - 1].activityType != activityType \
                    and baselinePattern.sequence[index].activityType != activityType:
                newPattern = copy.deepcopy(baselinePattern)
                newPattern.activityPattern = []
                newPattern.trips = []
                newEpisode = classEpisode.Episode(activityType, baselinePattern.sequence[index - 1].endTime,
                                                  baselinePattern.sequence[index - 1].endTime
                                                  + baselinePattern.averageEffectiveDuration[activityType],
                                                  activityLocations[activityType][0])
                newPattern.insert_episode(index, newEpisode)
                newPatterns.append(newPattern)

    # New sequence by removing
    for index in range(1, len(baselinePattern.sequence) - 1):
        if index not in baselinePattern.dayBreaks:
            newPattern = copy.deepcopy(baselinePattern)
            newPattern.remove_episode(index)
            newPattern.remove_adjacent([index])
            newPattern.activityPattern = []
            newPattern.trips = []
            newPatterns.append(newPattern)
    """
    # New sequence by swapping
    for episode_1 in range(1, len(baselineSequence) - 1):
        for episode_2 in range(episode_1 + 1, len(baselineSequence) - 1):
            if baselineSequence[episode_1] != baselineSequence[episode_2] and episode_1 not in baselineDayBreaks and \
                            episode_2 not in baselineDayBreaks:

                newSequence = baselineSequence[:]
                newSequence[episode_1], newSequence[episode_2] = newSequence[episode_2], newSequence[episode_1]
                newDayBreaks = baselineDayBreaks[:]
                seq_tuple = (newSequence, newDayBreaks)

                seq_tuple = remove_adjacent(seq_tuple, [episode_1, episode_2])

                newSequences.append([seq_tuple[0], seq_tuple[1]])
    """

    newPatterns = classPattern.remove_duplicate_sequences(newPatterns)
    totalNewSequences = len(newPatterns)

    # ____________________________________________ Determine Travel ___________________________________________
    # Need to code mode continuity for private vehicle modes --> track vehicle location in pattern class
    # Include opportunity cost
    for pattern in newPatterns:
        for episode in range(len(pattern.sequence) - 1):
            maxUtility = -9999
            preferredTrip = None
            for o in activityLocations[pattern.sequence[episode].activityType]:
                for d in activityLocations[pattern.sequence[episode + 1].activityType]:
                    for m in range(len(agent.modes)):
                        trip = classTrip.Trip(m, 0, travelTimes[postalCodes.index(o)][postalCodes.index(d)][m] * 60,
                                              travelCosts[postalCodes.index(o)][postalCodes.index(d)][m], o, d)
                        u = utility.trip_utility(agent, trip)
                        if u > maxUtility:
                            maxUtility = u
                            preferredTrip = copy.deepcopy(trip)

            pattern.add_trip(preferredTrip)

    # ____________________________________ Determine Actual Activity Durations _________________________________
    optimizedPatterns = []
    for pattern in newPatterns:
        optimizedPatterns.append(utility.optimize_activities(pattern, existingPattern, agent))

    # ____________________________________ Determine Best Activity Pattern _________________________________
    bestPattern = newPatterns[0]
    print(utility.pattern_utility(agent, baselinePattern, baselinePattern))
    # baselinePattern.print(agent)
    for pattern in newPatterns:
        print(utility.pattern_utility(agent, pattern, baselinePattern))
        # pattern.print(agent)
        if utility.pattern_utility(agent, pattern, baselinePattern) \
                > utility.pattern_utility(agent, bestPattern, baselinePattern):
            bestPattern = pattern

    existingPattern.print(agent)
    bestPattern.update_day_patterns()
    bestPattern.print(agent)

    if utility.pattern_utility(agent, bestPattern, baselinePattern) \
            - utility.pattern_utility(agent, baselinePattern, baselinePattern) > 0:
        baselinePattern = bestPattern
    else:
        localMaxFound = True
        print('Local Optimum Found')
