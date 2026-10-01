class Unit:
    def __init__(self, unit_id, owner, movement, upkeep, strength):
        self.unit_id = unit_id
        self.owner = owner
        self.tile = None

        self.movement = movement
        self.upkeep = upkeep
        self.strength = strength

        self.supporting_units = []

    def new_round(self):
        self.supporting_units = []