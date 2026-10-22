import socket
import select
import threading
import queue

from typing import Tuple

from simulation.simulation import PlayerStatus
from communication.lobby_state import LobbyState

from strAItegize_common.communication.transport import send_message, receive_message
from strAItegize_common.communication.message_model import MessageModel
from strAItegize_common.communication.message_types import MessageType
from strAItegize_common.communication.session_phases import SessionPhase

from communication.session_state import SessionState

class CommunicationContext:
    def __init__(self):
        self.players = []
        self.player_sockets = {}
        self.player_ports = {}
        self.player_connections = {}
        self.player_addresses = {}

        self.simulation_context = None

        self.state: SessionState = LobbyState(context=self)
        self.inbox = queue.Queue()

    # Methods for the states
    def transition_to(self, new_state: SessionState):
        print(f"[PHASE] Transition: {self.state.name} -> {new_state.name}")
        self.state = new_state

    def send_to_player(self, player: str, msg: MessageModel):
        conn = self.player_connections[player]
        send_message(conn, msg.model_dump())

    def broadcast(self, msg: MessageModel, players: list[str] = None):
        target_players = players or list(self.player_connections.keys())

        for player in target_players:
            self.send_to_player(player, msg)

    def drop_player(self, player: str):
        if player in self.player_connections:
            conn = self.player_connections[player]

            if conn:
                try:
                    conn.close()
                except Exception:
                    pass
            self.player_connections[player] = None

        if self.simulation:
            self.simulation.player_status[player] = PlayerStatus.LOST

        print(f"[COMM] Dropping player {player}.")

    def handle_state_mismatch(self, current_phase: SessionPhase, sender: str, received_msg: MessageModel):
        # Sending message to player to let them know to update their state
        self.send_to_player(
            sender,
            MessageModel(
                phase=current_phase,
                round_idx=self.get_current_round(),
                msg_type=MessageType.StateUpdate,
                payload={
                    "expected_phase": current_phase,
                    "desc": f"Cannot execute {received_msg.msg_type} type of request during {current_phase}."
                }
            )
        )

        # Sending additional message to allow them to proceed through new state properly
        self.state.resend_state(player=sender)
            

    # Inbox Access and Management
    def start_listening(self):
        for player, conn in self.player_connections.items():
            threading.Thread(
                target=self.message_receiver,
                args=(player, conn),
                daemon=True
            ).start()

    def message_receiver(self, player, conn):
        while True:
            try:
                raw_msg = receive_message(conn)
                if raw_msg is None: # Deal with empty messages
                    break

                self.inbox.put((player, raw_msg))
            except (ConnectionError, ConnectionResetError, socket.error):
                print(f"[COMM] Connection lost with player {player}")
                break
            except Exception as e:
                print(f"[COMM] Listener error for {player}: {e}")
                break

        try:
            conn.close()
        except Exception:
            pass
        self.player_connections[player] = None

        self.inbox.put((player, None))

    def get_next_message(self, timeout: float = None) -> Tuple[str, dict]:
        try:
            # Drawing data from the inbox
            sender, message = self.inbox.get(timeout=timeout)

            # Verifying the message validity
            message = self.state.handle_message(sender, message)
            if not message: 
                raise Exception

            return sender, message
        except queue.Empty:
            return None, None

    # High-level functions for other classes
    def start_session(self, players):
        self.players = players

        for player in players:
            self.player_sockets[player] = socket.socket(
                socket.AF_INET,
                socket.SOCK_STREAM
            )
            self.player_sockets[player].setsockopt(
                socket.SOL_SOCKET,
                socket.SO_KEEPALIVE,
                1
            )
            self.player_sockets[player].setsockopt(
                socket.SOL_SOCKET,
                socket.SO_REUSEADDR,
                1
            )

            # Letting OS choose a free port
            self.player_sockets[player].bind(("127.0.0.1", 0))

            # Save the port chosen by the OS
            self.player_ports[player] = self.player_sockets[player].getsockname()[1]

            # Start listening on the socket
            self.player_sockets[player].listen()
            
            # Initializing remaining dictionaries
            self.player_connections[player] = None
            self.player_addresses[player] = None

    def wait_for_players(self):
        listening_sockets = list(self.player_sockets.values())
        connection_sockets = []

        while None in self.player_connections.values():
            readable, _, _ = select.select(listening_sockets + connection_sockets, [], [])

            for sock in readable:
                if sock in listening_sockets:
                    conn, addr = sock.accept()
                    player = next(p for p, s in self.player_sockets.items() if s is sock)
                    
                    self.player_connections[player] = conn
                    self.player_addresses[player] = addr

                    connection_sockets.append(conn)

                    print(f"[COMM] {player} connected from {addr}")

        # Once everyone is connected, spin up receiver threads
        self.start_listening()

    def start_simulation(self, players: list[str], regions: list[str], neighbouring_regions: dict[str, list[str]], final_round: int, is_start_upkeep: bool):
        self.state.handle_start_simulation(
            players=players,
            regions=regions,
            neighbouring_regions=neighbouring_regions,
            final_round=final_round,
            is_start_upkeep=is_start_upkeep
        )

    def end_simulation(self):
        self.state.handle_end_simulation()

    def start_round(self, current_round: int, final_round: int, players: list[str], leaderboard: dict[str, int], units: dict[str, list[str]], regions: dict[str, list[str]], tresspasers: dict[str, dict[str, list[str]]], events: dict[str, list[str]]):
        self.state.handle_start_round(
            current_round=current_round,
            final_round=final_round,
            players=players,
            leaderboard=leaderboard,
            units=units,
            regions=regions,
            tresspasers=tresspasers,
            events=events
        )

    def end_round(self, is_next_round_upkeep: bool):
        self.state.handle_end_round(is_next_round_upkeep)

    def execute_upkeep(self, players: list[str], players_supplies: dict[str, int], players_regions: dict[str, list[str]]):
        self.state.handle_upkeep(
            players=players,
            players_supplies=players_supplies,
            players_regions=players_regions
        )

    # Others
    def set_simulation_object(self, simulation):
        self.simulation = simulation
    
    def get_connected_players(self):
        return [
            player 
            for player, connection 
            in self.player_connections.items()
            if connection is not None
        ]

    def get_current_round(self):
        return self.simulation.round
