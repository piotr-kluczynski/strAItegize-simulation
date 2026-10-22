import importlib

from communication.session_state import SessionState

from strAItegize_common.communication.message_model import MessageModel
from strAItegize_common.communication.message_types import MessageType
from strAItegize_common.communication.session_phases import SessionPhase

class LobbyState(SessionState):
    @property
    def session_phase(self) -> SessionPhase:
        return SessionPhase.LobbyPhase

    def handle_start_simulation(self, players, regions, neighbouring_regions, final_round, is_start_upkeep):
        # Caching data for potential resend operation
        self._sim_init_data = {
            "players": players,
            "regions": regions,
            "neighbouring_regions": neighbouring_regions,
            "final_round": final_round,
            "is_start_upkeep": is_start_upkeep
        }
        
        # Sending simulation start data to each player
        for player in players:
            self._send_simulation_init(target_player=player)

        # Awaiting each player's acknowledgment before proceeding
        ack_players = set()
        expected_players = set(players)

        ack_timeout = None #60.0

        while ack_players != expected_players:
            sender, received_msg = self.context.get_next_message(timeout=ack_timeout)

            # Timeout expired
            if sender is None and received_msg is None:
                missing_players = expected_players - ack_players

                print(f"[{self.session_phase}] Acknowldegment timeout. Missing response from {missing_players}")
                for player in missing_players:
                    self.context.drop_player(player)

                continue

            # Player disconnected (detected by message_receiver in communication_context)
            if received_msg is None:
                print(f"[{self.session_phase}] Player disconnected while waiting for the acknowledgment.")

                expected_players.discard(sender)
                self.context.drop_player(sender)

                continue


            if received_msg.msg_type == MessageType.Acknowledge:
                if sender not in ack_players:
                    ack_players.add(sender)
            else:
                print(f"[{self.name}] Incorrect {sender} message received.")

        # After each player confirmed the simulation initialization, we change state
        if is_start_upkeep:
            self.context.transition_to(upkeep_state.UpkeepState(self.context))
        else:
            self.context.transition_to(planning_state.PlanningState(self.context))


    def resend_state(self, player: str):
        self._send_simulation_init(player)
        
    def _send_simulation_init(self, target_player: str):
        message = MessageModel(
            phase=self.session_phase,
            round_idx=self.context.get_current_round(),
            msg_type=MessageType.StartSimulation,
            payload={
                "your_id": target_player,
                **self._sim_init_data
            }
        )
        
        self.context.send_to_player(player=target_player, msg=message)

upkeep_state = importlib.import_module("communication.upkeep_state")
planning_state = importlib.import_module("communication.planning_state")
