from typing import Callable, Dict, Any
from pydantic import ValidationError

from strAItegize_common.communication.message_model import MessageModel

class CommandDispatcher:
    def __init__(self):
        self._handlers: Dict[str, Callable] = {}

    def register(self, message_type: str):
        def decorator(func: Callable):
            self._handlers[message_type] = func
            return func

        return decorator

    def dispatch(self, message: MessageModel, sim_context: Any, sending_player: str) -> dict:
        message_type = message.msg_type
        payload = message.payload

        handler = self._handlers.get(message_type)
        if not handler:
            return {
                "error": True,
                "desc": f"Unrecognized message type: {message_type}.",
                "details": ""
            }

        try:
            response_payload = handler(payload, sim_context, sending_player)

            return response_payload
        except ValidationError as e:
            return {
                "error": True,
                "desc": "Invalid input data provided.", 
                "details": e.errors()
            }
        except Exception as e:
            return {
                "error": True,
                "desc": f"Internal error has occurred: {str(e)}",
                "details": ""
            }