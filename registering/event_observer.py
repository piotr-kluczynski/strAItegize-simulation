from registering.observer_abstracts import Observer
from registering.simulation_notification import SimulationNotification

class EventObserver(Observer):
    def __init__(self, game_controller):
        self.game_controller = game_controller

    def update(self, notification: SimulationNotification) -> None:
        if notification['category'] == "PLAYER_STATUS_CHANGE":
            for player in self.game_controller.players:
                self.game_controller.simulation.players_events[player].append(f"The status of player {notification['player_id']} changed from {notification['old_player_status']} to {notification['new_player_status']}.")
        elif notification['category'] == "UNIT_RECRUITED":
            self.game_controller.simulation.players_events[notification['player_id']].append(f"New unit {notification['unit_id']} was recruited and awaits orders.")
        elif notification['category'] == "UNIT_DESTROYED":
            self.game_controller.simulation.players_events[notification['player_id']].append(f"Unit {notification['unit_id']} was destroyed.")
        elif notification['category'] == "ATTACK_OUTCOME":
            if notification['combat_outcome'] == "defeat":
                self.game_controller.simulation.players_events[notification['player_id']].append(f"Your {notification['unit_id']} unit's attack was repelled by {notification['target_id']} unit.")
            elif notification['combat_outcome'] == "victory":
                self.game_controller.simulation.players_events[notification['player_id']].append(f"Your {notification['unit_id']} unit's attack defeated the {notification['target_id']} unit and forced it to retreat.")
            elif notification['combat_outcome'] == "obliteration":
                self.game_controller.simulation.players_events[notification['player_id']].append(f"Your {notification['unit_id']} unit's attack obliterated the {notification['target_id']} unit, destroying it.")
        elif notification['category'] == "DEFEND_OUTCOME":
            if notification['combat_outcome'] == "defeat":
                self.game_controller.simulation.players_events[notification['player_id']].append(f"An attack by the enemy unit {notification['target_id']} broke through the defenses of your unit {notification['unit_id']} and forced it to retreat.")
            elif notification['combat_outcome'] == "victory":
                self.game_controller.simulation.players_events[notification['player_id']].append(f"An attack by enemy unit {notification['target_id']} on your unit {notification['unit_id']} was repelled.")
            elif notification['combat_outcome'] == "obliteration":
                self.game_controller.simulation.players_events[notification['player_id']].append(f"Your {notification['unit_id']} unit was destroyed as a result of an attack by the {notification['target_id']} unit.")
        elif notification['category'] == "REGION_GAINED":
            self.game_controller.simulation.players_events[notification['player_id']].append(f"You gained control over the region of {notification['region_id']}.")
        elif notification['category'] == "REGION_LOST":
            self.game_controller.simulation.players_events[notification['player_id']].append(f"You lost control over the region of {notification['region_id']}.")
        elif notification['category'] == "ROUND_START":
            for player in self.game_controller.simulation.players_events.keys():
                self.game_controller.simulation.players_events[player] = []
        elif notification['category'] == "MOVE_BLOCKED":
            self.game_controller.simulation.players_events[notification['player_id']].append(f"Your movement order for unit: {notification['unit_id']} from tile ({notification['new_q']}, {notification['new_r']}, {notification['new_s']}) to tile: ({notification['old_q']}, {notification['old_r']}, {notification['old_s']}) was blocked.")
        elif notification['category'] == "ATTACK_BLOCKED":
            self.game_controller.simulation.players_events[notification['player_id']].append(f"Your attack order for unit: {notification['unit_id']} at unit: {notification['target_id']} was blocked.")
        elif notification['category'] == "SUPPORT_BLOCKED":
            self.game_controller.simulation.players_events[notification['player_id']].append(f"Your support order for unit: {notification['unit_id']} at unit: {notification['target_id']} was blocked.")
        elif notification['category'] == "DEFEND_BLOCKED":
            self.game_controller.simulation.players_events[notification['player_id']].append(f"Your defend order for unit: {notification['unit_id']} at unit: {notification['target_id']} was blocked.")
        elif notification['category'] == "UNIT_DISBANDED":
            self.game_controller.simulation.players_events[notification['player_id']].append(f"Your unit: {notification['unit_id']} was disbanded as result of low supplies.")
        elif notification['category'] == "RECRUITMENT_BLOCKED":
            self.game_controller.simulation.players_events[notification['player_id']].append(f"Your recruitment order at tile: ({notification['new_q']}, {notification['new_r']}, {notification['new_s']}) was blocked.")
        elif notification['category'] == "UNIT_MOVED":
            self.game_controller.simulation.players_events[notification['player_id']].append(f"Your unit: {notification['unit_id']} moved from tile: {notification['unit_id']} from tile ({notification['old_q']}, {notification['old_r']}, {notification['old_s']}) to tile: ({notification['new_q']}, {notification['new_r']}, {notification['new_s']}).")



