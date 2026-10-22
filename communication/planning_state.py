import importlib

from .handlers import dispatcher
from communication.session_state import SessionState

from strAItegize_common.communication.session_phases import SessionPhase
from strAItegize_common.communication.message_model import MessageModel
from strAItegize_common.communication.message_types import MessageType

class PlanningState(SessionState):
    @property
    def session_phase(self) -> SessionPhase:
        return SessionPhase.PlanningPhase

    def handle_start_round(self, current_round: int, final_round: int, players: list[str], leaderboard: dict[str, int], units: dict[str, list[str]], regions: dict[str, list[str]], tresspasers: dict[str, dict[str, list[str]]], events: dict[str, list[str]]):
        # Caching data for potential resend operation
        self._start_round_data = {
            "current_round": current_round,
            "final_round": final_round,
            "players": players,
            "leaderboard": leaderboard,
            "units": units,
            "regions": regions,
            "tresspasers": tresspasers,
            "events": events
        }
                
        # Sending round data to all players
        for player in players:
            self._send_round_init(target_player=player)

        # Awaiting each player's requests (stopping when each provides the orders to execute)
        done_players = set()
        expected_players = set(players)

        response_timeout = None #120.0

        while done_players != expected_players:
            sender, received_msg = self.context.get_next_message(timeout=response_timeout)

            # 1. Timeout expired
            if sender is None and received_msg is None:
                missing_players = expected_players - done_players

                print(f"[{self.session_phase}] Acknowldegment timeout. Missing response from {missing_players}. Submitting empty orders.")
                for player in missing_players:
                    # Submitting empty message
                    empty_msg = MessageModel(
                        phase=self.session_phase,
                        round_idx=self.context.get_current_round(),
                        msg_type=MessageType.IssueOrders,
                        payload={
                            "orders": []
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

            self.context.send_to_player(sender, message)

            # Marking player as done if they have submitted orders
            if received_msg.msg_type == MessageType.IssueOrders and not response.get("error"):
                done_players.add(sender)

            '''
            if received_msg.msg_type == MessageType.IssueOrders:
                if sender not in done_players:
                    try:
                        # Handling the issue orders message using dispatcher
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

                        self.context.send_to_player(sender, message)

                        # Adding player as done if there were no errors
                        if not response.get("error"):
                            done_players.add(sender)
                    except Exception as e:
                        print(f"[{self.name}] An error has occurred while adding {sender}'s orders: {e}.")
                else:
                    print(f"[{self.name}] Player {sender} already sent their orders. New orders are ignored.")
            else:
                # Handling
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
                '''

        # After each player submitted orders to their units, the session tranistions to the ExecutionState
        self.context.transition_to(execution_state.ExecutionState(context=self.context))

    def resend_state(self, player: str):
        self._send_round_init(player)

    def _send_round_init(self, target_player: str):
        message = MessageModel(
            phase=self.session_phase,
            round_idx=self.context.get_current_round(),
            msg_type=MessageType.StartRound,
            payload={
                "current_round": self._start_round_data["current_round"],
                "final_round": self._start_round_data["final_round"],
                "players": self._start_round_data["players"],
                "leaderboard": self._start_round_data["leaderboard"],
                "units": self._start_round_data["units"][target_player],
                "regions": self._start_round_data["regions"][target_player],
                "tresspasers": self._start_round_data["tresspasers"][target_player],
                "events": self._start_round_data["events"][target_player]
            }
        )
        
        self.context.send_to_player(player=target_player, msg=message)

execution_state = importlib.import_module("communication.execution_state")