import os
import argparse

from management.game_controller import GameController

from registering.event_observer import EventObserver
from registering.saver_observer import SaverObserver
from registering.log_observer import LogObserver

# Loading up and verifying the available simulation scenarios
available_scenarios = []

path = f"{os.path.abspath(os.getcwd())}//scenarios"
dir_list = os.listdir(path)
file_list = [entry for entry in dir_list if os.path.isfile(path+'/'+entry)]

for file in file_list:
    if file.endswith(".json"):
        available_scenarios.append(file[:-5])

# Setting up app console line parameters
parser = argparse.ArgumentParser(prog="StrAItegize - Simulation")

parser.add_argument("-s", "--scenario", help="Simulation scenario to load for this session.", choices=available_scenarios, type=str, required=True)
parser.add_argument("-t", "--response_timeout", help="Number of seconds, after which players will be forced to end their round.", type=int, default=180, required=False)
parser.add_argument("-l", "--log_session", help="Whether the session events should be saved to the corresponding json file.", type=bool, default=True, required=False)
parser.add_argument("-r", "--register_session", help="Whether the session state should be saved at the end of each round to the json files.", type=bool, default=True, required=False)

args = parser.parse_args()

if __name__ == '__main__':
    print("Welcome to the \"StrAItegize\" - Your own, local simulation for experimenting on Mulit-Agent Systems!")

    # Choosing simulation scenario
    game_controller = GameController(args.scenario)

    game_controller.create_lobby()

    # Registering observers based on app parameters
    observers = [
        EventObserver(game_controller)
    ]

    if args.log_session:
        observers.append(
            LogObserver(session_id=game_controller.session_id)
        )
    if args.register_session:
        observers.append(
            SaverObserver(game_controller)
        )

    game_controller.initialize_simulation(observers)
    game_controller.start_simulation()
    game_controller.end_simulation()