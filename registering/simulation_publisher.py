
from registering.observer_abstracts import Publisher
from registering.simulation_notification import SimulationNotification

class SimulationPublisher(Publisher):
    def __init__(self):
        self.observers = []

    def subscribe(self, observer):
        self.observers.append(observer)

    def unsubscribe(self, observer):
        self.observers.remove(observer)

    def notify(self, notification: SimulationNotification):
        for observer in self.observers:
            observer.update(notification)