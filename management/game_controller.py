import os
import uuid
import time
import threading

from communication.communication_context import CommunicationContext
from management.game_loader import GameLoader

class GameController:
    def __init__(self, scenario):
        # Generating unique session identifier
        self.session_id = {uuid.uuid1()}

        self.game_loader = GameLoader()
        self.scenario = scenario
        self.players = self.game_loader.get_players(scenario)

        self.simulation = None

        self.communication = CommunicationContext()
        self.communication.start_session(self.players)


    def create_lobby(self):
        comms_thread = threading.Thread(
                target=self.communication.wait_for_players,
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

        # Initialize simulation
        self.communication.start_simulation(
            players=self.simulation.players,
            regions=[region_id for region_id in self.simulation.board.regions.keys()],
            neighbouring_regions=self.simulation.get_neighbouring_regions(),
            final_round=self.simulation.max_round,
            is_start_upkeep=self.simulation.is_upkeep_round()
        )

    def start_simulation(self):
        simulation_active = True

        while simulation_active:
            # Execute Upkeep phase if necessary
            if self.simulation.is_upkeep_round():
                players_surplus = self.simulation.get_players_surplus()
                players = list(players_surplus.keys())

                players_regions = {
                    player: self.simulation.get_player_regions(player)
                    for player in players
                }

                self.communication.execute_upkeep(
                    players=players,
                    players_supplies=players_surplus,
                    players_regions=players_regions
                )

            # Start new round
            simulation_active = self.simulation.start_round()

            round_data = self.simulation.get_round_data()
            self.communication.start_round(
                current_round=round_data["current_round"],
                final_round=round_data["final_round"],
                players=round_data["players"],
                leaderboard=round_data["leaderboard"],
                units=round_data["units"],
                regions=round_data["regions"],
                tresspasers=round_data["tresspasers"],
                events=round_data["events"]
            )

            # End round
            self.simulation.end_round()

            self.communication.end_round(self.simulation.is_upkeep_round())

            # Resetting observer to remove outdated events
            self.simulation.reset_player_events()

    def end_simulation(self):
        # Inform players that the simulation has ended
        self.communication.end_simulation()