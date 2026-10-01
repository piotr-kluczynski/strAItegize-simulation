class Region:
    def __init__(self, region_id, tiles, command_centre, owner=None, region_upkeep=2):
        self.region_id = region_id
        self.tiles = tiles
        self.command_centre = command_centre
        self.owner = owner
        self.region_upkeep = region_upkeep