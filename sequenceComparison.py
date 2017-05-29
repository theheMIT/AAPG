

def comparison_dictionary(new_pattern, existing_pattern, activity_types):
    comparison_dictionary = {}
    for day in range(new_pattern.days):
        new_day_sequence = new_pattern.sequence[new_pattern.dayBreaks[day]:new_pattern.dayBreaks[day + 1]]
        existing_day_sequence = existing_pattern.sequence[existing_pattern.dayBreaks[day]:existing_pattern.dayBreaks[day + 1]]

        dictionary = build_comparison_dictionary(new_day_sequence, new_pattern.dayBreaks[day],
                                                 new_pattern.dayBreaks[day + 1], existing_day_sequence,
                                                 existing_pattern.dayBreaks[day], existing_pattern.dayBreaks[day + 1],
                                                 activity_types)
        comparison_dictionary = {**comparison_dictionary, **dictionary}
        comparison_dictionary[len(new_pattern.sequence) - 1] = len(existing_pattern.sequence) - 1
    return comparison_dictionary


def build_comparison_dictionary(new_sequence, new_day_start, new_day_end, existing_sequence, existing_day_start,
                                existing_day_end, activity_types):
    comparison_dictionary = {}

    # If sequences are the same --> match directly
    if new_sequence == existing_sequence:
        for episode in range(len(new_sequence)):
            comparison_dictionary[episode + new_day_start] = episode + existing_day_start
    else:
        # booleans to indicate whether each episode in existing and new have been matched yet
        new_matched = [False] * len(new_sequence)
        existing_matched = [False] * len(existing_sequence)

        # Determine discrepancy in number of episodes by type
        no_match_activities = [0] * len(activity_types)
        for episode in range(len(new_sequence)):
            no_match_activities[new_sequence[episode].activityType] += 1
        for episode in range(len(existing_sequence)):
            no_match_activities[existing_sequence[episode].activityType] -= 1

        # Forward pass - create match if there is no discrepancy in the number of episodes of that type,
        # and the episodes are of the same type
        for episode in range(0, min(len(new_sequence), len(existing_sequence))):
            if no_match_activities[new_sequence[episode].activityType] == 0 \
                    and new_sequence[episode].activityType == existing_sequence[episode].activityType:
                # activity_time_dictionary = {key: value for key, value in activity_time_dictionary.items()
                #                            if value != existing_day_start + episode}
                new_matched[episode] = True
                existing_matched[episode] = True
                comparison_dictionary[new_day_start + episode] = existing_day_start + episode

        # Backward pass
        for episode in range(-1, -1 * min(len(new_sequence), len(existing_sequence)), -1):
            if not new_matched[episode] and not existing_matched[episode] and \
                            no_match_activities[new_sequence[episode].activityType] == 0 and \
                            new_sequence[episode].activityType == existing_sequence[episode].activityType:
                new_matched[episode] = True
                existing_matched[episode] = True
                comparison_dictionary[new_day_end + episode] = existing_day_end + episode

        for activity_type in range(len(activity_types)):
            # If there are more episodes of given type in the new sequence than in the old sequence, find the closest
            # episode of same type in the old sequence
            if no_match_activities[activity_type] > 0:
                distances = []
                for episode in range(len(new_sequence)):
                    if new_sequence[episode].activityType == activity_type:
                        distances.append(find_closest(new_sequence, existing_sequence, episode, existing_matched))

                for match in range(len(distances) - no_match_activities[activity_type]):
                    min_dist = 1000
                    for d in range(len(distances)):
                        if abs(distances[d]) < abs(min_dist):
                            min_dist = distances[d]
                            min_index = d
                    index = 0
                    for episode in range(len(new_sequence)):
                        if new_sequence[episode].activityType == activity_type and not new_matched[episode]:
                            if index == min_index:
                                new_matched[episode] = True
                                existing_matched[episode + distances[min_index]] = True
                                comparison_dictionary[new_day_start + episode] = existing_day_start + episode \
                                                                                    + distances.pop(min_index)
                            index += 1

        # check remaining unmatched
        for episode in range(len(new_sequence)):
            if not new_matched[episode] and no_match_activities[new_sequence[episode].activityType] <= 0:
                new_matched[episode] = True
                distance = find_closest(new_sequence, existing_sequence, episode, existing_matched)
                existing_matched[episode + distance] = True
                comparison_dictionary[new_day_start + episode] = existing_day_start + episode + distance

    return comparison_dictionary


def find_closest(new_sequence, existing_sequence, episode, existing_matched):
    if episode < len(existing_sequence) \
            and new_sequence[episode].activityType == existing_sequence[episode].activityType \
            and not existing_matched[episode]:
        distance = 0
    else:
        upstream_dist = 0
        upstream_found = False
        downstream_dist = 0
        downstream_found = False

        if episode < len(existing_sequence):
            compare_episode = episode
        else:
            compare_episode = len(existing_sequence)
            upstream_dist = episode - len(existing_sequence)
        while not upstream_found and compare_episode > 0:
            compare_episode -= 1
            upstream_dist += 1
            if new_sequence[episode].activityType == existing_sequence[compare_episode].activityType \
                    and not existing_matched[compare_episode]:
                upstream_found = True

        compare_episode = episode
        while not downstream_found and compare_episode < min(len(new_sequence), len(existing_sequence)) - 1:
            compare_episode += 1
            downstream_dist += 1
            if new_sequence[episode].activityType == existing_sequence[compare_episode].activityType \
                    and not existing_matched[compare_episode]:
                downstream_found = True

        if upstream_found and downstream_found:
            if upstream_dist <= downstream_dist:
                distance = -upstream_dist
            else:
                distance = downstream_dist
        elif upstream_found and not downstream_found:
            distance = -upstream_dist
        else:
            distance = downstream_dist

    return distance
