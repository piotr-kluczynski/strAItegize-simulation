import socket
import select

from concurrent.futures import ThreadPoolExecutor, as_completed

from .handlers import dispatcher
from shared.communication.transport import receive_message, send_message

class Communication:
    def __init__(self, players):
        self.players = players
        self.player_sockets = {}
        self.player_ports = {}
        self.player_connections = {}
        self.player_addresses = {}

        self.simulation = None

        for player_id in players:
            self.player_sockets[player_id] = socket.socket(
                socket.AF_INET,
                socket.SOCK_STREAM
            )

            self.player_ports[player_id] = None
            self.player_connections[player_id] = None
            self.player_addresses[player_id] = None

    def get_connected_players(self):
        return [player for player, connection in self.player_connections.items()
                if connection is not None]

    def set_simulation_object(self, simulation):
        self.simulation = simulation

    def initialize_sockets(self):
        for player in self.players:
            sock = self.player_sockets[player]

            sock.setsockopt(
                socket.SOL_SOCKET,
                socket.SO_REUSEADDR,
                1
            )

            # Letting OS choose a free port
            sock.bind(("127.0.0.1", 0))

            # Save the port chosen by the OS
            self.player_ports[player] = sock.getsockname()[1]

            # Start listening
            sock.listen()

            print(
                f"{player} listening on "
                f"127.0.0.1:{self.player_ports[player]}"
            )

    def wait_for_players_to_join(self):
        listening_sockets = list(self.player_sockets.values())
        connection_sockets = []

        while None in self.player_connections.values():
            sockets_to_monitor = (listening_sockets + connection_sockets)
            readable, _, _ = select.select(sockets_to_monitor, [], [])

            for sock in readable:
                # New connections

                if sock in listening_sockets:

                    connection, address = sock.accept()

                    player = next(
                        player
                        for player, player_sock
                        in self.player_sockets.items()
                        if player_sock is sock
                    )

                    self.player_connections[player] = connection
                    self.player_addresses[player] = address

                    connection_sockets.append(connection)

                    print(
                        f"[COMM] {player} connected from {address}"
                    )

                # Existing connections
                else:
                    try:
                        data = sock.recv(1024)
                        # recv() == b'' means client disconnected
                        if not data:

                            player = next(
                                player
                                for player, connection
                                in self.player_connections.items()
                                if connection is sock
                            )

                            print(
                                f"[COMM] {player} disconnected"
                            )

                            sock.close()

                            connection_sockets.remove(sock)

                            self.player_connections[player] = None
                            self.player_addresses[player] = None

                    except socket.error as e:
                        print(
                            f"[COMM] Socket error: {e}"
                        )

    def execute_for_all(self, recipents, function, *args, operation_name="Function", **kwargs):
        results = {}

        with ThreadPoolExecutor(max_workers=len(recipents)) as executor:
            futures = {
                executor.submit(
                    function,
                    recipent,
                    *args,
                    **kwargs
                ): recipent for recipent in recipents
            }

            for future in as_completed(futures):
                recipent = futures[future]

                try:
                    results[recipent] = future.result()

                    if results[recipent]:
                        print(f"[SIMULATION] {operation_name} executed sucessfully for {recipent}")
                    else:
                        print(f"[SIMULATION] {operation_name} failed during execution for {recipent}")
                except Exception as e:
                    print(f"[SIMULATON] Exception has occurred while executing {operation_name} for {recipent}: {e}")
                    results[recipent] = False

            return all(results.values())

    def wait_for_readiness(self, target_player, timeout=30):
        self.player_connections[target_player].settimeout(timeout)

        while True:
            try:
                message = receive_message(self.player_connections[target_player])
            except socket.timeout:
                print("Agent readiness timeout")
                return False

            if message is None:
                return False

            message_type = message.get("type")

            if message["type"] == "READY":
                print("Agent ready")
                return True
            elif message["type"] == "ERROR":
                print(message["payload"].get("error"))
                return False
            else:
                print(f"Unexpected message: {message_type}")

    def initialize_simulation(self, target_player, players, regions, neighbouring_regions, max_round):
        message = {
            "type": "INIT_SIMULATION",
            "payload": {
                "your_id": target_player,
                "players": players,
                "regions": regions,
                "neighbouring_regions": neighbouring_regions,
                "max_round": max_round
            }
        }

        send_message(
            self.player_connections[target_player],
            message
        )
        return True

    def initialize_round(self, target_player, current_round, final_round, players, leaderboard_dict, controlled_units, controlled_regions, enemy_units_per_region, event_dict):
        message = {
            "type": "INIT_ROUND",
            "payload": {
                "current_round": current_round,
                "final_round": final_round,
                "players": players,
                "leaderboard_dict": leaderboard_dict,
                "controlled_units": controlled_units[target_player],
                "controlled_regions": controlled_regions[target_player],
                "enemy_units_per_region": enemy_units_per_region[target_player],
                "event_dict": event_dict[target_player]
            }
        }

        send_message(
            self.player_connections[target_player],
            message
        )
        return True

    def execute_upkeep_phase(self, players):
        recruitment_choices = {}

        for player in players:
            supplies = self.simulation.calculate_supplies(player)

            if supplies > 0:
                message = {
                    "type": "EXECUTE_UPKEEP",
                    "payload": {
                        "supply_surplus": supplies,
                        "regions": self.simulation.get_player_regions(player)
                    }
                }

                send_message(
                    self.player_connections[player],
                    message   
                )

                # Receiving the response
                message = receive_message(self.player_connections[player])
                    
                if message is None:
                    print(f"No message received while waiting for {player} unit recruitment choice.")
                    return None

                message_type = message.get("type")

                if message["type"] == "RECRUITMENT_CHOICE":
                    print("Agent send their recruitment choice.")
                    recruitment_choices[player] = message["payload"].get("recruitment", [])
                elif message["type"] == "ERROR":
                    print(message["payload"].get("error"))
                    return None
                else:
                    print(f"Unexpected message: {message_type}")

        return recruitment_choices

    def listen_for_tool_calls(self, target_player):
        conn = self.player_connections[target_player]

        while True:
            try:
                message = receive_message(conn)
                print(message)
                if message is None:
                    print(f"[COMM] Connection lost with {target_player}")
                    return False

                response = dispatcher.dispatch(message, self.simulation, target_player)

                send_message(conn, response)

                if message.get("type") == "ISSUE_ORDERS" and response.get("type") != "ERROR":
                    print(f"[SIMULATION] Player {target_player} has finished their turn.")
                    return True
            except Exception as e:
                print(f"[COMM] Error handling requests for {target_player}: {e}")
                return False

    def finalize_round(self, target_player):
        message = {
            "type": "FIN_ROUND",
            "payload": {}
        }

        send_message(
            self.player_connections[target_player],
            message
        )
        return True

    def finalize_simulation(self, target_player):
        message = {
            "type": "FIN_SESSION",
            "payload": {}
        }

        send_message(
            self.player_connections[target_player],
            message
        )

        return True

    def reset_connection_timeout(self):
        for player_connection in self.player_connections.values():
            player_connection.settimeout(None)
            