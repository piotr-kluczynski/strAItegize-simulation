import os
import json

from registering.observer_abstracts import Observer
from registering.simulation_notification import SimulationNotification
from registering.log_record import LogRecord

class LogObserver(Observer):
    def __init__(self, session_id: str, dir_name="logs"):
        filepath = os.path.join(os.getcwd(), dir_name, f"{session_id}.json")
        self.file = open(filepath, "w+")
        self.logs = []

        self.log_count = 0
        self.round_count = 0

        # Creating log entry to append to later
        json_data = {"log": []}
        json.dump(json_data, self.file, indent=4)

    def read_log(self) -> dict:
        self.file.seek(0)
        return json.load(self.file)

    def overwrite_log(self) -> None:
        json_data = self.read_log()

        json_data["log"].extend(self.logs)

        self.file.seek(0)
        json.dump(json_data, self.file, indent=4)
        self.file.truncate()

    def update(self, notification: SimulationNotification) -> None:
        log_id = f"{self.round_count}_{self.log_count}.json" # [round]_[log_num]
        json_dict = None

        if notification["category"] == "ROUND_START":
            self.log_count = 0
            self.round_count += 1

            json_dict = {
                log_id: LogRecord(
                    log_type="Simulation",
                    log_msg=f"Round {self.round_count} starts."
                )
            }
        elif notification["category"] == "ROUND_END":
            json_dict = {
                log_id: LogRecord(
                    log_type="Simulation",
                    log_msg=f"Round {self.round_count} ends."
                )
            }
            self.logs.append(json_dict)

            #print(f"Json data: {json_dict}")
            #print(f"File: {self.file}")

            self.overwrite_log()

            self.logs = []
        elif notification["category"] == "PLAYER_STATUS_CHANGE":
            json_dict = {
                log_id: LogRecord(
                    log_type="Simulation",
                    log_msg=f"Status of the player {notification['player_id']} changed: {notification['old_player_status']} -> {notification['new_player_status']}.",
                    metadata={
                        "player_id": notification["player_id"],
                        "old_player_status": notification["old_player_status"],
                        "new_player_status": notification["new_player_status"]
                    }
                )
            }
        elif notification["category"] == "UNIT_RECRUITED":
            json_dict = {
                log_id: LogRecord(
                    log_type="Simulation",
                    log_msg=f"Player {notification['player_id']} recruited unit: {notification['unit_id']}.",
                    metadata={
                        "player_id": notification["player_id"],
                        "unit_id": notification["unit_id"]
                    }
                )
            }
        elif notification["category"] == "UNIT_DESTROYED":
            json_dict = {
                log_id: LogRecord(
                    log_type="Simulation",
                    log_msg=f"{notification['player_id']}'s unit: {notification['unit_id']} was destroyed.",
                    metadata={
                        "player_id": notification["player_id"],
                        "unit_id": notification["unit_id"]
                    }
                )
            }
        elif notification["category"] == "ATTACK_OUTCOME":
            log_msg = "" 
            if notification["combat_outcome"] == "defeat": 
                log_msg = f"{notification["unit_id"]}'s attack on {notification["target_id"]} was repelled."
            elif notification["combat_outcome"] == "victory":
                log_msg = f"{notification["unit_id"]}'s attack on {notification["target_id"]} was successful."
            elif notification["combat_outcome"] == "obliteration":
                log_msg = f"{notification["unit_id"]}'s attack on {notification["target_id"]} obliterated the defenders."

            json_dict = {
                log_id: LogRecord(
                    log_type="Simulation",
                    log_msg=log_msg,
                    metadata={
                        "unit_id": notification["unit_id"],
                        "target_id": notification["target_id"],
                        "combat_outcome": notification["combat_outcome"]
                    }
                )
            }
        elif notification["category"] == "REGION_GAINED":
            json_dict = {
                log_id: LogRecord(
                    log_type="Simulation",
                    log_msg=f"Player {notification['player_id']} gained control over {notification["region_id"]} region.",
                    metadata={
                        "player_id": notification["player_id"],
                        "region_id": notification["region_id"]
                    }
                )
            }
        elif notification["category"] == "REGION_LOST":
            json_dict = {
                log_id: LogRecord(
                    log_type="Simulation",
                    log_msg=f"Player {notification['player_id']} lost control over {notification["region_id"]} region.",
                    metadata={
                        "player_id": notification["player_id"],
                        "region_id": notification["region_id"]
                    }
                )
            }
        elif notification["category"] == "UNIT_MOVED":
            json_dict = {
                log_id: LogRecord(
                    log_type="Simulation",
                    log_msg=f"Unit {notification["unit_id"]} moved from ({notification["old_q"]},{notification["old_r"]},{notification["old_s"]}) to ({notification["new_q"]},{notification["new_r"]},{notification["new_s"]}).",
                    metadata={
                        "unit_id": notification["unit_id"],
                        "old_q": notification["old_q"],
                        "old_r": notification["old_r"],
                        "old_s": notification["old_s"],
                        "new_q": notification["new_q"],
                        "new_r": notification["new_r"],                        
                        "new_s": notification["new_s"],
                    }
                )
            }

        if json_dict is not None:
            self.logs.append(json_dict)
            self.log_count += 1
        