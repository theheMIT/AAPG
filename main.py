import importFMS
import classAgent
import classPattern
import classEpisode
import classTrip
import utility
import copy
import csv


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

pcMTZDictionary = {}
MTZs = []
with open('postalCodeMTZ_lookup.csv') as file:
    postalCodeMTZLookUp = csv.reader(file)

    for pc in postalCodeMTZLookUp:
        pcMTZDictionary[pc[0]] = pc[1]
        if pc[1] not in MTZs:
            MTZs.append(pc[1])

zonesCount = len(set(pcMTZDictionary.values()))
OPtravelTimes = [[[500 for i in range(len(agent.modes))] for j in range(zonesCount)] for k in range(zonesCount)]
OPtravelCosts = [[[50 for i in range(len(agent.modes))] for j in range(zonesCount)] for k in range(zonesCount)]

with open('OPcosts.csv') as file:
    OPcosts = csv.reader(file)

    matched = 0
    unmatched = 0

    for entry in OPcosts:
        origin = entry[1]
        destination = entry[2]
        if origin != destination:
            travelTimes = [float(entry[3]) / 5 * 60, float(entry[5]),
                           float(entry[6]) + float(entry[7]) + float(entry[8]), float(entry[5])]
            travelCosts = [0, 2 + 0.14 * float(entry[3]) + float(entry[4]) / 100, float(entry[9]) / 100,
                           1 + 0.3 * float(entry[3])]
        else:
            travelTimes = [10, 10, 15, 10]
            travelCosts = [0, 2.5, 1, 1.2]

        if origin in MTZs and destination in MTZs:
            OPtravelTimes[MTZs.index(origin)][MTZs.index(destination)] = travelTimes
            OPtravelCosts[MTZs.index(origin)][MTZs.index(destination)] = travelCosts
            matched += 1
        else:
            unmatched += 1

for trip in existingPattern.trips:
    trip.cost = OPtravelCosts[MTZs.index(pcMTZDictionary[trip.origin])][MTZs.index(pcMTZDictionary[trip.destination])][trip.mode]

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
                        trip = classTrip.Trip(m, 0, OPtravelTimes[MTZs.index(pcMTZDictionary[o])][MTZs.index(
                            pcMTZDictionary[d])][m] * 60, OPtravelCosts[MTZs.index(pcMTZDictionary[o])][
                                                  MTZs.index(pcMTZDictionary[d])][m], o, d)
                        u = utility.trip_utility(agent, trip) - agent.averageUtility * trip.duration / 60
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
