from communication.dispatcher import CommandDispatcher

from strAItegize_common.communication.models import ObserveUnitRequest, ObserveUnitResponse
from strAItegize_common.communication.models import ObserveRegionRequest, ObserveRegionResponse
from strAItegize_common.communication.models import GetUnitsRequest, GetUnitsResponse
from strAItegize_common.communication.models import GetRegionsRequest, GetRegionsResponse
from strAItegize_common.communication.models import GetUnitDetailsRequest, GetUnitDetailsResponse
from strAItegize_common.communication.models import GetRegionDetailsRequest, GetRegionDetailsResponse
from strAItegize_common.communication.models import GetPlayersRequest, GetPlayersResponse
from strAItegize_common.communication.models import IssueOrdersReuqest, IssueOrdersResponse
from strAItegize_common.communication.models import RecruitmentChoiceRequest, RecruitmentChoiceResponse
from strAItegize_common.communication.models import ErrorResponse

from simulation.simulation import PlayerStatus
from simulation.utils import calc_distance

dispatcher = CommandDispatcher()

@dispatcher.register("OBSERVE_UNIT")
def handle_observe_unit(payload: dict, simulation, player: str) -> dict:
    req = ObserveUnitRequest.model_validate(payload)

    # Verifying whether the data exist in simulation - reality check
    if simulation.units.get(req.unit_id) is None:
        response = ErrorResponse(
            desc=f"Unit with unit_id:{req.unit_id} does not exist.",
            details=f"Available units:{str(simulation.get_player_units(player))}"
        )
        return response.model_dump()

    # Get unit observation, prepare data to send
    observed_tiles = simulation.observe_unit(req.unit_id)
    
    # Generating payload data based on the observed tiles
    observations = {}

    # Verifying whether the player can access this data - authority check
    unit = simulation.units.get(req.unit_id)

    if unit.owner != player:
        available_units = ""
        for unit_id in simulation.get_player_units(player):
            available_units += f"{unit_id}, "
        available_units = available_units[:-2]

        response = ErrorResponse(
            desc=f"You are not the owner of the unit with unit_id:{req.unit_id}.",
            details=f"Available units:{available_units}."
        )
        return response.model_dump()
    
    for tile in observed_tiles:
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

@dispatcher.register("OBSERVE_REGION")
def handle_observe_region(payload: dict, simulation, player: str) -> dict:
    req = ObserveRegionRequest.model_validate(payload)

    # Verifying whether the data exist in simulation - reality check
    if simulation.board.regions.get(req.region_id) is None:
        available_regions = ""
        for region_id in simulation.get_player_regions(player):
            available_regions += f"{region_id}, "
        available_regions = available_regions[:-2]

        response = ErrorResponse(
            desc=f"Region with region_id:{req.region_id} does not exist.",
            details=f"Available regions: {available_regions}."
        )
        return response.model_dump()

    # Verifying whether the player can access this data - authority check
    if simulation.board.regions.get(req.region_id).owner != player:
        response = ErrorResponse(
            desc=f"You are not the owner of the region with region_id:{req.region_id}.",
            details=f"Available regions: {str(simulation.get_player_regions(player))}"
        )
        return response.model_dump()

    observed_tiles = simulation.observe_region(req.region_id)
    region = simulation.board.regions.get(req.region_id)
    
    # Generating payload data based on the observed tiles
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
            "region": str(req.region_id),
            "is_command_center": str(is_command_center)
        }

    response = ObserveRegionResponse(observations=observations)
    return response.model_dump()

@dispatcher.register("GET_UNITS")
def handle_get_units(payload: dict, simulation, player: str) -> dict:
    req = GetUnitsRequest.model_validate(payload)

    response = GetUnitsResponse(units_list=simulation.get_player_units(player))
    return response.model_dump()

@dispatcher.register("GET_REGIONS")
def handle_get_regions(payload: dict, simulation, player: str) -> dict:
    req = GetRegionsRequest.model_validate(payload)

    response = GetRegionsResponse(regions_list=simulation.get_player_regions(player))
    return response.model_dump()

@dispatcher.register("GET_UNIT_DETAILS")
def handle_get_units_details(payload: dict, simulation, player: str) -> dict:
    req = GetUnitDetailsRequest.model_validate(payload)

    # Verifying whether the data exist in simulation - reality check
    if simulation.units.get(req.unit_id) is None:
        available_units = ""
        for unit_id in simulation.units.keys():
            available_units += f"{unit_id}, "
        available_units = available_units[:-2]

        response = ErrorResponse(
            desc=f"Unit with unit_id:{req.unit_id} does not exist.",
            details=f"Available units: {available_units}."
        )
        return response.model_dump()

    unit = simulation.units.get(req.unit_id)

    response = GetUnitDetailsResponse(
        unit_id=unit.unit_id,
        owner=unit.owner,
        coord=f"{unit.tile.q},{unit.tile.r},{unit.tile.s}",
        movement=unit.movement,
        upkeep=unit.upkeep,
        strength=unit.strength
    )
    return response.model_dump()

@dispatcher.register("GET_REGION_DETAILS")
def handle_get_regions_details(payload: dict, simulation, player: str) -> dict:
    req = GetRegionDetailsRequest.model_validate(payload)

    # Verifying whether the data exist in simulation - reality check
    if simulation.board.regions.get(req.region_id) is None:
        available_regions = ""
        for region_id in simulation.get_player_regions(player):
            available_regions += f"{region_id}, "
        available_regions = available_regions[:-2]

        response = ErrorResponse(
            desc=f"Region with region_id:{req.region_id} does not exist.",
            details=f"Available regions: {available_regions}."
        )
        return response.model_dump()

    region = simulation.board.regions.get(req.region_id)

    response = GetRegionDetailsResponse(
        region_id=region.region_id,
        owner=region.owner,
        region_upkeep=region.region_upkeep,
        command_center_coord=f"{region.command_centre[0]},{region.command_centre[1]},{region.command_centre[2]}",
        size=len(region.tiles),
        neighbour_regions=simulation.board.get_neighbouring_region_ids(region)
    )
    return response.model_dump()

@dispatcher.register("GET_PLAYERS")
def handle_get_players(payload: dict, simulation, player: str) -> dict:
    req = GetPlayersRequest.model_validate(payload)

    players_list = [player for player in simulation.players if simulation.players_status[player] is not PlayerStatus.LOST]

    response = GetPlayersResponse(
        players_list=players_list
    )
    return response.model_dump()

@dispatcher.register("ISSUE_ORDERS")
def handle_issue_orders(payload: dict, simulation, player: str) -> dict:
    req = IssueOrdersReuqest.model_validate(payload)
    orders = req.orders

    # Trying to add the received orders to the player within the simulation
    try:
        simulation.add_player_orders(player, orders)
    except Exception as e:
        response = ErrorResponse(
            desc=str(e),
            details=""
        )
        return response.model_dump()

    response = IssueOrdersResponse()
    return response.model_dump()

@dispatcher.register("RECRUIT_UNITS")
def handle_recruitment_choice(payload: dict, simulation, player: str) -> dict:
    req = RecruitmentChoiceRequest.model_validate(payload)

    simulation.unit_requests[player] = req.recruitment 

    response = RecruitmentChoiceResponse()
    return response.model_dump()