import random
from enum import Enum

from simulation.board import Board
from simulation.unit import Unit
from simulation.utils import calc_distance

from registering.simulation_publisher import SimulationPublisher
from registering.simulation_notification import SimulationNotification

from strAItegize_common.others.recruitment_choice import RecruitmentChoice

UNIT_TYPES = {
    "light_infantry": (2, 1, 6),
    "heavy_infantry": (1, 2, 8),
    "cavalry": (3, 3, 6)
}

class PlayerStatus(Enum):
    ACTIVE = "Active"
    LOST = "Lost"

class Simulation:
    def __init__(self, players, max_round, upkeep_round, tiles, regions, type_counters=None):
        self.players = players
        self.players_status = {player: PlayerStatus.ACTIVE for player in players}
        self.players_events = {player: [] for player in players}

        self.players_orders = {}

        self.units = {}
        self.board = Board(tiles, regions)

        self.round = 1
        self.max_round = max_round
        self.upkeep_round = upkeep_round

        self.type_counters = type_counters if type_counters is not None else {unit_type: 0 for unit_type in UNIT_TYPES}

        self.simulation_publisher = SimulationPublisher()

    # OBSERVATION ACTIONS
    def observe_unit(self, unit_id):
        unit = self.units[unit_id]
        return self.board.get_tiles_in_range(unit.tile, 3)
    def observe_region(self, region_id):
        return self.board.regions[region_id].tiles
    def get_player_units(self, player_id):
        return [unit.unit_id for unit in self.units.values() if unit.owner == player_id]
    def get_player_regions(self, player_id):
        return [region.region_id for region in self.board.regions.values() if region.owner == player_id]
    def get_neighbouring_regions(self):
        return [self.board.get_neighbouring_region_ids(region) for region in self.board.regions.values()]
    
    # TURN MANAGEMENT
    def start_round(self, new_units=None):
        print(f"CZY RUNDA JEST UPKEEP? {self.is_upkeep_round()}")
        print(f"RUNDA: {self.round}, UPKEEP: {self.upkeep_round}")
        if self.round > self.max_round:
            return False

        if len([player_status for player_status in self.players_status.values() if self.players_status == PlayerStatus.ACTIVE]) == 1:
            return False
        
        if new_units is None:
            new_units = { player: [] for player in self.players }

        # If the round is the upkeep round
        if self.round % self.upkeep_round == 0:

            # Recruiting/Disbanding units
            for player in self.players:
                supplies = self.calculate_supplies(player)

                if supplies > 0:
                    self.recruit_units(player, supplies, new_units.get(player, []))
                elif supplies < 0:
                    self.disband_units(player, supplies)

        # Checking if players should be removed from the game
        for player in self.players:
            owned_regions = self.get_player_regions(player)
            owned_units = self.get_player_units(player)

            if len(owned_regions) == 0 and len(owned_units) == 0:
                self.players_status[player] = PlayerStatus.LOST

                if self.simulation_publisher is not None:
                    self.simulation_publisher.notify(
                        SimulationNotification(
                            category="PLAYER_STATUS_CHANGE",
                            old_player_status="Active",
                            new_player_status="Lost"
                        )
                    )

        if self.simulation_publisher is not None:
            self.simulation_publisher.notify(
                SimulationNotification(
                    category="ROUND_START"
                )
            )
        return True
    def end_round(self):
        self.execute_players_orders()
        self.players_orders = {}

        # Resetting units temporary parameters
        for unit in self.units.values():
            unit.new_round()

        # Checking if any region should change ownership
        for _, region in self.board.regions.items():
            q, r, s = region.command_centre
            command_centre = self.board.get_tile_by_coord(q, r, s)

            if command_centre.unit is not None:
                unit_owner = command_centre.unit.owner
                region_owner = region.owner

                if unit_owner != region_owner:
                    if self.simulation_publisher is not None:
                        self.simulation_publisher.notify(
                            SimulationNotification(
                                category="REGION_LOST",
                                player_id=region_owner,
                                region_id=region.region_id
                            )
                        )

                    region.owner = unit_owner

                    if self.simulation_publisher is not None:
                        self.simulation_publisher.notify(
                            SimulationNotification(
                                category="REGION_GAINED",
                                player_id=unit_owner,
                                region_id=region.region_id
                            )
                        )

        # Progressing the round counter
        self.round += 1

        if self.simulation_publisher is not None:
            self.simulation_publisher.notify(
                SimulationNotification(
                    category="ROUND_END"
                )
            )

    # UPKEEP ROUND
    def recruit_units(self, player, budget, unit_requests: list[RecruitmentChoice]):
        for unit_request in unit_requests:
            region = self.board.regions[unit_request.region_id]
            cost = UNIT_TYPES[unit_request.unit_type][1]

            if budget < cost:
                break

            q, r, s = region.command_centre
            if self.add_unit(unit_request.unit_type, player, q, r, s):
                budget -= cost
    def disband_units(self, player, deficit):
            units_to_remove = []
    
            for unit in list(self.units.values()):
                if deficit >= 0:
                    break
    
                if unit.owner == player:
                    deficit += unit.upkeep
                    units_to_remove.append(unit)
    
            for unit in units_to_remove:
                self.remove_unit(unit)
    def calculate_supplies(self, player):
        income = 0

        # We add supply value of each controlled region
        for region in self.board.regions.values():
            if region.owner == player:
                income += region.region_upkeep

        # We detract value of each controlled unit
        for unit in self.units.values():
            if unit.owner == player:
                income -= unit.upkeep

        return income

    # PROCESSING PLAYER ACTIONS
    def add_player_orders(self, player, orders_list):
        movement_orders, support_orders, attack_orders = self.process_orders_list(player, orders_list)
        if movement_orders is None:
            return False

        self.players_orders[player] = (movement_orders, support_orders, attack_orders)
        return True
    def execute_order(self, order):
        unit = self.units[order.unit_id]

        if order.order_type == "hold":
            return True

        if order.order_type == "move":
            q = order["move_q"]
            r = order["move_r"]
            s = order["move_s"]

            return self.move_unit(unit, q, r, s)

        target_unit = self.units[order.target_id]

        if order.order_type == "attack":
            return self.attack_unit(unit, target_unit)

        if order.order_type == "support":
            return self.support_unit(unit, target_unit)

        return False
    def execute_players_orders(self):
        # Choosing random order of players
        players_priority = random.sample(self.players, len(self.players))

        # Creating global order of player orders
        all_movement_orders = []
        all_support_orders = []
        all_attack_orders = []
        for player_id in players_priority:
            # We skip the player if they didn't add any orders
            if player_id not in self.players_orders:
                continue

            movement_orders, support_orders, attack_orders = self.players_orders[player_id]

            all_movement_orders.extend(movement_orders)
            all_support_orders.extend(support_orders)
            all_attack_orders.extend(attack_orders)

        all_orders = all_movement_orders + all_support_orders + all_attack_orders
        for order in all_orders:
            self.execute_order(order)

    def process_orders_list(self, player, orders_list):
        # Check if every coordinates or unit_id exists within the simulation
        if not self.verify_faithfulness(orders_list):
            return None, None, None 

        # Check if every unit received up to 1 order
        if not self.verify_orders_uniqueness(orders_list):
            return None, None, None

        # Check if every ordered unit is owned by the player
        if not self.verify_unit_ownership(player, orders_list):
            return None, None, None

        # Check if orders are not invalidating each other
        if not self.verify_correctness(orders_list):
            return None, None, None

        return self.split_orders(orders_list)
    def verify_faithfulness(self, orders_list):
        for order in orders_list:
            # Verifying the unit_id
            if self.units.get(order.unit_id) is None:
                return False

            # Verifying the coordinates for movement orders
            if order.order_type == "move":
                dq = order.move_q
                dr = order.move_r
                ds = order.move_s

                unit = self.units[order.unit_id]
                target_coord = (unit.tile.q + dq, unit.tile.r + dr, unit.tile.s + ds)

                if self.board.tiles.get(target_coord) is None:
                    return False

            # Verifying target_id for attack and support orders
            elif order.order_type == "attack" or order.order_type == "support":
                if self.units.get(order.target_id) is None:
                    return False

        return True         
    def verify_orders_uniqueness(self, orders_list):
        ids = [a.unit_id for a in orders_list]
        return len(ids) == len(set(ids))
    def verify_unit_ownership(self, player, orders_list):
        for order in orders_list:
            unit = self.units[order.unit_id]
            if unit.owner != player:
                return False

        return True
    def verify_correctness(self, orders_list):
        # Creating artificial occupancy to predict unit movement
        sim_units = {
            unit_id: (self.units[unit_id]).copy()
            for order in orders_list 
            if (unit_id := order.unit_id) in self.units
        }
        sim_tiles = self.board.tiles.copy()

        # Simulating unit actions to check if orders are not invalidating each other
        move_orders, support_orders, attack_orders = self.split_orders(orders_list)

        for move_order in move_orders:
            unit_id = move_order.unit_id
            q = move_order.move_q
            r = move_order.move_r
            s = move_order.move_s

            if self.board.find_shortest_path(sim_units[unit_id].tile, sim_tiles[q, r, s], sim_units[unit_id].movement, sim_tiles) is None:
                return False

            # Updating the simulated occupancy
            sim_units[unit_id].tile.unit = None
            sim_units[unit_id].tile = sim_tiles[q, r, s]
            sim_tiles[q, r, s] = sim_units[unit_id]
            

        for support_order in support_orders:
            unit_id = support_order.unit_id
            target_id = support_order.target_id

            unit1 = sim_units[unit_id]
            unit2 = sim_units[target_id]

            q1, r1, s1 = unit1.tile.q, unit1.tile.r, unit1.tile.s
            q2, r2, s2 = unit2.tile.q, unit2.tile.r, unit2.tile.s

            if calc_distance(q1, r1, s1, q2, r2, s2) > 1:
                return False

        for attack_order in attack_orders:
            unit_id = attack_order.unit_id
            target_id = attack_order.target_id

            q1, r1, s1 = sim_tiles[unit_id]
            q2, r2, s2 = sim_tiles[target_id]

            if calc_distance(q1, r1, s1, q2, r2, s2) > 1:
                return False
        return True

    def split_orders(self, orders_list):
        move_orders = [a for a in orders_list if a.order_type == "move"]
        support_orders = [a for a in orders_list if a.order_type == "support"]
        attack_orders = [a for a in orders_list if a.order_type == "attack"]

        return move_orders, support_orders, attack_orders

    # UNITS MANAGMENT
    def add_unit(self, unit_type, owner, q, r, s):
        tile = self.board.get_tile_by_coord(q, r, s)
        if tile is None or tile.unit is not None:
            return False

        # Creating the new unit
        movement, upkeep, strength = UNIT_TYPES[unit_type]
        unit_id = f"{unit_type}_{self.type_counters[unit_type]}"
        unit = Unit(unit_id, owner, movement, upkeep, strength)
        self.units[unit_id] = unit

        if self.simulation_publisher is not None:
            self.simulation_publisher.notify(
                SimulationNotification(
                    category="UNIT_RECRUITED",
                    player_id=owner,
                    unit_id=unit_id
                )
            )

        # Placing the unit on the new position
        self.place_unit(unit, tile)

        self.type_counters[unit_type] += 1
        return True
    def remove_unit(self, unit):
        unit.tile.unit = None
        unit.tile = None
        del self.units[unit.unit_id]

        if self.simulation_publisher is not None:
            self.simulation_publisher.notify(
                SimulationNotification(
                    category="UNIT_DESTROYED",
                    player_id=unit.owner,
                    unit_id=unit.unit_id
                )
            )

    def push_chain(self, unit1, unit2):
        chain = []

        current_tile = unit2.tile

        # Calculating the direction of the push
        dq = current_tile.q - unit1.tile.q
        dr = current_tile.r - unit1.tile.r
        ds = current_tile.s - unit1.tile.s

        # Building chain of tiles
        while current_tile.unit is not None:
            unit = current_tile.unit
            chain.append(unit)

            next_tile = self.board.get_tile_by_coord(
                current_tile.q + dq,
                current_tile.r + dr,
                current_tile.s + ds
            )

            # Board end
            if next_tile is None:
                break

            # The path is blocked by not allied unit (if such unit exists)
            if next_tile.unit is not None and next_tile.unit.owner is not unit2.owner:
                break

            current_tile = next_tile

        # Checking if the last tile is free
        can_escape = current_tile.unit is None

        # If there's no space to fall back, the unit dies
        if not can_escape:
            self.remove_unit(unit2)
            return True

        # Moving to the back
        for unit in reversed(chain):
            old_tile = unit.tile

            new_tile = self.board.get_tile_by_coord(
                old_tile.q + dq,
                old_tile.r + dr,
                old_tile.s + ds
            )

            self.place_unit(unit, new_tile)
        return True
    def place_unit(self, unit, tile):
        # We remove the old tile
        if unit.tile is not None:
            # If the tile existed then the unit must have been moved
            if self.simulation_publisher is not None:
                self.simulation_publisher.notify(
                    SimulationNotification(
                        category="UNIT_MOVED",
                        unit_id=unit.unit_id,
                        old_q=unit.tile.q,
                        old_r=unit.tile.r,
                        old_s=unit.tile.s,
                        new_q=tile.q,
                        new_r=tile.r,
                        new_s=tile.s
                    )
                )

            unit.tile.unit = None

        # We place the unit on the new tile
        unit.tile = tile
        if tile is not None:
            tile.unit = unit

    # UNIT ACTIONS
    def move_unit(self, unit, dq, dr, ds):
        # Check if the target tile exists
        target_tile = self.board.get_tile_by_coord(unit.tile.q+dq, unit.tile.r+dr, unit.tile.s+ds)
        if target_tile is None:
            return False

        # Check if the target tile is in range
        shortest_path = self.board.find_shortest_path(unit.tile, target_tile, unit.movement, self.board.tiles)
        if shortest_path is None:
            return False

        # Check if the target tile isn't already occupied
        if target_tile.unit is not None:
            return False

        # Move unit to the target tile
        self.place_unit(unit, target_tile)
        return True
    def attack_unit(self, unit1, unit2):
        tile1 = unit1.tile
        tile2 = unit2.tile

        if calc_distance(tile1.q, tile1.r, tile1.s, tile2.q, tile2.r, tile2.s) > 1:
            return False

        if not unit2.alive:
            return False

        attack_power = random.randint(1, unit1.strength) + 2 * len(unit1.supporting_units)
        defend_power = random.randint(1, unit2.strength) + 2 * len(unit2.supporting_units)

        if defend_power >= attack_power:
            # Defenders stand their ground
            if self.simulation_publisher is not None:
                self.simulation_publisher.notify(
                    SimulationNotification(
                        category="ATTACK_OUTCOME",
                        player_id=unit1.owner,
                        unit_id=unit1.unit_id,
                        target_id=unit2.unit_id,
                        combat_outcome="defeat"
                    )
                )

                self.simulation_publisher.notify(
                    SimulationNotification(
                        category="DEFEND_OUTCOME",
                        player_id=unit2.owner,
                        unit_id=unit2.unit_id,
                        target_id=unit1.unit_id,
                        combat_outcome="victory"
                    )
                )

            return True
        else:
            if 2*defend_power <= attack_power:
                # Defenders are completely destroyed
                self.remove_unit(unit2)

                if self.simulation_publisher is not None:
                    self.simulation_publisher.notify(
                        SimulationNotification(
                            category="ATTACK_OUTCOME",
                            player_id=unit1.owner,
                            unit_id=unit1.unit_id,
                            target_id=unit2.unit_id,
                            combat_outcome="obliteration"
                        )
                    )

                    self.simulation_publisher.notify(
                        SimulationNotification(
                            category="DEFEND_OUTCOME",
                            player_id=unit2.owner,
                            unit_id=unit2.unit_id,
                            target_id=unit1.unit_id,
                            combat_outcome="obliteration"
                        )
                    )

                return True

            unit2_old_tile = unit2.tile

            # Defenders were defeated and fall back
            self.push_chain(unit1, unit2)

            # Attacker advances in the created free spot
            self.place_unit(unit1, unit2_old_tile)

            if self.simulation_publisher is not None:
                self.simulation_publisher.notify(
                    SimulationNotification(
                        category="ATTACK_OUTCOME",
                        player_id=unit1.owner,
                        unit_id=unit1.unit_id,
                        target_id=unit2.unit_id,
                        combat_outcome="victory"
                    )
                )

                self.simulation_publisher.notify(
                    SimulationNotification(
                        category="DEFEND_OUTCOME",
                        player_id=unit2.owner,
                        unit_id=unit2.unit_id,
                        target_id=unit1.unit_id,
                        combat_outcome="defeat"
                    )
                )

            return True
    def support_unit(self, unit1, unit2):
        tile1 = unit1.tile
        tile2 = unit2.tile

        if calc_distance(tile1.q, tile1.r, tile1.s, tile2.q, tile2.r, tile2.s) > 1:
            return False

        if not unit2.alive:
            return False

        unit2.supporting_units.append(unit1)
        return True

    # OTHERS
    def get_players_scores(self):
        players_scores = {}
        for player in self.players:
            players_scores[player] = 0
            owned_regions = self.get_player_regions(player)
            owned_units = self.get_player_units(player)

            for region_id in owned_regions:
                players_scores[player] += len(self.board.regions[region_id].tiles)

            for unit_id in owned_units:
                players_scores[player] += self.units[unit_id].upkeep

        return players_scores
    def is_upkeep_round(self):
        return self.round % self.upkeep_round == 0
    
    def get_round_data(self):
        leader_board_dict = self.get_players_scores()

        all_controlled_units = {}
        all_controlled_regions = {}
        all_enemy_units_per_region = {}
        all_enemy_units_per_region = {}
        for player in self.players:

            leader_board_dict = {player: score for player, score in sorted(leader_board_dict.items(), key=lambda score: score[1])}

            all_controlled_units[player] = []
            for unit_id, unit in self.units.items():
                if unit.owner == player:
                    all_controlled_units[player].append(unit_id)

            all_controlled_regions[player] = [region_id for region_id in self.get_player_regions(player)]

            all_enemy_units_per_region[player] = [[] for _ in all_controlled_regions]
            for unit_id, unit in self.units.items():
                if unit.owner != player:
                    for i in range(len(all_controlled_regions[player])):
                        if unit.tile in self.board.regions[all_controlled_regions[player][i]].tiles:
                            all_enemy_units_per_region[player][i].append(unit_id)

        return {
            "current_round": self.round,
            "final_round": self.max_round,
            "players": [player for player in self.players if self.players_status[player] == PlayerStatus.ACTIVE],
            "leaderboard_dict": leader_board_dict,
            "controlled_units": all_controlled_units,
            "controlled_regions": all_controlled_regions,
            "enemy_units_per_region": all_enemy_units_per_region,
            "event_dict": self.players_events
        }