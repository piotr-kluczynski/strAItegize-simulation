import random
import unittest

from unittest.mock import patch

from strAItegize_common.others.order import Order
from strAItegize_common.others.recruitment_choice import RecruitmentChoice

from simulation.region import Region
from simulation.simulation import Simulation, UNIT_TYPES, PlayerStatus
from simulation.tile import Tile
from simulation.unit import Unit

class TestPlacingUnits(unittest.TestCase):
    def test_place_unit_sets_tile(self):
        simulation = prepare_simulation()

        # We add unit to place on different tile
        simulation.add_unit(
            "light_infantry",
            simulation.players[0],
            0, 0, 0
        )

        unit = simulation.board.get_tile_by_coord(0, 0, 0).unit
        tile = simulation.board.get_tile_by_coord(0, -1, 1)

        simulation.place_unit(unit, tile)
        results = (
            unit.tile == tile, # Unit
            tile.unit == unit, # Tile
            simulation.board.tiles[(tile.q, tile.r, tile.s)].unit == unit # Occupancy
        )

        self.assertEqual(results, (True, True, True))
    def test_place_unit_clears_old_tile(self):
        simulation = prepare_simulation()

        # We add unit to place on different tile
        simulation.add_unit(
            "light_infantry",
            simulation.players[0],
            0, 0, 0
        )

        unit = simulation.board.get_tile_by_coord(0, 0, 0).unit
        tile = simulation.board.get_tile_by_coord(0, -1, 1)

        simulation.place_unit(unit, tile)
        results = (
            simulation.board.get_tile_by_coord(0, 0, 0).unit is None,
            (0, 0, 0) != (unit.tile.q, unit.tile.r, unit.tile.s)
        )

        self.assertEqual(results, (True, True))

class TestAddingUnits(unittest.TestCase):
    def test_add_unit_valid(self):
        simulation = prepare_simulation()

        simulation.add_unit(
            "light_infantry",
            simulation.players[0],
            0, 0, 0
        )

        self.assertIsInstance(simulation.units["light_infantry_0"], Unit)
    def test_add_unit_occupied_tile(self):
        simulation = prepare_simulation()

        simulation.add_unit(
            "light_infantry",
            simulation.players[0],
            0, 0, 0
        )

        # We try to add another unit on the same tile
        result = simulation.add_unit(
            "heavy_infantry",
            simulation.players[1],
            0, 0, 0
        )

        self.assertFalse(result)
    def test_add_unit_invalid_coord(self):
        simulation = prepare_simulation()

        result = simulation.add_unit(
            "light_infantry",
            simulation.players[0],
            -1, -1, 1
        )

        self.assertFalse(result)
    def test_add_unit_all_types(self):
        simulation = prepare_simulation()

        tiles = random.sample(list(simulation.board.tiles.values()), len(UNIT_TYPES))

        results = []
        expected = [True for _ in range(len(UNIT_TYPES))]

        for tile, unit_type in zip(tiles, UNIT_TYPES):
            results.append(
                simulation.add_unit(
                    unit_type,
                    random.choice(simulation.players),
                    tile.q, tile.r, tile.s
                )
            )

        self.assertEqual(results, expected)
    def test_add_unit_increments_id(self):
        simulation = prepare_simulation()

        # Creating one unit of each type
        tiles = random.sample(list(simulation.board.tiles.values()), len(UNIT_TYPES))

        results = []
        expected = [True for _ in range(len(UNIT_TYPES))]

        for tile, unit_type in zip(tiles, UNIT_TYPES):
            results.append(
                simulation.add_unit(
                    unit_type,
                    random.choice(simulation.players),
                    tile.q, tile.r, tile.s
                )
            )
        self.assertEqual(results, expected)

class TestMovementAction(unittest.TestCase):
    def test_move_unit_valid(self):
        simulation = prepare_simulation()

        # Adding unit to test movement on
        simulation.add_unit(
            "light_infantry",
            simulation.players[0],
            0, 0, 0
        )

        simulation.move_unit(
            simulation.board.get_tile_by_coord(0, 0, 0).unit,
            0, 1, -1
        )

        self.assertIsNotNone(simulation.board.get_tile_by_coord(0, 1, -1).unit)
    def test_move_unit_occupied(self):
        simulation = prepare_simulation()

        # Adding unit to test movement on
        simulation.add_unit(
            "light_infantry",
            simulation.players[0],
            0, 0, 0
        )

        # Adding unit to block the target tile
        simulation.add_unit(
            "cavalry",
            simulation.players[1],
            0, -1,  1
        )

        result = simulation.move_unit(
            simulation.board.get_tile_by_coord(0, 0, 0).unit,
            0, -1, 1
        )

        self.assertFalse(result)
    def test_move_unit_off_board(self):
        simulation = prepare_simulation(radius=1)

        # Adding unit to test movement on
        simulation.add_unit(
            "light_infantry",
            simulation.players[0],
            0, -1, 1
        )

        unit = simulation.board.get_tile_by_coord(0, -1, 1).unit

        simulation.move_unit(
            unit,
            0, -1, 1
        )

        self.assertEqual(
            unit.tile, 
            simulation.board.tiles[0, -1, 1]
        )

class TestAttackAction(unittest.TestCase):
    @patch('random.randint')
    def test_attack_defender_holds(self, mock_randint):
        mock_randint.side_effect = [3, 5]
        simulation = prepare_simulation()

        # Adding attacker unit
        simulation.add_unit(
            "light_infantry",
            simulation.players[0],
            0, 0, 0
        )
        attacker = simulation.board.get_tile_by_coord(0, 0, 0).unit

        # Adding defender unit
        simulation.add_unit(
            "heavy_infantry",
            simulation.players[1],
            0, -1, 1
        )
        defender = simulation.board.get_tile_by_coord(0, -1, 1).unit

        simulation.attack_unit(attacker, defender)
        self.assertIsNotNone(simulation.board.get_tile_by_coord(0, 0, 0).unit)
    @patch('random.randint')
    def test_attack_defender_pushed(self, mock_randint):
        mock_randint.side_effect = [5, 3]
        simulation = prepare_simulation()

        # Adding attacker unit
        simulation.add_unit(
            "light_infantry",
            simulation.players[0],
            0, 0, 0
        )
        attacker = simulation.board.get_tile_by_coord(0, 0, 0).unit

        # Adding defender unit
        simulation.add_unit(
            "heavy_infantry",
            simulation.players[1],
            0, -1, 1
        )
        defender = simulation.board.get_tile_by_coord(0, -1, 1).unit

        simulation.attack_unit(attacker, defender)
        self.assertEqual(simulation.board.get_tile_by_coord(0, -2, 2).unit, defender)
    @patch('random.randint')
    def test_attack_defender_destroyed(self, mock_randint):
        mock_randint.side_effect = [6, 2]
        simulation = prepare_simulation()

        # Adding attacker unit
        simulation.add_unit(
            "light_infantry",
            simulation.players[0],
            0, 0, 0
        )
        attacker = simulation.board.get_tile_by_coord(0, 0, 0).unit

        # Adding defender unit
        simulation.add_unit(
            "heavy_infantry",
            simulation.players[1],
            0, -1, 1
        )
        defender = simulation.board.get_tile_by_coord(0, -1, 1).unit

        defender_id = defender.unit_id

        simulation.attack_unit(attacker, defender)
        self.assertEqual(
            simulation.units.get(defender_id), 
            None
        )
    @patch('random.randint')
    def test_attack_attacker_advances(self, mock_randint):
        mock_randint.side_effect = [5, 3]
        simulation = prepare_simulation()

        # Adding attacker unit
        simulation.add_unit(
            "light_infantry",
            simulation.players[0],
            0, 0, 0
        )
        attacker = simulation.board.get_tile_by_coord(0, 0, 0).unit
        attacker.strength = 8

        # Adding defender unit
        simulation.add_unit(
            "heavy_infantry",
            simulation.players[1],
            0, -1, 1
        )
        defender = simulation.board.get_tile_by_coord(0, -1, 1).unit
        defender.strength = 1

        simulation.attack_unit(attacker, defender)
        self.assertEqual(simulation.board.get_tile_by_coord(0, -1, 1).unit, attacker)
        self.assertEqual(simulation.board.get_tile_by_coord(0, -2, 2).unit, defender)
    def test_attack_out_of_range(self):
        simulation = prepare_simulation()

        # Adding attacker unit
        simulation.add_unit(
            "light_infantry",
            simulation.players[0],
            0, 0, 0
        )
        attacker = simulation.board.get_tile_by_coord(0, 0, 0).unit

        # Adding defender unit
        simulation.add_unit(
            "heavy_infantry",
            simulation.players[1],
            0, -2, 2
        )
        defender = simulation.board.get_tile_by_coord(0, -2, 2).unit

        result = simulation.attack_unit(attacker, defender)
        self.assertFalse(result)
    def test_attack_dead_unit(self):
        simulation = prepare_simulation()

        # Adding attacker unit
        simulation.add_unit(
            "light_infantry",
            simulation.players[0],
            0, 0, 0
        )
        attacker = simulation.board.get_tile_by_coord(0, 0, 0).unit

        # Adding defender unit
        simulation.add_unit(
            "heavy_infantry",
            simulation.players[1],
            0, -1, 1
        )
        defender = simulation.board.get_tile_by_coord(0, -1, 1).unit
        defender.alive = False

        result = simulation.attack_unit(attacker, defender)
        self.assertFalse(result)

class TestChainPush(unittest.TestCase):
    def test_push_single_unit_free_space(self):
        simulation = prepare_simulation()

        # Adding attacker unit
        simulation.add_unit(
            "light_infantry",
            simulation.players[0],
            0, 0, 0
        )
        attacker = simulation.board.get_tile_by_coord(0, 0, 0).unit

        # Adding defender unit
        simulation.add_unit(
            "heavy_infantry",
            simulation.players[1],
            0, -1, 1
        )
        defender = simulation.board.get_tile_by_coord(0, -1, 1).unit

        simulation.push_chain(attacker, defender)
        self.assertEqual(simulation.board.get_tile_by_coord(0, -2, 2).unit, defender)
    def test_push_chain_two_allies(self):
        simulation = prepare_simulation()

        # Adding attacker unit
        simulation.add_unit(
            "light_infantry",
            simulation.players[0],
            0, 0, 0
        )
        attacker = simulation.board.get_tile_by_coord(0, 0, 0).unit

        # Adding defender unit
        simulation.add_unit(
            "heavy_infantry",
            simulation.players[1],
            0, -1, 1
        )
        defender = simulation.board.get_tile_by_coord(0, -1, 1).unit

        # Adding another unit behind defender
        simulation.add_unit(
            "cavalry",
            simulation.players[1],
            0, -2, 2
        )
        ally = simulation.board.get_tile_by_coord(0, -2, 2).unit

        simulation.push_chain(attacker, defender)
        self.assertEqual(simulation.board.get_tile_by_coord(0, -3, 3).unit, ally)
    def test_push_unit_against_wall(self):
        simulation = prepare_simulation(radius=1)

        # Adding attacker unit
        simulation.add_unit(
            "light_infantry",
            simulation.players[0],
            0, 0, 0
        )
        attacker = simulation.board.get_tile_by_coord(0, 0, 0).unit

        # Adding defender unit
        simulation.add_unit(
            "heavy_infantry",
            simulation.players[1],
            0, -1, 1
        )
        defender = simulation.board.get_tile_by_coord(0, -1, 1).unit
        defender_tile = defender.tile

        simulation.push_chain(attacker, defender)
        self.assertFalse(
            defender_tile.unit,
            None
        )
    def test_push_unit_against_enemy(self):
        simulation = prepare_simulation()

        # Adding attacker unit
        simulation.add_unit(
            "light_infantry",
            simulation.players[0],
            0, 0, 0
        )
        attacker = simulation.board.get_tile_by_coord(0, 0, 0).unit

        # Adding defender unit
        simulation.add_unit(
            "heavy_infantry",
            simulation.players[1],
            0, -1, 1
        )
        defender = simulation.board.get_tile_by_coord(0, -1, 1).unit
        defender_tile = defender.tile

        # Adding another enemy unit behind
        simulation.add_unit(
            "cavalry",
            simulation.players[0],
            0, -2, 2
        )

        simulation.push_chain(attacker, defender)
        self.assertEqual(
            defender_tile.unit,
            None
        )

class TestSupportAction(unittest.TestCase):
    def test_support_adds_to_supporting_units(self):
        simulation = prepare_simulation()

        # Adding supporting unit
        simulation.add_unit(
            "light_infantry",
            simulation.players[0],
            0, 0, 0
        )
        supporting = simulation.board.get_tile_by_coord(0, 0, 0).unit

        # Adding supported unit
        simulation.add_unit(
            "heavy_infantry",
            simulation.players[0],
            0, -1, 1
        )
        supported = simulation.board.get_tile_by_coord(0, -1, 1).unit

        simulation.support_unit(supporting, supported)
        self.assertIn(supporting, supported.supporting_units)
    def test_support_out_of_range(self):
        simulation = prepare_simulation()

        # Adding supporting unit
        simulation.add_unit(
            "light_infantry",
            simulation.players[0],
            0, 0, 0
        )
        supporting = simulation.board.get_tile_by_coord(0, 0, 0).unit

        # Adding supported unit
        simulation.add_unit(
            "heavy_infantry",
            simulation.players[0],
            0, -2, 2
        )
        supported = simulation.board.get_tile_by_coord(0, -2, 2).unit

        result = simulation.support_unit(supporting, supported)
        self.assertFalse(result)
    def test_support_dead_unit(self):
        simulation = prepare_simulation()

        # Adding supporting unit
        simulation.add_unit(
            "light_infantry",
            simulation.players[0],
            0, 0, 0
        )
        supporting = simulation.board.get_tile_by_coord(0, 0, 0).unit

        # Adding supported unit
        simulation.add_unit(
            "heavy_infantry",
            simulation.players[0],
            0, -1, 1
        )
        supported = simulation.board.get_tile_by_coord(0, -1, 1).unit
        supported.alive = False

        result = simulation.support_unit(supporting, supported)
        self.assertFalse(result)

class TestBoardOperations(unittest.TestCase):
    def test_get_tile_invalid_coords(self):
        simulation = prepare_simulation()

        result = simulation.board.get_tile_by_coord(3, -1, -1)
        self.assertIsNone(result)
    def test_get_neighbour_center(self):
        simulation = prepare_simulation()

        tile = simulation.board.get_tile_by_coord(0, 0, 0)
        neighbours = simulation.board.get_neighbouring_tiles(tile)

        self.assertIsNotNone(len(neighbours), 6)
    def test_get_neighbours_edge(self):
        simulation = prepare_simulation(radius=1)

        tile = simulation.board.get_tile_by_coord(0, -1, 1)
        neighbours = simulation.board.get_neighbouring_tiles(tile)

        self.assertLess(len(neighbours), 6)
    def test_get_tiles_in_range_no_nones(self):
        simulation = prepare_simulation(radius=1)

        center_tile = simulation.board.get_tile_by_coord(0, 0, 0)
        tiles = simulation.board.get_tiles_in_range(center_tile=center_tile, radius=3)

        self.assertNotIn(None, tiles)
    def test_find_shortest_path_direct(self):
        simulation = prepare_simulation()

        start_tile = simulation.board.get_tile_by_coord(0, 0, 0)
        end_tile = simulation.board.get_tile_by_coord(0, -1, 1)

        path = simulation.board.find_shortest_path(start_tile, end_tile, max_distance=3)
        self.assertEqual(len(path), 2)
    def test_find_shortest_path_blocked(self):
        simulation = prepare_simulation()

        # We add unit to block path
        simulation.add_unit(
            "light_infantry",
            simulation.players[0],
            0, -1, 1
        )
        occupied_tile = simulation.board.get_tile_by_coord(0, -1, 1)

        start_tile = simulation.board.get_tile_by_coord(0, 0, 0)
        end_tile = simulation.board.get_tile_by_coord(0, -2, 2)

        path = simulation.board.find_shortest_path(start_tile, end_tile, max_distance=10)
        self.assertNotIn(occupied_tile, path)
    def test_find_shortest_path_too_far(self):
        simulation = prepare_simulation(radius=5)

        start_tile = simulation.board.get_tile_by_coord(0, 0, 0)
        end_tile = simulation.board.get_tile_by_coord(0, -5, 5)

        path = simulation.board.find_shortest_path(start_tile, end_tile, max_distance=3)
        self.assertIsNone(path)

class TestActionVerification(unittest.TestCase):
    def test_duplicate_action_rejected(self):
        simulation = prepare_simulation()

        # We add unit to give orders to
        simulation.add_unit(
            "light_infantry",
            simulation.players[0],
            0, 0, 0
        )
        unit = simulation.board.get_tile_by_coord(0, 0, 0).unit

        # We add 2 movement orders to the same unit
        player_actions = [
            Order(
                order_type='move',
                unit_id=unit.unit_id,
                move_q=0,
                move_r=-1,
                move_s=1
            ),
            Order(
                order_type='move',
                unit_id=unit.unit_id,
                move_q=1,
                move_r=0,
                move_s=-1
            )
        ]

        with self.assertRaises(Exception):
            simulation.verify_orders_uniqueness(player_actions)

    def test_unowned_unit_rejected(self):
        simulation = prepare_simulation()

        # We add unit to give orders to
        simulation.add_unit(
            "light_infantry",
            simulation.players[1],
            0, 0, 0
        )
        unit = simulation.board.get_tile_by_coord(0, 0, 0).unit

        # We add movement order for the unit
        player = simulation.players[0]

        player_actions = [
            Order(
                order_type='move',
                unit_id=unit.unit_id,
                move_q=0,
                move_r=-1,
                move_s=1
            )
        ]

        with self.assertRaises(Exception):
            simulation.verify_unit_ownership(player, player_actions)
    def test_two_units_same_destination_accepted(self):
        simulation = prepare_simulation()

        # We add first moving unit
        simulation.add_unit(
            "light_infantry",
            simulation.players[1],
            0, 0, 0
        )
        unit1 = simulation.board.get_tile_by_coord(0, 0, 0).unit

        # We add second moving unit
        simulation.add_unit(
            "light_infantry",
            simulation.players[1],
            1, 0, -1
        )
        unit2 = simulation.board.get_tile_by_coord(1, 0, -1).unit

        # We add movement orders
        player_actions = [
            Order(
                order_type='move',
                unit_id=unit1.unit_id,
                move_q=1,
                move_r=-1,
                move_s=0
            ),
            Order(
                order_type='move',
                unit_id=unit2.unit_id,
                move_q=0,
                move_r=-1,
                move_s=1
            )
        ]

        player = simulation.players[1]

        with self.assertRaises(Exception):
            simulation.add_player_orders(player, player_actions)

class TestStartingRound(unittest.TestCase):
    def test_start_round_max_round(self):
        simulation = prepare_simulation(max_round=0)
        result = simulation.start_round()
        self.assertFalse(result)
    def test_start_round_spawns_units(self):
        simulation = prepare_simulation(upkeep_round=1)

        # We set the owner of the region to the first player
        simulation.board.regions["Dalaran"].owner = simulation.players[0]

        # We create recruitment choice for one new unit
        simulation.unit_requests[simulation.players[0]] = [RecruitmentChoice(
            unit_type='light_infantry',
            region='Dalaran'
        )]

        # Start new round with the new_units order
        simulation.start_round()

        self.assertIsNotNone(simulation.board.get_tile_by_coord(0, 0, 0).unit)
    def test_start_round_disbands_unit(self):
        simulation = prepare_simulation(upkeep_round=1)

        # We create new unit to disband
        simulation.add_unit(
            "cavalry",
            simulation.players[1],
            1, 0, -1
        )
        unit = simulation.board.get_tile_by_coord(1, 0, -1)

        simulation.start_round()
        self.assertNotIn(unit, simulation.units.values())
    def test_start_round_non_upkeep(self):
        simulation = prepare_simulation()

        # We set the owner of the region to the first player
        simulation.board.regions["Dalaran"].owner = simulation.players[0]

        # We create new unit (which will be kept even though player 1 can't afford it)
        simulation.add_unit(
            "cavalry",
            simulation.players[1],
            1, 0, -1
        )
        unit = simulation.board.get_tile_by_coord(1, 0, -1).unit

        # We create player recruitment choice for one new unit (which shouldn't go through)
        simulation.unit_requests[simulation.players[0]] = [RecruitmentChoice(
            unit_type='light_infantry',
            region='Dalaran'
        )]

        simulation.start_round()

        result = (
            simulation.board.get_tile_by_coord(1, 0, -1).unit == unit,
            True if simulation.board.get_tile_by_coord(0, 0, 0).unit is None else False,
        )

        self.assertEqual(result, (True, True))

class TestEndingRound(unittest.TestCase):
    def test_end_round_clears_dead_units(self):
        simulation = prepare_simulation()

        simulation.add_unit(
            "light_infantry",
            simulation.players[0],
            0, 0, 0
        )
        unit = simulation.board.get_tile_by_coord(0, 0, 0)
        unit.alive = False

        simulation.end_round()
        self.assertNotIn(unit, simulation.units.values())

    def test_end_round_clears_supports(self):
        simulation = prepare_simulation()

        # We add supporting unit
        simulation.add_unit(
            "light_infantry",
            simulation.players[0],
            0, 0, 0
        )
        supporting = simulation.board.get_tile_by_coord(0, 0, 0).unit

        # We add supported unit
        simulation.add_unit(
            "heavy_infantry",
            simulation.players[0],
            -1, 0, 1
        )
        supported = simulation.board.get_tile_by_coord(-1, 0, 1).unit

        simulation.support_unit(supporting, supported)

        simulation.end_round()
        self.assertEqual([], supported.supporting_units)
    def test_end_round_changes_region_owner(self):
        simulation = prepare_simulation()

        simulation.add_unit(
            "light_infantry",
            simulation.players[0],
            0, 0, 0
        )

        # We set region owner to the second player
        simulation.board.regions["Dalaran"].owner = simulation.players[1]

        simulation.end_round()
        self.assertEqual(simulation.board.regions["Dalaran"].owner, simulation.players[0])

class TestPlayerStatusChange(unittest.TestCase):
    def test_status_change_active_to_lost(self):
        simulation = prepare_simulation()

        # We set the owner of the region to the first player
        simulation.board.regions["Dalaran"].owner = simulation.players[0]

        # Start new round
        simulation.start_round()

        player = simulation.players[1]
        self.assertEqual(PlayerStatus(simulation.players_status[player]), PlayerStatus.LOST)

class TestEndToEnd(unittest.TestCase):
    def test_few_turns(self):
        simulation = prepare_simulation()
        playerA = simulation.players[0]
        playerB = simulation.players[1]

        simulation.board.regions["Dalaran"].owner = simulation.players[0]

        # Creating initial armies for both players
        simulation.add_unit(
            "light_infantry",
            simulation.players[0],
            0, 0, 0
        )
        unitA_1 = simulation.board.get_tile_by_coord(0, 0, 0).unit
        simulation.add_unit(
            "light_infantry",
            simulation.players[0],
            0, -1, 1
        )
        unitA_2 = simulation.board.get_tile_by_coord(0, -1, 1).unit

        simulation.add_unit(
            "heavy_infantry",
            simulation.players[1],
            -1, 2, -1
        )
        unitB_1 = simulation.board.get_tile_by_coord(-1, 2, -1).unit

        simulation.add_unit(
            "cavalry",
            simulation.players[1],
            0, 3, -3
        )
        unitB_2 = simulation.board.get_tile_by_coord(0, 3, -3).unit

        simulation.add_unit(
            "light_infantry",
            simulation.players[1],
            2, 0, -2
        )
        unitB_3 = simulation.board.get_tile_by_coord(2, 0, -2).unit

        # Players give orders
        actions_A = [
            Order(
                order_type='hold',
                unit_id=unitA_1.unit_id
            ),
            Order(
                order_type='support',
                unit_id=unitA_2.unit_id,
                target_id=unitA_1.unit_id
            )
        ]
        simulation.add_player_orders(playerA, actions_A)

        actions_B = [
            Order(
                order_type='move',
                unit_id=unitB_3.unit_id,
                move_q=-1,
                move_r=0,
                move_s=1
            ),
            Order(
                order_type='move',
                unit_id=unitB_1.unit_id,
                move_q=1,
                move_r=-1,
                move_s=0
            ),
            Order(
                order_type='move',
                unit_id=unitB_2.unit_id,
                move_q=-1,
                move_r=-1,
                move_s=2
            )
        ]

        simulation.add_player_orders(playerB, actions_B)

        # Ending first round
        simulation.end_round()

        # Starting second round
        simulation.start_round()

        # Players give orders
        actions_A = [
            Order(
                order_type='hold',
                unit_id=unitA_1.unit_id
            ),
            Order(
                order_type='support',
                unit_id=unitA_2.unit_id,
                target_id=unitA_1.unit_id
            )
        ]
        simulation.add_player_orders(playerA, actions_A)

        actions_B = [
            Order(
                order_type='attack',
                unit_id=unitB_3.unit_id,
                target_id=unitA_1.unit_id
            ),
            Order(
                order_type='attack',
                unit_id=unitB_1.unit_id,
                target_id=unitA_1.unit_id
            ),
            Order(
                order_type='support',
                unit_id=unitB_2.unit_id,
                target_id=unitB_1.unit_id
            )
        ]
        simulation.add_player_orders(playerB, actions_B)

        # Ending second round
        simulation.end_round()

        self.assertTrue(True)

def prepare_simulation(radius=3, max_round=20, upkeep_round=5):
    tiles = {}
    for q in range(-radius, radius+1):
        for r in range(max(-radius, -q-radius), min(radius, -q+radius)+1):
            s = -q - r
            tiles[(q, r, s)] = Tile(q, r, s)

    region = Region(
        "Dalaran",
        tiles,
        (0, 0, 0)
    )

    simulation = Simulation(
        players = ["Alice", "Bob"],
        max_round = max_round,
        upkeep_round = upkeep_round,
        tiles = tiles,
        regions = {region.region_id: region}
    )

    return simulation