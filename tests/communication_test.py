import unittest

from pydantic import BaseModel

from strAItegize_common.communication.message_model import MessageModel
from strAItegize_common.communication.message_types import MessageType
from strAItegize_common.communication.session_phases import SessionPhase
from strAItegize_common.others.order import Order
from strAItegize_common.others.recruitment_choice import RecruitmentChoice
from strAItegize_common.communication.models import ObserveUnitResponse
from strAItegize_common.communication.models import ObserveRegionResponse

from communication.dispatcher import CommandDispatcher
from simulation.simulation import Simulation
from simulation.region import Region
from simulation.tile import Tile
from simulation.utils import calc_distance

class TestCommandDispatcher(unittest.TestCase):
    def test_registering_handler(self):
        # Preparing dispatcher with test handler
        mockup_dispatcher = CommandDispatcher()

        @mockup_dispatcher.register("TEST")
        def handle_test(payload: dict, simulation, player: str) -> dict:
            pass

        self.assertIn(handle_test, mockup_dispatcher._handlers.values())

    def test_using_handler(self):
        # Preparing simulation
        simulation = prepare_simulation()

        # Preparing dispatcher with test handler
        mockup_dispatcher = CommandDispatcher()

        @mockup_dispatcher.register("GET_PLAYERS")
        def handle_test(payload: dict, simulation, player: str) -> dict:
            return {
                "players": simulation.players
            }

        # Preparing mockup message
        message = MessageModel(
            phase=SessionPhase.LobbyPhase,
            round_idx=0,
            msg_type=MessageType.GetPlayers,
            payload={}
        )

        response = mockup_dispatcher.dispatch(message=message, sim_context=simulation, sending_player="test_player")

        self.assertEqual(
            response.get('players'),
            simulation.players
        )

    def test_missing_handler(self):
        # Preparing simulation
        simulation = prepare_simulation()

        # Preparing dispatcher with test handler
        mockup_dispatcher = CommandDispatcher()

        # Preparing mockup message
        message = MessageModel(
            phase=SessionPhase.LobbyPhase,
            round_idx=0,
            msg_type=MessageType.GetPlayers,
            payload={}
        )

        response = mockup_dispatcher.dispatch(message=message, sim_context=simulation, sending_player="test_player")

        print(response)

        self.assertTrue(response.get("error"))

    def test_model_validation_correct(self):
        # Preparing simulation
        simulation = prepare_simulation()

        # Preparing request, response models
        class test_request(BaseModel):
            test_id: int

        class test_response(BaseModel):
            test_id: int

        # Preparing dispatcher with test handler
        mockup_dispatcher = CommandDispatcher()

        @mockup_dispatcher.register("GET_PLAYERS")
        def handle_test(payload: dict, simulation, player: str) -> dict:
            request = test_request.model_validate(payload)
            response = test_response(test_id=request.test_id)

            return response.model_dump()

        # Preparing mockup message
        test_id = 4

        message = MessageModel(
            phase=SessionPhase.LobbyPhase,
            round_idx=0,
            msg_type=MessageType.GetPlayers,
            payload={
                "test_id": test_id
            }
        )

        response = mockup_dispatcher.dispatch(message=message, sim_context=simulation, sending_player="test_player")

        self.assertEqual(
            response.get('test_id'),
            test_id
        )

    def test_model_validation_error(self):
        # Preparing simulation
        simulation = prepare_simulation()

        # Preparing request, response models
        class test_request(BaseModel):
            test_id: int

        class test_response(BaseModel):
            test_id: int

        # Preparing dispatcher with test handler
        mockup_dispatcher = CommandDispatcher()

        @mockup_dispatcher.register("GET_PLAYERS")
        def handle_test(payload: dict, simulation, player: str) -> dict:
            request = test_request.model_validate(payload)
            response = test_response(test_id=request.test_id)

            return response.model_dump()

        # Preparing mockup message
        message = MessageModel(
            phase=SessionPhase.LobbyPhase,
            round_idx=0,
            msg_type=MessageType.GetPlayers,
            payload={}
        )

        
        response = mockup_dispatcher.dispatch(message=message, sim_context=simulation, sending_player="test_player")

        self.assertTrue(response.get("error"))

    def test_other_exceptions(self):
        # Preparing simulation
        simulation = prepare_simulation()

        # Preparing dispatcher with test handler
        mockup_dispatcher = CommandDispatcher()

        @mockup_dispatcher.register("GET_PLAYERS")
        def handle_test(payload: dict, simulation, player: str) -> dict:
            return 2 / 0

        # Preparing mockup message
        message = MessageModel(
            phase=SessionPhase.LobbyPhase,
            round_idx=0,
            msg_type=MessageType.GetPlayers,
            payload={}
        )

        response = mockup_dispatcher.dispatch(message=message, sim_context=simulation, sending_player="test_player")

        self.assertTrue(response.get("error"))

class TestHandlers(unittest.TestCase):
    from communication.handlers import dispatcher

    def test_observe_unit(self):
        # Preparing simulation
        simulation = prepare_simulation()

        simulation.board.regions["Dalaran"].owner = simulation.players[0]

        simulation.add_unit(
            "light_infantry",
            simulation.players[0],
            0, 0, 0
        )

        unit = simulation.board.get_tile_by_coord(0, 0, 0).unit

        # Preparing mockup message
        message = MessageModel(
            phase=SessionPhase.PlanningPhase,
            round_idx=0,
            msg_type=MessageType.ObserveUnit,
            payload={
                "unit_id": unit.unit_id
            }
        )

        response = self.dispatcher.dispatch(
            message=message, 
            sim_context=simulation, 
            sending_player=simulation.players[0]
        )

        self.assertEqual(
            response['observations'],
            prepare_unit_tile_observation(unit=unit, tiles=simulation.observe_unit(unit.unit_id), simulation=simulation)['observations']
        )

    def test_observe_unit_faithfulness_error(self):
        # Preparing simulation
        simulation = prepare_simulation()
        
        simulation.board.regions["Dalaran"].owner = simulation.players[0]

        simulation.add_unit(
            "light_infantry",
            simulation.players[0],
            0, 0, 0
        )
        
        # Preparing mockup message
        message = MessageModel(
            phase=SessionPhase.PlanningPhase,
            round_idx=0,
            msg_type=MessageType.ObserveUnit,
            payload={
                "unit_id": "test_unit"
            }
        )
        
        response = self.dispatcher.dispatch(
            message=message, 
            sim_context=simulation, 
            sending_player=simulation.players[0]
        )
        
        self.assertEqual(
            response,
            {
                "error": True,
                "desc": f"Unit with unit_id:test_unit does not exist.",
                "details": f"Available units:{str(simulation.get_player_units(simulation.players[0]))}"
            }
        )

    def test_observe_unit_authority_error(self):
        # Preparing simulation
        simulation = prepare_simulation()
        
        simulation.board.regions["Dalaran"].owner = simulation.players[0]

        simulation.add_unit(
            "light_infantry",
            simulation.players[1],
            0, 0, 0
        )

        unit = simulation.board.get_tile_by_coord(0, 0, 0).unit
        
        # Preparing mockup message
        message = MessageModel(
            phase=SessionPhase.PlanningPhase,
            round_idx=0,
            msg_type=MessageType.ObserveUnit,
            payload={
                "unit_id": unit.unit_id
            }
        )
        
        response = self.dispatcher.dispatch(
            message=message, 
            sim_context=simulation, 
            sending_player=simulation.players[0]
        )

        available_units = ""
        for unit_id in simulation.get_player_units(simulation.players[0]):
            available_units += f"{unit_id}, "
        available_units = available_units[:-2]
        
        self.assertEqual(
            response,
            {
                "error": True,
                "desc": f"You are not the owner of the unit with unit_id:{unit.unit_id}.",
                "details": f"Available units:{available_units}."
            }
        )

    def test_observe_region(self):
        # Preparing simulation
        simulation = prepare_simulation()

        simulation.board.regions["Dalaran"].owner = simulation.players[0]

        region = simulation.board.get_region_by_coord(0, 0, 0)

        # Preparing mockup message
        message = MessageModel(
            phase=SessionPhase.PlanningPhase,
            round_idx=0,
            msg_type=MessageType.ObserveRegion,
            payload={
                "region_id": region.region_id
            }
        )

        response = self.dispatcher.dispatch(
            message=message, 
            sim_context=simulation, 
            sending_player=simulation.players[0]
        )

        self.assertEqual(
            response['observations'],
            prepare_region_tile_observation(region=region, observed_tiles=simulation.observe_region(region.region_id))['observations']
        )

    def test_observe_region_faithfulness_error(self):
        # Preparing simulation
        simulation = prepare_simulation()
        
        simulation.board.regions["Dalaran"].owner = simulation.players[0]
        
        # Preparing mockup message
        message = MessageModel(
            phase=SessionPhase.PlanningPhase,
            round_idx=0,
            msg_type=MessageType.ObserveRegion,
            payload={
                "region_id": "test_region"
            }
        )
        
        response = self.dispatcher.dispatch(
            message=message, 
            sim_context=simulation, 
            sending_player=simulation.players[0]
        )

        available_regions = ""
        for region_id in simulation.get_player_regions(simulation.players[0]):
            available_regions += f"{region_id}, "
        available_regions = available_regions[:-2]
        
        self.assertEqual(
            response,
            {
                "error": True,
                "desc": f"Region with region_id:test_region does not exist.",
                "details": f"Available regions: {available_regions}."
            }
        )

    def test_observe_region_authority_error(self):
        # Preparing simulation
        simulation = prepare_simulation()
        
        simulation.board.regions["Dalaran"].owner = simulation.players[1]

        region = simulation.board.get_region_by_coord(0, 0, 0)
        
        # Preparing mockup message
        message = MessageModel(
            phase=SessionPhase.PlanningPhase,
            round_idx=0,
            msg_type=MessageType.ObserveRegion,
            payload={
                "region_id": region.region_id
            }
        )
        
        response = self.dispatcher.dispatch(
            message=message, 
            sim_context=simulation, 
            sending_player=simulation.players[0]
        )
        
        self.assertEqual(
            response,
            {
                "error": True,
                "desc": f"You are not the owner of the region with region_id:{region.region_id}.",
                "details": f"Available regions: {str(simulation.get_player_regions(simulation.players[0]))}"
            }
        )

    def test_get_players(self):
        # Preparing simulation
        simulation = prepare_simulation()
        
        simulation.board.regions["Dalaran"].owner = simulation.players[0]
        
        # Preparing mockup message
        message = MessageModel(
            phase=SessionPhase.PlanningPhase,
            round_idx=0,
            msg_type=MessageType.GetPlayers,
            payload={}
        )
        
        response = self.dispatcher.dispatch(
            message=message, 
            sim_context=simulation, 
            sending_player=simulation.players[0]
        )
        
        self.assertEqual(
            response['players_list'],
            simulation.players
        )

    def test_get_regions(self):
        # Preparing simulation
        simulation = prepare_simulation()
        
        simulation.board.regions["Dalaran"].owner = simulation.players[0]

        # Preparing mockup message
        message = MessageModel(
            phase=SessionPhase.PlanningPhase,
            round_idx=0,
            msg_type=MessageType.GetRegions,
            payload={}
        )
        
        response = self.dispatcher.dispatch(
            message=message, 
            sim_context=simulation, 
            sending_player=simulation.players[0]
        )
        
        self.assertEqual(
            response['regions_list'],
            simulation.get_player_regions(simulation.players[0])
        )

    def test_get_units(self):
        # Preparing simulation
        simulation = prepare_simulation()
        
        simulation.board.regions["Dalaran"].owner = simulation.players[0]

        # Preparing mockup message
        message = MessageModel(
            phase=SessionPhase.PlanningPhase,
            round_idx=0,
            msg_type=MessageType.GetUnits,
            payload={}
        )
        
        response = self.dispatcher.dispatch(
            message=message, 
            sim_context=simulation, 
            sending_player=simulation.players[0]
        )
        
        self.assertEqual(
            response['units_list'],
            simulation.get_player_units(simulation.players[0])
        )

    def test_get_unit_details(self):
        # Preparing simulation
        simulation = prepare_simulation()
        
        simulation.board.regions["Dalaran"].owner = simulation.players[0]

        simulation.add_unit(
            "light_infantry",
            simulation.players[0],
            0, 0, 0
        )

        unit = simulation.board.get_tile_by_coord(0, 0, 0).unit

        # Preparing mockup message
        message = MessageModel(
            phase=SessionPhase.PlanningPhase,
            round_idx=0,
            msg_type=MessageType.GetUnitDetails,
            payload={
                "unit_id": unit.unit_id
            }
        )
        
        response = self.dispatcher.dispatch(
            message=message, 
            sim_context=simulation, 
            sending_player=simulation.players[0]
        )
        
        self.assertEqual(
            response,
            {
                "unit_id": unit.unit_id,
                "owner": unit.owner,
                "coord": f"{unit.tile.q},{unit.tile.r},{unit.tile.s}",
                "movement": unit.movement,
                "upkeep": unit.upkeep,
                "strength": unit.strength
            }
        )

    def test_get_unit_details_faithfulness_error(self):
        # Preparing simulation
        simulation = prepare_simulation()
        
        simulation.board.regions["Dalaran"].owner = simulation.players[0]

        simulation.add_unit(
            "light_infantry",
            simulation.players[0],
            0, 0, 0
        )

        unit = simulation.board.get_tile_by_coord(0, 0, 0).unit
        
        # Preparing mockup message
        message = MessageModel(
            phase=SessionPhase.PlanningPhase,
            round_idx=0,
            msg_type=MessageType.GetUnitDetails,
            payload={
                "unit_id": "test_unit"
            }
        )
        
        response = self.dispatcher.dispatch(
            message=message, 
            sim_context=simulation, 
            sending_player=simulation.players[0]
        )

        available_units = ""
        for unit_id in simulation.units.keys():
            available_units += f"{unit_id}, "
        available_units = available_units[:-2]
        
        self.assertEqual(
            response,
            {
                "error": True,
                "desc": f"Unit with unit_id:test_unit does not exist.",
                "details": f"Available units: {available_units}."
            }
        )

    def test_get_region_details(self):
        # Preparing simulation
        simulation = prepare_simulation()
        
        simulation.board.regions["Dalaran"].owner = simulation.players[0]

        region = simulation.board.get_region_by_coord(0, 0, 0)

        # Preparing mockup message
        message = MessageModel(
            phase=SessionPhase.PlanningPhase,
            round_idx=0,
            msg_type=MessageType.GetRegionDetails,
            payload={
                "region_id": region.region_id
            }
        )
        
        response = self.dispatcher.dispatch(
            message=message, 
            sim_context=simulation, 
            sending_player=simulation.players[0]
        )
        
        self.assertEqual(
            response,
            {
                "region_id": region.region_id,
                "owner": region.owner,
                "command_center_coord": f"{region.command_centre[0]},{region.command_centre[1]},{region.command_centre[2]}",
                "region_upkeep": region.region_upkeep,
                "size": len(region.tiles),
                "neighbour_regions": simulation.board.get_neighbouring_region_ids(region)
            }
        )

    def test_get_region_details_faithfulness_error(self):
        # Preparing simulation
        simulation = prepare_simulation()
        
        simulation.board.regions["Dalaran"].owner = simulation.players[0]
        
        # Preparing mockup message
        message = MessageModel(
            phase=SessionPhase.PlanningPhase,
            round_idx=0,
            msg_type=MessageType.GetRegionDetails,
            payload={
                "region_id": "test_region"
            }
        )
        
        response = self.dispatcher.dispatch(
            message=message, 
            sim_context=simulation, 
            sending_player=simulation.players[0]
        )

        available_regions = ""
        for region_id in simulation.get_player_regions(simulation.players[0]):
            available_regions += f"{region_id}, "
        available_regions = available_regions[:-2]
        
        self.assertEqual(
            response,
            {
                "error": True,
                "desc": f"Region with region_id:test_region does not exist.",
                "details": f"Available regions: {available_regions}."
            }
        )

    def test_issue_orders(self):
        # Preparing simulation
        simulation = prepare_simulation()
        
        simulation.board.regions["Dalaran"].owner = simulation.players[0]

        simulation.add_unit(
            "light_infantry",
            simulation.players[0],
            0, 0, 0
        )

        unit = simulation.board.get_tile_by_coord(0, 0, 0).unit

        orders = [
            Order(
                order_type='move',
                unit_id=unit.unit_id,
                move_q=0,
                move_r=-1,
                move_s=1
            )
        ]

        # Preparing mockup message
        message = MessageModel(
            phase=SessionPhase.PlanningPhase,
            round_idx=0,
            msg_type=MessageType.IssueOrders,
            payload={
                "orders": orders
            }
        )
        
        self.dispatcher.dispatch(
            message=message, 
            sim_context=simulation, 
            sending_player=simulation.players[0]
        )

        print(orders)
        print(simulation.players_orders.get(simulation.players[0]))
        
        self.assertEqual(
            simulation.players_orders.get(simulation.players[0])[0],
            orders
        )

    def test_recruitment_choice(self):
        # Preparing simulation
        simulation = prepare_simulation()
        
        simulation.board.regions["Dalaran"].owner = simulation.players[0]

        recruitment_choices = [
            RecruitmentChoice(
                unit_type='light_infantry',
                region='Dalaran'
            )
        ]

        # Preparing mockup message
        message = MessageModel(
            phase=SessionPhase.UpkeepPhase,
            round_idx=0,
            msg_type=MessageType.RecruitUnits,
            payload={
                "recruitment": recruitment_choices
            }
        )
        
        self.dispatcher.dispatch(
            message=message, 
            sim_context=simulation, 
            sending_player=simulation.players[0]
        )
        
        self.assertEqual(
            simulation.unit_requests.get(simulation.players[0]),
            recruitment_choices
        )

def prepare_unit_tile_observation(unit, tiles: list[Tile], simulation):
    observations = {}
    for tile in tiles:
        unit_tile = unit.tile
        tile_region = simulation.board.get_region_by_coord(tile.q, tile.r, tile.s)
    
        rel_q = unit_tile.q - tile.q
        rel_r = unit_tile.r - tile.r
        rel_s =  unit_tile.s - tile.s
        distance = calc_distance(unit_tile.q, unit_tile.r, unit_tile.s, tile.q, tile.r, tile.s)
        unit_id = unit.unit_id if tile.unit is not None else "Empty"
        owner = tile_region.owner
        region = tile_region.region_id
        is_command_center = True if tile_region.command_centre == (tile.q, tile.r, tile.s) else False

        coord_key = f"{rel_q},{rel_r},{rel_s}"
    
        observations[coord_key] = {
            "rel_coord": str(coord_key),
            "distance": str(distance),
            "unit": str(unit_id),
            "owner": str(owner),
            "region": str(region),
            "is_command_center": str(is_command_center)
        }
    
    response = ObserveUnitResponse(observations=observations)
    return response.model_dump()

def prepare_region_tile_observation(region, observed_tiles: list[Tile]):
    command_centre_q, command_centre_r, command_centre_s = region.command_centre

    observations = {}
    for tile in observed_tiles.values():
        rel_q = command_centre_q - tile.q
        rel_r = command_centre_r - tile.r
        rel_s =  command_centre_s - tile.s

        distance = calc_distance(command_centre_q, command_centre_r, command_centre_s, tile.q, tile.r, tile.s)
        unit_id = tile.unit.unit_id if tile.unit is not None else "Empty"
        owner = region.owner
        is_command_center = True if (command_centre_q, command_centre_r, command_centre_s) == (tile.q, tile.r, tile.s) else False

        coord_key = f"{rel_q},{rel_r},{rel_s}"
    
        observations[coord_key] = {
            "rel_coord": str(coord_key),
            "distance": str(distance),
            "unit": str(unit_id),
            "owner": str(owner), 
            "region": str(region.region_id),
            "is_command_center": str(is_command_center)
        }

    response = ObserveRegionResponse(observations=observations)
    return response.model_dump()

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