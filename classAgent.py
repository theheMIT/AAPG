import math


class Agent:
    def __init__(self):

        # Update user parameters
        # --------------------------------------------------------------------------------------

        self.discretionaryActivities = ['Home', 'Meal']
        self.modes = ['Foot', 'Car/Van', 'Bus']

        self.flexibility = 15
        self.specificActivityInertia = [1, 10, 2, 5, 2]
        self.valueOfTime = 1
        self.valueOfMoney = 1
        self.travelUtilityScale = 300
        self.betaTravelTime = [self.travelUtilityScale * self.valueOfTime * -2.21 / 60,
                               self.travelUtilityScale * self.valueOfTime * -1.10 / 60,
                               self.travelUtilityScale * self.valueOfTime * -0.717 / 60]
        self.betaTravelCost = [self.travelUtilityScale * self.valueOfMoney * 0,
                               self.travelUtilityScale * self.valueOfMoney * -0.04,
                               self.travelUtilityScale * self.valueOfMoney * -0.0375]

        # --------------------------------------------------------------------------------------

        self.averageUtility = 0
        self.substitutionDictionary = {}
        self.parameters = []
        self.activityTypes = []
        self.mandatoryActivityTypes = []
        self.discretionaryActivityTypes = []
        for activity in range(len(self.activityTypes)):
            if activity in self.discretionaryActivities:
                self.discretionaryActivityTypes.append(activity)
            else:
                self.mandatoryActivityTypes.append(activity)
        self.pattern = None

    def determine_parameters(self):
        for a in range(len(self.activityTypes)):
            # beta (scale) parameter
            self.parameters.append([self.pattern.averageEffectiveDuration[a]])

        # Minimum duration for home activity
        self.parameters[0].append(0)
        # parameters[0].append(8)

        # Minimum duration for other activityTypes
        for a in range(1, len(self.activityTypes)):
            self.parameters[a].append(0)
            # parameters[a].append(parameters[a][0] * (1 - (parameters[0][0] - parameters[0][1]) / parameters[0][0]))

        # Set shape parameter for home activity
        self.parameters[0].append(1)

        # Shape parameter for other activityTypes
        for a in range(1, len(self.activityTypes)):
            self.parameters[a].append(self.parameters[0][2] * (self.parameters[0][0] - self.parameters[0][1]) /
                                 (self.parameters[a][0] - self.parameters[a][1]))

        self.averageUtility = math.log2(self.pattern.averageEffectiveDuration[0])

