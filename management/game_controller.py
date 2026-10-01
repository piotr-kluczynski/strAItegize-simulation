import os
import sys
import uuid
import time
import threading

from simulation.simulation import PlayerStatus
from communication.communication import Communication
from management.game_loader import GameLoader

class GameController:
    def __init__(self, scenario):
        # Generating unique session identifier
        self.session_id = {uuid.uuid1()}

        self.game_loader = GameLoader()
        self.scenario = scenario
        self.players = self.game_loader.get_players(scenario)

        self.simulation = None

        self.communication = Communication(self.players)
        self.communication.initialize_sockets()

    def create_lobby(self):
        comms_thread = threading.Thread(
                target=self.communication.wait_for_players_to_join,
                daemon=True
        )
        comms_thread.start()
        
        # Waiting for players to connect via socket
        while len(self.communication.get_connected_players()) < len(self.players):
            connected = self.communication.get_connected_players()
        
            os.system('cls')
        
            print("===== STRAITEGIZE LOBBY =====\n")
        
            for player in self.communication.players:
                port = self.communication.player_ports[player]
        
                if player in connected:
                    print(f"[PORT:{port}] [CONNECTED] {player}")
                else:
                    print(f"[PORT:{port}] [  EMPTY  ] {player}")
        
            time.sleep(1)

        print("All players connected!")

    def initialize_simulation(self, observers):
        self.simulation = self.game_loader.load_game(self.scenario)

        # Registering observers
        for observer in observers:
            self.simulation.simulation_publisher.subscribe(observer)

        self.communication.set_simulation_object(simulation=self.simulation)

        # Wait for all players to signal readiness
        session_init_result = self.communication.execute_for_all(
            recipents=self.simulation.players,
            function=self.communication.wait_for_readiness,
            operation_name="Readiness Check"
        )

        if not session_init_result:
            print("Some players have encountered an error while preparing for simulation!\r\nClosing the simulation")
            sys.exit()

        # Initialize simulation on all players
        sim_init_result = self.communication.execute_for_all(
            recipents=self.simulation.players,
            function=self.communication.initialize_simulation,
            players=self.simulation.players,
            regions=[region_id for region_id in self.simulation.board.regions.keys()],
            neighbouring_regions=self.simulation.get_neighbouring_regions(), 
            max_round=self.simulation.max_round,
            operation_name="Session Initialization"
        )

        if not sim_init_result:
            print("A simulation could not have been initialized properly!\r\nClosing the simulation.")
            sys.exit()

    def start_simulation(self):
        current_round = 1
        simulation_active = True

        while simulation_active:
            # Awaiting player readiness for a new round
            round_ready_result = self.communication.execute_for_all(
                recipents=[player for player, status in self.simulation.players_status.items() if status != PlayerStatus.LOST],
                function=self.communication.wait_for_readiness,
                operation_name="Readiness Check"
            )

            if not round_ready_result:
                print("Some players have encountered an error while preparing for new round!\r\nClosing the simulation.")
                sys.exit()

            self.communication.reset_connection_timeout()

            # Executing the upkeep phase if necessary
            recruitment_choices = None
            if self.simulation.is_upkeep_round():
                recruitment_choices = self.communication.execute_upkeep_phase([player for player, status in self.simulation.players_status.items() if status != PlayerStatus.LOST])

                if recruitment_choices is None:
                    print("Some players have encountered an error while choosing which units to recruit.\r\nClosing the simulation.")
                    sys.exit()

                self.communication.reset_connection_timeout()

            # Starting new round within the simulation
            simulation_active = self.simulation.start_round(recruitment_choices)
            self.communication.reset_connection_timeout()

            # Sending new round data
            round_data = self.simulation.get_round_data()

            round_init_result = self.communication.execute_for_all(
                recipents=[player for player, status in self.simulation.players_status.items() if status != PlayerStatus.LOST],
                function=self.communication.initialize_round,
                **round_data,
                operation_name="Round Initialization"
            )
            self.communication.reset_connection_timeout()

            # Serving data requests of all active players
            round_end_result = self.communication.execute_for_all(
                recipents=[player_id for player_id, status in self.simulation.players_status.items() if status != PlayerStatus.LOST],
                function=self.communication.listen_for_tool_calls,
                operation_name="Listening for tool calls"
            )
            self.communication.reset_connection_timeout()

            # Inform all players that the round ended and await their confirmation
            round_fin_result = self.communication.execute_for_all(
                recipents=[player for player, status in self.simulation.players_status.items() if status != PlayerStatus.LOST],
                function=self.communication.finalize_round,
                operation_name="Round Finalization"
            )
            self.communication.reset_connection_timeout()

            # Ending current round within the simulation
            self.simulation.end_round()

            # Resetting observer to remove outdated events
            self.event_observer.reset_events()

    def end_simulation(self):
        # Inform players that the simulation has ended
        self.communication.execute_for_all(
            recipents=[player for player, status in self.simulation.players_status.items() if status != PlayerStatus.LOST],
            function=self.communication.finalize_simulation,
            operation_name="Session Finalization"
        )
        self.communication.reset_connection_timeout()