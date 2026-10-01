from typing import Literal, Optional

from registering.notification import Notification

class SimulationNotification(Notification):
    category: Literal["PLAYER_STATUS_CHANGE", "UNIT_RECRUITED", "UNIT_DESTROYED", "ATTACK_OUTCOME", "DEFEND_OUTCOME", "REGION_GAINED", "REGION_LOST", "ROUND_START", "ROUND_END", "UNIT_MOVED"]

    player_id: Optional[str]
    old_player_status: Optional[Literal["Active", "Exiled", "Lost"]]
    new_player_status: Optional[Literal["Active", "Exiled", "Lost"]]

    unit_id: Optional[str]

    region_id: Optional[str]

    combat_outcome: Optional[Literal["victory", "defeat", "obliteration"]]
    target_id: Optional[str]

    old_q: Optional[int]
    old_r: Optional[int]
    old_s: Optional[int]

    new_q: Optional[int]
    new_r: Optional[int]
    new_s: Optional[int]