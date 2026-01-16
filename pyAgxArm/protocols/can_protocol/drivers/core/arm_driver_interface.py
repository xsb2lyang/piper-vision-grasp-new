from abc import ABC, abstractmethod

class ArmDriverInterface(ABC):

    @abstractmethod
    def get_instance(self):
        ...

    @abstractmethod
    def get_driver_version(self):
        ...
    
    @abstractmethod
    def create_comm(self):
        ...

    @abstractmethod
    def connect(self, **kwargs) -> None:
        ...
    
    @abstractmethod
    def is_connected(self) -> bool:
        ...
    
    @abstractmethod
    def is_ok(self) -> bool:
        ...

    @abstractmethod
    def get_fps(self):
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
    def get_joint_states(self):
        ...

    @abstractmethod
    def get_ee_pose(self):
        ...

    @abstractmethod
    def get_arm_status(self):
        ...

    @abstractmethod
    def get_driver_states(self):
        ...
    
    @abstractmethod
    def get_motor_states(self):
        ...

    @abstractmethod
    def enable(self):
        ...

    @abstractmethod
    def disable(self):
        ...

    @abstractmethod
    def reset(self):
        ...

    @abstractmethod
    def electronic_emergency_stop(self):
        ...
