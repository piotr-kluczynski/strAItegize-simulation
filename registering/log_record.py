from typing import TypedDict, Literal, Optional

class LogRecord(TypedDict):
    log_type: Literal["Error", "Simulation"]
    log_msg: str
    metadata: Optional[dict]