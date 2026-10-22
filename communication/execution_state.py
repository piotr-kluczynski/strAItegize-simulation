import importlib

from communication.session_state import SessionState

from strAItegize_common.communication.session_phases import SessionPhase
from strAItegize_common.communication.message_model import MessageModel
from strAItegize_common.communication.message_types import MessageType

class ExecutionState(SessionState):
    @property
    def session_phase(self) -> SessionPhase:
        return SessionPhase.ExecutionPHase

    def handle_end_round(self, is_next_round_upkeep: bool):
        # Caching data for potential resend operation
        self.end_round_data = {
            "is_next_round_upkeep": is_next_round_upkeep
        }

        # Messaging each player about phase change
        message = MessageModel(
            phase=self.session_phase,
            round_idx=self.context.get_current_round(),
            msg_type=MessageType.EndRound,
            payload={
                "is_next_round_upkeep": is_next_round_upkeep
            }
        )

        self.context.broadcast(
            msg=message,
            players=self.context.get_connected_players()
        )

        # Transitioning to the next phase
        if is_next_round_upkeep:
            self.context.transition_to(upkeep_state.UpkeepState(self.context))
        else:
            self.context.transition_to(planning_state.PlanningState(self.context))

    def handle_end_simulation(self):
        message = MessageModel(
            phase=self.session_phase,
            round_idx=self.context.get_current_round(),
            msg_type=MessageType.EndSimulation,
            payload={}
        )

        self.context.broadcast(
            msg=message,
            players=self.context.get_connected_players()
        )

    def resend_state(self, player):
        self._send_round_end(target_player=player)

    def _send_round_end(self, target_player: str):
        message = MessageModel(
            phase=self.session_phase,
            round_idx=self.context.get_current_round(),
            msg_type=MessageType.EndRound,
            payload=self.end_round_data
        )

        self.context.send_to_player(player=target_player, msg=message)

upkeep_state = importlib.import_module("communication.upkeep_state")
planning_state = importlib.import_module("communication.planning_state")