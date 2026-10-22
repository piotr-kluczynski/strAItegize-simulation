import os
import uuid
import datetime

from management.game_controller import GameController
from registering.observer_abstracts import Observer
from registering.simulation_notification import SimulationNotification
from management.game_loader import GameLoader

class SaverObserver(Observer):
    def __init__(self, game_controller: GameController, dir_name="saves"):
        self.game_loader = GameLoader(dir_name)
        self.game_controller = game_controller

        self.session_dir = os.path.join(os.getcwd(), dir_name, str(self.game_controller.session_id))
        os.makedirs(self.session_dir, exist_ok=True)

    def update(self, notification: SimulationNotification) -> None:
        if notification['category'] == "ROUND_END":
            # Creating unique snapshot id
            x = datetime.datetime.now()
            snapshot_id = f"{x.strftime("%d-%m-%Y")}_{x.strftime("%H-%M-%S")}_{uuid.uuid1()}"

            self.game_loader.save_game(self.game_controller.simulation, os.path.join(self.session_dir, snapshot_id))