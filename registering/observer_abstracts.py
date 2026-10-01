from __future__ import annotations
from abc import ABC, abstractmethod
from registering.notification import Notification

class Publisher(ABC):
    @abstractmethod
    def subscribe(self, observer: Observer) -> None:
        pass

    @abstractmethod
    def unsubscribe(self, observer: Observer) -> None:
        pass

    @abstractmethod
    def notify(self, notification: Notification) -> None:
        pass

class Observer(ABC):
    @abstractmethod
    def update(self, notification: Notification) -> None:
        pass