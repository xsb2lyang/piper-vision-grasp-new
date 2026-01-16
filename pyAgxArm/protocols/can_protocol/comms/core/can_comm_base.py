from .comm_abstract import CommAbstract
from can.message import Message
from typing import Optional

class CanCommBase(CommAbstract):
    def __init__(self):
        super().__init__()
        self._config = {}
        self._type = ""
        self._channel = ""
        self._is_connected = False
        self._is_stopped = False
    
    def connect(self, **kwargs) -> bool:
        raise NotImplementedError

    def is_connected(self) -> bool:
        return self._is_connected

    def close(self) -> None:
        raise NotImplementedError

    def is_stopped(self) -> bool:
        return self._is_stopped
    
    def get_status(self) -> None:
        raise NotImplementedError

    def get_config(self) -> dict:
        return self._config.copy()
    
    def get_type(self) -> str:
        return self._type

    def get_channel(self) -> str:
        return self._channel
    
    def send(self, Message:Message, **kwargs) -> None:
        raise NotImplementedError

    def recv(self, **kwargs) -> Optional[Message]:
        raise NotImplementedError