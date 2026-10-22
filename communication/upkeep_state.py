import importlib

from .handlers import dispatcher
from communication.session_state import SessionState

from strAItegize_common.communication.session_phases import SessionPhase
from strAItegize_common.communication.message_model import MessageModel
from strAItegize_common.communication.message_types import MessageType

class UpkeepState(SessionState):
    @property
    def session_phase(self) -> SessionPhase:
        return SessionPhase.UpkeepPhase

    def handle_upkeep(self, players: list[str], players_supplies: dict[str, int], players_regions: dict[str, list[str]]):
        # Caching data for potential resend operation
        self._upkeep_data = {
            "players_supplies": players_supplies,
            "players_regions": players_regions
        }
        
        # Sending upkeep information to all players
        for player in players:
            self._send_upkeep(target_player=player)

        # Awaiting each player's requests (stopping when each provides recruitment choices)
        done_players = set()
        expected_players = set(players)

        response_timeout = None #120.0

        while done_players != expected_players:
            sender, received_msg = self.context.get_next_message(timeout=response_timeout)

            # 1. Timeout expired
            if sender is None and received_msg is None:
                missing_players = expected_players - done_players

                print(f"[{self.session_phase}] Acknowldegment timeout. Missing response from {missing_players}. Submitting empty recruitment choices.")
                for player in missing_players:
                    # Submitting empty message
                    empty_msg = MessageModel(
                        phase=self.session_phase,
                        round_idx=self.context.get_current_round(),
                        msg_type=MessageType.RecruitUnits,
                        payload={
                            "recruitment": []
                        }
                    )
                    
                    dispatcher.dispatch(
                        message=empty_msg,
                        sim_context=self.context.simulation,
                        sending_player=player
                    )

                    # Sending an information about timeout to the user
                    error_msg = MessageModel(
                        phase=self.session_phase,
                        round_idx=self.context.get_current_round(),
                        msg_type=MessageType.Error,
                        payload={
                            "desc": f"No orders were received within {response_timeout} seconds, and in consequence no orders were given to your units.",
                            "details": ""
                        }
                    )

                    self.context.send_to_player(player, error_msg)
                    done_players.add(sender)
                continue

            # 2. Player disconnected
            if received_msg is None:
                print(f"[{self.session_phase}] Player disconnected while waiting for the response.")

                expected_players.discard(sender)
                self.context.drop_player(sender)

                continue

            # 3. Player send correct message
            response = dispatcher.dispatch(
                message=received_msg,
                sim_context=self.context.simulation,
                sending_player=sender
            )

            msg_type = MessageType.ToolResponse
            payload = response

            # Sending back the error if such occurred
            if response.get("error"):
                msg_type = MessageType.Error
                payload = {
                    "desc": response["desc"],
                    "details": response.get("details")
                }

            message = MessageModel(
                phase=self.session_phase,
                round_idx=self.context.get_current_round(),
                msg_type=msg_type,
                payload=payload
            )

            self.context.send_to_player(player, message)

            # Marking player as done if they have submitted recruit orders
            if received_msg.msg_type == MessageType.RecruitUnits and not response.get("error"):
                done_players.add(sender)

            '''
            if received_msg.msg_type == MessageType.RecruitUnits:
                if sender not in done_players:
                    try:
                        response = dispatcher.dispatch(
                            message=received_msg,
                            sim_context=self.context.simulation,
                            sending_player=sender
                        )

                        msg_type = MessageType.ToolResponse
                        payload = response
                        if response.get("error"):
                            msg_type = MessageType.Error
                            payload = {
                                "desc": response["desc"],
                                "details": response.get("details")
                            }

                        message = MessageModel(
                            phase=self.session_phase,
                            round_idx=self.context.get_current_round(),
                            msg_type=msg_type,
                            payload=payload
                        )

                        self.context.send_to_player(player, message)
                        done_players.add(sender)
                    except Exception as e:
                        print(f"[{self.name}] An error has occurred while adding {sender}'s recruitment choice: {e}.")
                else:
                    print(f"[{self.name}] Player {sender} already sent their recruitment choice. New recruitment choices are ignored.")
            else:
                try:
                    response = dispatcher.dispatch(
                        message=received_msg,
                        sim_context=self.context.simulation,
                        sending_player=sender
                    )
                        
                    msg_type = MessageType.ToolResponse
                    payload = response
                    if response.get("error"):
                        msg_type = MessageType.Error
                        payload = {
                            "desc": response["desc"],
                            "details": response.get("details")
                        }

                    message = MessageModel(
                        phase=self.session_phase,
                        round_idx=self.context.get_current_round(),
                        msg_type=msg_type,
                        payload=payload
                    )

                    self.context.send_to_player(player, message)
                except Exception as e:
                    print(f"[{self.name}] An error has occurred while serving {sender}'s request: {e}.")
            '''
                    
        # Transitioning to the next state
        self.context.transition_to(planning_state.PlanningState(context=self.context))

    def _send_upkeep(self, target_player: str):
        message = MessageModel(
            phase=self.session_phase,
            round_idx=self.context.get_current_round(),
            msg_type=MessageType.Upkeep,
            payload={
                "supply_surplus": self._upkeep_data["players_supplies"][target_player],
                "regions": self._upkeep_data["players_regions"][target_player],
            }
        )
        
        self.context.send_to_player(player=target_player, msg=message)

planning_state = importlib.import_module("communication.planning_state")