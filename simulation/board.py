from collections import deque

from simulation.utils import calc_distance

HEX_DIRECTIONS = [
    (1, -1, 0),
    (1, 0, -1),
    (0, 1, -1),
    (-1, 1, 0),
    (-1, 0, 1),
    (0, -1, 1)
]

class Board:
    def __init__(self, tiles=None, regions=None):
        if tiles is None:
            tiles = {}
        self.tiles = tiles

        if regions is None:
            regions = {}
        self.regions = regions

    def get_tile_by_coord(self, q, r, s):
        if q + r + s != 0:
            return None

        return self.tiles.get((q, r, s))

    def get_region_by_coord(self, q, r, s):
        if q + r + s != 0:
            print(f"{q}, {r}, {s}")
            return None

        tile = self.get_tile_by_coord(q, r, s)
        corresponding_region = None

        for region in self.regions.values():

            if tile in region.tiles.values():
                corresponding_region = region

        return corresponding_region

    def get_tiles_in_range(self, center_tile, radius):
        results = []

        for dq in range(-radius, radius + 1):
            for dr in range(max(-radius, -dq - radius), min(radius, -dq + radius) + 1):
                ds = -dq - dr

                tile = self.tiles.get((center_tile.q + dq, center_tile.r + dr, center_tile.s + ds))
                if tile is not None:
                    results.append(tile)
        return results

    def get_neighbouring_tiles(self, tile, tiles=None):
        results = []

        if tiles is None:
            tiles = self.tiles

        for dq, dr, ds in HEX_DIRECTIONS:
            neighbour = tiles.get((
                tile.q + dq,
                tile.r + dr,
                tile.s + ds
            ))

            if neighbour is not None:
                results.append(neighbour)
        return results

    def get_neighbouring_region_ids(self, region):
        neighbouring_regions = set()

        tile_to_region = {
            tile: current_region
            for current_region in self.regions.values()
            for tile in current_region.tiles
        }

        for tile in region.tiles:
            for neighbour in self.get_neighbouring_tiles(self.get_tile_by_coord(tile[0], tile[1], tile[2])):

                neighbour_region = tile_to_region.get(neighbour)

                if neighbour_region is not None and neighbour_region != region:
                    neighbouring_regions.add(neighbour_region.region_id)

        return list(neighbouring_regions)      

    def find_shortest_path(self, start_tile, end_tile, max_distance, occupancy=None):
        if calc_distance(start_tile.q, start_tile.r, start_tile.s, end_tile.q, end_tile.r, end_tile.s) > max_distance:
            return None

        queue = deque([start_tile])
        visited = {start_tile}
        came_from = {}
        distance = {
            start_tile: 0,
        }

        if occupancy is None:
            occupancy = self.tiles

        while queue:
            current = queue.popleft()

            if current == end_tile:
                break

            for neighbour in self.get_neighbouring_tiles(current, tiles=occupancy):
                if occupancy.get((neighbour.q, neighbour.r, neighbour.s)).unit is not None:
                    continue

                if neighbour in visited:
                    continue

                new_distance = distance[current] + 1
                if new_distance > max_distance:
                    continue

                visited.add(neighbour)
                distance[neighbour] = new_distance
                came_from[neighbour] = current

                queue.append(neighbour)

        if end_tile not in came_from and end_tile != start_tile:
            return None

        path = [end_tile]
        current = end_tile
        while current != start_tile:
            current = came_from[current]
            path.append(current)

        path.reverse()
        return path