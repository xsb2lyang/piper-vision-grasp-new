from abc import ABC, abstractmethod
from typing import Any, Callable

class CommInterface(ABC):

    @abstractmethod
    def connect(self, **kwargs) -> None:
        ...
    
    @abstractmethod
    def is_connected(self) -> bool:
        ...

    @abstractmethod
    def close(self) -> None:
        ...

    @abstractmethod
    def is_stopped(self):
        ...
    
    @abstractmethod
    def get_status(self):
        ...

    @abstractmethod
    def get_config(self):
        ...

    @abstractmethod
    def get_type(self):
        ...
    
    @abstractmethod
    def get_channel(self):
        ...

    @abstractmethod
    def send(self, data: Any, **kwargs) -> Any:
        ...

    @abstractmethod
    def recv(self, **kwargs) -> Any:
        ...

    @abstractmethod
    def set_callback(self, cb: Callable[[Any, "CommInterface"], None]) -> None:
        ...
    
    @abstractmethod
    def get_callback(self) -> Callable[[Any, "CommInterface"], None]:
        ...

    @abstractmethod
    def clear_callback(self) -> None:
        ...
    
    @abstractmethod
    def has_callback(self) -> bool:
        ...
