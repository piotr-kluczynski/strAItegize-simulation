from abc import ABC

from typing import Optional

from strAItegize_common.communication.message_model import MessageModel
from strAItegize_common.communication.session_phases import SessionPhase

class SessionState(ABC):
    def __init__(self, context):
        self.context = context
    
    @property
    def name(self) -> str:
        return self.__class__.__name__

    @property
    def session_phase(self) -> SessionPhase:
        return self.__class__.__session_phase__

    # Actions called from the simulation
    def handle_start_simulation(self, players: list[str], regions: list[str], neighbouring_regions: dict[str, list[str]], final_round: int, is_start_upkeep: bool):
        raise Exception(f"Cannot start simulation while in phase: {self.name}")

    def handle_end_simulation(self):
        raise Exception(f"Cannot end simulation while in phase: {self.name}")      

    def handle_start_round(self, current_round: int, final_round: int, players: list[str], leaderboard: dict[str, int], units: dict[str, list[str]], regions: dict[str, list[str]], tresspasers: dict[str, dict[str, list[str]]], events: dict[str, list[str]]):
        raise Exception(f"Cannot start round while in phase: {self.name}")   

    def handle_end_round(self, is_next_round_upkeep: bool):
        raise Exception(f"Cannot end round while in phase: {self.name}")

    def handle_upkeep(self, players: list[str], players_supplies: dict[str, int], players_regions: dict[str, list[str]]):
        raise Exception(f"Cannot execute upkeep while in phase: {self.name}")

    # Actions called from the network
    def handle_message(self, sender: str, msg: MessageModel) -> Optional[MessageModel]:
        msg = MessageModel.model_validate(msg)

        if msg.phase != self.session_phase:
            self.context.handle_state_mismatch(current_phase=self.session_phase, sender=sender, received_msg=msg)
            return None
        else:
            return msg

    def resend_state(self, player: str):
        pass