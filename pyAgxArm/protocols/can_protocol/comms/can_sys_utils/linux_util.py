from .base_util import CanSystemInfoBase
import subprocess
import os

class LinuxSocketCanSystemInfo(CanSystemInfoBase):
    
    @staticmethod
    def is_exists(channel):
        return os.path.exists(f"/sys/class/net/{channel}")

    @staticmethod
    def is_up(channel):
        with open(f"/sys/class/net/{channel}/operstate", "r") as f:
            return f.read().strip() == "up"

    def get_bitrate(channel):
        result = subprocess.run(['ip', '-details', 'link', 'show', channel],
                                    stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                                    universal_newlines=True, check=True)  # Python 3.6
        output = result.stdout
        for line in output.split('\n'):
            if 'bitrate' in line:
                return int(line.split('bitrate ')[1].split(' ')[0])

    @staticmethod
    def get_available_can_channel() -> list:
        '''
        获取系统中所有可用的 CAN 端口。
        '''
        '''
        Get all available CAN ports in the system.
        '''
        import os
        can_ports = []
        for item in os.listdir('/sys/class/net/'):
            if 'can' in item:
                can_ports.append(item)
        return can_ports
    
    @staticmethod
    def get_can_channel_info(channel: str) -> str:
        '''
        获取指定 CAN 端口的详细信息，包括状态、类型和比特率。
        '''
        '''
        Get detailed information about the specified CAN port, including status, type, and bit rate.
        '''
        try:
            with open(f"/sys/class/net/{channel}/operstate", "r") as file:
                state = file.read().strip()
            with open(f"/sys/class/net/{channel}/type", "r") as file:
                port_type = file.read().strip()
            return f"CAN port {channel}: State={state}, Type={port_type}"
        except FileNotFoundError:
            return f"CAN port {channel} not found."
