from management.game_controller import GameController

from registering.event_observer import EventObserver
from registering.saver_observer import SaverObserver
from registering.log_observer import LogObserver

# Input parameters which will be later given through the console
LOG_SESSION = True
REGISTER_SESSION = True
SCENARIO = "hello_conquest"

if __name__ == '__main__':
    print("Welcome to the \"StrAItegize\" - Your own, local simulation for experimenting on Mulit-Agent Systems!")

    # Choosing simulation scenario
    game_controller = GameController(SCENARIO)

    game_controller.create_lobby()
    input("Press enter to begin the simulation:\r\n")

    # Registering observers based on app parameters
    observers = [
        EventObserver(game_controller)
    ]

    if LOG_SESSION:
        observers.append(
            LogObserver(session_id=game_controller.session_id)
        )
    if REGISTER_SESSION:
        observers.append(
            SaverObserver(game_controller)
        )

    game_controller.initialize_simulation(observers)
    game_controller.start_simulation()
    game_controller.end_simulation()