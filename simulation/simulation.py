import random
from enum import Enum

from simulation.tile import Tile
from simulation.region import Region

from simulation.board import Board
from simulation.unit import Unit
from simulation.utils import calc_distance

from registering.simulation_publisher import SimulationPublisher
from registering.simulation_notification import SimulationNotification

from strAItegize_common.others.recruitment_choice import RecruitmentChoice
from strAItegize_common.others.order import Order

UNIT_TYPES = {
    "light_infantry": (2, 1, 6),
    "heavy_infantry": (1, 2, 8),
    "cavalry": (3, 3, 6)
}

class PlayerStatus(Enum):
    ACTIVE = "Active"
    LOST = "Lost"

class Simulation:
    """ Class responsible for managing the simulation, allowing for seamless proceeding between round, using methods such as start_round or add_player_orders.
        Utilizes middle and low-level classes, such as Board, or Unit to provide a high-level interface to interact with its environment.
    """
    def __init__(self, players: list[str], max_round: int, upkeep_round: int, tiles: dict[tuple[int, int, int], Tile], regions: dict[str, Region], type_counters:dict[str, int]=None):
        """Method initializing the Simulation object, and setting up default values for its properties.

        Args: 
        - players: list[str] - list of player_id's, assigned to players property,
        - max_round: int - round limit, after which simulation will end, assigned to max_round property,
        - tiles: dict[tuple[int, int, int], Tile] - dictionary ((q, r, s):Tile) building together the game board, used to initialize the Board object for board property,
        - regions: dict[str, Region] - dictionary (region_id:Region) creating the administrative division of the game board, used to initialize the Board object for board property,
        - type_counters: dict[str, int] - dictionary (str:int) containing the first available id number per unit type, assigned to the type_counters property.

        Returns: None
        """
        # List of player_id's (str) used for their identification.
        self.players = players 
        # Dictionary (player_id:PlayerStatus) describing whether player still participates in the simulation.
        self.players_status = {player: PlayerStatus.ACTIVE for player in players}
        # Dictionary (player_id:List[str]) containing "simulation events" to display for players at the round start.
        self.players_events = {player: [] for player in players}

        self.unit_requests: dict[str, list[RecruitmentChoice]] = {player: [] for player in players}

        # Dictionary (player_id:List[UnitOrder]) containing orders given by the players to be executed at the round end.
        self.players_orders = {}

        # Dictionary (unit_id:Unit) containing all units within the simulation.
        self.units = {}
        # Board class object, related to the current session.
        self.board = Board(tiles, regions)

        # Round counter, increased at the round end.
        self.round = 1
        # Round limit (integer), after which the simulation will end.
        self.max_round = max_round
        # The round frequency (integer) with which the "upkeep round" occurs, resulting in recruitment/disbanding of units.
        self.upkeep_round = upkeep_round

        # Dictionary (str:int) containing the most recent id number of recruited unit, separate for each unit type. Used to generate unique unit ids.
        self.type_counters = type_counters if type_counters is not None else {unit_type: 0 for unit_type in UNIT_TYPES}

        # SimulationPublisher class object, allowing simulation to signal specific occurrences to be processed independently by other systems.
        self.simulation_publisher = SimulationPublisher()

    # OBSERVATION ACTIONS
    def observe_unit(self, unit_id: str) -> list[Tile]:
        """
        Method returning all tiles within the range of 3 units of distance from the unit with given unit_id. Used for providing simulation information to the session participants.
        
        Args:
            - unit_id - unique identifier of the chosen unit.

        Returns: List of Tile class objects surrounding the unit with given unit_id.
        """
        unit = self.units[unit_id]
        return self.board.get_tiles_in_range(unit.tile, 3)
    def observe_region(self, region_id: str) -> list[Tile]:
        """
        Method returning all tiles belonging to the region with given region_id. Used for providing simulation information to the session participants.

        Args:
        - region_id: str - unique identifier of the chosen region.

        Returns:
        tiles: list[Tile] - List of Tile class objects assigned to the region with given region_id.
        """
        return self.board.regions[region_id].tiles
    def get_player_units(self, player_id: str) -> list[str]:
        """
        Method returning unit_id's of all units belonging to the player with given player_id. Used for providing simulation information to the session participants.

        Args:
        - player_id: str - unique identifier of the chosen player.

        Returns:
        unit_ids: list[str] - List of unit_ids of all units owned by the player.
        """
        return [unit.unit_id for unit in self.units.values() if unit.owner == player_id]
    def get_player_regions(self, player_id: str) -> list[str]:
        """
        Method returning region_id's of all regions controlled by the player with given player_id. Used for providing simulation information to the session participants.

        Args:
        - player_id: str - unique identifier of the chosen player.

        Returns:
        region_ids: list[str] - List of region_ids of all regions controlled by the player.
        """
        return [region.region_id for region in self.board.regions.values() if region.owner == player_id]
    def get_neighbouring_regions(self) -> list[list[str]]:
        """
        Method returning nested list of neighbouring region ids for each region within the simulation session. 
        Used for providing simulation information to the session participants.

        Args: None

        Returns:
        neighbouring_regions_ids: list[list[str]] - List of region_ids for each region.
        """
        return [self.board.get_neighbouring_region_ids(region) for region in self.board.regions.values()]
    
    # TURN MANAGEMENT
    def start_round(self) -> bool:
        """
        High-level method initializing new round, and preparing components within the simulation. Stops the simulation if game over conditions has been met, performs the upkeep phase if needed, and removing unsuccessful participants from the simulation.

        Args:
        - new_units: dict[str, list[RecruitmentChoice]] - optional argument, by which the choice regarding unit recruitment choice is passed(only on upkeep rounds). None by default.

        Returns: 
        does_sim_cont: bool - False if simulation has come to an end, True otherwise.
        """
        if self.round > self.max_round:
            return False

        if len([player_status for player_status in self.players_status.values() if self.players_status == PlayerStatus.ACTIVE]) == 1:
            return False

        # If the round is the upkeep round
        if self.round % self.upkeep_round == 0:

            # Recruiting/Disbanding units
            for player in self.players:
                supplies = self.calculate_supplies(player)

                if supplies > 0:
                    self.recruit_units(player, supplies, self.unit_requests[player])
                elif supplies < 0:
                    self.disband_units(player, supplies)

            self.unit_requests[player] = []

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
        """
        High-level method finalizing current round, and preparing the components within the simulation. 
        Executing player's orders, resetting unit's temporary parameters, changing regions ownership, and increasing round counter.

        Args: None

        Returns: None
        """

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
    def recruit_units(self, player: str, budget: int, recruitment_choices: list[RecruitmentChoice]) -> None:
        """
        Medium-level method creating new units, of type and in a location given by the list of RecruitmentChoice objects. Each request is resolved in for loop, which stops when the end of the list is reached, or the unit requests cost surpasses the budget.

        Args:
        - player: str -  unique identifier of the player recruiting the units,
        - budget: int - the surplus of supplies used to recruit new units,
        - unit_requests: list[RecruitmentChoice] - list of RecruitmentChoice objects containing information, necessary to create new unit.

        Returns: None
        """
        for recruitment_choice in recruitment_choices:
            recruitment_choice = RecruitmentChoice.model_validate(recruitment_choice)

            region = self.board.regions[recruitment_choice.region]
            cost = UNIT_TYPES[recruitment_choice.unit_type][1]

            if budget < cost:
                break

            q, r, s = region.command_centre

            # Attempting to add new unit
            if self.add_unit(recruitment_choice.unit_type, player, q, r, s):
                budget -= cost
    def disband_units(self, player: str, deficit: int) -> None:
        """
        Medium-level method removing units the player's units in the chronological order, called during upkeep phase, when the player's supply is lesser than player's units supply cost.
        Starting from the oldest unit, they are removed from the simulation within a loop, which stops until all units are removed or the supply deficit surprasses zero.

        Args:
        - player: str - unique identifier of the player who's units are being disbanded.
        - deficit: int - the negative integer representing the missing supplies.

        Returns: None 
        """
        units_to_remove = []
    
        for unit in list(self.units.values()):
            if deficit >= 0:
                    break
    
            if unit.owner == player:
                deficit += unit.upkeep
                units_to_remove.append(unit)
    
        for unit in units_to_remove:
            self.simulation_publisher.notify(
                SimulationNotification(
                    category="UNIT_DISBANDED",
                    player_id=player,
                    unit_id=unit.unit_id
                )
            )
            self.remove_unit(unit)
    def calculate_supplies(self, player: str) -> int:
        """
        Low-level method calculating the supply surplus/deficit based on the controlled regions and units. 
        The value is calculated as sum of all controlled regions supply incomes minus sum of all units upkeep costs. 
        Called during the upkeep phase to decide whether the player ought get to choose new units to recruit, or get some of their units disbanded.

        Args:
        - player: str - unique identifier of the player who's units are being disbanded.

        Returns:
        - supply_balance: int - the difference between supply income and supply costs.
        """
        supply_balance = 0

        # We add supply value of each controlled region
        for region in self.board.regions.values():
            if region.owner == player:
                supply_balance += region.region_upkeep

        # We detract value of each controlled unit
        for unit in self.units.values():
            if unit.owner == player:
                supply_balance -= unit.upkeep

        return supply_balance

    # PROCESSING PLAYER ACTIONS
    def add_player_orders(self, player: str, orders_list: list[Order]):
        """
        High-level method verifying the validity and registering the list of orders given by the player. Used to register the player's orders before the round end (when all orders are executed).
        The verification is delegated to the process_orders_list method.

        Args:
        - player: str - unique identifier of the player who's units are being disbanded,
        - orders_list: list[Order] - list of Order objects, assigned by the player.

        """
        movement_orders, support_orders, attack_orders = self.process_orders_list(player, orders_list)
        self.players_orders[player] = (movement_orders, support_orders, attack_orders)
    def execute_order(self, order: Order):
        """
        Medium-level method for executing an appropriate in-simulation action according to the given order type. 

        Args:
        - order: Order - data object containing information needed to perform given action within the simulation.

        Returns:
        - success: bool - False if the action was not possible to perform (e.g.: unit targeted by the attack, was already destroyed), True otherwise.
        """
        unit = self.units[order.unit_id]

        if order.order_type == "hold":
            return

        if order.order_type == "move":
            q = order.move_q
            r = order.move_r
            s = order.move_s

            return self.move_unit(unit, q, r, s)

        target_unit = self.units[order.target_id]

        if order.order_type == "attack":
            return self.attack_unit(unit, target_unit)

        if order.order_type == "support":
            return self.support_unit(unit, target_unit)
    def execute_players_orders(self):
        """
        Medium-level method which combines each player's list of orders, and executes them. 
        The orders are first split into categories based on their type ("hold", "move", "attack" and "support"), before being combined into single order list. All orders are executed in the following order: 1. movement, 2. support, 3. attack. The player order within this hierarchy is chosen randomly each round.

        Args: None

        Returns: None
        """
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
    def process_orders_list(self, player: str, orders_list: list[Order]) -> tuple:
        """
        Medium-level method for preparing the orders for execution. The process is split into 5 separate steps, each calling lower-level function to execute it. 
        In 4 first steps, functions verify_faithfulness, verify_orders_uniqueness, verify_unit_ownership, and verify_correctness are used to check for the errors in the order list. 
        In the final, fifth step, the split_orders function is called to split the list into distinct order lists based on their type.

        Args:
        - player: str - unique identifier of the player who's units are being disbanded,
        - orders_list: list[Order] - list of Order objects assigned by the player.

        Returns:
        - order lists: tuple - (None, None, None) if error has occurred during the verification process, (movement orders, support orders, attack orders) otherwise.
        """
        # Check if every coordinates or unit_id exists within the simulation
        self.verify_faithfulness(orders_list)

        # Check if every unit received up to 1 order
        self.verify_orders_uniqueness(orders_list)

        # Check if every ordered unit is owned by the player
        self.verify_unit_ownership(player, orders_list)

        # Check if orders are not invalidating each other
        self.verify_correctness(orders_list)

        return self.split_orders(orders_list)
    def verify_faithfulness(self, orders_list: list[Order]):
        """
        Low-level method iterating over the orders within the list, verifying whether the target unit/tile exists within the simulation (e.g.: cubic coordinates can be valid, but not actually exist on the game board).

        Args:
        - orders_list: list[Order] - list of Order objects assigned by the player.
        """
        for order in orders_list:
            # Verifying the unit_id
            if self.units.get(order.unit_id) is None:
                raise Exception(f"Unit with unit_id: {order.unit_id} does not exist.")

            # Verifying the coordinates for movement orders
            if order.order_type == "move":
                dq = order.move_q
                dr = order.move_r
                ds = order.move_s

                unit = self.units[order.unit_id]
                target_coord = (unit.tile.q + dq, unit.tile.r + dr, unit.tile.s + ds)

                if self.board.tiles.get(target_coord) is None:
                    raise Exception(f"Tile with position: ({target_coord[0]}, {target_coord[1]}, {target_coord[2]}) does not exist.")

            # Verifying target_id for attack and support orders
            elif order.order_type == "attack" or order.order_type == "support":
                if self.units.get(order.target_id) is None:
                    raise Exception(f"Target of the action with unit_id: {order.target_id} does not exist.")
    def verify_orders_uniqueness(self, orders_list: list[Order]):
        """
        Low-level method verifying whether each unit was given less or equal to 1 order (e.g.: each unit can execute only one action per round).

        Args:
        - orders_list: list[Order] - list of Order objects assigned by the player.
        """
        units_with_orders = []

        for order in orders_list:
            if order.unit_id in units_with_orders:
                raise Exception(f"Unit with unit_id: {order.unit_id} received multiple orders during the same round.")
            else:
                units_with_orders.append(order.unit_id)
    def verify_unit_ownership(self, player: str, orders_list: list[Order]):
        """
        Low-level method for verifying that each order was assigned to the unit owned by the player giving them.

        Args:
        - player: str - unique identifier of the player who gave the order,
        - orders_list: list[Order] - list of Order objects assigned by the player.
        """
        for order in orders_list:
            unit = self.units[order.unit_id]

            if unit.owner != player:
                raise Exception(f"An order to unit with unit_id: {order.unit_id} cannot be assigned, as it belongs to another player: {unit.owner}.")
    def verify_correctness(self, orders_list: list[Order]):
        """
        Low-level method for verifying that the execution of player's own orders do not invalidate the following orders.

        Args:
        - orders_list: list[Order] - list of Order objects assigned by the player.
        """
        # Creating artificial occupancy to predict unit movement
        sim_tiles =  {} 
        for og_tile in self.board.tiles.values():
            tile_copy = Tile(
                q=og_tile.q,
                r=og_tile.r,
                s=og_tile.s
            )

            sim_tiles[(og_tile.q, og_tile.r, og_tile.s)] = tile_copy

        sim_units = {}
        for og_unit in self.units.values():
            unit_copy = Unit(
                unit_id=og_unit.unit_id,
                owner=og_unit.owner,
                movement=og_unit.movement,
                upkeep=og_unit.upkeep,
                strength=og_unit.strength
            )

            # Placing copy on the simulated occupancy
            sim_tile = sim_tiles[(og_unit.tile.q, og_unit.tile.r, og_unit.tile.s)]

            sim_tile.unit = unit_copy
            unit_copy.tile = sim_tile

            sim_units[unit_copy.unit_id] = unit_copy

        # Simulating unit actions to check if orders are not invalidating each other
        move_orders, support_orders, attack_orders = self.split_orders(orders_list)

        for move_order in move_orders:
            unit_id = move_order.unit_id
            dq = move_order.move_q
            dr = move_order.move_r
            ds = move_order.move_s

            unit = sim_units[unit_id]
            start_tile = unit.tile
            target_tile = sim_tiles[(start_tile.q+dq, start_tile.r+dr, start_tile.s+ds)]

            if self.board.find_shortest_path(start_tile, target_tile, unit.movement, sim_tiles) is None:
                raise Exception(f"A movement order to unit with unit_id: {move_order.unit_id} cannot be assigned, as the target tile is out of reach (possibly due to your other unit blocking its path).")

            # Updating the simulated occupancy
            start_tile.unit = None
            unit.tile = target_tile
            target_tile.unit = unit

        for support_order in support_orders:
            unit_id = support_order.unit_id
            target_id = support_order.target_id

            unit1 = sim_units[unit_id]
            unit2 = sim_units[target_id]

            q1, r1, s1 = unit1.tile.q, unit1.tile.r, unit1.tile.s
            q2, r2, s2 = unit2.tile.q, unit2.tile.r, unit2.tile.s

            if calc_distance(q1, r1, s1, q2, r2, s2) > 1:
                raise Exception(f"A support order to unit with unit_id: {support_order.unit_id} cannot be assigned, as the target unit is out of reach (possibly due to your other unit moving).")

        for attack_order in attack_orders:
            unit_id = attack_order.unit_id
            target_id = attack_order.target_id

            unit1 = sim_units[unit_id]
            unit2 = sim_units[target_id]

            q1, r1, s1 = unit1.tile.q, unit1.tile.r, unit1.tile.s
            q2, r2, s2 = unit2.tile.q, unit2.tile.r, unit2.tile.s

            if calc_distance(q1, r1, s1, q2, r2, s2) > 1:
                raise Exception(f"A attack order to unit with unit_id: {attack_order.unit_id} cannot be assigned, as the target unit is out of reach.")
    def split_orders(self, orders_list: list[Order]) -> tuple[list[Order], list[Order], list[Order]]:
        """
        Medium-level method that splits the overall order list into 3 separate lists: movement orders, support orders, attack orders.

        Args:
        - orders_list: list[Order] - list of Order objects assigned by the player.

        Returns:
        - split_orders: tuple[list[Order], list[Order], list[Order]] - tuple containing 3 separate lists of orders.
        """
        move_orders = [a for a in orders_list if a.order_type == "move"]
        support_orders = [a for a in orders_list if a.order_type == "support"]
        attack_orders = [a for a in orders_list if a.order_type == "attack"]

        return move_orders, support_orders, attack_orders

    # UNITS MANAGMENT
    def add_unit(self, unit_type: str, owner: str, q: int, r: int, s: int) -> bool:
        """
        Low-level method creating new unit, and placing it on the game board.

        Args:
        - unit_type: str - identifier of the unit type, used as key in the UNIT_TYPE dictionary,
        - owner: str - unique player identifier, to which new unit is assigned.
        - q: int - value of q coordinate of the tile unit will be placed on,
        - r: int - value of r coordinate of the tile unit will be placed on,
        - s: int - value of s coordinate of the tile unit will be placed on.

        Returns:
        - success: bool - False if an error has occurred while creating or placing the unit, True otherwise.
        """
        tile = self.board.get_tile_by_coord(q, r, s)

        # Checking if tile exists
        if tile is None:
            if self.simulation_publisher is not None:
                self.simulation_publisher.notify(
                    SimulationNotification(
                        category="RECRUITMENT_BLOCKED",
                        player_id=owner,
                        new_q=q,
                        new_r=r,
                        new_s=s
                    )
                )
            return False

        # Checking if tile is not occupied
        if tile.unit is not None:
            if self.simulation_publisher is not None:
                self.simulation_publisher.notify(
                    SimulationNotification(
                        category="RECRUITMENT_BLOCKED",
                        player_id=owner,
                        new_q=q,
                        new_r=r,
                        new_s=s
                    )
                )
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
    def remove_unit(self, unit: Unit):
        """
        Low-level method for completely removing the unit from the simulation.
        All references to it are removed, and the unit key:value pair is removed from the units property dictionary.

        Args:
        - unit: Unit - the unit object to be removed from the simulation.

        Returns: None
        """
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
    def push_chain(self, unit1: Unit, unit2: Unit):
        """
        Low-level method for resolving combat outcome in which retreating defender is blocked by another unit.
        Method iteratively attempts to move the second unit into next tile in the direction opposite to the direction of the attack, creating chain of pushed units until a free tile is found, or lack of it is established. Then either all units in the chain are moved, or the first unit in the chain is destroyed.

        Args:
        - unit1: Unit - the unit object corresponding to the attacker,
        - unit2: Unit - the unit object corresponding to the defender.
        """
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
            return

        # Moving to the back
        for unit in reversed(chain):
            old_tile = unit.tile

            new_tile = self.board.get_tile_by_coord(
                old_tile.q + dq,
                old_tile.r + dr,
                old_tile.s + ds
            )

            self.place_unit(unit, new_tile)
    def place_unit(self, unit: Unit, tile: Tile):
        """
        Low-level method changing the position of given unit to the given tile.
        Modifies all relevant references, in order to ensure game board consistency.

        Args:
        - unit: Unit - the unit object, which location needs to be changed,
        - tile: Tile - the tile object, to which unit needs move to.

        Returns: None.
        """
        # We remove the old tile
        if unit.tile is not None:
            # If the tile existed then the unit must have been moved
            if self.simulation_publisher is not None:
                self.simulation_publisher.notify(
                    SimulationNotification(
                        category="UNIT_MOVED",
                        player_id=unit.owner,
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
    def move_unit(self, unit: Unit, dq: int, dr: int, ds: int):
        """
        Low-level method executing the movement action, by verifying whether the action is possible, and then changing the unit position using place_unit method.

        Args:
        - unit: Unit - the unit object, which location needs to be changed,
        - dq: int - value of change applied to the current q coordinate, 
        - dr: int - value of change applied to the current r coordinate, 
        - ds: int - value of change applied to the current s coordinate, 

        Returns:
        - success: bool - False if movement action is impossible to execute, True otherwise.
        """
        error_flag = False

        # Check if the target tile exists
        target_tile = self.board.get_tile_by_coord(unit.tile.q+dq, unit.tile.r+dr, unit.tile.s+ds)
        if target_tile is None:
            # Sending notification if movement was impossible
            self.simulation_publisher.notify(
                SimulationNotification(
                    category="MOVE_BLOCKED",
                    player_id=unit.owner,
                    unit_id=unit.unit_id,
                    old_q=unit.tile.q,
                    old_r=unit.tile.r,
                    old_s=unit.tile.s,
                    new_q=unit.tile.q+dq,
                    new_r=unit.tile.r+dr,
                    new_s=unit.tile.s+ds
                )
            )
            return

        # Check if the target tile is in range
        shortest_path = self.board.find_shortest_path(unit.tile, target_tile, unit.movement, self.board.tiles)
        if shortest_path is None:
            # Sending notification if movement was impossible
            self.simulation_publisher.notify(
                SimulationNotification(
                    category="MOVE_BLOCKED",
                    player_id=unit.owner,
                    unit_id=unit.unit_id,
                    old_q=unit.tile.q,
                    old_r=unit.tile.r,
                    old_s=unit.tile.s,
                    new_q=unit.tile.q+dq,
                    new_r=unit.tile.r+dr,
                    new_s=unit.tile.s+ds
                )
            )
            return

        # Check if the target tile isn't already occupied
        if target_tile.unit is not None:
            # Sending notification if movement was impossible
            self.simulation_publisher.notify(
                SimulationNotification(
                    category="MOVE_BLOCKED",
                    player_id=unit.owner,
                    unit_id=unit.unit_id,
                    old_q=unit.tile.q,
                    old_r=unit.tile.r,
                    old_s=unit.tile.s,
                    new_q=unit.tile.q+dq,
                    new_r=unit.tile.r+dr,
                    new_s=unit.tile.s+ds
                )
            )
            return

        # Move unit to the target tile
        self.place_unit(unit, target_tile)
    def attack_unit(self, unit1: Unit, unit2: Unit):
        """
        Low-level method executing the attack action, by verifying whether the action is possible, and then performing combat between given units.

        Args:
        - unit1: Unit - attacker object,
        - unit2: Unit - defender object.

        Returns:
        - success: bool - False if attack action is impossible to execute, True otherwise.        
        """
        tile1 = unit1.tile
        tile2 = unit2.tile

        if calc_distance(tile1.q, tile1.r, tile1.s, tile2.q, tile2.r, tile2.s) > 1:
            self.simulation_publisher.notify(
                SimulationNotification(
                    category="ATTACK_BLOCKED",
                    player_id=unit1.owner,
                    unit_id=unit1.unit_id,
                    target_id=unit2.unit_id
                )
            )
            return

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

                return

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
    def support_unit(self, unit1: Unit, unit2: Unit):
        """
        Low-level method executing the support action, by verifying whether the action is possible, and then registering the supporting unit in the list of supporting units of the supported units.

        Args: 
        - unit1: Unit - supporting unit's object,
        - unit2: Unit - supported unit's object.
        """
        error_flag = False

        tile1 = unit1.tile
        tile2 = unit2.tile

        if calc_distance(tile1.q, tile1.r, tile1.s, tile2.q, tile2.r, tile2.s) > 1:
            error_flag = True

        if not error_flag:
            unit2.supporting_units.append(unit1)
        else:
            self.simulation_publisher.notify(
                SimulationNotification(
                    category="SUPPORT_BLOCKED",
                    player_id=unit1.owner,
                    target_id=unit2.unit_id
                )
            )

    # OTHERS
    def get_players_scores(self) -> dict[str, int]:
        """
        Low-level method calculating the player's scores based on their control over the game board.
        Total score is calculated by adding total number of controlled tiles to the sum of controlled unit's upkeep costs.

        Args: None

        Returns: 
        - player scores: dict[str, int] - dictionary containig pairs player_id:score for each player in the simulation.
        """
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
    def is_upkeep_round(self) -> bool:
        """
        Low-level method calculating if the current round should be an upkeep one or not.

        Args: None

        Returns:
        - is_upkeep_round: bool - True if current round is an upkeep one, False otherwise.
        """
        return self.round % self.upkeep_round == 0
    def reset_player_events(self) -> None:
        self.players_events = {player: [] for player in self.players}
    def get_round_data(self) -> dict:
        """
        Low-level method preparing a detailed data about the current round, tailored for each player participating in the simulation. 
        Used to provide information to each player at the beginning of each round.

        Args: None

        Returns:
        - players round data: dict - dictionary containing data about current round.
        """
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
            "leaderboard": leader_board_dict,
            "units": all_controlled_units,
            "regions": all_controlled_regions,
            "tresspasers": all_enemy_units_per_region,
            "events": self.players_events
        }
    def get_players_surplus(self):
        return {
            player: self.calculate_supplies(player) for player in self.players
            if self.players_status[player] != PlayerStatus.LOST and 
            self.calculate_supplies(player) > 0
        }