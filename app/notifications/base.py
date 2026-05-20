from abc import ABC, abstractmethod


class NotificationChannel(ABC):
    name: str

    @abstractmethod
    async def send(self, payload: dict[str, object]) -> None:
        raise NotImplementedError
