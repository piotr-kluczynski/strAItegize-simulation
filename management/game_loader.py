import os
import json

from simulation.simulation import Simulation, PlayerStatus
from simulation.region import Region
from simulation.tile import Tile
from simulation.unit import Unit

class GameLoader:
    def __init__(self, dir_name="scenarios"):
        self.path = f"{os.path.abspath(os.getcwd())}//{dir_name}"

    def list_games(self):
        dir_list = os.listdir(self.path)

        # We return only files with .json extension
        return [file for file in dir_list if file.endswith(".json")]

    def get_players(self, file_name):
        with open(f"{self.path}//{file_name}.json") as file:
            data = json.load(file)

            players = []
            for player_data in data["players"]:
                if PlayerStatus(player_data["status"]) != PlayerStatus.LOST:
                    players.append(player_data["player_id"])

            return players

    def load_game(self, file_name):
        with open(os.path.join(self.path, f"{file_name}.json")) as file:
            data = json.load(file)

            # Reading data
            current_round = data["metadata"]["current_round"]
            max_round = data["metadata"]["max_round"]
            upkeep_round = data["metadata"]["upkeep_round"]

            units = {
                unit_data["unit_id"]: Unit(
                    unit_id=unit_data["unit_id"],
                    owner = None,
                    movement=unit_data["movement"],
                    strength=unit_data["strength"],
                    upkeep=unit_data["upkeep"]
                ) for unit_data in data["units"]
            }

            tiles = {
                (tile_data["q"], tile_data["r"], tile_data["s"]): Tile(
                    q=tile_data["q"],
                    r=tile_data["r"],
                    s=tile_data["s"]
                ) for tile_data in data["tiles"]
            }

            regions = {
                region_data["region_id"]: Region(
                    region_id=region_data["region_id"],
                    tiles=[],
                    command_centre=None,
                    owner=None,
                    region_upkeep=region_data["region_upkeep"]
                ) for region_data in data["regions"]
            }

            players = []
            players_status = {}
            for player_data in data["players"]:
                player_id = player_data["player_id"]

                players.append(player_id)
                players_status[player_id] = PlayerStatus(player_data["status"])

                for unit_id in player_data["owned_unit_ids"]:
                    units[unit_id].owner = player_id

                for region_id in player_data["owned_region_ids"]:
                    regions[region_id].owner = player_id

            for region in regions.values():
                region_tiles_data = [tile_data for tile_data in data["tiles"] if tile_data["region"] == region.region_id]
                command_centre_tile_data = [tile_data for tile_data in region_tiles_data if tile_data["is_command_centre"] == True][0]

                region.tiles = []
                for tile_data in region_tiles_data:
                    region.tiles.append(tiles[(tile_data["q"], tile_data["r"], tile_data["s"])])

                region.command_centre = (command_centre_tile_data["q"], command_centre_tile_data["r"], command_centre_tile_data["s"])

            for tile_data in data["tiles"]:
                tile = tiles[(tile_data["q"], tile_data["r"], tile_data["s"])]

                # Linking regions
                region = regions[tile_data["region"]]
                region.tiles.append(tile)

                if tile_data["is_command_centre"]:
                    region.command_centre = (tile_data["q"], tile_data["r"], tile_data["s"])


                # Linking units
                if tile_data["unit"] is not "":
                    unit = units[tile_data["unit"]]

                    tile.unit = unit
                    unit.tile = tile

            simulation = Simulation(
                players=players,
                max_round=max_round,
                upkeep_round=upkeep_round,
                tiles=tiles,
                regions=regions
            )

            simulation.round=current_round
            simulation.units=units
            simulation.players_status=players_status

            return simulation

    def save_game(self, simulation: Simulation, file_name):
        json_dict = {}

        # Writing metadata
        json_dict["metadata"] = {
            "current_round": simulation.round,
            "max_round": simulation.max_round,
            "upkeep_round": simulation.upkeep_round
        }

        # Writing tiles
        json_dict["tiles"] = []
        for tile in simulation.board.tiles.values():
            unit = tile.unit
            region = simulation.board.get_region_by_coord(tile.q, tile.r, tile.s)
            is_command_centre = True if (tile.q, tile.r, tile.s) == region.command_centre else False

            json_dict["tiles"].append(
                {
                    "q": tile.q,
                    "r": tile.r,
                    "s": tile.s,
                    "unit": unit.unit_id if unit is not None else None,
                    "region": region.region_id,
                    "is_command_centre": is_command_centre
                }
            )

        # Writing regions
        json_dict["regions"] = []
        for region in simulation.board.regions.values():
            json_dict["regions"].append(
                {
                    "region_id": region.region_id,
                    "region_upkeep": region.region_upkeep
                }
            )

        # Writing units
        json_dict["units"] = []
        for unit in simulation.units.values():
            json_dict["units"].append(
                {
                    "unit_id": unit.unit_id,
                    "movement": unit.movement,
                    "upkeep": unit.upkeep,
                    "strength": unit.strength
                }
            )

        # Writing players
        json_dict["players"] = []
        for player in simulation.players:
            owned_units = simulation.get_player_units(player)
            owned_regions = simulation.get_player_regions(player)

            json_dict["players"].append(
                {
                    "player_id": player,
                    "owned_unit_ids": owned_units,
                    "owned_region_ids": owned_regions,
                    "status": simulation.players_status[player].value
                }
            )

        with open(os.path.join(self.path, f"{file_name}.json"), "w") as file:
            json.dump(json_dict, file, indent=4)